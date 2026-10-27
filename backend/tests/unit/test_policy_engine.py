"""Unit tests for PolicyEngine and verdict combination.

WHY:
- Section 6 & Principle P5: Most restrictive verdict wins (BLOCK > ASK_OWNER > ALLOW).
- Principle P4: Fail closed on unexpected errors or missing data.
- Read-only tools (GREEN) allow instant query without requiring Deal.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

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
from app.policy.engine import PolicyEngine
from app.policy.provenance import ProvenanceTag
from app.policy.verdict import Verdict, combine_verdicts


def _make_engine_fixture() -> tuple[str, Mandate, Intent, Deal, PaymentRequest]:
    priv, pub = generate_keypair()
    now = datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)

    mandate_dict = {
        "mandate_id": "m-eng",
        "version": 1,
        "owner_id": "owner-1",
        "agent_id": "agent-1",
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(days=7)).isoformat(),
        "currency": "USD",
        "per_payment_cap_minor": 10000,
        "daily_cap_minor": 50000,
        "max_payments_per_hour": 5,
        "approval_threshold_minor": 3000,
        "allowed_payees": [
            {
                "payee_id": "seller-eng",
                "display_name": "Acme Corp",
                "paypal_email": "acme@example.com",
            }
        ],
        "allowed_purposes": ["SUPPLIES"],
        "new_payee_policy": "ASK_OWNER",
        "red_tier_policy": "BLOCK",
        "key_id": "key-eng",
    }
    mandate_sig = sign_canonical_payload(mandate_dict, priv)

    mandate = Mandate(
        mandate_id="m-eng",
        version=1,
        owner_id="owner-1",
        agent_id="agent-1",
        issued_at=now,
        expires_at=now + timedelta(days=7),
        currency="USD",
        per_payment_cap_minor=10000,
        daily_cap_minor=50000,
        max_payments_per_hour=5,
        approval_threshold_minor=3000,
        allowed_payees=[
            AllowedPayee(
                payee_id="seller-eng",
                display_name="Acme Corp",
                paypal_email="acme@example.com",
            )
        ],
        allowed_purposes=["SUPPLIES"],
        new_payee_policy="ASK_OWNER",
        red_tier_policy="BLOCK",
        key_id="key-eng",
        signature=mandate_sig,
    )

    intent_dict = {
        "intent_id": "i-eng",
        "mandate_id": "m-eng",
        "description": "Buy supplies",
        "max_total_minor": 5000,
        "items": [{"sku": "SUP-1", "qty": 1, "max_unit_price_minor": 5000}],
        "deadline": (now + timedelta(hours=4)).isoformat(),
    }
    intent_sig = sign_canonical_payload(intent_dict, priv)

    intent = Intent(
        intent_id="i-eng",
        mandate_id="m-eng",
        description="Buy supplies",
        max_total_minor=5000,
        items=[IntentItem(sku="SUP-1", qty=1, max_unit_price_minor=5000)],
        deadline=now + timedelta(hours=4),
        signature=intent_sig,
    )

    items = [DealItem(sku="SUP-1", qty=1, unit_price_minor=2000, title="Widget")]
    terms_hash = Deal.compute_terms_hash(
        intent_id="i-eng",
        payee_id="seller-eng",
        payee_email="acme@example.com",
        items=items,
        total_minor=2000,
        currency="USD",
    )
    deal = Deal(
        deal_id="d-eng",
        intent_id="i-eng",
        payee_id="seller-eng",
        payee_email="acme@example.com",
        items=items,
        total_minor=2000,
        currency="USD",
        terms_hash=terms_hash,
    )

    req = PaymentRequest(
        request_id="r-eng",
        mandate_id="m-eng",
        intent_id="i-eng",
        deal_id="d-eng",
        tool_name="payouts",
        payee=PayeeInfo(id="seller-eng", email="acme@example.com"),
        amount_minor=2000,
        currency="USD",
        purpose="SUPPLIES",
        provenance={"amount_minor": ProvenanceTag.OWNER.value, "payee": ProvenanceTag.OWNER.value},
        idempotency_key="idemp-eng",
        created_at=now + timedelta(minutes=5),
    )

    return pub, mandate, intent, deal, req


def test_verdict_combination_priority() -> None:
    """Verify BLOCK > ASK_OWNER > ALLOW priority."""
    assert combine_verdicts([Verdict.ALLOW, Verdict.ALLOW]) == Verdict.ALLOW
    assert combine_verdicts([Verdict.ALLOW, Verdict.ASK_OWNER]) == Verdict.ASK_OWNER
    assert combine_verdicts([Verdict.ASK_OWNER, Verdict.ALLOW]) == Verdict.ASK_OWNER
    assert combine_verdicts([Verdict.ASK_OWNER, Verdict.BLOCK]) == Verdict.BLOCK
    assert combine_verdicts([Verdict.BLOCK, Verdict.ALLOW]) == Verdict.BLOCK
    assert combine_verdicts([]) == Verdict.BLOCK  # fail-closed


def test_policy_engine_allow_happy_path() -> None:
    pub, mandate, intent, deal, req = _make_engine_fixture()
    decision = PolicyEngine.evaluate(req, mandate, intent, deal, pub)
    assert decision.is_allowed
    assert decision.verdict == Verdict.ALLOW
    assert len(decision.reasons) > 0


def test_policy_engine_ask_owner_threshold() -> None:
    pub, mandate, intent, deal, req = _make_engine_fixture()
    # Amount 3500 exceeds threshold 3000 but within per_payment_cap 10000
    items = [DealItem(sku="SUP-1", qty=1, unit_price_minor=3500, title="Widget")]
    deal_3500 = deal.model_copy(
        update={
            "total_minor": 3500,
            "items": items,
            "terms_hash": Deal.compute_terms_hash(
                intent.intent_id, deal.payee_id, deal.payee_email, items, 3500, "USD"
            ),
        }
    )
    req_3500 = req.model_copy(update={"amount_minor": 3500})
    decision = PolicyEngine.evaluate(req_3500, mandate, intent, deal_3500, pub)
    assert decision.requires_approval
    assert decision.verdict == Verdict.ASK_OWNER


def test_policy_engine_most_restrictive_wins() -> None:
    pub, mandate, intent, deal, req = _make_engine_fixture()
    # Trigger ASK_OWNER (unlisted payee) AND BLOCK (exceeds per_payment_cap)
    unlisted_big_req = req.model_copy(
        update={
            "payee": PayeeInfo(id="new-vendor", email="new@example.com"),
            "amount_minor": 999999,  # exceeds cap
        }
    )
    decision = PolicyEngine.evaluate(unlisted_big_req, mandate, intent, deal, pub)
    assert decision.is_blocked
    assert decision.verdict == Verdict.BLOCK


def test_policy_engine_green_tool_bypass() -> None:
    pub, mandate, _, _, req = _make_engine_fixture()
    read_req = req.model_copy(update={"tool_name": "list_invoices"})
    decision = PolicyEngine.evaluate(read_req, mandate, None, None, pub)
    assert decision.is_allowed
    assert decision.verdict == Verdict.ALLOW
