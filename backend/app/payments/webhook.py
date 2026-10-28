"""PayPal Webhook receiver and cryptographic signature verification.

WHY:
As per SPEC.md Phase 2:
"optional webhook receiver with signature verification"
Ensures that async events from PayPal (payment completed, dispute opened, etc.)
are authentic and have not been spoofed or tampered with before triggering
audit logging or status updates.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.payments.token import PayPalTokenManager

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WebhookVerificationResult:
    """Result of webhook signature verification."""

    is_valid: bool
    status: str
    event_type: str | None = None
    event_id: str | None = None
    error_message: str | None = None


class PayPalWebhookVerifier:
    """Verifies incoming PayPal webhook notifications against PayPal API."""

    def __init__(
        self,
        token_manager: PayPalTokenManager,
        webhook_id: str,
        base_url: str = "https://api-m.sandbox.paypal.com",
        http_client: httpx.Client | None = None,
    ) -> None:
        self.token_manager = token_manager
        self.webhook_id = webhook_id
        self.base_url = base_url.rstrip("/")
        self._client = http_client

    def _get_client(self) -> httpx.Client:
        if self._client is not None:
            return self._client
        return httpx.Client(timeout=10.0)

    def verify(
        self,
        headers: dict[str, str],
        event_body: dict[str, Any],
    ) -> WebhookVerificationResult:
        """Verify the webhook signature via PayPal's verify-webhook-signature endpoint.

        Required headers (case-insensitive):
        - paypal-auth-algo
        - paypal-cert-url
        - paypal-transmission-id
        - paypal-transmission-sig
        - paypal-transmission-time
        """
        # Normalize headers to lowercase
        norm_headers = {k.lower(): v for k, v in headers.items()}

        auth_algo = norm_headers.get("paypal-auth-algo")
        cert_url = norm_headers.get("paypal-cert-url")
        transmission_id = norm_headers.get("paypal-transmission-id")
        transmission_sig = norm_headers.get("paypal-transmission-sig")
        transmission_time = norm_headers.get("paypal-transmission-time")

        if not all([auth_algo, cert_url, transmission_id, transmission_sig, transmission_time]):
            return WebhookVerificationResult(
                is_valid=False,
                status="MISSING_HEADERS",
                error_message="One or more required PayPal signature headers are missing.",
            )

        token = self.token_manager.get_token()
        url = f"{self.base_url}/v1/notifications/verify-webhook-signature"

        verification_payload = {
            "auth_algo": auth_algo,
            "cert_url": cert_url,
            "transmission_id": transmission_id,
            "transmission_sig": transmission_sig,
            "transmission_time": transmission_time,
            "webhook_id": self.webhook_id,
            "webhook_event": event_body,
        }

        req_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            client = self._get_client()
            resp = client.post(url, headers=req_headers, json=verification_payload)
            if resp.status_code == 200:
                body = resp.json()
                status = body.get("verification_status", "FAILURE")
                is_valid = status == "SUCCESS"
                event_type = event_body.get("event_type")
                event_id = event_body.get("id")

                return WebhookVerificationResult(
                    is_valid=is_valid,
                    status=status,
                    event_type=event_type,
                    event_id=event_id,
                )

            return WebhookVerificationResult(
                is_valid=False,
                status=f"HTTP_{resp.status_code}",
                error_message=f"PayPal API returned status {resp.status_code}: {resp.text[:200]}",
            )
        except Exception as exc:
            logger.error("Error verifying webhook signature: %s", exc)
            return WebhookVerificationResult(
                is_valid=False,
                status="ERROR",
                error_message=str(exc),
            )
