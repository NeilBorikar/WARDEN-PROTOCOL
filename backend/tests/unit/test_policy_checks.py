"""Unit tests for individual policy checks C1 through C8.

WHY:
- Section 6: Full verification of every individual check in the Bouncer.
- Proves exact failure codes, fail-closed behaviour, and condition boundaries.
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
from app.mandate.signing import generate_keypair
from app.policy.checks import (
    HistoricalPayment,
    check_c1_mandate_validity,
    check_c2_tool_tier,
    check_c3_payee_allowlist,
    check_c4_amount_caps,
    check_c5_rolling_limits,
    check_c6_deal_lock,
    check_c7_provenance,
    check_c8_purpose,
)
from app.policy.provenance import ProvenanceTag
from app.policy.verdict import Verdict


def _create_test_fixture(
    per_payment_cap: int = 10000,
    daily_cap: int = 50000,
    hourly_limit: int = 5,
    threshold: int = 2500,
    new_payee_policy: str = "BLOCK",
    red_tier_policy: str = "BLOCK",
) -> tuple[str, str, Mandate, Intent, Deal, PaymentRequest]:
    """Helper to create a fully consistent valid test fixture."""
    priv, pub = generate_keypair()
    now = datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)

    mandate = Mandate.create_and_sign(
        mandate_id="m-1",
        version=1,
        owner_id="owner-1",
        agent_id="agent-1",
        issued_at=now,
        expires_at=now + timedelta(days=7),
        currency="USD",
        per_payment_cap_minor=per_payment_cap,
        daily_cap_minor=daily_cap,
        max_payments_per_hour=hourly_limit,
        approval_threshold_minor=threshold,
        allowed_payees=[
            AllowedPayee(
                payee_id="seller-1",
                display_name="Acme Supplies",
                paypal_email="acme@example.com",
            )
        ],
        allowed_purposes=["SUBSCRIPTION", "SUPPLIES"],
        new_payee_policy=new_payee_policy,  # type: ignore[arg-type]
        red_tier_policy=red_tier_policy,  # type: ignore[arg-type]
        key_id="key-1",
        private_key_hex=priv,
    )

    intent = Intent.create_and_sign(
        intent_id="i-1",
        mandate_id="m-1",
        description="Buy pens",
        max_total_minor=3000,
        items=[IntentItem(sku="PEN-BLUE", qty=10, max_unit_price_minor=200)],
        deadline=now + timedelta(hours=4),
        private_key_hex=priv,
    )

    items = [DealItem(sku="PEN-BLUE", qty=10, unit_price_minor=200, title="Blue Pens")]
    terms_hash = Deal.compute_terms_hash(
        intent_id="i-1",
        payee_id="seller-1",
        payee_email="acme@example.com",
        items=items,
        total_minor=2000,
        currency="USD",
    )
    deal = Deal(
        deal_id="d-1",
        intent_id="i-1",
        payee_id="seller-1",
        payee_email="acme@example.com",
        items=items,
        total_minor=2000,
        currency="USD",
        terms_hash=terms_hash,
    )

    req = PaymentRequest(
        request_id="r-1",
        mandate_id="m-1",
        intent_id="i-1",
        deal_id="d-1",
        tool_name="payouts",
        payee=PayeeInfo(id="seller-1", email="acme@example.com"),
        amount_minor=2000,
        currency="USD",
        purpose="SUPPLIES",
        provenance={"amount_minor": ProvenanceTag.OWNER.value, "payee": ProvenanceTag.OWNER.value},
        idempotency_key="idemp-1",
        created_at=now + timedelta(minutes=10),
    )

    return priv, pub, mandate, intent, deal, req


# ─── C1 Tests ───


def test_c1_valid() -> None:
    _, pub, mandate, intent, _, req = _create_test_fixture()
    res = check_c1_mandate_validity(req, mandate, intent, pub)
    assert res.verdict == Verdict.ALLOW
    assert res.reason.code == "MANDATE_AND_INTENT_VALID"


def test_c1_expired_mandate() -> None:
    _, pub, mandate, intent, _, req = _create_test_fixture()
    expired_req = req.model_copy(update={"created_at": mandate.expires_at + timedelta(minutes=1)})
    res = check_c1_mandate_validity(expired_req, mandate, intent, pub)
    assert res.verdict == Verdict.BLOCK
    assert res.reason.code == "MANDATE_EXPIRED"


def test_c1_invalid_signature() -> None:
    _, _, mandate, intent, _, req = _create_test_fixture()
    _, other_pub = generate_keypair()
    res = check_c1_mandate_validity(req, mandate, intent, other_pub)
    assert res.verdict == Verdict.BLOCK
    assert res.reason.code == "MANDATE_INVALID_SIGNATURE"


def test_c1_revoked_mandate() -> None:
    _, pub, mandate, intent, _, req = _create_test_fixture()
    res = check_c1_mandate_validity(req, mandate, intent, pub, revoked_mandate_ids={"m-1"})
    assert res.verdict == Verdict.BLOCK
    assert res.reason.code == "MANDATE_REVOKED"


# ─── C2 Tests ───


def test_c2_green_tier() -> None:
    _, _, mandate, _, _, req = _create_test_fixture()
    green_req = req.model_copy(update={"tool_name": "get_invoice"})
    res = check_c2_tool_tier(green_req, mandate)
    assert res.verdict == Verdict.ALLOW
    assert res.reason.code == "TOOL_TIER_GREEN"


def test_c2_yellow_tier() -> None:
    _, _, mandate, _, _, req = _create_test_fixture()
    res = check_c2_tool_tier(req, mandate)
    assert res.verdict == Verdict.ALLOW
    assert res.reason.code == "TOOL_TIER_YELLOW"


def test_c2_red_tier_block() -> None:
    _, _, mandate, _, _, req = _create_test_fixture(red_tier_policy="BLOCK")
    red_req = req.model_copy(update={"tool_name": "delete_invoice"})
    res = check_c2_tool_tier(red_req, mandate)
    assert res.verdict == Verdict.BLOCK
    assert res.reason.code == "TOOL_TIER_RED"


def test_c2_red_tier_ask_owner() -> None:
    _, _, mandate, _, _, req = _create_test_fixture(red_tier_policy="ASK_OWNER")
    red_req = req.model_copy(update={"tool_name": "create_refund"})
    res = check_c2_tool_tier(red_req, mandate)
    assert res.verdict == Verdict.ASK_OWNER
    assert res.reason.code == "TOOL_TIER_RED"


# ─── C3 Tests ───


def test_c3_allowlisted_payee() -> None:
    _, _, mandate, _, deal, req = _create_test_fixture()
    res = check_c3_payee_allowlist(req, mandate, deal)
    assert res.verdict == Verdict.ALLOW
    assert res.reason.code == "PAYEE_ALLOWLISTED"


def test_c3_new_payee_block() -> None:
    _, _, mandate, _, _, req = _create_test_fixture(new_payee_policy="BLOCK")
    unlisted_req = req.model_copy(
        update={"payee": PayeeInfo(id="stranger", email="stranger@example.com")}
    )
    res = check_c3_payee_allowlist(unlisted_req, mandate, None)
    assert res.verdict == Verdict.BLOCK
    assert res.reason.code == "NEW_PAYEE"


def test_c3_new_payee_ask_owner() -> None:
    _, _, mandate, _, _, req = _create_test_fixture(new_payee_policy="ASK_OWNER")
    unlisted_req = req.model_copy(
        update={"payee": PayeeInfo(id="stranger", email="stranger@example.com")}
    )
    res = check_c3_payee_allowlist(unlisted_req, mandate, None)
    assert res.verdict == Verdict.ASK_OWNER
    assert res.reason.code == "NEW_PAYEE"


def test_c3_payee_mismatch_with_deal() -> None:
    _, _, mandate, _, deal, req = _create_test_fixture()
    swapped_req = req.model_copy(
        update={"payee": PayeeInfo(id="attacker", email="attacker@example.com")}
    )
    res = check_c3_payee_allowlist(swapped_req, mandate, deal)
    assert res.verdict == Verdict.BLOCK
    assert res.reason.code == "PAYEE_MISMATCH"


# ─── C4 Tests ───


def test_c4_within_caps() -> None:
    _, _, mandate, _, _, req = _create_test_fixture(threshold=2500, per_payment_cap=10000)
    res = check_c4_amount_caps(req, mandate)  # 2000 USD <= 2500 threshold
    assert res.verdict == Verdict.ALLOW
    assert res.reason.code == "AMOUNT_WITHID_CAPS" or res.reason.code == "AMOUNT_WITHIN_CAPS"


def test_c4_approval_threshold_exceeded() -> None:
    _, _, mandate, _, _, req = _create_test_fixture(threshold=1500, per_payment_cap=10000)
    res = check_c4_amount_caps(req, mandate)  # 2000 USD > 1500 threshold
    assert res.verdict == Verdict.ASK_OWNER
    assert res.reason.code == "APPROVAL_THRESHOLD_EXCEEDED"


def test_c4_per_payment_cap_exceeded() -> None:
    _, _, mandate, _, _, req = _create_test_fixture(threshold=1500, per_payment_cap=1800)
    res = check_c4_amount_caps(req, mandate)  # 2000 USD > 1800 cap
    assert res.verdict == Verdict.BLOCK
    assert res.reason.code == "PER_PAYMENT_CAP_EXCEEDED"


def test_c4_currency_mismatch() -> None:
    _, _, mandate, _, _, req = _create_test_fixture()
    eur_req = req.model_copy(update={"currency": "EUR"})
    res = check_c4_amount_caps(eur_req, mandate)
    assert res.verdict == Verdict.BLOCK
    assert res.reason.code == "CURRENCY_MISMATCH"


# ─── C5 Tests ───


def test_c5_rolling_limits_allow() -> None:
    _, _, mandate, _, _, req = _create_test_fixture(daily_cap=50000, hourly_limit=5)
    history = [
        HistoricalPayment(amount_minor=10000, executed_at=req.created_at - timedelta(hours=2))
    ]
    res = check_c5_rolling_limits(req, mandate, history)  # 10000 + 2000 = 12000 <= 50000
    assert res.verdict == Verdict.ALLOW
    assert res.reason.code == "ROLLING_LIMITS_SATISFIED"


def test_c5_daily_cap_exceeded() -> None:
    _, _, mandate, _, _, req = _create_test_fixture(daily_cap=10000)
    history = [
        HistoricalPayment(amount_minor=9000, executed_at=req.created_at - timedelta(hours=2))
    ]
    res = check_c5_rolling_limits(req, mandate, history)  # 9000 + 2000 = 11000 > 10000
    assert res.verdict == Verdict.BLOCK
    assert res.reason.code == "DAILY_CAP_EXCEEDED"


def test_c5_hourly_velocity_exceeded() -> None:
    _, _, mandate, _, _, req = _create_test_fixture(hourly_limit=2)
    history = [
        HistoricalPayment(amount_minor=100, executed_at=req.created_at - timedelta(minutes=10)),
        HistoricalPayment(amount_minor=100, executed_at=req.created_at - timedelta(minutes=5)),
    ]
    # Projected is 2 + 1 = 3 > 2
    res = check_c5_rolling_limits(req, mandate, history)
    assert res.verdict == Verdict.BLOCK
    assert res.reason.code == "HOURLY_VELOCITY_EXCEEDED"


# ─── C6 Tests ───


def test_c6_deal_lock_valid() -> None:
    _, _, _, intent, deal, req = _create_test_fixture()
    res = check_c6_deal_lock(req, intent, deal)
    assert res.verdict == Verdict.ALLOW
    assert res.reason.code == "DEAL_LOCK_SATISFIED"


def test_c6_deal_missing() -> None:
    _, _, _, intent, _, req = _create_test_fixture()
    res = check_c6_deal_lock(req, intent, None)
    assert res.verdict == Verdict.BLOCK
    assert res.reason.code == "DEAL_MISSING"


def test_c6_amount_mismatch() -> None:
    _, _, _, intent, deal, req = _create_test_fixture()
    mismatch_req = req.model_copy(update={"amount_minor": 2500})
    res = check_c6_deal_lock(mismatch_req, intent, deal)
    assert res.verdict == Verdict.BLOCK
    assert res.reason.code == "DEAL_MISMATCH"


def test_c6_intent_max_total_exceeded() -> None:
    _, _, _, intent, deal, req = _create_test_fixture()
    small_intent = intent.model_copy(update={"max_total_minor": 1500})
    res = check_c6_deal_lock(req, small_intent, deal)
    assert res.verdict == Verdict.BLOCK
    assert res.reason.code == "INTENT_MAX_TOTAL_EXCEEDED"


# ─── C7 Tests ───


def test_c7_provenance_conflict() -> None:
    _, _, _, _, deal, req = _create_test_fixture()
    conflict_req = req.model_copy(
        update={
            "amount_minor": 9999,
            "provenance": {"amount_minor": ProvenanceTag.UNTRUSTED_EXTERNAL.value},
        }
    )
    res = check_c7_provenance(conflict_req, deal)
    assert res.verdict == Verdict.BLOCK
    assert res.reason.code == "UNTRUSTED_DATA_CONFLICT"


# ─── C8 Tests ───


def test_c8_purpose_allowed() -> None:
    _, _, mandate, _, _, req = _create_test_fixture()
    res = check_c8_purpose(req, mandate)
    assert res.verdict == Verdict.ALLOW
    assert res.reason.code == "PURPOSE_ALLOWED"


def test_c8_purpose_disallowed() -> None:
    _, _, mandate, _, _, req = _create_test_fixture()
    bad_req = req.model_copy(update={"purpose": "GAMBLING"})
    res = check_c8_purpose(bad_req, mandate)
    assert res.verdict == Verdict.BLOCK
    assert res.reason.code == "PURPOSE_DISALLOWED"
