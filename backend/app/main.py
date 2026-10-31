"""Mandate Arena - FastAPI application entry point.

WHY: Thin entry point that wires together routers and middleware. Business logic
lives in domain packages, not here. Auto-seeds demo data on startup so deployed
instances always have realistic Mandate, Intent, and audit trail data.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.approvals import router as approvals_router
from app.api.arena import router as arena_router
from app.api.audit import router as audit_router
from app.api.mandates import router as mandates_router
from app.api.results import router as results_router
from app.api.runs import router as runs_router

logger = logging.getLogger(__name__)


def _seed_demo_state_on_startup() -> None:
    """Auto-seed demo data so deployed instances are never empty.

    WHY: In-memory state is lost on restart. Without seeding, deployed Render
    instances would show empty mandate/intent/audit screens — appearing broken
    to hackathon judges. This populates realistic demo data on every boot.
    """
    from app.api.deps import get_app_state
    from app.mandate.models import AllowedPayee, Intent, IntentItem, Mandate
    from app.mandate.signing import generate_keypair

    state = get_app_state()

    # Skip if already seeded (e.g. multiple workers)
    if state.mandates:
        return

    priv_hex, pub_hex = generate_keypair()
    now = datetime.now(UTC)
    state.owner_keys["owner-alice"] = pub_hex

    mandate = Mandate.create_and_sign(
        mandate_id="demo-mandate",
        version=1,
        owner_id="owner-alice",
        agent_id="buyer-agent-01",
        issued_at=now,
        expires_at=now + timedelta(days=30),
        currency="USD",
        per_payment_cap_minor=20000,  # $200.00
        daily_cap_minor=100000,  # $1,000.00
        max_payments_per_hour=10,
        approval_threshold_minor=5000,  # $50.00
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
            AllowedPayee(
                payee_id="PAYEE-CLEAN-01",
                display_name="CleanCo Janitorial",
                paypal_email="orders@cleanco.test",
            ),
        ],
        allowed_purposes=["OFFICE_SUPPLIES", "HARDWARE", "SOFTWARE", "FACILITIES"],
        new_payee_policy="BLOCK",
        red_tier_policy="ASK_OWNER",
        key_id="key-alice-1",
        private_key_hex=priv_hex,
    )
    state.mandates[mandate.mandate_id] = mandate

    intent = Intent.create_and_sign(
        intent_id="demo-intent",
        mandate_id=mandate.mandate_id,
        description="Procure workstation peripherals and copy paper",
        max_total_minor=8500,  # $85.00
        items=[
            IntentItem(sku="PAPER-A4", qty=2, max_unit_price_minor=2000),
            IntentItem(sku="KB-WIRELESS", qty=1, max_unit_price_minor=4500),
            IntentItem(sku="HUB-USBC", qty=1, max_unit_price_minor=3000),
        ],
        deadline=now + timedelta(hours=24),
        private_key_hex=priv_hex,
    )
    state.intents[intent.intent_id] = intent

    # Seed initial audit trail
    state.audit_log.append(
        type_="MANDATE_REGISTERED",
        payload={
            "mandate_id": mandate.mandate_id,
            "owner_id": mandate.owner_id,
            "daily_cap_minor": mandate.daily_cap_minor,
            "currency": mandate.currency,
            "allowed_payees": len(mandate.allowed_payees),
        },
        ts=now - timedelta(hours=6),
    )
    state.audit_log.append(
        type_="INTENT_CREATED",
        payload={
            "intent_id": intent.intent_id,
            "mandate_id": intent.mandate_id,
            "max_total_minor": intent.max_total_minor,
            "description": intent.description,
        },
        ts=now - timedelta(hours=3),
    )

    # Seed 2 realistic pending approvals so the Approvals screen is immediately active
    from app.mandate.models import PayeeInfo, PaymentRequest
    from app.policy.provenance import ProvenanceTag
    from app.policy.verdict import Decision, Reason, Verdict

    req1 = PaymentRequest(
        request_id="req-6500-legit",
        mandate_id=mandate.mandate_id,
        intent_id=intent.intent_id,
        deal_id="deal-8842",
        tool_name="payouts",
        payee=PayeeInfo(id="PAYEE-OFFICE-01", email="office@supplies.test"),
        amount_minor=6500,
        currency="USD",
        purpose="OFFICE_SUPPLIES",
        memo="Keyboard and USB-C Hub procurement",
        provenance={
            "payee": ProvenanceTag.VERIFIED_RECORD.value,
            "amount_minor": ProvenanceTag.VERIFIED_RECORD.value,
            "purpose": ProvenanceTag.OWNER.value,
            "memo": ProvenanceTag.AGENT_DERIVED.value,
        },
        idempotency_key="idem-demo-6500",
        created_at=now - timedelta(minutes=3),
    )
    dec1 = Decision(
        verdict=Verdict.ASK_OWNER,
        reasons=[
            Reason(
                code="AMOUNT_EXCEEDS_APPROVAL_THRESHOLD",
                check_id="C4",
                message="Requested amount $65.00 exceeds standing approval threshold $50.00. Owner confirmation required.",
            )
        ],
        policy_version="1.0.0",
        mandate_hash="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        request_hash=req1.compute_hash(),
        evaluated_at=now - timedelta(minutes=3),
    )
    state.approval_service.create_request(payment_request=req1, decision=dec1, now=now - timedelta(minutes=3))

    req2 = PaymentRequest(
        request_id="req-8900-cloud",
        mandate_id=mandate.mandate_id,
        intent_id=intent.intent_id,
        deal_id="deal-8900",
        tool_name="payouts",
        payee=PayeeInfo(id="NEW-PAYEE-09", email="hosting@cloudservices.test"),
        amount_minor=8900,
        currency="USD",
        purpose="SOFTWARE",
        memo="Monthly staging server upgrade",
        provenance={
            "payee": ProvenanceTag.UNTRUSTED_EXTERNAL.value,
            "amount_minor": ProvenanceTag.VERIFIED_RECORD.value,
            "purpose": ProvenanceTag.OWNER.value,
            "memo": ProvenanceTag.AGENT_DERIVED.value,
        },
        idempotency_key="idem-demo-8900",
        created_at=now - timedelta(minutes=7),
    )
    dec2 = Decision(
        verdict=Verdict.ASK_OWNER,
        reasons=[
            Reason(
                code="NEW_PAYEE_CONFIRMATION",
                check_id="C3",
                message="Payee 'hosting@cloudservices.test' is not yet in allowlist. Mandate policy triggers owner approval.",
            )
        ],
        policy_version="1.0.0",
        mandate_hash="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        request_hash=req2.compute_hash(),
        evaluated_at=now - timedelta(minutes=7),
    )
    state.approval_service.create_request(payment_request=req2, decision=dec2, now=now - timedelta(minutes=7))

    logger.info(
        "Demo state seeded: mandate=%s, intent=%s, pending_approvals=%d, audit_events=%d",
        mandate.mandate_id,
        intent.intent_id,
        len(state.approval_service.list_pending()),
        len(state.audit_log.events),
    )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Seed demo data on startup, clean up on shutdown."""
    _seed_demo_state_on_startup()
    yield


app = FastAPI(
    title="Warden Protocol",
    description="Deterministic safety layer for AI agent spending via PayPal",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for React frontend (Vite default: http://localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(runs_router)
app.include_router(approvals_router)
app.include_router(audit_router)
app.include_router(mandates_router)
app.include_router(arena_router)
app.include_router(results_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check. No auth required."""
    return {"status": "ok"}


# Mount static frontend in production / Docker if dist exists
dist_dir = Path(__file__).resolve().parents[2] / "web" / "dist"
if dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="static")
