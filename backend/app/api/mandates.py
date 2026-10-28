"""API Router for Mandates and Intents.

WHY:
- Section 8: "Mandate and Intent: view, edit, sign."
- Manages owner-signed standing spending rules (Mandates) and task budgets (Intents).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import AppState, get_app_state
from app.mandate.models import AllowedPayee, Intent, IntentItem, Mandate
from app.mandate.signing import generate_keypair

router = APIRouter(prefix="/api/mandates", tags=["mandates"])


class CreateMandateRequest(BaseModel):
    """Payload to create and sign a new Mandate."""

    mandate_id: str = Field(
        default_factory=lambda: f"mandate-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )
    version: int = 1
    owner_id: str = "owner-alice"
    agent_id: str = "buyer-agent-01"
    valid_days: int = 30
    currency: str = "USD"
    per_payment_cap_minor: int = 10000  # $100.00
    daily_cap_minor: int = 50000  # $500.00
    max_payments_per_hour: int = 5
    approval_threshold_minor: int = 5000  # $50.00
    allowed_payees: list[dict[str, str]] = Field(
        default_factory=lambda: [
            {
                "payee_id": "PAYEE-OFFICE-01",
                "display_name": "Office Supplies Co",
                "paypal_email": "office@supplies.test",
            }
        ]
    )
    allowed_purposes: list[str] = Field(default_factory=lambda: ["OFFICE_SUPPLIES", "EQUIPMENT"])
    new_payee_policy: str = "BLOCK"
    red_tier_policy: str = "ASK_OWNER"
    key_id: str = "key-owner-1"


class CreateIntentRequest(BaseModel):
    """Payload to create and sign a new Intent."""

    intent_id: str = Field(
        default_factory=lambda: f"intent-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )
    mandate_id: str
    description: str = "Procure supplies"
    max_total_minor: int = 5000  # $50.00
    items: list[dict[str, Any]] = Field(
        default_factory=lambda: [{"sku": "ITEM-01", "qty": 1, "max_unit_price_minor": 5000}]
    )
    valid_hours: int = 24


@router.get("", response_model=list[dict[str, Any]])
def list_mandates(state: AppState = Depends(get_app_state)) -> list[dict[str, Any]]:
    """List all configured mandates."""
    # Ensure at least the default demo mandate exists
    from app.api.runs import _ensure_default_mandate_and_intent

    _ensure_default_mandate_and_intent(state)
    return [m.model_dump() for m in state.mandates.values()]


@router.get("/{mandate_id}", response_model=dict[str, Any])
def get_mandate(mandate_id: str, state: AppState = Depends(get_app_state)) -> dict[str, Any]:
    """Retrieve a single mandate by ID."""
    mandate = state.mandates.get(mandate_id)
    if not mandate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mandate '{mandate_id}' not found.",
        )
    return mandate.model_dump()


@router.post("", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_mandate(
    req: CreateMandateRequest,
    state: AppState = Depends(get_app_state),
) -> dict[str, Any]:
    """Create and sign a new Mandate with an owner Ed25519 keypair."""
    priv_hex, pub_hex = generate_keypair()
    now = datetime.now(UTC)
    state.owner_keys[req.owner_id] = pub_hex

    payees = [
        AllowedPayee(
            payee_id=p["payee_id"],
            display_name=p["display_name"],
            paypal_email=p["paypal_email"],
        )
        for p in req.allowed_payees
    ]

    mandate = Mandate.create_and_sign(
        mandate_id=req.mandate_id,
        version=req.version,
        owner_id=req.owner_id,
        agent_id=req.agent_id,
        issued_at=now,
        expires_at=now + timedelta(days=req.valid_days),
        currency=req.currency,
        per_payment_cap_minor=req.per_payment_cap_minor,
        daily_cap_minor=req.daily_cap_minor,
        max_payments_per_hour=req.max_payments_per_hour,
        approval_threshold_minor=req.approval_threshold_minor,
        allowed_payees=payees,
        allowed_purposes=req.allowed_purposes,
        new_payee_policy=req.new_payee_policy,
        red_tier_policy=req.red_tier_policy,
        key_id=req.key_id,
        private_key_hex=priv_hex,
    )
    state.mandates[mandate.mandate_id] = mandate

    state.audit_log.append(
        type_="MANDATE_CREATED",
        payload={
            "mandate_id": mandate.mandate_id,
            "owner_id": mandate.owner_id,
            "daily_cap_minor": mandate.daily_cap_minor,
            "currency": mandate.currency,
        },
    )

    return mandate.model_dump()


@router.get("/intents/list", response_model=list[dict[str, Any]])
def list_intents(state: AppState = Depends(get_app_state)) -> list[dict[str, Any]]:
    """List all created errand intents."""
    from app.api.runs import _ensure_default_mandate_and_intent

    _ensure_default_mandate_and_intent(state)
    return [i.model_dump() for i in state.intents.values()]


@router.post("/intents", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_intent(
    req: CreateIntentRequest,
    state: AppState = Depends(get_app_state),
) -> dict[str, Any]:
    """Create and sign a new Intent referencing an existing Mandate."""
    mandate = state.mandates.get(req.mandate_id)
    if not mandate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Referenced Mandate '{req.mandate_id}' does not exist.",
        )

    priv_hex, pub_hex = generate_keypair()
    now = datetime.now(UTC)

    items = [
        IntentItem(
            sku=it["sku"],
            qty=it.get("qty", 1),
            max_unit_price_minor=it.get("max_unit_price_minor", req.max_total_minor),
        )
        for it in req.items
    ]

    intent = Intent.create_and_sign(
        intent_id=req.intent_id,
        mandate_id=mandate.mandate_id,
        description=req.description,
        max_total_minor=req.max_total_minor,
        items=items,
        deadline=now + timedelta(hours=req.valid_hours),
        private_key_hex=priv_hex,
    )
    state.intents[intent.intent_id] = intent

    state.audit_log.append(
        type_="INTENT_CREATED",
        payload={
            "intent_id": intent.intent_id,
            "mandate_id": intent.mandate_id,
            "max_total_minor": intent.max_total_minor,
        },
    )

    return intent.model_dump()
