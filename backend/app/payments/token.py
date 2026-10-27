"""PayPal OAuth2 token manager with automatic refresh.

WHY: PayPal sandbox access tokens expire after ~9 hours (32400s).
This module handles token acquisition and automatic refresh before expiry.
The token is never logged. A clock injectable makes testing deterministic
without sleeping or hitting the real API.

Credentials are read from environment variables only (P2, P6).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

import httpx


class Clock(Protocol):
    """Abstraction over time so tests can use a fake clock."""

    def now(self) -> float:
        """Return current time as a Unix timestamp."""
        ...


class SystemClock:
    """Real system clock."""

    def now(self) -> float:
        return time.time()


@dataclass(frozen=True)
class TokenResponse:
    """Parsed OAuth2 token response from PayPal."""

    access_token: str
    token_type: str
    expires_in: int
    acquired_at: float

    def is_expired(self, now: float, buffer_seconds: int = 300) -> bool:
        """Check if token is expired or about to expire.

        WHY buffer: We refresh 5 minutes early to avoid races where a token
        expires between the check and the API call.
        """
        return now >= (self.acquired_at + self.expires_in - buffer_seconds)


class PayPalTokenManager:
    """Manages PayPal OAuth2 client-credentials tokens with auto-refresh.

    The manager is intentionally NOT async because token refresh is a rare,
    fast call and simplicity wins (P8). Callers in async contexts can use
    asyncio.to_thread if needed.
    """

    TOKEN_ENDPOINT = "/v1/oauth2/token"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        base_url: str = "https://api-m.sandbox.paypal.com",
        clock: Clock | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not client_id or not client_secret:
            raise ValueError(
                "PayPal client_id and client_secret must be provided. "
                "Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET env vars."
            )
        self._client_id = client_id
        self._client_secret = client_secret
        self._base_url = base_url.rstrip("/")
        self._clock = clock or SystemClock()
        self._http = http_client or httpx.Client(timeout=30.0)
        self._token: TokenResponse | None = None

    def get_token(self) -> str:
        """Return a valid access token, refreshing if needed.

        Raises httpx.HTTPStatusError on auth failure.
        """
        if self._token is None or self._token.is_expired(self._clock.now()):
            self._refresh()
        assert self._token is not None
        return self._token.access_token

    def _refresh(self) -> None:
        """Fetch a new token from PayPal's OAuth2 endpoint."""
        now = self._clock.now()
        response = self._http.post(
            f"{self._base_url}{self.TOKEN_ENDPOINT}",
            data={"grant_type": "client_credentials"},
            auth=(self._client_id, self._client_secret),
            headers={"Accept": "application/json", "Accept-Language": "en_US"},
        )
        response.raise_for_status()
        body = response.json()
        self._token = TokenResponse(
            access_token=body["access_token"],
            token_type=body["token_type"],
            expires_in=int(body["expires_in"]),
            acquired_at=now,
        )

    def invalidate(self) -> None:
        """Force the next call to get_token() to refresh.

        WHY: Useful when a 401 is received, indicating the token was
        revoked server-side before our expected expiry.
        """
        self._token = None

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._http.close()
