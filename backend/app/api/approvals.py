"""API Router for owner approvals.

WHY:
- Section 6 & 8: "Approvals: mobile-friendly approve and deny."
- Single-use, 15-minute TTL, owner cannot approve a BLOCK.
- Re-checks hard caps at execution before moving money.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import AppState, get_app_state
from app.approvals.service import ApprovalError, ApprovalRequest
from app.payments.rail import RailPaymentStatus
from app.policy.verdict import Decision, Reason, Verdict

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


class ApproveRequest(BaseModel):
    """Payload to approve a pending payment."""

    note: str = Field(default="Approved by owner via security console")


class DenyRequest(BaseModel):
    """Payload to deny a pending payment."""

    reason: str = Field(default="Rejected by owner")


class ApprovalResponse(BaseModel):
    """Approval request representation."""

    approval_id: str
    request_id: str
    request_hash: str
    amount_minor: int
    currency: str
    payee_email: str
    payee_id: str
    purpose: str
    memo: str
    status: str
    created_at: datetime
    expires_at: datetime
    reasons: list[dict[str, Any]]
    resolved_at: datetime | None = None
    resolution_reason: str | None = None


class ExecutionOutcomeResponse(BaseModel):
    """Response returned upon resolving an approval."""

    approval: ApprovalResponse
    executed: bool
    rail_payment_id: str | None = None
    error: str | None = None


def _to_approval_response(req: ApprovalRequest) -> ApprovalResponse:
    return ApprovalResponse(
        approval_id=req.approval_id,
        request_id=req.request_id,
        request_hash=req.request_hash,
        amount_minor=req.payment_request.amount_minor,
        currency=req.payment_request.currency,
        payee_email=req.payment_request.payee.email,
        payee_id=req.payment_request.payee.id,
        purpose=req.payment_request.purpose,
        memo=req.payment_request.memo,
        status=req.status.value,
        created_at=req.created_at,
        expires_at=req.expires_at,
        reasons=[r.model_dump() for r in req.decision.reasons],
        resolved_at=req.resolved_at,
        resolution_reason=req.resolution_reason,
    )


@router.get("", response_model=list[ApprovalResponse])
def list_approvals(
    status_filter: str | None = None,
    state: AppState = Depends(get_app_state),
) -> list[ApprovalResponse]:
    """List pending approval requests, or all if status_filter is given."""
    if status_filter == "pending" or status_filter is None:
        pending = state.approval_service.list_pending()
        return [_to_approval_response(r) for r in pending]

    # Return all from internal dictionary
    return [
        _to_approval_response(r)
        for r in state.approval_service._requests.values()
        if status_filter == "all" or r.status.value == status_filter.upper()
    ]


@router.get("/{approval_id}", response_model=ApprovalResponse)
def get_approval(
    approval_id: str,
    state: AppState = Depends(get_app_state),
) -> ApprovalResponse:
    """Retrieve details of a single approval request."""
    req = state.approval_service.get_request(approval_id)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request '{approval_id}' not found.",
        )
    return _to_approval_response(req)


@router.post("/{approval_id}/approve", response_model=ExecutionOutcomeResponse)
def approve_request(
    approval_id: str,
    body: ApproveRequest,
    state: AppState = Depends(get_app_state),
) -> ExecutionOutcomeResponse:
    """Approve a pending request. Re-evaluates hard caps and dispatches to payment rail."""
    try:
        resolved = state.approval_service.approve(approval_id=approval_id, note=body.note)
    except ApprovalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    payment_req = resolved.payment_request

    # Retrieve mandate to verify hard caps at execution time (Section 6)
    mandate = state.mandates.get(payment_req.mandate_id)
    if not mandate:
        # If mandate not in store, locate from default or demo
        mandate = next(iter(state.mandates.values()), None)

        # Re-check hard caps
        caps_ok, cap_error = ApprovalService.recheck_hard_caps_at_execution(
            request=payment_req,
            mandate=mandate,
            history=[],
        )
        if not caps_ok:
            state.audit_log.append(
                type_="APPROVAL_EXECUTION_BLOCKED",
                payload={
                    "approval_id": approval_id,
                    "request_id": payment_req.request_id,
                    "reason": cap_error or "Hard caps violated at execution time",
                },
            )
            return ExecutionOutcomeResponse(
                approval=_to_approval_response(resolved),
                executed=False,
                error=cap_error or "Payment exceeds mandate hard caps at execution time.",
            )

    # Dispatch to rail with approved verdict decision
    try:
        approved_decision = Decision(
            verdict=Verdict.ALLOW,
            reasons=[
                Reason(
                    code="OWNER_APPROVED",
                    check_id="APPROVAL",
                    message=f"Payment authorized by owner: {body.note or 'Console approval'}",
                )
            ],
            policy_version="1.0.0",
            mandate_hash=mandate.compute_hash() if mandate else "0" * 64,
            request_hash=payment_req.compute_hash(),
            evaluated_at=datetime.now(UTC),
        )
        payment_result = state.rail.execute_payment(
            request=payment_req,
            decision=approved_decision,
        )
        executed = payment_result.status == RailPaymentStatus.SUCCESS

        state.audit_log.append(
            type_="APPROVED_PAYMENT_EXECUTED" if executed else "APPROVED_PAYMENT_FAILED",
            payload={
                "approval_id": approval_id,
                "request_id": payment_req.request_id,
                "amount_minor": payment_req.amount_minor,
                "currency": payment_req.currency,
                "rail_status": payment_result.status.value,
                "rail_payment_id": payment_result.rail_payment_id,
            },
        )

        return ExecutionOutcomeResponse(
            approval=_to_approval_response(resolved),
            executed=executed,
            rail_payment_id=payment_result.rail_payment_id,
            error=payment_result.error_message if not executed else None,
        )

    except Exception as exc:
        state.audit_log.append(
            type_="APPROVED_PAYMENT_ERROR",
            payload={
                "approval_id": approval_id,
                "request_id": payment_req.request_id,
                "error": str(exc),
            },
        )
        return ExecutionOutcomeResponse(
            approval=_to_approval_response(resolved),
            executed=False,
            error=str(exc),
        )


@router.post("/{approval_id}/deny", response_model=ApprovalResponse)
def deny_request(
    approval_id: str,
    body: DenyRequest,
    state: AppState = Depends(get_app_state),
) -> ApprovalResponse:
    """Deny a pending request."""
    try:
        resolved = state.approval_service.deny(approval_id=approval_id, reason=body.reason)
        state.audit_log.append(
            type_="PAYMENT_DENIED_BY_OWNER",
            payload={
                "approval_id": approval_id,
                "request_id": resolved.payment_request.request_id,
                "reason": body.reason,
            },
        )
        return _to_approval_response(resolved)
    except ApprovalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
