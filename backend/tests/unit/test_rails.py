"""Unit tests for payment rails, webhook verifier, gateway, and tool registry.

WHY:
Verifies Phase 2 requirements:
- MockRail and PayPal Payouts / Orders rail implementations
- Idempotency and safe retries
- Non-ALLOW verdicts strictly raise PaymentNotAllowedError (fail-closed)
- Webhook signature verification
- PaymentGateway end-to-end integration with Bouncer and Audit Log
- Tool risk tier classifications fail closed to RED
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256

import httpx
import pytest
import respx

from app.approvals.service import ApprovalService
from app.audit.log import AuditLog
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
from app.mandate.signing import generate_keypair
from app.payments.gateway import PaymentGateway
from app.payments.mock_rail import MockRail
from app.payments.paypal_orders import PayPalOrdersRail
from app.payments.paypal_payouts import (
    PayPalPayoutsRail,
    format_minor_to_decimal_str,
    map_paypal_batch_status,
)
from app.payments.rail import (
    PaymentNotAllowedError,
    RailPaymentStatus,
    RailPermanentError,
)
from app.payments.token import PayPalTokenManager
from app.payments.webhook import PayPalWebhookVerifier
from app.policy.engine import evaluate_payment_request
from app.policy.provenance import ProvenanceTag
from app.policy.verdict import Decision, Reason, Verdict
from app.tools.registry import ToolRiskTier, get_tool_tier


class FakeClock:
    """Deterministic fake clock for token manager testing."""

    def __init__(self, current: float = 1000.0) -> None:
        self.current = current

    def now(self) -> float:
        return self.current


@pytest.fixture
def keypair() -> tuple[str, str]:
    return generate_keypair()


@pytest.fixture
def mandate_and_intent(keypair: tuple[str, str]) -> tuple[Mandate, Intent, str]:
    priv, pub = keypair
    now = datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)

    mandate = Mandate.create_and_sign(
        mandate_id="m-rail-test",
        version=1,
        owner_id="owner-1",
        agent_id="agent-1",
        issued_at=now,
        expires_at=datetime(2026, 10, 28, 12, 0, 0, tzinfo=UTC),
        currency="USD",
        per_payment_cap_minor=5000,
        daily_cap_minor=10000,
        max_payments_per_hour=10,
        approval_threshold_minor=3000,
        allowed_payees=[
            AllowedPayee(
                payee_id="seller-bob",
                display_name="Bob Supplies",
                paypal_email="bob@supplies.example.com",
            )
        ],
        allowed_purposes=["SUPPLIES"],
        new_payee_policy="BLOCK",
        red_tier_policy="BLOCK",
        key_id="k1",
        private_key_hex=priv,
    )

    intent = Intent.create_and_sign(
        intent_id="intent-rail-1",
        mandate_id=mandate.mandate_id,
        description="Buy paper",
        max_total_minor=5000,
        items=[IntentItem(sku="PAPER-1", qty=2, max_unit_price_minor=2500)],
        deadline=datetime(2026, 10, 28, 12, 0, 0, tzinfo=UTC),
        private_key_hex=priv,
    )
    return mandate, intent, pub


@pytest.fixture
def legitimate_payment(
    mandate_and_intent: tuple[Mandate, Intent, str],
) -> tuple[Mandate, Intent, Deal, PaymentRequest, Decision, str]:
    mandate, intent, pub = mandate_and_intent
    items = [DealItem(sku="PAPER-1", qty=1, unit_price_minor=2000, title="Paper")]
    terms_hash = Deal.compute_terms_hash(
        intent_id=intent.intent_id,
        payee_id="seller-bob",
        payee_email="bob@supplies.example.com",
        items=items,
        total_minor=2000,
        currency="USD",
    )
    deal = Deal(
        deal_id="deal-rail-1",
        intent_id=intent.intent_id,
        payee_id="seller-bob",
        payee_email="bob@supplies.example.com",
        items=items,
        total_minor=2000,
        currency="USD",
        terms_hash=terms_hash,
    )
    req = PaymentRequest(
        request_id="req-rail-1",
        mandate_id=mandate.mandate_id,
        intent_id=intent.intent_id,
        deal_id=deal.deal_id,
        tool_name="payouts",
        payee=PayeeInfo(
            id="seller-bob",
            email="bob@supplies.example.com",
        ),
        amount_minor=2000,
        currency="USD",
        purpose="SUPPLIES",
        memo="Office paper order",
        provenance={
            "amount_minor": ProvenanceTag.OWNER.value,
            "payee": ProvenanceTag.VERIFIED_RECORD.value,
        },
        idempotency_key="idem-key-rail-test-1",
        created_at=datetime(2026, 10, 27, 12, 10, 0, tzinfo=UTC),
    )
    decision = evaluate_payment_request(req, mandate, intent, deal, pub)
    return mandate, intent, deal, req, decision, pub


# ==============================================================================
# 1. MockRail Tests
# ==============================================================================


def test_mock_rail_executes_allow(
    legitimate_payment: tuple[Mandate, Intent, Deal, PaymentRequest, Decision, str],
) -> None:
    """MockRail successfully executes a payment when verdict is ALLOW."""
    _, _, _, req, decision, _ = legitimate_payment
    assert decision.verdict == Verdict.ALLOW

    rail = MockRail()
    result = rail.execute_payment(req, decision)

    assert result.status == RailPaymentStatus.SUCCESS
    assert result.amount_minor == 2000
    assert result.currency == "USD"
    assert result.idempotency_key == req.idempotency_key
    assert result.rail_payment_id.startswith("mock-tx-")
    assert rail.get_payment_status(result.rail_payment_id) == RailPaymentStatus.SUCCESS


def test_mock_rail_strict_idempotency(
    legitimate_payment: tuple[Mandate, Intent, Deal, PaymentRequest, Decision, str],
) -> None:
    """Re-executing with the identical idempotency key returns the cached result."""
    _, _, _, req, decision, _ = legitimate_payment
    rail = MockRail()

    result1 = rail.execute_payment(req, decision)
    result2 = rail.execute_payment(req, decision)

    assert result1.rail_payment_id == result2.rail_payment_id
    assert result1.executed_at == result2.executed_at
    # Should only create one record in payments_by_idempotency
    assert len(rail.payments_by_idempotency) == 1
    # But two execution attempts recorded in history
    assert len(rail.execution_attempts) == 2


def test_mock_rail_blocks_non_allow(
    legitimate_payment: tuple[Mandate, Intent, Deal, PaymentRequest, Decision, str],
) -> None:
    """MockRail raises PaymentNotAllowedError if verdict is BLOCK or ASK_OWNER."""
    _, _, _, req, _, _ = legitimate_payment
    rail = MockRail()

    dummy_hash = sha256(b"test").hexdigest()
    block_decision = Decision(
        verdict=Verdict.BLOCK,
        reasons=[Reason(code="CAP_EXCEEDED", check_id="C4", message="Per payment cap exceeded")],
        mandate_hash=dummy_hash,
        request_hash=dummy_hash,
        evaluated_at=datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC),
    )
    with pytest.raises(PaymentNotAllowedError, match="verdict is BLOCK"):
        rail.execute_payment(req, block_decision)

    ask_decision = Decision(
        verdict=Verdict.ASK_OWNER,
        reasons=[Reason(code="APPROVAL_NEEDED", check_id="C4", message="Above threshold")],
        mandate_hash=dummy_hash,
        request_hash=dummy_hash,
        evaluated_at=datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC),
    )
    with pytest.raises(PaymentNotAllowedError, match="verdict is ASK_OWNER"):
        rail.execute_payment(req, ask_decision)


# ==============================================================================
# 2. PayPal Payouts Rail Tests
# ==============================================================================


def test_format_minor_to_decimal_str() -> None:
    """Decimal formatting respects ISO standard decimal rules."""
    assert format_minor_to_decimal_str(2000, "USD") == "20.00"
    assert format_minor_to_decimal_str(50, "USD") == "0.50"
    assert format_minor_to_decimal_str(7, "USD") == "0.07"
    assert format_minor_to_decimal_str(100000, "EUR") == "1000.00"
    # Zero decimal currency
    assert format_minor_to_decimal_str(500, "JPY") == "500"


def test_map_paypal_batch_status() -> None:
    """Status mapping is robust."""
    assert map_paypal_batch_status("SUCCESS") == RailPaymentStatus.SUCCESS
    assert map_paypal_batch_status("COMPLETED") == RailPaymentStatus.SUCCESS
    assert map_paypal_batch_status("PENDING") == RailPaymentStatus.PENDING
    assert map_paypal_batch_status("PROCESSING") == RailPaymentStatus.PENDING
    assert map_paypal_batch_status("DENIED") == RailPaymentStatus.FAILED
    assert map_paypal_batch_status("FAILED") == RailPaymentStatus.FAILED


@respx.mock
def test_paypal_payouts_rail_happy_path(
    legitimate_payment: tuple[Mandate, Intent, Deal, PaymentRequest, Decision, str],
) -> None:
    """PayPalPayoutsRail sends valid request and parses 201 Created response."""
    _, _, _, req, decision, _ = legitimate_payment

    # Mock OAuth2 token response
    respx.post("https://api-m.sandbox.paypal.com/v1/oauth2/token").respond(
        200,
        json={"access_token": "mock-token-xyz", "token_type": "Bearer", "expires_in": 3600},
    )

    # Mock Payouts API response
    payout_route = respx.post("https://api-m.sandbox.paypal.com/v1/payments/payouts").respond(
        201,
        json={
            "batch_header": {
                "payout_batch_id": "BATCH-12345",
                "batch_status": "PENDING",
                "sender_batch_header": {"sender_batch_id": f"ma-{req.idempotency_key}"[:30]},
            }
        },
    )

    token_mgr = PayPalTokenManager(
        client_id="cid",
        client_secret="sec",
        base_url="https://api-m.sandbox.paypal.com",
    )
    rail = PayPalPayoutsRail(token_manager=token_mgr)

    result = rail.execute_payment(req, decision)

    assert result.status == RailPaymentStatus.PENDING
    assert result.rail_payment_id == "BATCH-12345"
    assert result.idempotency_key == req.idempotency_key
    assert payout_route.called

    # Verify outgoing headers and payload
    sent_request = payout_route.calls.last.request
    assert sent_request.headers["Authorization"] == "Bearer mock-token-xyz"
    assert sent_request.headers["PayPal-Request-Id"] == req.idempotency_key
    sent_json = json.loads(sent_request.content)
    assert sent_json["items"][0]["receiver"] == "bob@supplies.example.com"
    assert sent_json["items"][0]["amount"]["value"] == "20.00"


@respx.mock
def test_paypal_payouts_duplicate_batch_id(
    legitimate_payment: tuple[Mandate, Intent, Deal, PaymentRequest, Decision, str],
) -> None:
    """If PayPal detects DUPLICATE_BATCH_ID, rail gracefully fetches existing status."""
    _, _, _, req, decision, _ = legitimate_payment

    respx.post("https://api-m.sandbox.paypal.com/v1/oauth2/token").respond(
        200,
        json={"access_token": "token-1", "token_type": "Bearer", "expires_in": 3600},
    )

    # Post returns 400 DUPLICATE_BATCH_ID
    respx.post("https://api-m.sandbox.paypal.com/v1/payments/payouts").respond(
        400,
        json={"name": "DUPLICATE_BATCH_ID", "message": "Batch already processed"},
    )

    expected_batch_id = f"ma-{req.idempotency_key}"[:30]
    # Status lookup returns SUCCESS
    respx.get(f"https://api-m.sandbox.paypal.com/v1/payments/payouts/{expected_batch_id}").respond(
        200,
        json={"batch_header": {"payout_batch_id": expected_batch_id, "batch_status": "SUCCESS"}},
    )

    token_mgr = PayPalTokenManager(
        client_id="cid",
        client_secret="sec",
        base_url="https://api-m.sandbox.paypal.com",
    )
    rail = PayPalPayoutsRail(token_manager=token_mgr)

    result = rail.execute_payment(req, decision)
    assert result.status == RailPaymentStatus.SUCCESS
    assert result.raw_response.get("duplicate_replayed") is True


@respx.mock
def test_paypal_payouts_transient_retry(
    legitimate_payment: tuple[Mandate, Intent, Deal, PaymentRequest, Decision, str],
) -> None:
    """PayPalPayoutsRail retries transient 500 error and succeeds on 2nd attempt."""
    _, _, _, req, decision, _ = legitimate_payment

    respx.post("https://api-m.sandbox.paypal.com/v1/oauth2/token").respond(
        200,
        json={"access_token": "token-1", "token_type": "Bearer", "expires_in": 3600},
    )

    payout_route = respx.post("https://api-m.sandbox.paypal.com/v1/payments/payouts")
    # First call: 502 Bad Gateway; Second call: 201 Created
    payout_route.side_effect = [
        httpx.Response(502, text="Bad Gateway"),
        httpx.Response(
            201,
            json={"batch_header": {"payout_batch_id": "RETRY-OK", "batch_status": "SUCCESS"}},
        ),
    ]

    token_mgr = PayPalTokenManager(
        client_id="cid",
        client_secret="sec",
        base_url="https://api-m.sandbox.paypal.com",
    )
    rail = PayPalPayoutsRail(token_manager=token_mgr, backoff_factor=0.01)

    result = rail.execute_payment(req, decision)
    assert result.status == RailPaymentStatus.SUCCESS
    assert result.rail_payment_id == "RETRY-OK"
    assert payout_route.call_count == 2


@respx.mock
def test_paypal_payouts_permanent_failure(
    legitimate_payment: tuple[Mandate, Intent, Deal, PaymentRequest, Decision, str],
) -> None:
    """PayPal 400 invalid account raises RailPermanentError without retrying."""
    _, _, _, req, decision, _ = legitimate_payment

    respx.post("https://api-m.sandbox.paypal.com/v1/oauth2/token").respond(
        200,
        json={"access_token": "token-1", "token_type": "Bearer", "expires_in": 3600},
    )
    respx.post("https://api-m.sandbox.paypal.com/v1/payments/payouts").respond(
        400,
        json={"name": "ACCOUNT_RESTRICTED", "message": "Sender account is restricted"},
    )

    token_mgr = PayPalTokenManager(
        client_id="cid",
        client_secret="sec",
        base_url="https://api-m.sandbox.paypal.com",
    )
    rail = PayPalPayoutsRail(token_manager=token_mgr)

    with pytest.raises(RailPermanentError, match="Sender account is restricted"):
        rail.execute_payment(req, decision)


# ==============================================================================
# 3. PayPal Orders Rail Tests
# ==============================================================================


@respx.mock
def test_paypal_orders_rail_create_and_capture(
    legitimate_payment: tuple[Mandate, Intent, Deal, PaymentRequest, Decision, str],
) -> None:
    """PayPalOrdersRail creates an order and supports capture."""
    _, _, _, req, decision, _ = legitimate_payment

    respx.post("https://api-m.sandbox.paypal.com/v1/oauth2/token").respond(
        200,
        json={"access_token": "token-1", "token_type": "Bearer", "expires_in": 3600},
    )
    respx.post("https://api-m.sandbox.paypal.com/v2/checkout/orders").respond(
        201,
        json={"id": "ORDER-999", "status": "CREATED"},
    )
    respx.post("https://api-m.sandbox.paypal.com/v2/checkout/orders/ORDER-999/capture").respond(
        201,
        json={"id": "ORDER-999", "status": "COMPLETED"},
    )

    token_mgr = PayPalTokenManager(
        client_id="cid",
        client_secret="sec",
        base_url="https://api-m.sandbox.paypal.com",
    )
    rail = PayPalOrdersRail(token_manager=token_mgr)

    create_res = rail.execute_payment(req, decision)
    assert create_res.rail_payment_id == "ORDER-999"
    assert create_res.status == RailPaymentStatus.PENDING

    capture_res = rail.capture_order("ORDER-999", idempotency_key="cap-idem-1")
    assert capture_res.status == RailPaymentStatus.SUCCESS


# ==============================================================================
# 4. Webhook Verification Tests
# ==============================================================================


@respx.mock
def test_paypal_webhook_verifier() -> None:
    """PayPalWebhookVerifier validates PayPal signature headers via PayPal API."""
    respx.post("https://api-m.sandbox.paypal.com/v1/oauth2/token").respond(
        200,
        json={"access_token": "token-1", "token_type": "Bearer", "expires_in": 3600},
    )

    respx.post(
        "https://api-m.sandbox.paypal.com/v1/notifications/verify-webhook-signature"
    ).respond(
        200,
        json={"verification_status": "SUCCESS"},
    )

    token_mgr = PayPalTokenManager(
        client_id="cid",
        client_secret="sec",
        base_url="https://api-m.sandbox.paypal.com",
    )
    verifier = PayPalWebhookVerifier(token_manager=token_mgr, webhook_id="WH-1234")

    headers = {
        "PAYPAL-AUTH-ALGO": "SHA256withRSA",
        "PAYPAL-CERT-URL": "https://api.sandbox.paypal.com/v1/notifications/certs/cert.pem",
        "PAYPAL-TRANSMISSION-ID": "tx-123",
        "PAYPAL-TRANSMISSION-SIG": "sig-xyz",
        "PAYPAL-TRANSMISSION-TIME": "2026-10-27T12:00:00Z",
    }
    body = {"id": "WH-EV-1", "event_type": "PAYMENT.PAYOUTSBATCH.SUCCESS"}

    result = verifier.verify(headers, body)
    assert result.is_valid is True
    assert result.status == "SUCCESS"
    assert result.event_type == "PAYMENT.PAYOUTSBATCH.SUCCESS"

    # Test missing headers
    bad_result = verifier.verify({}, body)
    assert bad_result.is_valid is False
    assert bad_result.status == "MISSING_HEADERS"


# ==============================================================================
# 5. PaymentGateway Bouncer-Gated Integration Tests
# ==============================================================================


def test_gateway_allow_executes_rail_and_logs(
    legitimate_payment: tuple[Mandate, Intent, Deal, PaymentRequest, Decision, bytes],
) -> None:
    """Gateway executes payment only on ALLOW and records in audit chain."""
    mandate, intent, deal, req, _, pub = legitimate_payment
    rail = MockRail()
    audit = AuditLog()
    approval_svc = ApprovalService()
    gateway = PaymentGateway(rail=rail, audit_log=audit, approval_service=approval_svc)

    outcome = gateway.process_payment(req, mandate, pub, intent, deal)

    assert outcome.executed is True
    assert outcome.payment_result is not None
    assert outcome.payment_result.status == RailPaymentStatus.SUCCESS
    assert outcome.decision.verdict == Verdict.ALLOW

    # Verify audit event
    assert len(audit.events) == 1
    event = audit.events[0]
    assert event.type == "PAYMENT_EXECUTED"
    assert event.payload["request_id"] == req.request_id
    assert event.payload["amount_minor"] == 2000
    assert verify_chain(audit.events).is_valid is True


def test_gateway_blocks_excessive_amount(
    legitimate_payment: tuple[Mandate, Intent, Deal, PaymentRequest, Decision, str],
) -> None:
    """Gateway blocks payment exceeding caps and NEVER calls the rail."""
    mandate, intent, deal, _, _, pub = legitimate_payment
    rail = MockRail()
    audit = AuditLog()
    gateway = PaymentGateway(rail=rail, audit_log=audit)

    # Over per-payment cap ($50 cap vs $100 requested)
    bad_req = PaymentRequest(
        request_id="req-blocked",
        mandate_id=mandate.mandate_id,
        intent_id=intent.intent_id,
        deal_id=deal.deal_id,
        tool_name="payouts",
        payee=PayeeInfo(id=deal.payee_id, email=deal.payee_email),
        amount_minor=10000,
        currency="USD",
        purpose="SUPPLIES",
        provenance={"amount_minor": ProvenanceTag.OWNER.value},
        idempotency_key="idem-blocked",
        created_at=datetime(2026, 10, 27, 12, 10, 0, tzinfo=UTC),
    )

    outcome = gateway.process_payment(bad_req, mandate, pub, intent, deal)

    assert outcome.executed is False
    assert outcome.decision.verdict == Verdict.BLOCK
    assert outcome.payment_result is None
    # Rail was never invoked!
    assert len(rail.execution_attempts) == 0

    # Blocked event written to audit log
    assert len(audit.events) == 1
    assert audit.events[0].type == "PAYMENT_BLOCKED"


def test_gateway_escalates_to_ask_owner(
    legitimate_payment: tuple[Mandate, Intent, Deal, PaymentRequest, Decision, str],
) -> None:
    """Gateway routes payments above approval_threshold to ASK_OWNER."""
    mandate, intent, _, _, _, pub = legitimate_payment
    rail = MockRail()
    audit = AuditLog()
    approval_svc = ApprovalService()
    gateway = PaymentGateway(rail=rail, audit_log=audit, approval_service=approval_svc)

    # Threshold is $30 (3000 minor); request $40 (4000 minor) within $50 cap
    items_40 = [DealItem(sku="PAPER-1", qty=2, unit_price_minor=2000, title="Paper")]
    terms_40 = Deal.compute_terms_hash(
        intent_id=intent.intent_id,
        payee_id="seller-bob",
        payee_email="bob@supplies.example.com",
        items=items_40,
        total_minor=4000,
        currency="USD",
    )
    deal_40 = Deal(
        deal_id="deal-40",
        intent_id=intent.intent_id,
        payee_id="seller-bob",
        payee_email="bob@supplies.example.com",
        items=items_40,
        total_minor=4000,
        currency="USD",
        terms_hash=terms_40,
    )
    req_40 = PaymentRequest(
        request_id="req-ask-owner",
        mandate_id=mandate.mandate_id,
        intent_id=intent.intent_id,
        deal_id=deal_40.deal_id,
        tool_name="payouts",
        payee=PayeeInfo(id=deal_40.payee_id, email=deal_40.payee_email),
        amount_minor=4000,
        currency="USD",
        purpose="SUPPLIES",
        provenance={"amount_minor": ProvenanceTag.OWNER.value},
        idempotency_key="idem-ask",
        created_at=datetime(2026, 10, 27, 12, 10, 0, tzinfo=UTC),
    )

    outcome = gateway.process_payment(req_40, mandate, pub, intent, deal_40)

    assert outcome.executed is False
    assert outcome.decision.verdict == Verdict.ASK_OWNER
    assert outcome.approval_request is not None
    # Rail was not invoked!
    assert len(rail.execution_attempts) == 0
    # Audit log contains approval requested event
    assert audit.events[0].type == "PAYMENT_APPROVAL_REQUESTED"


# ==============================================================================
# 6. Tool Registry Classification Tests
# ==============================================================================


def test_tool_registry_tiers() -> None:
    """Tool tiers correctly partition read-only, money-moving, and dangerous tools."""
    # GREEN
    assert get_tool_tier("get_invoice") == ToolRiskTier.GREEN
    assert get_tool_tier("list_invoices") == ToolRiskTier.GREEN
    assert get_tool_tier("get_order") == ToolRiskTier.GREEN
    assert get_tool_tier("get_balance") == ToolRiskTier.GREEN
    assert get_tool_tier("list_transactions") == ToolRiskTier.GREEN
    assert get_tool_tier("get_tracking_info") == ToolRiskTier.GREEN

    # YELLOW
    assert get_tool_tier("payouts") == ToolRiskTier.YELLOW
    assert get_tool_tier("create_order") == ToolRiskTier.YELLOW
    assert get_tool_tier("create_invoice") == ToolRiskTier.YELLOW
    assert get_tool_tier("send_invoice") == ToolRiskTier.YELLOW
    assert get_tool_tier("request_payment") == ToolRiskTier.YELLOW

    # RED
    assert get_tool_tier("create_refund") == ToolRiskTier.RED
    assert get_tool_tier("cancel_sent_invoice") == ToolRiskTier.RED
    assert get_tool_tier("accept_dispute_claim") == ToolRiskTier.RED
    assert get_tool_tier("cancel_subscription") == ToolRiskTier.RED

    # Unknown tool MUST fail closed to RED (P4)
    assert get_tool_tier("unknown_drain_funds_tool") == ToolRiskTier.RED
    assert get_tool_tier("bypass_check") == ToolRiskTier.RED
