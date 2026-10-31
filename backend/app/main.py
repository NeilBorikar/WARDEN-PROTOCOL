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

    logger.info(
        "Demo state seeded: mandate=%s, intent=%s, audit_events=%d",
        mandate.mandate_id,
        intent.intent_id,
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
