"""Live PayPal Sandbox integration tests.

WHY:
Per SPEC.md Phase 2:
"Sandbox integration tests (skipped without creds)."
These tests execute against the live PayPal sandbox when PAYPAL_CLIENT_ID
and PAYPAL_CLIENT_SECRET are provided in environment variables.
In CI without credentials, they are skipped automatically.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest

from app.mandate.models import AllowedPayee, Mandate, PayeeInfo, PaymentRequest
from app.mandate.signing import generate_keypair
from app.payments.paypal_payouts import PayPalPayoutsRail
from app.payments.rail import RailPaymentStatus
from app.payments.token import PayPalTokenManager
from app.policy.provenance import ProvenanceTag
from app.policy.verdict import Decision, Verdict

CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
SANDBOX_EMAIL = os.environ.get("PAYPAL_SANDBOX_RECEIVER", "sb-buyer@personal.example.com")

requires_sandbox = pytest.mark.skipif(
    not (CLIENT_ID and CLIENT_SECRET),
    reason="PayPal sandbox credentials not set in environment (PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET)",
)


@requires_sandbox
def test_sandbox_token_and_payout_execution() -> None:
    """Execute live token acquisition and sandbox payout."""
    token_mgr = PayPalTokenManager(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        base_url="https://api-m.sandbox.paypal.com",
    )
    token = token_mgr.get_token()
    assert token != ""
    assert len(token) > 20

    rail = PayPalPayoutsRail(token_manager=token_mgr)

    # Prepare legitimate request
    priv, _ = generate_keypair()
    now = datetime.now(UTC)
    mandate = Mandate.create_and_sign(
        mandate_id=f"m-sb-{uuid.uuid4().hex[:6]}",
        version=1,
        owner_id="owner-live",
        agent_id="agent-live",
        issued_at=now,
        expires_at=datetime(2030, 1, 1, tzinfo=UTC),
        currency="USD",
        per_payment_cap_minor=500,
        daily_cap_minor=1000,
        max_payments_per_hour=10,
        approval_threshold_minor=500,
        allowed_payees=[
            AllowedPayee(
                payee_id="sandbox-receiver",
                display_name="Sandbox Receiver",
                paypal_email=SANDBOX_EMAIL,
            )
        ],
        allowed_purposes=["SANDBOX_TEST"],
        new_payee_policy="BLOCK",
        red_tier_policy="BLOCK",
        key_id="k1",
        private_key_hex=priv,
    )

    req = PaymentRequest(
        request_id=f"req-sb-{uuid.uuid4().hex[:8]}",
        mandate_id=mandate.mandate_id,
        intent_id="intent-sb",
        deal_id="deal-sb",
        tool_name="payouts",
        payee=PayeeInfo(
            id="sandbox-receiver",
            email=SANDBOX_EMAIL,
        ),
        amount_minor=100,  # $1.00
        currency="USD",
        purpose="SANDBOX_TEST",
        memo="Mandate Arena automated sandbox test",
        provenance={"amount_minor": ProvenanceTag.OWNER.value},
        idempotency_key=f"idem-sb-{uuid.uuid4().hex[:12]}",
        created_at=now,
    )

    decision = Decision(
        verdict=Verdict.ALLOW,
        reasons=[],
        policy_version="1.0",
        mandate_hash="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        request_hash="abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
        evaluated_at=now,
    )
    from app.payments.rail import RailPermanentError
    try:
        result = rail.execute_payment(req, decision)
        assert result.status in (RailPaymentStatus.PENDING, RailPaymentStatus.SUCCESS)
        assert result.rail_payment_id != ""
        assert result.idempotency_key == req.idempotency_key
    except RailPermanentError as e:
        if "PAYOUT_NOT_AVAILABLE" in str(e):
            pytest.skip(f"PayPal sandbox live account country restriction: {e}")
        raise
