"""PayPal Orders v2 rail adapter.

WHY:
Orders v2 is the standard PayPal checkout rail.
While Orders require buyer approval in the browser for non-vaulted checkout,
this adapter allows agents to create structured orders, inspect order status,
and capture approved orders while enforcing Bouncer checks.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from app.mandate.models import PaymentRequest
from app.payments.paypal_payouts import format_minor_to_decimal_str
from app.payments.rail import (
    PaymentNotAllowedError,
    PaymentRail,
    PaymentResult,
    RailError,
    RailPaymentStatus,
    RailPermanentError,
)
from app.payments.token import PayPalTokenManager
from app.policy.verdict import Decision, Verdict

logger = logging.getLogger(__name__)


def map_paypal_order_status(order_status: str) -> RailPaymentStatus:
    """Map PayPal order status to RailPaymentStatus."""
    status = order_status.upper()
    if status == "COMPLETED":
        return RailPaymentStatus.SUCCESS
    if status in ("CREATED", "SAVED", "APPROVED", "PAYER_ACTION_REQUIRED"):
        return RailPaymentStatus.PENDING
    if status == "VOIDED":
        return RailPaymentStatus.FAILED
    return RailPaymentStatus.PENDING


class PayPalOrdersRail(PaymentRail):
    """Adapter for PayPal Orders v2 API."""

    def __init__(
        self,
        token_manager: PayPalTokenManager,
        base_url: str = "https://api-m.sandbox.paypal.com",
        http_client: httpx.Client | None = None,
    ) -> None:
        self.token_manager = token_manager
        self.base_url = base_url.rstrip("/")
        self._client = http_client

    def _get_client(self) -> httpx.Client:
        if self._client is not None:
            return self._client
        return httpx.Client(timeout=10.0)

    def execute_payment(
        self,
        request: PaymentRequest,
        decision: Decision,
    ) -> PaymentResult:
        """Create a PayPal Order for the given PaymentRequest if ALLOW.

        Returns a PaymentResult with status PENDING (until captured) or SUCCESS.
        """
        if decision.verdict != Verdict.ALLOW:
            raise PaymentNotAllowedError(
                f"Cannot create order on PayPal rail: Bouncer verdict is {decision.verdict.value}."
            )

        token = self.token_manager.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "PayPal-Request-Id": request.idempotency_key,
        }

        amount_str = format_minor_to_decimal_str(request.amount_minor, request.currency)

        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": request.request_id[:30],
                    "description": request.memo or f"Order for {request.purpose}",
                    "amount": {
                        "currency_code": request.currency.upper(),
                        "value": amount_str,
                    },
                    "payee": {
                        "email_address": request.payee.email.strip().lower(),
                    },
                }
            ],
        }

        client = self._get_client()
        url = f"{self.base_url}/v2/checkout/orders"

        resp = client.post(url, headers=headers, json=payload)
        if resp.status_code in (200, 201):
            body: dict[str, Any] = resp.json()
            order_id = body.get("id", "")
            raw_status = body.get("status", "CREATED")
            status = map_paypal_order_status(raw_status)

            return PaymentResult(
                status=status,
                rail_payment_id=order_id,
                idempotency_key=request.idempotency_key,
                amount_minor=request.amount_minor,
                currency=request.currency,
                payee_email=request.payee.email,
                raw_response=body,
                executed_at=datetime.now(UTC),
                fee_minor=0,
            )

        err_msg = resp.text[:200]
        raise RailPermanentError(f"Failed to create PayPal order ({resp.status_code}): {err_msg}")

    def capture_order(self, order_id: str, idempotency_key: str) -> PaymentResult:
        """Capture an approved PayPal order."""
        token = self.token_manager.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "PayPal-Request-Id": idempotency_key,
        }

        client = self._get_client()
        url = f"{self.base_url}/v2/checkout/orders/{order_id}/capture"

        resp = client.post(url, headers=headers, json={})
        if resp.status_code in (200, 201):
            body: dict[str, Any] = resp.json()
            raw_status = body.get("status", "COMPLETED")
            status = map_paypal_order_status(raw_status)

            return PaymentResult(
                status=status,
                rail_payment_id=order_id,
                idempotency_key=idempotency_key,
                amount_minor=0,
                currency="USD",
                payee_email="",
                raw_response=body,
                executed_at=datetime.now(UTC),
                fee_minor=0,
            )

        raise RailError(f"Capture failed ({resp.status_code}): {resp.text[:200]}")

    def get_payment_status(self, rail_payment_id: str) -> RailPaymentStatus:
        """Fetch the current status of an order."""
        token = self.token_manager.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/v2/checkout/orders/{rail_payment_id}"
        client = self._get_client()

        try:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                body = resp.json()
                return map_paypal_order_status(body.get("status", "UNKNOWN"))
            return RailPaymentStatus.FAILED
        except Exception:
            return RailPaymentStatus.FAILED
