"""PayPal Payouts rail adapter.

WHY:
As established in spike_paypal.py and DECISIONS.md:
PayPal Payouts is the primary autonomous payment rail because it executes
payer-less payouts directly to verified PayPal receiver emails without requiring
an interactive human browser click.

Guarantees enforced:
1. P1/P4: Fails closed. Checks that decision.verdict == Verdict.ALLOW before any network call.
2. P2: Operates only with OAuth2 bearer token obtained via PayPalTokenManager.
3. Idempotency: Uses request.idempotency_key for sender_batch_id and PayPal-Request-Id.
4. Retries: Retries transient errors safely with exponential backoff using identical idempotency keys.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from app.mandate.models import PaymentRequest
from app.payments.rail import (
    PaymentNotAllowedError,
    PaymentRail,
    PaymentResult,
    RailError,
    RailPaymentStatus,
    RailPermanentError,
    RailTransientError,
)
from app.payments.token import PayPalTokenManager
from app.policy.verdict import Decision, Verdict

logger = logging.getLogger(__name__)

# Zero-decimal currencies
ZERO_DECIMAL_CURRENCIES = {"JPY", "KRW", "VND", "CLP", "PYG"}


def format_minor_to_decimal_str(amount_minor: int, currency: str) -> str:
    """Format minor unit integer to decimal string for PayPal API."""
    curr = currency.upper()
    if curr in ZERO_DECIMAL_CURRENCIES:
        return str(amount_minor)
    # Default: 2 decimal places (cents)
    major = amount_minor // 100
    minor = amount_minor % 100
    return f"{major}.{minor:02d}"


def map_paypal_batch_status(paypal_status: str) -> RailPaymentStatus:
    """Map PayPal payout batch status to RailPaymentStatus."""
    status = paypal_status.upper()
    if status in ("SUCCESS", "COMPLETED"):
        return RailPaymentStatus.SUCCESS
    if status in ("PENDING", "PROCESSING"):
        return RailPaymentStatus.PENDING
    if status in ("DENIED", "CANCELED", "FAILED"):
        return RailPaymentStatus.FAILED
    return RailPaymentStatus.PENDING


class PayPalPayoutsRail(PaymentRail):
    """Executes payments via PayPal Payouts v1 API."""

    def __init__(
        self,
        token_manager: PayPalTokenManager,
        base_url: str = "https://api-m.sandbox.paypal.com",
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.token_manager = token_manager
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
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
        """Execute a payment via PayPal Payouts API if decision is ALLOW."""
        # Non-negotiable check: P1 & P4
        if decision.verdict != Verdict.ALLOW:
            raise PaymentNotAllowedError(
                f"Cannot execute payment on PayPal rail: Bouncer verdict is {decision.verdict.value}. "
                f"Reasons: {[r.code for r in decision.reasons]}"
            )

        amount_str = format_minor_to_decimal_str(request.amount_minor, request.currency)
        token = self.token_manager.get_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "PayPal-Request-Id": request.idempotency_key,
        }

        # Truncate or format batch ID (max 30 chars for PayPal sender_batch_id)
        batch_id = f"ma-{request.idempotency_key}"[:30]

        payload = {
            "sender_batch_header": {
                "sender_batch_id": batch_id,
                "email_subject": f"Payment: {request.purpose}",
                "email_message": request.memo or f"Payment of {amount_str} {request.currency}",
            },
            "items": [
                {
                    "recipient_type": "EMAIL",
                    "amount": {
                        "value": amount_str,
                        "currency": request.currency.upper(),
                    },
                    "receiver": request.payee.email.strip().lower(),
                    "note": request.memo or "Mandate Arena verified payment",
                    "sender_item_id": request.request_id[:30],
                }
            ],
        }

        client = self._get_client()
        url = f"{self.base_url}/v1/payments/payouts"

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code in (200, 201):
                    body: dict[str, Any] = resp.json()
                    header = body.get("batch_header", {})
                    payout_batch_id = header.get("payout_batch_id", batch_id)
                    batch_status = header.get("batch_status", "PENDING")
                    status = map_paypal_batch_status(batch_status)

                    return PaymentResult(
                        status=status,
                        rail_payment_id=payout_batch_id,
                        idempotency_key=request.idempotency_key,
                        amount_minor=request.amount_minor,
                        currency=request.currency,
                        payee_email=request.payee.email,
                        raw_response=body,
                        executed_at=datetime.now(UTC),
                        fee_minor=0,
                    )

                # Check for idempotent duplicate batch response
                if resp.status_code == 400:
                    body = (
                        resp.json()
                        if resp.headers.get("content-type", "").startswith("application/json")
                        else {}
                    )
                    error_name = body.get("name", "")
                    if error_name == "DUPLICATE_BATCH_ID":
                        logger.info(
                            "PayPal detected duplicate batch ID %s, fetching existing status",
                            batch_id,
                        )
                        return self._handle_duplicate_batch(batch_id, request)

                    # Other 4xx errors are permanent failures
                    err_msg = body.get("message", resp.text[:200])
                    raise RailPermanentError(
                        f"PayPal Payouts rejected request ({resp.status_code}): {err_msg}"
                    )

                if resp.status_code >= 500:
                    # Server side error - retriable
                    last_error = RailTransientError(
                        f"PayPal server error ({resp.status_code}): {resp.text[:200]}"
                    )
                else:
                    raise RailPermanentError(
                        f"Unexpected PayPal status {resp.status_code}: {resp.text[:200]}"
                    )

            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = RailTransientError(f"Network error communicating with PayPal: {exc}")

            # Backoff before retrying
            if attempt < self.max_retries:
                sleep_secs = self.backoff_factor * (2 ** (attempt - 1))
                time.sleep(sleep_secs)

        if last_error:
            raise last_error
        raise RailError("Payment execution failed after retries")

    def _handle_duplicate_batch(
        self,
        batch_id: str,
        request: PaymentRequest,
    ) -> PaymentResult:
        """Handle idempotent replay when PayPal reports DUPLICATE_BATCH_ID."""
        # Query payout status for existing batch
        status = self.get_payment_status(batch_id)
        return PaymentResult(
            status=status,
            rail_payment_id=batch_id,
            idempotency_key=request.idempotency_key,
            amount_minor=request.amount_minor,
            currency=request.currency,
            payee_email=request.payee.email,
            raw_response={"duplicate_replayed": True, "batch_id": batch_id},
            executed_at=datetime.now(UTC),
            fee_minor=0,
        )

    def get_payment_status(self, rail_payment_id: str) -> RailPaymentStatus:
        """Fetch the current status of a payout batch from PayPal."""
        token = self.token_manager.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/v1/payments/payouts/{rail_payment_id}"
        client = self._get_client()

        try:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                body = resp.json()
                header = body.get("batch_header", {})
                batch_status = header.get("batch_status", "UNKNOWN")
                return map_paypal_batch_status(batch_status)
            return RailPaymentStatus.FAILED
        except Exception:
            return RailPaymentStatus.FAILED
