"""Approval Service - manages owner authorization for ASK_OWNER verdicts.

WHY:
- Section 6: "ASK_OWNER creates an ApprovalRequest bound to the hash of the exact
  PaymentRequest. It expires in 15 minutes, is single-use, and the owner cannot
  approve a BLOCK. After approval, hard caps are re-checked at execution."
- Principle P4: Fail closed. Expired, invalid, or already resolved approvals reject.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.mandate.models import Mandate, PaymentRequest
from app.policy.checks import (
    HistoricalPayment,
    check_c4_amount_caps,
    check_c5_rolling_limits,
)
from app.policy.verdict import Decision, Verdict


class ApprovalStatus(StrEnum):
    """Lifecycle status of an owner approval request."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    EXPIRED = "EXPIRED"


class ApprovalRequest(BaseModel):
    """An owner approval request bound to a specific payment request hash."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    approval_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    request_hash: str = Field(min_length=64, max_length=64)
    payment_request: PaymentRequest
    decision: Decision
    created_at: datetime
    expires_at: datetime
    status: ApprovalStatus
    resolved_at: datetime | None = None
    resolution_reason: str | None = None

    def is_expired(self, at: datetime) -> bool:
        """Return True if expiration time has passed."""
        return at >= self.expires_at


class ApprovalError(Exception):
    """Raised when an invalid approval operation is attempted."""


class ApprovalService:
    """Service for creating, tracking, and resolving owner approval requests."""

    APPROVAL_TTL_MINUTES: int = 15

    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}

    def create_request(
        self,
        payment_request: PaymentRequest,
        decision: Decision,
        now: datetime | None = None,
    ) -> ApprovalRequest:
        """Create a new approval request for an ASK_OWNER decision.

        Raises ApprovalError if decision is a BLOCK (P5: owner cannot approve a BLOCK).
        """
        if decision.verdict == Verdict.BLOCK:
            raise ApprovalError("Owner cannot approve a BLOCK decision (Section 6).")

        current_time = now or datetime.now(UTC)
        expires_at = current_time + timedelta(minutes=self.APPROVAL_TTL_MINUTES)
        approval_id = f"appr_{uuid.uuid4().hex[:12]}"

        req = ApprovalRequest(
            approval_id=approval_id,
            request_id=payment_request.request_id,
            request_hash=payment_request.compute_hash(),
            payment_request=payment_request,
            decision=decision,
            created_at=current_time,
            expires_at=expires_at,
            status=ApprovalStatus.PENDING,
        )
        self._requests[approval_id] = req
        return req

    def get_request(self, approval_id: str) -> ApprovalRequest | None:
        """Retrieve an approval request by its ID."""
        return self._requests.get(approval_id)

    def list_pending(self, now: datetime | None = None) -> list[ApprovalRequest]:
        """List all currently pending and unexpired approval requests."""
        current_time = now or datetime.now(UTC)
        return [
            req
            for req in self._requests.values()
            if req.status == ApprovalStatus.PENDING and not req.is_expired(current_time)
        ]

    def approve(
        self,
        approval_id: str,
        note: str = "",
        now: datetime | None = None,
    ) -> ApprovalRequest:
        """Approve a pending approval request.

        Single-use, enforces 15-minute TTL, cryptographically validates request hash.
        """
        current_time = now or datetime.now(UTC)
        req = self._requests.get(approval_id)
        if req is None:
            raise ApprovalError(f"Approval request '{approval_id}' not found.")

        if req.status != ApprovalStatus.PENDING:
            raise ApprovalError(
                f"Approval '{approval_id}' is already resolved with status '{req.status.value}'."
            )

        if req.is_expired(current_time):
            # Expire it
            expired_req = ApprovalRequest(
                approval_id=req.approval_id,
                request_id=req.request_id,
                request_hash=req.request_hash,
                payment_request=req.payment_request,
                decision=req.decision,
                created_at=req.created_at,
                expires_at=req.expires_at,
                status=ApprovalStatus.EXPIRED,
                resolved_at=current_time,
                resolution_reason="Approval request expired after 15 minutes.",
            )
            self._requests[approval_id] = expired_req
            raise ApprovalError("Approval request has expired (15-minute TTL).")

        # Verify hash binding
        computed_hash = req.payment_request.compute_hash()
        if computed_hash != req.request_hash:
            raise ApprovalError("Payment request was tampered with after approval creation.")

        resolved_req = ApprovalRequest(
            approval_id=req.approval_id,
            request_id=req.request_id,
            request_hash=req.request_hash,
            payment_request=req.payment_request,
            decision=req.decision,
            created_at=req.created_at,
            expires_at=req.expires_at,
            status=ApprovalStatus.APPROVED,
            resolved_at=current_time,
            resolution_reason=note or "Approved by owner.",
        )
        self._requests[approval_id] = resolved_req
        return resolved_req

    def deny(
        self,
        approval_id: str,
        reason: str = "",
        now: datetime | None = None,
    ) -> ApprovalRequest:
        """Deny a pending approval request."""
        current_time = now or datetime.now(UTC)
        req = self._requests.get(approval_id)
        if req is None:
            raise ApprovalError(f"Approval request '{approval_id}' not found.")

        if req.status != ApprovalStatus.PENDING:
            raise ApprovalError(
                f"Approval '{approval_id}' is already resolved with status '{req.status.value}'."
            )

        resolved_req = ApprovalRequest(
            approval_id=req.approval_id,
            request_id=req.request_id,
            request_hash=req.request_hash,
            payment_request=req.payment_request,
            decision=req.decision,
            created_at=req.created_at,
            expires_at=req.expires_at,
            status=ApprovalStatus.DENIED,
            resolved_at=current_time,
            resolution_reason=reason or "Denied by owner.",
        )
        self._requests[approval_id] = resolved_req
        return resolved_req

    @staticmethod
    def recheck_hard_caps_at_execution(
        request: PaymentRequest,
        mandate: Mandate,
        history: list[HistoricalPayment],
    ) -> tuple[bool, str | None]:
        """Re-check hard caps (per-payment cap & daily cap) at moment of execution.

        WHY: Even after owner approves, rolling velocity or daily cap could have been
        exhausted by concurrent transactions. Hard caps must NEVER be breached (P4).
        """
        # Hard per-payment cap
        c4_result = check_c4_amount_caps(request, mandate)
        if c4_result.verdict == Verdict.BLOCK:
            return False, c4_result.reason.message

        # Hard rolling daily & hourly caps
        c5_result = check_c5_rolling_limits(request, mandate, history)
        if c5_result.verdict == Verdict.BLOCK:
            return False, c5_result.reason.message

        return True, None
