"""Unit tests for owner approvals service.

WHY:
- Section 6: "Approvals: ASK_OWNER creates an ApprovalRequest bound to the hash of the exact
  PaymentRequest. It expires in 15 minutes, is single-use, and the owner cannot approve a
  BLOCK. After approval, hard caps are re-checked at execution."
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.approvals.service import ApprovalError, ApprovalService, ApprovalStatus
from app.mandate.models import AllowedPayee, Mandate, PayeeInfo, PaymentRequest
from app.mandate.signing import generate_keypair, sign_canonical_payload
from app.policy.checks import HistoricalPayment
from app.policy.verdict import Decision, Reason, Verdict


def _make_approval_fixture(
    verdict: Verdict = Verdict.ASK_OWNER,
) -> tuple[Mandate, PaymentRequest, Decision]:
    priv, _ = generate_keypair()
    now = datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)

    mandate_dict = {
        "mandate_id": "m-appr",
        "version": 1,
        "owner_id": "owner-1",
        "agent_id": "agent-1",
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(days=7)).isoformat(),
        "currency": "USD",
        "per_payment_cap_minor": 10000,
        "daily_cap_minor": 50000,
        "max_payments_per_hour": 5,
        "approval_threshold_minor": 2000,
        "allowed_payees": [
            {
                "payee_id": "seller-1",
                "display_name": "Acme",
                "paypal_email": "acme@example.com",
            }
        ],
        "allowed_purposes": ["SUPPLIES"],
        "new_payee_policy": "ASK_OWNER",
        "red_tier_policy": "BLOCK",
        "key_id": "key-1",
    }
    mandate_sig = sign_canonical_payload(mandate_dict, priv)

    mandate = Mandate(
        mandate_id="m-appr",
        version=1,
        owner_id="owner-1",
        agent_id="agent-1",
        issued_at=now,
        expires_at=now + timedelta(days=7),
        currency="USD",
        per_payment_cap_minor=10000,
        daily_cap_minor=50000,
        max_payments_per_hour=5,
        approval_threshold_minor=2000,
        allowed_payees=[
            AllowedPayee(
                payee_id="seller-1",
                display_name="Acme",
                paypal_email="acme@example.com",
            )
        ],
        allowed_purposes=["SUPPLIES"],
        new_payee_policy="ASK_OWNER",
        red_tier_policy="BLOCK",
        key_id="key-1",
        signature=mandate_sig,
    )

    req = PaymentRequest(
        request_id="r-appr-1",
        mandate_id="m-appr",
        intent_id="i-appr-1",
        deal_id="d-appr-1",
        tool_name="payouts",
        payee=PayeeInfo(id="seller-1", email="acme@example.com"),
        amount_minor=3000,
        currency="USD",
        purpose="SUPPLIES",
        idempotency_key="idemp-appr-1",
        created_at=now,
    )

    dec = Decision(
        verdict=verdict,
        reasons=[
            Reason(
                code="APPROVAL_THRESHOLD_EXCEEDED" if verdict == Verdict.ASK_OWNER else "BLOCKED",
                check_id="C4",
                message="Test reason",
            )
        ],
        policy_version="1.0.0",
        mandate_hash=mandate.compute_hash(),
        request_hash=req.compute_hash(),
        evaluated_at=now,
    )

    return mandate, req, dec


def test_create_approval_request() -> None:
    service = ApprovalService()
    _, req, dec = _make_approval_fixture(Verdict.ASK_OWNER)

    appr = service.create_request(req, dec, now=req.created_at)
    assert appr.status == ApprovalStatus.PENDING
    assert appr.request_hash == req.compute_hash()
    assert appr.expires_at == req.created_at + timedelta(minutes=15)


def test_cannot_create_approval_for_block() -> None:
    service = ApprovalService()
    _, req, dec = _make_approval_fixture(Verdict.BLOCK)

    with pytest.raises(ApprovalError, match="Owner cannot approve a BLOCK"):
        service.create_request(req, dec)


def test_approval_resolution_lifecycle() -> None:
    service = ApprovalService()
    _, req, dec = _make_approval_fixture(Verdict.ASK_OWNER)

    appr = service.create_request(req, dec, now=req.created_at)

    # Approve within 15 minutes
    resolved = service.approve(
        appr.approval_id, note="Approved by Alice", now=req.created_at + timedelta(minutes=5)
    )
    assert resolved.status == ApprovalStatus.APPROVED
    assert resolved.resolution_reason == "Approved by Alice"

    # Single-use: cannot approve again
    with pytest.raises(ApprovalError, match="already resolved"):
        service.approve(appr.approval_id, now=req.created_at + timedelta(minutes=6))


def test_approval_expiration_15_minutes() -> None:
    service = ApprovalService()
    _, req, dec = _make_approval_fixture(Verdict.ASK_OWNER)

    appr = service.create_request(req, dec, now=req.created_at)

    # Attempt approval at 16 minutes (expired)
    with pytest.raises(ApprovalError, match="expired"):
        service.approve(appr.approval_id, now=req.created_at + timedelta(minutes=16))

    updated = service.get_request(appr.approval_id)
    assert updated is not None
    assert updated.status == ApprovalStatus.EXPIRED


def test_denial_lifecycle() -> None:
    service = ApprovalService()
    _, req, dec = _make_approval_fixture(Verdict.ASK_OWNER)

    appr = service.create_request(req, dec, now=req.created_at)
    denied = service.deny(appr.approval_id, reason="Price too high", now=req.created_at)

    assert denied.status == ApprovalStatus.DENIED

    # Cannot approve after denial
    with pytest.raises(ApprovalError, match="already resolved"):
        service.approve(appr.approval_id)


def test_recheck_hard_caps_at_execution() -> None:
    mandate, req, _ = _make_approval_fixture(Verdict.ASK_OWNER)

    # Within limits: passes
    ok, err = ApprovalService.recheck_hard_caps_at_execution(req, mandate, history=[])
    assert ok is True
    assert err is None

    # Exceeds daily cap due to concurrent history: blocks
    concurrent_history = [
        HistoricalPayment(amount_minor=48000, executed_at=req.created_at - timedelta(hours=1))
    ]
    # req is 3000 -> 48000 + 3000 = 51000 > 50000 daily cap
    ok, err = ApprovalService.recheck_hard_caps_at_execution(
        req, mandate, history=concurrent_history
    )
    assert ok is False
    assert err is not None
    assert "daily cap" in err.lower()
