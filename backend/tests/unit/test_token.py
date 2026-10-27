"""Tests for PayPal token manager with fake clock.

WHY: Phase 0 exit criterion requires token auto-refresh tested with a fake
clock. We verify: initial fetch, cache hit, auto-refresh on expiry,
buffer-before-expiry behaviour, invalidate(), and error handling.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from app.payments.token import PayPalTokenManager, TokenResponse

# ─── Fake clock ───


class FakeClock:
    """Clock whose time can be advanced manually for deterministic tests."""

    def __init__(self, start: float = 1_000_000.0) -> None:
        self._now = start

    def now(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


# ─── Fixtures ───

MOCK_BASE = "https://api-m.sandbox.paypal.com"
TOKEN_URL = f"{MOCK_BASE}/v1/oauth2/token"


def _token_response(token: str = "tok_123", expires_in: int = 32400) -> dict:
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "scope": "...",
        "nonce": "...",
    }


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(start=1_000_000.0)


@pytest.fixture
def mock_paypal():
    """Context manager that mocks PayPal HTTP calls via respx."""
    with respx.mock(base_url=MOCK_BASE) as router:
        yield router


# ─── TokenResponse unit tests ───


class TestTokenResponse:
    def test_not_expired_initially(self) -> None:
        tr = TokenResponse("tok", "Bearer", 3600, acquired_at=1000.0)
        assert not tr.is_expired(now=1000.0)

    def test_expired_after_full_lifetime(self) -> None:
        tr = TokenResponse("tok", "Bearer", 3600, acquired_at=1000.0)
        assert tr.is_expired(now=4600.0 + 1)

    def test_expired_within_buffer(self) -> None:
        """Token should be considered expired 5 min before actual expiry."""
        tr = TokenResponse("tok", "Bearer", 3600, acquired_at=0.0)
        # 3600 - 300 = 3300 seconds is the effective lifetime
        assert not tr.is_expired(now=3299.0)
        assert tr.is_expired(now=3300.0)

    def test_custom_buffer(self) -> None:
        tr = TokenResponse("tok", "Bearer", 3600, acquired_at=0.0)
        assert not tr.is_expired(now=3500.0, buffer_seconds=60)
        assert tr.is_expired(now=3540.0, buffer_seconds=60)


# ─── PayPalTokenManager tests ───


class TestPayPalTokenManager:
    def test_missing_credentials_raises(self) -> None:
        with pytest.raises(ValueError, match="client_id and client_secret"):
            PayPalTokenManager("", "secret")

        with pytest.raises(ValueError, match="client_id and client_secret"):
            PayPalTokenManager("id", "")

    def test_get_token_fetches_on_first_call(
        self, clock: FakeClock, mock_paypal: respx.MockRouter
    ) -> None:
        mock_paypal.post("/v1/oauth2/token").mock(
            return_value=httpx.Response(200, json=_token_response("first_token"))
        )
        mgr = PayPalTokenManager("client_id", "client_secret", MOCK_BASE, clock=clock)
        token = mgr.get_token()
        assert token == "first_token"

    def test_get_token_returns_cached(
        self, clock: FakeClock, mock_paypal: respx.MockRouter
    ) -> None:
        route = mock_paypal.post("/v1/oauth2/token").mock(
            return_value=httpx.Response(200, json=_token_response("cached"))
        )
        mgr = PayPalTokenManager("client_id", "client_secret", MOCK_BASE, clock=clock)
        mgr.get_token()
        clock.advance(100)  # well within the 32400s lifetime
        token = mgr.get_token()
        assert token == "cached"
        assert route.call_count == 1  # only one HTTP call

    def test_auto_refresh_after_expiry(
        self, clock: FakeClock, mock_paypal: respx.MockRouter
    ) -> None:
        """Token should auto-refresh when the fake clock passes expiry."""
        route = mock_paypal.post("/v1/oauth2/token").mock(
            side_effect=[
                httpx.Response(200, json=_token_response("old", expires_in=3600)),
                httpx.Response(200, json=_token_response("new", expires_in=3600)),
            ]
        )
        mgr = PayPalTokenManager("client_id", "client_secret", MOCK_BASE, clock=clock)

        first = mgr.get_token()
        assert first == "old"

        # Advance past expiry (3600 - 300 buffer = 3300s effective)
        clock.advance(3301)

        second = mgr.get_token()
        assert second == "new"
        assert route.call_count == 2

    def test_refresh_happens_within_buffer(
        self, clock: FakeClock, mock_paypal: respx.MockRouter
    ) -> None:
        """Refresh should happen 5 min before actual expiry, not after."""
        route = mock_paypal.post("/v1/oauth2/token").mock(
            side_effect=[
                httpx.Response(200, json=_token_response("old", expires_in=3600)),
                httpx.Response(200, json=_token_response("refreshed", expires_in=3600)),
            ]
        )
        mgr = PayPalTokenManager("client_id", "client_secret", MOCK_BASE, clock=clock)
        mgr.get_token()

        # At 3299s - should NOT refresh (buffer is 300s, so 3300 is the boundary)
        clock.advance(3299)
        token = mgr.get_token()
        assert token == "old"
        assert route.call_count == 1

        # At 3300s - should refresh
        clock.advance(1)
        token = mgr.get_token()
        assert token == "refreshed"
        assert route.call_count == 2

    def test_invalidate_forces_refresh(
        self, clock: FakeClock, mock_paypal: respx.MockRouter
    ) -> None:
        route = mock_paypal.post("/v1/oauth2/token").mock(
            side_effect=[
                httpx.Response(200, json=_token_response("a")),
                httpx.Response(200, json=_token_response("b")),
            ]
        )
        mgr = PayPalTokenManager("client_id", "client_secret", MOCK_BASE, clock=clock)
        assert mgr.get_token() == "a"
        mgr.invalidate()
        assert mgr.get_token() == "b"
        assert route.call_count == 2

    def test_auth_failure_raises(self, clock: FakeClock, mock_paypal: respx.MockRouter) -> None:
        mock_paypal.post("/v1/oauth2/token").mock(
            return_value=httpx.Response(401, json={"error": "invalid_client"})
        )
        mgr = PayPalTokenManager("client_id", "client_secret", MOCK_BASE, clock=clock)
        with pytest.raises(httpx.HTTPStatusError):
            mgr.get_token()


class TestHealthEndpoint:
    """Smoke test for the FastAPI app."""

    def test_health(self) -> None:
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
