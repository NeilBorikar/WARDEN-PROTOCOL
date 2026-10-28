"""Mock payment rail for offline testing, CI, and deterministic demonstrations.

WHY:
P6: Sandbox only. No real money, secrets, or mandatory external dependencies in tests.
Idempotency: Replaying an execution with the same idempotency_key returns the
identical original result without duplicate charges.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.mandate.models import PaymentRequest
from app.payments.rail import (
    PaymentNotAllowedError,
    PaymentRail,
    PaymentResult,
    RailError,
    RailPaymentStatus,
)
from app.policy.verdict import Decision, Verdict


class MockRail(PaymentRail):
    """In-memory payment rail implementation."""

    def __init__(self, auto_succeed: bool = True) -> None:
        self.auto_succeed = auto_succeed
        # Store payments keyed by idempotency_key: idempotency_key -> PaymentResult
        self.payments_by_idempotency: dict[str, PaymentResult] = {}
        # Store payments keyed by rail_payment_id: rail_payment_id -> PaymentResult
        self.payments_by_id: dict[str, PaymentResult] = {}
        # History of all execution calls (including retries and rejects)
        self.execution_attempts: list[dict[str, Any]] = []

    def execute_payment(
        self,
        request: PaymentRequest,
        decision: Decision,
    ) -> PaymentResult:
        """Execute a payment or return an idempotent cached result."""
        self.execution_attempts.append(
            {
                "request_id": request.request_id,
                "idempotency_key": request.idempotency_key,
                "amount_minor": request.amount_minor,
                "verdict": decision.verdict.value,
                "attempted_at": datetime.now(UTC),
            }
        )

        # Rule P1/P4: Fail closed. Never execute unless ALLOW.
        if decision.verdict != Verdict.ALLOW:
            raise PaymentNotAllowedError(
                f"Cannot execute payment on rail: Decision verdict is {decision.verdict.value}, "
                f"not ALLOW. Reasons: {[r.code for r in decision.reasons]}"
            )

        # Idempotency check: if this key was already processed, return existing result
        if request.idempotency_key in self.payments_by_idempotency:
            return self.payments_by_idempotency[request.idempotency_key]

        if not self.auto_succeed:
            raise RailError("MockRail configured to fail payment execution")

        rail_id = f"mock-tx-{uuid.uuid4().hex[:12]}"
        result = PaymentResult(
            status=RailPaymentStatus.SUCCESS,
            rail_payment_id=rail_id,
            idempotency_key=request.idempotency_key,
            amount_minor=request.amount_minor,
            currency=request.currency,
            payee_email=request.payee.email,
            raw_response={
                "mock": True,
                "transaction_id": rail_id,
                "status": "COMPLETED",
            },
            executed_at=datetime.now(UTC),
            fee_minor=0,
        )

        self.payments_by_idempotency[request.idempotency_key] = result
        self.payments_by_id[rail_id] = result
        return result

    def get_payment_status(self, rail_payment_id: str) -> RailPaymentStatus:
        """Lookup payment status by rail payment ID."""
        payment = self.payments_by_id.get(rail_payment_id)
        if payment is None:
            return RailPaymentStatus.FAILED
        return payment.status

    def reset(self) -> None:
        """Clear all stored payments and history."""
        self.payments_by_idempotency.clear()
        self.payments_by_id.clear()
        self.execution_attempts.clear()
