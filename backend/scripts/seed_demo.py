"""Seed Demo Data for Mandate Arena.

WHY:
- Section 4 & Makefile: `make demo` runs `python -m scripts.seed_demo`.
- Populates the application with realistic data for live UI testing, video recordings,
  and offline demo evaluation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.api.deps import reset_app_state
from app.mandate.models import AllowedPayee, Intent, IntentItem, Mandate
from app.mandate.signing import generate_keypair


def seed_demo_data() -> None:
    print("=" * 60)
    print("  SEEDING MANDATE ARENA DEMO ENVIRONMENT")
    print("=" * 60)

    state = reset_app_state()

    # 1. Generate Owner Keys & Standing Mandate
    priv_hex, pub_hex = generate_keypair()
    now = datetime.now(UTC)
    state.owner_keys["owner-alice"] = pub_hex

    mandate = Mandate.create_and_sign(
        mandate_id="mandate-corp-01",
        version=1,
        owner_id="owner-alice",
        agent_id="buyer-agent-01",
        issued_at=now - timedelta(days=2),
        expires_at=now + timedelta(days=28),
        currency="USD",
        per_payment_cap_minor=20000,  # $200.00
        daily_cap_minor=100000,  # $1,000.00
        max_payments_per_hour=10,
        approval_threshold_minor=5000,  # $50.00
        allowed_payees=[
            AllowedPayee(
                payee_id="PAYEE-OFFICE-MAX",
                display_name="Office Supplies Direct",
                paypal_email="supplies@officemax.test",
            ),
            AllowedPayee(
                payee_id="PAYEE-TECH-DEPOT",
                display_name="Tech Depot",
                paypal_email="billing@techdepot.test",
            ),
            AllowedPayee(
                payee_id="PAYEE-CLEAN-CO",
                display_name="CleanCo Janitorial",
                paypal_email="orders@cleanco.test",
            ),
        ],
        allowed_purposes=["OFFICE_SUPPLIES", "HARDWARE", "FACILITIES"],
        new_payee_policy="BLOCK",
        red_tier_policy="ASK_OWNER",
        key_id="key-alice-1",
        private_key_hex=priv_hex,
    )
    state.mandates[mandate.mandate_id] = mandate
    print(f"[OK] Mandate created: {mandate.mandate_id} (Daily cap: $1,000.00)")

    # 2. Create Active Errand Intent
    intent = Intent.create_and_sign(
        intent_id="intent-errand-q4",
        mandate_id=mandate.mandate_id,
        description="Procure workstation peripherals and copy paper",
        max_total_minor=8500,  # $85.00
        items=[
            IntentItem(sku="PAPER-A4", qty=2, max_unit_price_minor=2000),
            IntentItem(sku="KEYBOARD-USB", qty=1, max_unit_price_minor=3500),
        ],
        deadline=now + timedelta(hours=18),
        private_key_hex=priv_hex,
    )
    state.intents[intent.intent_id] = intent
    print(f"[OK] Intent created: {intent.intent_id} (Max total: $85.00)")

    # 3. Seed an initial audit event trail
    state.audit_log.append(
        type_="MANDATE_CREATED",
        payload={
            "mandate_id": mandate.mandate_id,
            "owner_id": mandate.owner_id,
            "daily_cap_minor": mandate.daily_cap_minor,
            "currency": mandate.currency,
        },
        ts=now - timedelta(days=2),
    )
    state.audit_log.append(
        type_="INTENT_CREATED",
        payload={
            "intent_id": intent.intent_id,
            "mandate_id": intent.mandate_id,
            "max_total_minor": intent.max_total_minor,
        },
        ts=now - timedelta(hours=12),
    )

    print("[OK] Initial audit log initialized with 2 events.")

    # 4. Run benchmark runner to ensure results.json is up to date
    from app.eval.report import generate_markdown_report
    from app.eval.runner import EvalRunner

    runner = EvalRunner()
    results_data = runner.run_benchmark()

    # Generate RESULTS.md
    docs_file = Path(__file__).resolve().parents[2] / "docs" / "RESULTS.md"
    with open(docs_file, "w", encoding="utf-8") as f:
        f.write(generate_markdown_report(results_data))

    print("[OK] Benchmark results and docs/RESULTS.md refreshed.")
    print("=" * 60)
    print("  DEMO SEED COMPLETE - Ready for web UI and presentation")
    print("=" * 60)


if __name__ == "__main__":
    seed_demo_data()
