"""Phase 1 Demonstration Script.

Demonstrates:
  1. $20 ALLOW - Legitimate transaction within all bounds
  2. $500 BLOCK - Per-payment cap enforcement
  3. Split payments BLOCK - Rolling daily cap enforcement (salami-slicing defense)
  4. Payee swap BLOCKED - Direct payee mismatch & unlisted payee defense
  5. Audit tamper detected - SHA-256 cryptographic hash chain verification

Run:
  python -m scripts.demo_phase1
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.audit.log import AuditEvent, AuditLog
from app.audit.verify import verify_chain
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
from app.mandate.signing import generate_keypair, sign_canonical_payload
from app.policy.checks import HistoricalPayment
from app.policy.engine import PolicyEngine
from app.policy.provenance import ProvenanceTag
from app.policy.verdict import Verdict


def print_header(title: str) -> None:
    print(f"\n{'=' * 65}")
    print(f"  {title}")
    print(f"{'=' * 65}")


def main() -> None:
    print_header("MANDATE ARENA: PHASE 1 ENGINE DEMONSTRATION")
    now = datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)
    audit_log = AuditLog()

    # 0. Setup: Owner generates Ed25519 keypair and signs Mandate
    priv, pub = generate_keypair()
    print("\n[Setup] Generated Owner Ed25519 Keypair.")
    print(f"  Owner Public Key: {pub[:16]}...{pub[-16:]}")

    mandate_dict = {
        "mandate_id": "mandate-demo-1",
        "version": 1,
        "owner_id": "owner-alice",
        "agent_id": "agent-buyer-1",
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(days=30)).isoformat(),
        "currency": "USD",
        "per_payment_cap_minor": 5000,  # $50.00
        "daily_cap_minor": 10000,  # $100.00
        "max_payments_per_hour": 10,
        "approval_threshold_minor": 3000,  # $30.00
        "allowed_payees": [
            {
                "payee_id": "seller-bob",
                "display_name": "Bob's Office Supplies",
                "paypal_email": "bob@supplies.example.com",
            }
        ],
        "allowed_purposes": ["OFFICE_SUPPLIES"],
        "new_payee_policy": "BLOCK",
        "red_tier_policy": "BLOCK",
        "key_id": "key-alice-main",
    }
    mandate_sig = sign_canonical_payload(mandate_dict, priv)

    mandate = Mandate(
        mandate_id="mandate-demo-1",
        version=1,
        owner_id="owner-alice",
        agent_id="agent-buyer-1",
        issued_at=now,
        expires_at=now + timedelta(days=30),
        currency="USD",
        per_payment_cap_minor=5000,
        daily_cap_minor=10000,
        max_payments_per_hour=10,
        approval_threshold_minor=3000,
        allowed_payees=[
            AllowedPayee(
                payee_id="seller-bob",
                display_name="Bob's Office Supplies",
                paypal_email="bob@supplies.example.com",
            )
        ],
        allowed_purposes=["OFFICE_SUPPLIES"],
        new_payee_policy="BLOCK",
        red_tier_policy="BLOCK",
        key_id="key-alice-main",
        signature=mandate_sig,
    )
    audit_log.append("MANDATE_REGISTERED", {"mandate_id": mandate.mandate_id})
    print("  Mandate signed: Cap=$50/txn, Daily Cap=$100, Threshold=$30")

    # Owner signs Intent
    intent_dict = {
        "intent_id": "intent-demo-1",
        "mandate_id": "mandate-demo-1",
        "description": "Purchase notebook packs for team",
        "max_total_minor": 2500,  # $25.00
        "items": [{"sku": "NOTEBOOK-A5", "qty": 2, "max_unit_price_minor": 1200}],
        "deadline": (now + timedelta(hours=6)).isoformat(),
    }
    intent_sig = sign_canonical_payload(intent_dict, priv)

    intent = Intent(
        intent_id="intent-demo-1",
        mandate_id="mandate-demo-1",
        description="Purchase notebook packs for team",
        max_total_minor=2500,
        items=[IntentItem(sku="NOTEBOOK-A5", qty=2, max_unit_price_minor=1200)],
        deadline=now + timedelta(hours=6),
        signature=intent_sig,
    )
    audit_log.append("INTENT_REGISTERED", {"intent_id": intent.intent_id})
    print("  Intent signed: Max $25.00 for 2x NOTEBOOK-A5")

    # ─── 1. $20 ALLOW ───
    print_header("1. SCENARIO: $20 ALLOW (Normal Errands Payment)")
    deal_items = [
        DealItem(sku="NOTEBOOK-A5", qty=2, unit_price_minor=1000, title="A5 Spiral Notebook")
    ]
    deal_hash = Deal.compute_terms_hash(
        intent_id=intent.intent_id,
        payee_id="seller-bob",
        payee_email="bob@supplies.example.com",
        items=deal_items,
        total_minor=2000,
        currency="USD",
    )
    deal = Deal(
        deal_id="deal-demo-1",
        intent_id=intent.intent_id,
        payee_id="seller-bob",
        payee_email="bob@supplies.example.com",
        items=deal_items,
        total_minor=2000,  # $20.00
        currency="USD",
        terms_hash=deal_hash,
    )

    req_20 = PaymentRequest(
        request_id="req-demo-20",
        mandate_id=mandate.mandate_id,
        intent_id=intent.intent_id,
        deal_id=deal.deal_id,
        tool_name="payouts",
        payee=PayeeInfo(id="seller-bob", email="bob@supplies.example.com"),
        amount_minor=2000,  # $20.00
        currency="USD",
        purpose="OFFICE_SUPPLIES",
        provenance={"amount_minor": ProvenanceTag.OWNER.value, "payee": ProvenanceTag.OWNER.value},
        idempotency_key="idemp-demo-20",
        created_at=now + timedelta(minutes=10),
    )

    dec_20 = PolicyEngine.evaluate(req_20, mandate, intent, deal, pub)
    print("  Proposed Amount: $20.00 | Payee: bob@supplies.example.com")
    print(f"  Bouncer Verdict: {dec_20.verdict.value}")
    for r in dec_20.reasons:
        print(f"    - [{r.check_id}] {r.code}: {r.message}")
    assert dec_20.verdict == Verdict.ALLOW, "Expected ALLOW"
    audit_log.append(
        "PAYMENT_EVALUATED", {"request_id": req_20.request_id, "verdict": dec_20.verdict.value}
    )

    # Record historical execution
    history: list[HistoricalPayment] = [
        HistoricalPayment(amount_minor=2000, executed_at=req_20.created_at)
    ]

    # ─── 2. $500 BLOCK ───
    print_header("2. SCENARIO: $500 BLOCK (Per-Payment Cap Exceeded)")
    req_500 = PaymentRequest(
        request_id="req-demo-500",
        mandate_id=mandate.mandate_id,
        intent_id=intent.intent_id,
        deal_id=deal.deal_id,
        tool_name="payouts",
        payee=PayeeInfo(id="seller-bob", email="bob@supplies.example.com"),
        amount_minor=50000,  # $500.00 (cap is $50.00)
        currency="USD",
        purpose="OFFICE_SUPPLIES",
        provenance={
            "amount_minor": ProvenanceTag.UNTRUSTED_EXTERNAL.value,
            "payee": ProvenanceTag.OWNER.value,
        },
        idempotency_key="idemp-demo-500",
        created_at=now + timedelta(minutes=20),
    )

    dec_500 = PolicyEngine.evaluate(req_500, mandate, intent, deal, pub, history=history)
    print("  Proposed Amount: $500.00 | Per-Payment Cap: $50.00")
    print(f"  Bouncer Verdict: {dec_500.verdict.value}")
    blocked_reasons = [
        r
        for r in dec_500.reasons
        if r.code in ("PER_PAYMENT_CAP_EXCEEDED", "DAILY_CAP_EXCEEDED", "DEAL_MISMATCH")
    ]
    for r in blocked_reasons:
        print(f"    - [{r.check_id}] {r.code}: {r.message}")
    assert dec_500.verdict == Verdict.BLOCK, "Expected BLOCK"
    audit_log.append(
        "PAYMENT_EVALUATED", {"request_id": req_500.request_id, "verdict": dec_500.verdict.value}
    )

    # ─── 3. SPLIT PAYMENTS BLOCK ───
    print_header("3. SCENARIO: SPLIT PAYMENTS BLOCK (Salami-Slicing Attack)")
    print("  Attacker attempts to drain funds using 3x $30 split payments.")
    print("  Daily Cap: $100.00 | Already spent: $20.00 | Remaining: $80.00")

    # Owner signed an intent for supplies up to $100
    intent_split_dict = {
        "intent_id": "intent-split-demo",
        "mandate_id": mandate.mandate_id,
        "description": "Bulk supplies replenishment",
        "max_total_minor": 10000,
        "items": [{"sku": "NOTEBOOK-A5", "qty": 10, "max_unit_price_minor": 1200}],
        "deadline": (now + timedelta(hours=6)).isoformat(),
    }
    intent_split_sig = sign_canonical_payload(intent_split_dict, priv)
    intent_split = Intent(
        intent_id="intent-split-demo",
        mandate_id=mandate.mandate_id,
        description="Bulk supplies replenishment",
        max_total_minor=10000,
        items=[IntentItem(sku="NOTEBOOK-A5", qty=10, max_unit_price_minor=1200)],
        deadline=now + timedelta(hours=6),
        signature=intent_split_sig,
    )

    split_items = [DealItem(sku="NOTEBOOK-A5", qty=3, unit_price_minor=1000, title="A5 Notebook")]
    deal_split1 = Deal(
        deal_id="deal-split-1",
        intent_id=intent_split.intent_id,
        payee_id="seller-bob",
        payee_email="bob@supplies.example.com",
        items=split_items,
        total_minor=3000,
        currency="USD",
        terms_hash=Deal.compute_terms_hash(
            intent_split.intent_id,
            "seller-bob",
            "bob@supplies.example.com",
            split_items,
            3000,
            "USD",
        ),
    )

    # Split payment 1: $30 (allowed, cumulative = $50)
    split1 = req_20.model_copy(
        update={
            "request_id": "req-split-1",
            "intent_id": intent_split.intent_id,
            "deal_id": deal_split1.deal_id,
            "amount_minor": 3000,
            "created_at": now + timedelta(minutes=30),
        }
    )

    dec_s1 = PolicyEngine.evaluate(split1, mandate, intent_split, deal_split1, pub, history=history)
    print(f"  Payment 1 ($30.00): Verdict={dec_s1.verdict.value} (Total today: $50.00)")
    history.append(HistoricalPayment(amount_minor=3000, executed_at=split1.created_at))

    # Split payment 2: $30 (allowed, cumulative = $80)
    split2 = split1.model_copy(
        update={"request_id": "req-split-2", "created_at": now + timedelta(minutes=35)}
    )
    dec_s2 = PolicyEngine.evaluate(split2, mandate, intent_split, deal_split1, pub, history=history)
    print(f"  Payment 2 ($30.00): Verdict={dec_s2.verdict.value} (Total today: $80.00)")
    history.append(HistoricalPayment(amount_minor=3000, executed_at=split2.created_at))

    # Split payment 3: $30 (cumulative = $110 > $100 daily cap -> BLOCKED!)
    split3 = split1.model_copy(
        update={"request_id": "req-split-3", "created_at": now + timedelta(minutes=40)}
    )
    dec_s3 = PolicyEngine.evaluate(split3, mandate, intent_split, deal_split1, pub, history=history)
    print(
        f"  Payment 3 ($30.00): Verdict={dec_s3.verdict.value} (Cumulative would be $110.00 > $100 cap)"
    )
    daily_cap_reason = next(r for r in dec_s3.reasons if r.code == "DAILY_CAP_EXCEEDED")
    print(
        f"    - [{daily_cap_reason.check_id}] {daily_cap_reason.code}: {daily_cap_reason.message}"
    )
    assert dec_s3.verdict == Verdict.BLOCK, "Expected split payment 3 to be BLOCKED by daily cap"
    audit_log.append(
        "PAYMENT_EVALUATED", {"request_id": split3.request_id, "verdict": dec_s3.verdict.value}
    )

    # ─── 4. PAYEE SWAP BLOCKED ───
    print_header("4. SCENARIO: PAYEE SWAP BLOCKED (BEC / Vendor Impersonation)")
    print("  Attacker injects prompt into negotiation to swap payee to evil@attacker.com.")
    req_swap = req_20.model_copy(
        update={
            "request_id": "req-swap-attack",
            "payee": PayeeInfo(id="attacker-carol", email="evil@attacker.com"),
        }
    )
    dec_swap = PolicyEngine.evaluate(req_swap, mandate, intent, deal, pub, history=history)
    print("  Requested Payee: evil@attacker.com | Deal Payee: bob@supplies.example.com")
    print(f"  Bouncer Verdict: {dec_swap.verdict.value}")
    for r in [r for r in dec_swap.reasons if r.code in ("PAYEE_MISMATCH", "NEW_PAYEE")]:
        print(f"    - [{r.check_id}] {r.code}: {r.message}")
    assert dec_swap.verdict == Verdict.BLOCK, "Expected payee swap to be BLOCKED"
    audit_log.append(
        "PAYMENT_EVALUATED", {"request_id": req_swap.request_id, "verdict": dec_swap.verdict.value}
    )

    # ─── 5. AUDIT TAMPER DETECTION ───
    print_header("5. SCENARIO: AUDIT CHAIN TAMPER DETECTION")
    print(f"  Audit chain contains {len(audit_log)} events chained with SHA-256.")

    # Check legitimate chain
    clean_result = verify_chain(audit_log.events)
    print(f"  Original Chain Verification: {clean_result}")
    assert clean_result.is_valid, "Original audit chain should be valid"

    # Attacker attempts to alter the audit log in storage (e.g. modify amount in event 3)
    events = list(audit_log.events)
    target_ev = events[2]
    tampered_ev = AuditEvent(
        seq=target_ev.seq,
        ts=target_ev.ts,
        type=target_ev.type,
        payload={"request_id": "req-demo-20", "verdict": "ALLOW", "forged_amount": "$2,000"},
        prev_hash=target_ev.prev_hash,
        hash=target_ev.hash,  # Stored hash no longer matches modified payload
    )
    events[2] = tampered_ev

    tampered_result = verify_chain(events)
    print(f"  Tampered Chain Verification: {tampered_result}")
    assert not tampered_result.is_valid, "Tampered audit chain must be detected as invalid"
    print(f"  -> Caught Error: {tampered_result.error}")

    print_header("PHASE 1 DEMONSTRATION COMPLETE: ALL 5 GUARANTEES VERIFIED!")


if __name__ == "__main__":
    main()
