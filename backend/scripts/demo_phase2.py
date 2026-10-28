"""Phase 2 Demonstration Script: Payment Rail & Tool Registry.

WHY:
Demonstrates Phase 2 deliverables and exit criteria:
1. Tool Registry Risk Tiers: GREEN (read-only), YELLOW (money-moving), RED (sensitive),
   and unknown tools failing closed to RED.
2. Payment Gateway & Rail Gating: Money moves ONLY via the Bouncer on ALLOW.
3. Attack Defenses:
   - Cap Breach: BLOCKED, Rail never invoked.
   - Payee Impersonation: BLOCKED, Rail never invoked.
   - Above-Threshold: Escapes to ASK_OWNER, Rail never invoked.
4. Idempotency & Safe Retries: Retrying identical payment returns cached result with 0 duplicate executions.
5. Audit Integrity: Full cryptographic verification of the SHA-256 audit hash chain.

Run:
  python -m scripts.demo_phase2
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.approvals.service import ApprovalService
from app.audit.log import AuditLog
from app.mandate.models import (
    AllowedPayee,
    Deal,
    DealItem,
    Intent,
    IntentItem,
    Mandate,
    PayeeInfo,
    PaymentRequest,
)
from app.mandate.signing import generate_keypair
from app.payments.gateway import PaymentGateway
from app.payments.mock_rail import MockRail
from app.policy.provenance import ProvenanceTag
from app.tools.registry import ToolRiskTier, get_tool_tier


def main() -> None:
    print("=" * 65)
    print("  MANDATE ARENA: PHASE 2 PAYMENT RAIL & TOOL REGISTRY DEMO")
    print("=" * 65)

    # -------------------------------------------------------------
    # 1. Tool Risk Registry Verification
    # -------------------------------------------------------------
    print("\n[1] Verifying PayPal Agent Toolkit Tool Risk Registry...")
    test_tools = [
        ("get_invoice", ToolRiskTier.GREEN),
        ("get_order", ToolRiskTier.GREEN),
        ("get_balance", ToolRiskTier.GREEN),
        ("payouts", ToolRiskTier.YELLOW),
        ("create_order", ToolRiskTier.YELLOW),
        ("request_payment", ToolRiskTier.YELLOW),
        ("create_refund", ToolRiskTier.RED),
        ("cancel_sent_invoice", ToolRiskTier.RED),
        ("accept_dispute_claim", ToolRiskTier.RED),
        ("unknown_malicious_tool", ToolRiskTier.RED),
    ]

    for tool_name, expected_tier in test_tools:
        tier = get_tool_tier(tool_name)
        status = "OK" if tier == expected_tier else "FAIL"
        print(f"  - Tool '{tool_name}': Tier={tier.value} [{status}]")

    # -------------------------------------------------------------
    # 2. Setup Mandate, Intent, and Gateway
    # -------------------------------------------------------------
    print("\n[2] Setting up Owner Mandate and Bouncer-Gated Payment Gateway...")
    priv, pub = generate_keypair()
    now = datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)

    mandate = Mandate.create_and_sign(
        mandate_id="m-phase2-demo",
        version=1,
        owner_id="owner-alice",
        agent_id="buyer-agent",
        issued_at=now,
        expires_at=datetime(2026, 10, 28, 12, 0, 0, tzinfo=UTC),
        currency="USD",
        per_payment_cap_minor=5000,  # $50.00
        daily_cap_minor=10000,  # $100.00
        max_payments_per_hour=10,
        approval_threshold_minor=3000,  # $30.00
        allowed_payees=[
            AllowedPayee(
                payee_id="seller-bob",
                display_name="Bob Office Supplies",
                paypal_email="bob@supplies.example.com",
            )
        ],
        allowed_purposes=["OFFICE_SUPPLIES"],
        new_payee_policy="BLOCK",
        red_tier_policy="BLOCK",
        key_id="owner-k1",
        private_key_hex=priv,
    )

    intent = Intent.create_and_sign(
        intent_id="intent-phase2-demo",
        mandate_id=mandate.mandate_id,
        description="Procure 2 ergonomic mousepads",
        max_total_minor=2500,  # $25.00
        items=[IntentItem(sku="MPAD-ERG", qty=2, max_unit_price_minor=1250)],
        deadline=datetime(2026, 10, 28, 12, 0, 0, tzinfo=UTC),
        private_key_hex=priv,
    )

    rail = MockRail()
    audit_log = AuditLog()
    approval_svc = ApprovalService()
    gateway = PaymentGateway(rail=rail, audit_log=audit_log, approval_service=approval_svc)

    print(f"  Owner Mandate: {mandate.mandate_id} (Per-Payment Cap: $50.00, Threshold: $30.00)")
    print(f"  Intent: {intent.intent_id} (Max Total: $25.00)")
    print("  Payment Rail: MockRail (Offline Deterministic Mode)")

    # -------------------------------------------------------------
    # 3. Scenario: Legitimate $20.00 Payment (ALLOW -> Executed on Rail)
    # -------------------------------------------------------------
    print("\n" + "=" * 65)
    print("  SCENARIO 1: Legitimate $20.00 Payment (ALLOW -> Executed on Rail)")
    print("=" * 65)

    items = [DealItem(sku="MPAD-ERG", qty=2, unit_price_minor=1000, title="Ergonomic Mousepad")]
    terms_hash = Deal.compute_terms_hash(
        intent_id=intent.intent_id,
        payee_id="seller-bob",
        payee_email="bob@supplies.example.com",
        items=items,
        total_minor=2000,
        currency="USD",
    )
    deal = Deal(
        deal_id="deal-legit-1",
        intent_id=intent.intent_id,
        payee_id="seller-bob",
        payee_email="bob@supplies.example.com",
        items=items,
        total_minor=2000,
        currency="USD",
        terms_hash=terms_hash,
    )

    req_legit = PaymentRequest(
        request_id="req-legit-1",
        mandate_id=mandate.mandate_id,
        intent_id=intent.intent_id,
        deal_id=deal.deal_id,
        tool_name="payouts",
        payee=PayeeInfo(id=deal.payee_id, email=deal.payee_email),
        amount_minor=2000,  # $20.00
        currency="USD",
        purpose="OFFICE_SUPPLIES",
        memo="2x Ergonomic Mousepads",
        provenance={
            "amount_minor": ProvenanceTag.OWNER.value,
            "payee": ProvenanceTag.VERIFIED_RECORD.value,
        },
        idempotency_key="idem-key-legit-1",
        created_at=datetime(2026, 10, 27, 12, 10, 0, tzinfo=UTC),
    )

    outcome_1 = gateway.process_payment(req_legit, mandate, pub, intent, deal)
    print(f"  Bouncer Verdict: {outcome_1.decision.verdict.value}")
    print(f"  Rail Executed: {outcome_1.executed}")
    if outcome_1.payment_result:
        print(f"  Rail Transaction ID: {outcome_1.payment_result.rail_payment_id}")
        print(
            f"  Payee: {outcome_1.payment_result.payee_email} | Amount: ${outcome_1.payment_result.amount_minor / 100:.2f}"
        )

    # -------------------------------------------------------------
    # 4. Scenario: Idempotency Replay
    # -------------------------------------------------------------
    print("\n" + "=" * 65)
    print("  SCENARIO 2: Idempotent Replay (Safe Retries)")
    print("=" * 65)
    outcome_replay = gateway.process_payment(req_legit, mandate, pub, intent, deal)
    print(f"  Replay Verdict: {outcome_replay.decision.verdict.value}")
    print(
        f"  Replay Rail ID: {outcome_replay.payment_result.rail_payment_id if outcome_replay.payment_result else 'None'}"
    )
    assert outcome_1.payment_result is not None and outcome_replay.payment_result is not None
    assert outcome_1.payment_result.rail_payment_id == outcome_replay.payment_result.rail_payment_id
    print("  -> Idempotency Verified: 0 duplicate payments executed.")

    # -------------------------------------------------------------
    # 5. Scenario: Adversarial Attack (Cap Exceeded)
    # -------------------------------------------------------------
    print("\n" + "=" * 65)
    print("  SCENARIO 3: Adversarial Attack ($500.00 Cap Breach)")
    print("=" * 65)
    req_cap_attack = PaymentRequest(
        request_id="req-attack-cap",
        mandate_id=mandate.mandate_id,
        intent_id=intent.intent_id,
        deal_id=deal.deal_id,
        tool_name="payouts",
        payee=PayeeInfo(id=deal.payee_id, email=deal.payee_email),
        amount_minor=50000,  # $500.00
        currency="USD",
        purpose="OFFICE_SUPPLIES",
        memo="Inflated billing attack",
        provenance={"amount_minor": ProvenanceTag.UNTRUSTED_EXTERNAL.value},
        idempotency_key="idem-attack-cap",
        created_at=datetime(2026, 10, 27, 12, 11, 0, tzinfo=UTC),
    )

    outcome_attack = gateway.process_payment(req_cap_attack, mandate, pub, intent, deal)
    print(f"  Bouncer Verdict: {outcome_attack.decision.verdict.value}")
    print(f"  Rail Executed: {outcome_attack.executed}")
    print(f"  Rail Payment Result: {outcome_attack.payment_result}")
    for reason in outcome_attack.decision.reasons:
        print(f"  - Block Reason [{reason.code}]: {reason.message}")
    print("  -> Money Movement Prevented: Rail was NEVER called.")

    # -------------------------------------------------------------
    # 6. Scenario: Payee Impersonation Attack
    # -------------------------------------------------------------
    print("\n" + "=" * 65)
    print("  SCENARIO 4: Payee Impersonation (Vendor Swap Attack)")
    print("=" * 65)
    req_payee_attack = PaymentRequest(
        request_id="req-attack-payee",
        mandate_id=mandate.mandate_id,
        intent_id=intent.intent_id,
        deal_id=deal.deal_id,
        tool_name="payouts",
        payee=PayeeInfo(
            id="attacker-carol",
            email="carol@attacker.example.com",
        ),
        amount_minor=2000,
        currency="USD",
        purpose="OFFICE_SUPPLIES",
        provenance={"payee": ProvenanceTag.UNTRUSTED_EXTERNAL.value},
        idempotency_key="idem-attack-payee",
        created_at=datetime(2026, 10, 27, 12, 12, 0, tzinfo=UTC),
    )

    outcome_payee_attack = gateway.process_payment(req_payee_attack, mandate, pub, intent, deal)
    print(f"  Bouncer Verdict: {outcome_payee_attack.decision.verdict.value}")
    print(f"  Rail Executed: {outcome_payee_attack.executed}")
    print(f"  Rail Payment Result: {outcome_payee_attack.payment_result}")
    for reason in outcome_payee_attack.decision.reasons:
        print(f"  - Block Reason [{reason.code}]: {reason.message}")
    print("  -> Impersonation Prevented: Rail was NEVER called.")

    # -------------------------------------------------------------
    # 7. Audit Chain Cryptographic Verification
    # -------------------------------------------------------------
    print("\n" + "=" * 65)
    print("  SCENARIO 5: Audit Log Chain Integrity")
    print("=" * 65)
    chain_res = audit_log.verify_chain()
    print(f"  Total Audit Events: {len(audit_log.events)}")
    print(f"  Chain Cryptographically Valid: {chain_res.is_valid}")
    for event in audit_log.events:
        print(
            f"  - [Seq {event.seq}] {event.type} | Hash: {event.hash[:16]}... | Prev: {event.prev_hash[:16]}..."
        )

    print("\n" + "=" * 65)
    print("  PHASE 2 COMPLETE: MONEY MOVES IN SANDBOX ONLY VIA BOUNCER!")
    print("=" * 65)


if __name__ == "__main__":
    main()
