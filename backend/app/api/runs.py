"""API Router for negotiation runs.

WHY:
- Section 8: "Live Run: negotiation transcript left, decision timeline with
  plain-English reasons right."
- Coordinates initiating runs, retrieving real-time transcripts, and querying outcomes.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.agents.buyer import BuyerAgent
from app.agents.negotiation import (
    NegotiationLoop,
    run_scripted_negotiation,
)
from app.agents.seller import SellerAgent
from app.api.deps import AppState, get_app_state
from app.mandate.models import (
    AllowedPayee,
    Intent,
    IntentItem,
    Mandate,
)
from app.mandate.signing import generate_keypair

router = APIRouter(prefix="/api/runs", tags=["runs"])


class StartRunRequest(BaseModel):
    """Payload to start a negotiation run."""

    mandate_id: str | None = None
    intent_id: str | None = None
    scripted: bool = True
    seller_offer: dict[str, Any] | None = None
    purpose: str = "OFFICE_SUPPLIES"
    memo: str = "Automated procurement"
    initial_message: str = "Hello, do you have office supplies in stock?"


class RunSummaryResponse(BaseModel):
    """Concise summary of a negotiation run."""

    run_id: str
    status: str
    turns_count: int
    started_at: datetime
    completed_at: datetime | None = None
    has_deal: bool
    has_payment: bool
    verdict: str | None = None


class RunDetailResponse(BaseModel):
    """Complete detail of a negotiation run."""

    run_id: str
    status: str
    turns: list[dict[str, Any]]
    deal: dict[str, Any] | None = None
    payment_request: dict[str, Any] | None = None
    decision: dict[str, Any] | None = None
    payment_executed: bool = False
    rail_payment_id: str | None = None
    verifier_opinion: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime
    completed_at: datetime | None = None


def _ensure_default_mandate_and_intent(state: AppState) -> tuple[Mandate, Intent, str]:
    """Helper: create demo mandate & intent if none exist."""
    if "demo-mandate" in state.mandates and "demo-intent" in state.intents:
        return (
            state.mandates["demo-mandate"],
            state.intents["demo-intent"],
            state.owner_keys["owner-demo"],
        )

    priv_hex, pub_hex = generate_keypair()
    now = datetime.now(UTC)
    state.owner_keys["owner-demo"] = pub_hex

    mandate = Mandate.create_and_sign(
        mandate_id="demo-mandate",
        version=1,
        owner_id="owner-demo",
        agent_id="buyer-agent-01",
        issued_at=now,
        expires_at=now + timedelta(days=30),
        currency="USD",
        per_payment_cap_minor=20000,  # $200.00
        daily_cap_minor=100000,  # $1,000.00
        max_payments_per_hour=10,
        approval_threshold_minor=3000,  # $30.00 (triggers ASK_OWNER above $30)
        allowed_payees=[
            AllowedPayee(
                payee_id="PAYEE-OFFICE-01",
                display_name="Office Supplies Co",
                paypal_email="office@supplies.test",
            ),
            AllowedPayee(
                payee_id="PAYEE-TECH-01",
                display_name="Tech Depot",
                paypal_email="tech@depot.test",
            ),
        ],
        allowed_purposes=["OFFICE_SUPPLIES", "HARDWARE", "SOFTWARE"],
        new_payee_policy="BLOCK",
        red_tier_policy="ASK_OWNER",
        key_id="key-demo-1",
        private_key_hex=priv_hex,
    )
    state.mandates["demo-mandate"] = mandate

    intent = Intent.create_and_sign(
        intent_id="demo-intent",
        mandate_id=mandate.mandate_id,
        description="Procure standard printer paper and supplies",
        max_total_minor=8000,  # $80.00
        items=[
            IntentItem(sku="PAPER-A4", qty=2, max_unit_price_minor=2000),
            IntentItem(sku="TONER-BLK", qty=1, max_unit_price_minor=4000),
        ],
        deadline=now + timedelta(hours=24),
        private_key_hex=priv_hex,
    )
    state.intents["demo-intent"] = intent
    return mandate, intent, pub_hex


@router.post("/start", response_model=RunDetailResponse, status_code=status.HTTP_201_CREATED)
def start_run(
    req: StartRunRequest,
    state: AppState = Depends(get_app_state),
) -> RunDetailResponse:
    """Initiate a new negotiation run (scripted or interactive)."""
    # 1. Resolve Mandate and Intent
    if req.mandate_id and req.mandate_id in state.mandates:
        mandate = state.mandates[req.mandate_id]
        pub_hex = state.owner_keys.get(mandate.owner_id, "")
    else:
        mandate, _, pub_hex = _ensure_default_mandate_and_intent(state)

    if req.intent_id and req.intent_id in state.intents:
        intent = state.intents[req.intent_id]
    else:
        _, intent, pub_hex = _ensure_default_mandate_and_intent(state)

    buyer = BuyerAgent(mandate=mandate, intent=intent)
    seller = SellerAgent(
        payee_email="office@supplies.test",
        payee_id="PAYEE-OFFICE-01",
    )

    if req.scripted:
        default_offer = req.seller_offer or {
            "sku": "PAPER-A4",
            "quantity": 2,
            "unit_price_minor": 1200,
            "total_minor": 2400,
            "currency": "USD",
            "payee_email": "office@supplies.test",
            "payee_id": "PAYEE-OFFICE-01",
        }

        result = run_scripted_negotiation(
            buyer=buyer,
            seller=seller,
            gateway=state.gateway,
            audit_log=state.audit_log,
            offer=default_offer,
            purpose=req.purpose,
            owner_public_key_hex=pub_hex,
            memo=req.memo,
        )
    else:
        loop = NegotiationLoop(
            buyer=buyer,
            seller=seller,
            gateway=state.gateway,
            audit_log=state.audit_log,
        )
        result = loop.run(
            initial_buyer_message=req.initial_message,
            owner_public_key_hex=pub_hex,
        )

    # Save run
    state.runs[result.run_id] = result

    # Format response
    turns_data = [
        {
            "turn_number": t.turn_number,
            "buyer_message": t.buyer_message,
            "seller_message": t.seller_message,
            "timestamp": t.timestamp.isoformat(),
        }
        for t in result.turns
    ]

    decision_data = (
        result.gateway_outcome.decision.model_dump()
        if result.gateway_outcome and result.gateway_outcome.decision
        else None
    )

    rail_tx_id = (
        result.gateway_outcome.payment_result.rail_payment_id
        if result.gateway_outcome and result.gateway_outcome.payment_result
        else None
    )

    return RunDetailResponse(
        run_id=result.run_id,
        status=result.status.value,
        turns=turns_data,
        deal=result.deal.model_dump() if result.deal else None,
        payment_request=result.payment_request.model_dump() if result.payment_request else None,
        decision=decision_data,
        payment_executed=result.gateway_outcome.executed if result.gateway_outcome else False,
        rail_payment_id=rail_tx_id,
        error=result.error,
        started_at=result.started_at,
        completed_at=result.completed_at,
    )


@router.get("", response_model=list[RunSummaryResponse])
def list_runs(state: AppState = Depends(get_app_state)) -> list[RunSummaryResponse]:
    """List all negotiation runs in descending order of creation."""
    summaries = []
    for r in sorted(state.runs.values(), key=lambda x: x.started_at, reverse=True):
        verdict_str = None
        if r.gateway_outcome and r.gateway_outcome.decision:
            verdict_str = r.gateway_outcome.decision.verdict.value

        summaries.append(
            RunSummaryResponse(
                run_id=r.run_id,
                status=r.status.value,
                turns_count=r.total_turns,
                started_at=r.started_at,
                completed_at=r.completed_at,
                has_deal=r.deal is not None,
                has_payment=r.payment_request is not None,
                verdict=verdict_str,
            )
        )
    return summaries


@router.get("/{run_id}", response_model=RunDetailResponse)
def get_run(run_id: str, state: AppState = Depends(get_app_state)) -> RunDetailResponse:
    """Retrieve full details for a specific run."""
    result = state.runs.get(run_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found.",
        )

    turns_data = [
        {
            "turn_number": t.turn_number,
            "buyer_message": t.buyer_message,
            "seller_message": t.seller_message,
            "timestamp": t.timestamp.isoformat(),
        }
        for t in result.turns
    ]

    decision_data = (
        result.gateway_outcome.decision.model_dump()
        if result.gateway_outcome and result.gateway_outcome.decision
        else None
    )

    rail_tx_id = (
        result.gateway_outcome.payment_result.rail_payment_id
        if result.gateway_outcome and result.gateway_outcome.payment_result
        else None
    )

    return RunDetailResponse(
        run_id=result.run_id,
        status=result.status.value,
        turns=turns_data,
        deal=result.deal.model_dump() if result.deal else None,
        payment_request=result.payment_request.model_dump() if result.payment_request else None,
        decision=decision_data,
        payment_executed=result.gateway_outcome.executed if result.gateway_outcome else False,
        rail_payment_id=rail_tx_id,
        error=result.error,
        started_at=result.started_at,
        completed_at=result.completed_at,
    )
