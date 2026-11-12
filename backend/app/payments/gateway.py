"""Bouncer-Gated Payment Gateway.

WHY:
P1: AI proposes, deterministic code decides.
P4: Fail closed. Errors, timeouts, or policy violations produce BLOCK or ASK_OWNER, never money movement.
Auditability: Every evaluation and payment execution is recorded in the SHA-256 audit hash chain.
Exit Criterion: Money moves in the sandbox only via the Bouncer.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field

from app.approvals.service import ApprovalRequest, ApprovalService
from app.audit.log import AuditLog
from app.mandate.models import Deal, Intent, Mandate, PaymentRequest
from app.payments.rail import (
    PaymentNotAllowedError,
    PaymentRail,
    PaymentResult,
    RailError,
    RailPaymentStatus,
)
from app.policy.checks import HistoricalPayment
from app.policy.engine import PolicyEngine
from app.policy.verdict import Decision, Verdict

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GatewayOutcome:
    """Consolidated outcome of Bouncer policy evaluation and rail dispatch."""

    decision: Decision
    payment_result: PaymentResult | None = None
    approval_request: ApprovalRequest | None = None
    error_message: str | None = None

    @property
    def executed(self) -> bool:
        """True if the payment was successfully executed on the payment rail."""
        return (
            self.decision.verdict == Verdict.ALLOW
            and self.payment_result is not None
            and self.payment_result.status == RailPaymentStatus.SUCCESS
        )


class PaymentGateway:
    """Coordinates Bouncer policy evaluation, audit logging, approvals, and rail execution."""

    def __init__(
        self,
        rail: PaymentRail,
        audit_log: AuditLog,
        approval_service: ApprovalService | None = None,
    ) -> None:
        self.rail = rail
        self.audit_log = audit_log
        self.approval_service = approval_service
        self._lock = threading.Lock()
        self._history: list[HistoricalPayment] = []
        self._reservations: dict[str, HistoricalPayment] = {}

    def get_historical_payments(self) -> list[HistoricalPayment]:
        """Return a snapshot copy of all committed payments."""
        with self._lock:
            return list(self._history)

    def get_active_reservations(self) -> dict[str, HistoricalPayment]:
        """Return a snapshot copy of in-flight reservations."""
        with self._lock:
            return dict(self._reservations)

    def process_payment(
        self,
        request: PaymentRequest,
        mandate: Mandate,
        owner_public_key_hex: str,
        intent: Intent | None = None,
        deal: Deal | None = None,
        historical_payments: list[HistoricalPayment] | None = None,
    ) -> GatewayOutcome:
        """Two-phase check-and-reserve Bouncer evaluation and rail dispatch.

        WHY:
        1. Lock only check-and-reserve: The lock is held for microsecond policy checks
           and balance reservation, NEVER during external PayPal network I/O.
        2. In-flight protection: Parallel requests evaluate against committed history
           PLUS active in-flight reservations, preventing concurrent overspend.
        3. Safe failure: If PayPal times out or rejects, the reservation is immediately
           released, preventing permanent cap loss on transient network errors.
        """
        # PHASE 1: ATOMIC CHECK & RESERVE (HELD UNDER LOCK)
        with self._lock:
            # Combine committed history + active reservations + external records
            active_history = list(self._history) + list(self._reservations.values())
            if historical_payments:
                active_history.extend(historical_payments)

            # Deterministic policy evaluation
            decision = PolicyEngine.evaluate(
                request=request,
                mandate=mandate,
                intent=intent,
                deal=deal,
                owner_public_key_hex=owner_public_key_hex,
                history=active_history,
            )

            # Case: BLOCK
            if decision.verdict == Verdict.BLOCK:
                self.audit_log.append(
                    type_="PAYMENT_BLOCKED",
                    payload={
                        "request_id": request.request_id,
                        "mandate_id": request.mandate_id,
                        "amount_minor": request.amount_minor,
                        "currency": request.currency,
                        "payee": {"email": request.payee.email, "id": request.payee.id},
                        "reasons": [r.model_dump() for r in decision.reasons],
                    },
                )
                return GatewayOutcome(decision=decision)

            # Case: ASK_OWNER
            if decision.verdict == Verdict.ASK_OWNER:
                approval_req: ApprovalRequest | None = None
                if self.approval_service is not None:
                    approval_req = self.approval_service.create_request(
                        payment_request=request,
                        decision=decision,
                    )

                self.audit_log.append(
                    type_="PAYMENT_APPROVAL_REQUESTED",
                    payload={
                        "request_id": request.request_id,
                        "mandate_id": request.mandate_id,
                        "amount_minor": request.amount_minor,
                        "currency": request.currency,
                        "approval_id": approval_req.approval_id if approval_req else None,
                        "reasons": [r.model_dump() for r in decision.reasons],
                    },
                )
                return GatewayOutcome(decision=decision, approval_request=approval_req)

            # Case: ALLOW -> Reserve funds in-flight before releasing lock
            reservation = HistoricalPayment(
                amount_minor=request.amount_minor,
                executed_at=request.created_at,
            )
            self._reservations[request.request_id] = reservation

        # PHASE 2: DISPATCH TO RAIL (OUTSIDE THE LOCK - NON-BLOCKING)
        try:
            payment_result = self.rail.execute_payment(request=request, decision=decision)

            # PHASE 3A: COMMIT RESERVATION ON SUCCESS
            with self._lock:
                self._reservations.pop(request.request_id, None)
                self._history.append(
                    HistoricalPayment(
                        amount_minor=payment_result.amount_minor,
                        executed_at=request.created_at,
                    )
                )

            self.audit_log.append(
                type_="PAYMENT_EXECUTED",
                payload={
                    "request_id": request.request_id,
                    "idempotency_key": request.idempotency_key,
                    "rail_payment_id": payment_result.rail_payment_id,
                    "amount_minor": payment_result.amount_minor,
                    "currency": payment_result.currency,
                    "status": payment_result.status.value,
                    "payee_email": payment_result.payee_email,
                },
            )
            return GatewayOutcome(decision=decision, payment_result=payment_result)

        except PaymentNotAllowedError as pna_err:
            # PHASE 3B: ROLLBACK RESERVATION ON FAILURE
            with self._lock:
                self._reservations.pop(request.request_id, None)

            logger.error("Bouncer blocked rail execution: %s", pna_err)
            self.audit_log.append(
                type_="PAYMENT_EXECUTION_DENIED",
                payload={
                    "request_id": request.request_id,
                    "error": str(pna_err),
                },
            )
            return GatewayOutcome(decision=decision, error_message=str(pna_err))

        except Exception as rail_err:
            # PHASE 3C: ROLLBACK RESERVATION ON TIMEOUT OR RAIL ERROR
            with self._lock:
                self._reservations.pop(request.request_id, None)

            logger.error("Payment rail error: %s", rail_err)
            self.audit_log.append(
                type_="PAYMENT_RAIL_FAILED",
                payload={
                    "request_id": request.request_id,
                    "error": str(rail_err),
                },
            )
            return GatewayOutcome(decision=decision, error_message=str(rail_err))
