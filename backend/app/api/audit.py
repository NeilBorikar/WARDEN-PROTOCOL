"""API Router for the cryptographic audit log.

WHY:
- Section 8: "Audit: searchable table with a 'verify chain' button."
- Provides immutable event log access and instantaneous SHA-256 hash chain verification.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import AppState, get_app_state
from app.audit.verify import verify_chain

router = APIRouter(prefix="/api/audit", tags=["audit"])


class AuditEventResponse(BaseModel):
    """An immutable audit event."""

    seq: int
    ts: datetime
    type: str
    payload: dict[str, Any]
    prev_hash: str
    hash: str


class ChainVerificationResponse(BaseModel):
    """Result of cryptographic audit chain verification."""

    is_valid: bool
    verified_count: int
    error: str | None = None
    checked_at: datetime


@router.get("", response_model=list[AuditEventResponse])
def list_audit_events(
    type_filter: str | None = Query(None, description="Filter by event type"),
    limit: int = Query(100, ge=1, le=1000),
    state: AppState = Depends(get_app_state),
) -> list[AuditEventResponse]:
    """Retrieve audit events in reverse chronological order."""
    events = state.audit_log.events
    if type_filter:
        events = [e for e in events if e.type == type_filter]

    # Return latest first
    events_slice = list(reversed(events))[:limit]

    return [
        AuditEventResponse(
            seq=e.seq,
            ts=e.ts,
            type=e.type,
            payload=e.payload,
            prev_hash=e.prev_hash,
            hash=e.hash,
        )
        for e in events_slice
    ]


@router.get("/{seq}", response_model=AuditEventResponse)
def get_audit_event(
    seq: int,
    state: AppState = Depends(get_app_state),
) -> AuditEventResponse:
    """Retrieve a single audit event by sequence number."""
    event = state.audit_log.get_by_seq(seq)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit event with seq={seq} not found.",
        )
    return AuditEventResponse(
        seq=event.seq,
        ts=event.ts,
        type=event.type,
        payload=event.payload,
        prev_hash=event.prev_hash,
        hash=event.hash,
    )


@router.post("/verify", response_model=ChainVerificationResponse)
def verify_audit_chain(state: AppState = Depends(get_app_state)) -> ChainVerificationResponse:
    """Cryptographically verify the complete audit hash chain from genesis to head."""
    events = state.audit_log.events
    result = verify_chain(events)
    return ChainVerificationResponse(
        is_valid=result.is_valid,
        verified_count=result.verified_count,
        error=result.error,
        checked_at=datetime.now(),
    )
