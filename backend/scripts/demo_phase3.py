"""Phase 3 Demonstration Script: AI Agents, Negotiation, and Bouncer Gating.

WHY:
Demonstrates Phase 3 deliverables and exit criteria:
1. Owner signs Mandate (standing rules) and Intent (errand budget) using Ed25519.
2. Buyer agent negotiates with Seller agent under Mandate constraints.
3. Deal is agreed and terms_hash locks payee, items, and total amount.
4. Buyer agent submits PaymentRequest with strict provenance tags.
5. Verifier agent (Second Opinion) evaluates payment consistency (P5: can only escalate).
6. Bouncer policy engine evaluates all 8 checks deterministically (P1).
7. Payment executes on PaymentRail (MockRail or Sandbox) only on ALLOW.
8. Full negotiation transcript, turns, decisions, and outcomes are chained in AuditLog.
9. Cryptographic hash chain verification proves 100% tamper evidence.

Run:
  python -m scripts.demo_phase3
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from app.agents.buyer import BuyerAgent
from app.agents.negotiation import NegotiationLoop
from app.agents.seller import SellerAgent
from app.agents.verifier import VerifierAgent
from app.audit.log import AuditLog
from app.llm.client import LLMResponse, ToolCall
from app.llm.fake import FakeLLMClient
from app.mandate.models import (
    AllowedPayee,
    Intent,
    IntentItem,
    Mandate,
)
from app.mandate.signing import generate_keypair
from app.payments.gateway import PaymentGateway
from app.payments.mock_rail import MockRail


def main() -> None:
    print("=" * 70)
    print("   MANDATE ARENA: PHASE 3 AI AGENTS & NEGOTIATION DEMO")
    print("=" * 70)

    # -------------------------------------------------------------
    # 1. Owner Signs Mandate & Intent (Ed25519)
    # -------------------------------------------------------------
    print("\n[1] Generating Ed25519 Keypair & Owner-Signed Documents...")
    priv_hex, pub_hex = generate_keypair()
    now = datetime.now(UTC)

    mandate = Mandate.create_and_sign(
        mandate_id="mandate-demo-p3",
        version=1,
        owner_id="owner-alice",
        agent_id="buyer-agent-01",
        issued_at=now,
        expires_at=now + timedelta(days=14),
        currency="USD",
        per_payment_cap_minor=15000,  # $150.00
        daily_cap_minor=50000,  # $500.00
        max_payments_per_hour=5,
        approval_threshold_minor=8000,  # $80.00
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
        ],
        allowed_purposes=["OFFICE_SUPPLIES", "EQUIPMENT"],
        new_payee_policy="BLOCK",
        red_tier_policy="ASK_OWNER",
        key_id="key-alice-1",
        private_key_hex=priv_hex,
    )
    print(f"  [OK] Mandate Signed: {mandate.mandate_id}")
    print(f"    - Daily Cap: ${mandate.daily_cap_minor / 100:.2f} {mandate.currency}")
    print(f"    - Per-Payment Cap: ${mandate.per_payment_cap_minor / 100:.2f}")
    print(f"    - Allowed Payees: {[p.paypal_email for p in mandate.allowed_payees]}")

    intent = Intent.create_and_sign(
        intent_id="intent-errand-01",
        mandate_id=mandate.mandate_id,
        description="Restock copy paper and ink cartridges for office",
        max_total_minor=7500,  # $75.00
        items=[
            IntentItem(sku="PAPER-A4", qty=2, max_unit_price_minor=2000),
            IntentItem(sku="INK-CART-BLK", qty=1, max_unit_price_minor=3500),
        ],
        deadline=now + timedelta(hours=12),
        private_key_hex=priv_hex,
    )
    print(f"  [OK] Intent Signed: {intent.intent_id}")
    print(f"    - Description: {intent.description}")
    print(f"    - Max Total: ${intent.max_total_minor / 100:.2f} {mandate.currency}")

    # -------------------------------------------------------------
    # 2. Setup Agents & Mock Environment
    # -------------------------------------------------------------
    print("\n[2] Setting up Buyer, Seller, Verifier, and Bouncer Gateway...")
    audit_log = AuditLog()
    rail = MockRail()
    gateway = PaymentGateway(rail=rail, audit_log=audit_log)

    # Scripted LLM responses for deterministic multi-turn negotiation
    seller_offer_tool = ToolCall(
        tool_name="make_offer",
        arguments={
            "sku": "PAPER-A4",
            "quantity": 2,
            "unit_price_minor": 1800,  # $18.00 each
            "total_minor": 3600,  # $36.00 total
            "currency": "USD",
            "payee_email": "supplies@officemax.test",
            "payee_id": "PAYEE-OFFICE-MAX",
        },
        call_id="call-seller-1",
    )
    seller_client = FakeLLMClient(
        [
            LLMResponse(
                content="Hello! We have A4 paper in stock at $18.00 per box.",
                tool_calls=[seller_offer_tool],
                prompt_tokens=25,
                completion_tokens=30,
                model="seller-gpt",
                finish_reason="tool_calls",
            )
        ]
    )

    buyer_deal_tool = ToolCall(
        tool_name="confirm_deal",
        arguments={
            "payee_id": "PAYEE-OFFICE-MAX",
            "payee_email": "supplies@officemax.test",
            "items": [
                {
                    "sku": "PAPER-A4",
                    "title": "A4 Copy Paper",
                    "qty": 2,
                    "unit_price_minor": 1800,
                }
            ],
            "total_minor": 3600,
            "currency": "USD",
        },
        call_id="call-buyer-1",
    )
    buyer_pay_tool = ToolCall(
        tool_name="request_payment",
        arguments={
            "purpose": "OFFICE_SUPPLIES",
            "memo": "Restock copy paper for office",
        },
        call_id="call-buyer-2",
    )
    buyer_client = FakeLLMClient(
        [
            LLMResponse(
                content="That price works. I will confirm the deal and submit for payment.",
                tool_calls=[buyer_deal_tool, buyer_pay_tool],
                prompt_tokens=40,
                completion_tokens=35,
                model="buyer-gpt",
                finish_reason="tool_calls",
            )
        ]
    )

    verifier_client = FakeLLMClient(
        [
            LLMResponse(
                content=json.dumps(
                    {
                        "consistent": True,
                        "concerns": [],
                        "suggested_verdict": "ALLOW",
                    }
                ),
                tool_calls=[],
                prompt_tokens=30,
                completion_tokens=25,
                model="verifier-gpt",
                finish_reason="stop",
            )
        ]
    )

    seller = SellerAgent(
        llm_client=seller_client,
        payee_email="supplies@officemax.test",
        payee_id="PAYEE-OFFICE-MAX",
    )
    buyer = BuyerAgent(
        mandate=mandate,
        intent=intent,
        llm_client=buyer_client,
    )
    verifier = VerifierAgent(llm_client=verifier_client)

    # -------------------------------------------------------------
    # 3. Execute Negotiation Loop
    # -------------------------------------------------------------
    print("\n[3] Executing Turn-Based Negotiation Loop...")
    loop = NegotiationLoop(
        buyer=buyer,
        seller=seller,
        gateway=gateway,
        audit_log=audit_log,
        verifier=verifier,
    )

    result = loop.run(
        initial_buyer_message="Hello, do you have A4 copy paper in stock?",
        owner_public_key_hex=pub_hex,
    )

    print(f"  [OK] Negotiation Status: {result.status.value}")
    print(f"  [OK] Total Turns: {result.total_turns}")
    for turn in result.turns:
        print(f"    - Turn {turn.turn_number}:")
        print(f"      Buyer:  {turn.buyer_message[:70]}...")
        print(f"      Seller: {turn.seller_message[:70]}...")

    # -------------------------------------------------------------
    # 4. Verifier Second Opinion & Gateway Outcome
    # -------------------------------------------------------------
    print("\n[4] Evaluating Security Verifications...")
    assert result.deal is not None, "Deal must be created"
    print("  [OK] Deal Confirmed:")
    print(f"    - Deal ID: {result.deal.deal_id}")
    print(f"    - Payee: {result.deal.payee_email} ({result.deal.payee_id})")
    print(f"    - Total: ${result.deal.total_minor / 100:.2f} {result.deal.currency}")
    print(f"    - Terms Hash: {result.deal.terms_hash[:16]}...")

    assert result.payment_request is not None, "Payment request must be created"
    print("  [OK] PaymentRequest Submitted to Bouncer:")
    print(f"    - Request ID: {result.payment_request.request_id}")
    print(f"    - Amount: ${result.payment_request.amount_minor / 100:.2f}")
    print(f"    - Provenance: {result.payment_request.provenance}")

    assert result.gateway_outcome is not None
    decision = result.gateway_outcome.decision
    print(f"  [OK] Bouncer Policy Verdict: {decision.verdict.value}")
    print(f"    - Policy Version: {decision.policy_version}")
    print("    - Reasons:")
    for r in decision.reasons:
        print(f"      [{r.check_id}] ({r.code}): {r.message}")

    print(
        f"  [OK] Payment Rail Execution: {'EXECUTED' if result.gateway_outcome.executed else 'NOT EXECUTED'}"
    )
    if result.gateway_outcome.payment_result:
        print(f"    - Rail Status: {result.gateway_outcome.payment_result.status.value}")
        print(f"    - Rail Transaction ID: {result.gateway_outcome.payment_result.rail_payment_id}")

    # -------------------------------------------------------------
    # 5. Cryptographic Audit Chain Verification
    # -------------------------------------------------------------
    print("\n[5] Cryptographic Audit Chain Verification...")
    print(f"  Total Audit Events Recorded: {len(audit_log)}")
    for ev in audit_log.events:
        print(f"    seq={ev.seq} | type={ev.type:<28} | hash={ev.hash[:16]}...")

    is_valid, err = audit_log.verify()
    print(f"\n  [OK] Audit Chain Integrity: {'VALID' if is_valid else 'COMPROMISED'}")
    assert is_valid is True, f"Audit chain verification failed: {err}"

    print("\n" + "=" * 70)
    print("  PHASE 3 EXIT CRITERIA MET: End-to-end happy path executed,")
    print("  Second opinion verified, money moved via Bouncer, audit chain intact.")
    print("=" * 70)


if __name__ == "__main__":
    main()
