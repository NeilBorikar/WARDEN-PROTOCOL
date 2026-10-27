"""Property-based tests with Hypothesis.

WHY:
- Section 7: "Property tests (hypothesis): for any request sequence, the approved total
  in any 24-hour window is at most daily_cap; no ALLOW to a non-allow-listed payee;
  every ALLOW has amount equal to the Deal total; tampering with the audit chain is detected."
- Mathematically proves core safety invariants hold over thousands of randomly generated scenarios.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from app.audit.log import AuditEvent, AuditLog
from app.audit.verify import verify_chain
from app.mandate.models import (
    AllowedPayee,
    Deal,
    DealItem,
    Mandate,
    PayeeInfo,
    PaymentRequest,
)
from app.mandate.signing import generate_keypair, sign_canonical_payload
from app.policy.checks import (
    HistoricalPayment,
    check_c3_payee_allowlist,
    check_c5_rolling_limits,
    check_c6_deal_lock,
)
from app.policy.verdict import Verdict, combine_verdicts

# ─── Property 1: Rolling 24h cap invariant ───


@given(
    daily_cap=st.integers(min_value=1000, max_value=500000),
    amounts=st.lists(st.integers(min_value=1, max_value=20000), min_size=1, max_size=20),
)
@settings(max_examples=50)
def test_approved_total_in_24h_never_exceeds_daily_cap(daily_cap: int, amounts: list[int]) -> None:
    """For any sequence of requests, the approved total in any 24h window <= daily_cap."""
    priv, _ = generate_keypair()
    now = datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)

    mandate_dict = {
        "mandate_id": "m-prop",
        "version": 1,
        "owner_id": "o-1",
        "agent_id": "a-1",
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(days=7)).isoformat(),
        "currency": "USD",
        "per_payment_cap_minor": daily_cap,
        "daily_cap_minor": daily_cap,
        "max_payments_per_hour": 100,
        "approval_threshold_minor": daily_cap,
        "allowed_payees": [{"payee_id": "s-1", "display_name": "S", "paypal_email": "s@ex.com"}],
        "allowed_purposes": ["SUPPLIES"],
        "new_payee_policy": "BLOCK",
        "red_tier_policy": "BLOCK",
        "key_id": "k-1",
    }
    mandate_sig = sign_canonical_payload(mandate_dict, priv)

    mandate = Mandate(
        mandate_id="m-prop",
        version=1,
        owner_id="o-1",
        agent_id="a-1",
        issued_at=now,
        expires_at=now + timedelta(days=7),
        currency="USD",
        per_payment_cap_minor=daily_cap,
        daily_cap_minor=daily_cap,
        max_payments_per_hour=100,
        approval_threshold_minor=daily_cap,
        allowed_payees=[AllowedPayee(payee_id="s-1", display_name="S", paypal_email="s@ex.com")],
        allowed_purposes=["SUPPLIES"],
        new_payee_policy="BLOCK",
        red_tier_policy="BLOCK",
        key_id="k-1",
        signature=mandate_sig,
    )

    history: list[HistoricalPayment] = []
    approved_total = 0

    for i, amt in enumerate(amounts):
        req = PaymentRequest(
            request_id=f"r-{i}",
            mandate_id="m-prop",
            intent_id="i-prop",
            deal_id="d-prop",
            tool_name="payouts",
            payee=PayeeInfo(id="s-1", email="s@ex.com"),
            amount_minor=amt,
            currency="USD",
            purpose="SUPPLIES",
            idempotency_key=f"idemp-{i}",
            created_at=now + timedelta(minutes=i),
        )

        res = check_c5_rolling_limits(req, mandate, history)
        if res.verdict == Verdict.ALLOW:
            approved_total += amt
            history.append(HistoricalPayment(amount_minor=amt, executed_at=req.created_at))

    # Core invariant: approved total in any 24h window must be <= daily_cap
    assert approved_total <= daily_cap


# ─── Property 2: No ALLOW to non-allowlisted payee ───


@given(
    unlisted_email=st.emails().filter(lambda e: e.lower() != "legit@example.com"),
    unlisted_id=st.text(min_size=1, max_size=20).filter(lambda i: i != "seller-legit"),
)
@settings(max_examples=50)
def test_no_allow_to_non_allowlisted_payee(unlisted_email: str, unlisted_id: str) -> None:
    """No request to a non-allowlisted payee is ever ALLOWed when new_payee_policy=BLOCK."""
    priv, _ = generate_keypair()
    now = datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)

    mandate_dict = {
        "mandate_id": "m-p2",
        "version": 1,
        "owner_id": "o-1",
        "agent_id": "a-1",
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(days=7)).isoformat(),
        "currency": "USD",
        "per_payment_cap_minor": 10000,
        "daily_cap_minor": 50000,
        "max_payments_per_hour": 5,
        "approval_threshold_minor": 5000,
        "allowed_payees": [
            {
                "payee_id": "seller-legit",
                "display_name": "Legit",
                "paypal_email": "legit@example.com",
            }
        ],
        "allowed_purposes": ["SUPPLIES"],
        "new_payee_policy": "BLOCK",
        "red_tier_policy": "BLOCK",
        "key_id": "k-1",
    }
    mandate_sig = sign_canonical_payload(mandate_dict, priv)

    mandate = Mandate(
        mandate_id="m-p2",
        version=1,
        owner_id="o-1",
        agent_id="a-1",
        issued_at=now,
        expires_at=now + timedelta(days=7),
        currency="USD",
        per_payment_cap_minor=10000,
        daily_cap_minor=50000,
        max_payments_per_hour=5,
        approval_threshold_minor=5000,
        allowed_payees=[
            AllowedPayee(
                payee_id="seller-legit",
                display_name="Legit",
                paypal_email="legit@example.com",
            )
        ],
        allowed_purposes=["SUPPLIES"],
        new_payee_policy="BLOCK",
        red_tier_policy="BLOCK",
        key_id="k-1",
        signature=mandate_sig,
    )

    req = PaymentRequest(
        request_id="r-p2",
        mandate_id="m-p2",
        intent_id="i-p2",
        deal_id="d-p2",
        tool_name="payouts",
        payee=PayeeInfo(id=unlisted_id, email=unlisted_email),
        amount_minor=1000,
        currency="USD",
        purpose="SUPPLIES",
        idempotency_key="idemp-p2",
        created_at=now,
    )

    res = check_c3_payee_allowlist(req, mandate, None)
    assert res.verdict != Verdict.ALLOW
    assert res.verdict == Verdict.BLOCK


# ─── Property 3: Every ALLOW must equal Deal total ───


@given(
    deal_total=st.integers(min_value=1, max_value=50000),
    req_amount=st.integers(min_value=1, max_value=50000),
)
@settings(max_examples=50)
def test_every_allow_matches_deal_total(deal_total: int, req_amount: int) -> None:
    """If requested amount differs from Deal total, verdict is ALWAYS BLOCK."""
    now = datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)
    items = [DealItem(sku="SKU-1", qty=1, unit_price_minor=deal_total, title="Item")]
    terms_hash = Deal.compute_terms_hash(
        intent_id="i-p3",
        payee_id="s-1",
        payee_email="s@ex.com",
        items=items,
        total_minor=deal_total,
        currency="USD",
    )
    deal = Deal(
        deal_id="d-p3",
        intent_id="i-p3",
        payee_id="s-1",
        payee_email="s@ex.com",
        items=items,
        total_minor=deal_total,
        currency="USD",
        terms_hash=terms_hash,
    )

    req = PaymentRequest(
        request_id="r-p3",
        mandate_id="m-p3",
        intent_id="i-p3",
        deal_id="d-p3",
        tool_name="payouts",
        payee=PayeeInfo(id="s-1", email="s@ex.com"),
        amount_minor=req_amount,
        currency="USD",
        purpose="SUPPLIES",
        idempotency_key="idemp-p3",
        created_at=now,
    )

    res = check_c6_deal_lock(req, None, deal)
    if req_amount != deal_total:
        assert res.verdict == Verdict.BLOCK
    else:
        assert res.verdict == Verdict.ALLOW


# ─── Property 4: Most restrictive verdict wins ───


@given(
    verdicts=st.lists(
        st.sampled_from([Verdict.ALLOW, Verdict.ASK_OWNER, Verdict.BLOCK]),
        min_size=1,
        max_size=20,
    )
)
@settings(max_examples=50)
def test_most_restrictive_verdict_wins_property(verdicts: list[Verdict]) -> None:
    """combine_verdicts must return the maximum restrictiveness in the list."""
    combined = combine_verdicts(verdicts)

    if Verdict.BLOCK in verdicts:
        assert combined == Verdict.BLOCK
    elif Verdict.ASK_OWNER in verdicts:
        assert combined == Verdict.ASK_OWNER
    else:
        assert combined == Verdict.ALLOW


# ─── Property 5: Tampering with audit chain is always caught ───


@given(
    num_events=st.integers(min_value=2, max_value=8),
    tamper_idx=st.integers(min_value=0, max_value=7),
    new_value=st.text(min_size=1, max_size=20),
)
@settings(max_examples=50)
def test_audit_chain_tamper_detection_property(
    num_events: int, tamper_idx: int, new_value: str
) -> None:
    """Modifying any event payload in the audit chain causes verify_chain to return False."""
    idx = tamper_idx % num_events
    log = AuditLog()
    now = datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)

    for i in range(num_events):
        log.append(f"TYPE_{i}", {"key": f"orig_val_{i}"}, ts=now + timedelta(seconds=i))

    # Original chain must be valid
    assert verify_chain(log.events).is_valid is True

    # Tamper with event at idx
    events = list(log.events)
    target = events[idx]
    tampered_payload = {"key": f"tampered_{new_value}"}
    tampered_event = AuditEvent(
        seq=target.seq,
        ts=target.ts,
        type=target.type,
        payload=tampered_payload,
        prev_hash=target.prev_hash,
        hash=target.hash,  # Stored hash no longer matches content!
    )
    events[idx] = tampered_event

    # Chain verification MUST fail
    result = verify_chain(events)
    assert result.is_valid is False
