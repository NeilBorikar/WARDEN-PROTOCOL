"""Unit tests for mandate models, canonical JSON, and Ed25519 signing.

WHY:
- Section 3: "Canonical JSON (sorted keys, no whitespace) before any hashing or signing."
- Section 5: Data contracts for Mandate, Intent, Deal, and PaymentRequest.
- Verifies Ed25519 cryptographic signatures and tampering detection.
"""

from __future__ import annotations

import json
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
from app.mandate.signing import (
    canonical_json_bytes,
    generate_keypair,
    sign_canonical_payload,
    verify_canonical_payload,
)


def test_canonical_json_key_sorting() -> None:
    """Keys must be alphabetically sorted at all depths."""
    d1 = {"z": 1, "a": {"d": 4, "b": 2}}
    d2 = {"a": {"b": 2, "d": 4}, "z": 1}

    bytes1 = canonical_json_bytes(d1)
    bytes2 = canonical_json_bytes(d2)

    assert bytes1 == bytes2
    assert bytes1 == b'{"a":{"b":2,"d":4},"z":1}'


def test_canonical_json_no_whitespace() -> None:
    """No spaces after colons or commas."""
    data = {"hello": "world", "items": [1, 2, 3]}
    res = canonical_json_bytes(data)
    assert b": " not in res
    assert b", " not in res
    assert b" \n" not in res


def test_canonical_json_utf8() -> None:
    """UTF-8 unicode characters are preserved without escaping."""
    data = {"emoji": "🛡️", "text": "MANDATE_ARENA"}
    res = canonical_json_bytes(data)
    decoded = json.loads(res.decode("utf-8"))
    assert decoded["emoji"] == "🛡️"


def test_ed25519_sign_and_verify() -> None:
    """Generate keypair, sign payload, and verify signature."""
    priv, pub = generate_keypair()
    payload = {"mandate_id": "m-123", "amount": 5000}

    sig = sign_canonical_payload(payload, priv)
    assert len(sig) == 128  # 64 bytes in hex

    is_valid = verify_canonical_payload(payload, sig, pub)
    assert is_valid is True


def test_ed25519_tampered_payload_fails() -> None:
    """Any modification to signed payload causes verification to fail."""
    priv, pub = generate_keypair()
    payload = {"mandate_id": "m-123", "amount": 5000}

    sig = sign_canonical_payload(payload, priv)

    # Tamper with amount
    tampered = {"mandate_id": "m-123", "amount": 5001}
    assert verify_canonical_payload(tampered, sig, pub) is False


def test_ed25519_wrong_key_fails() -> None:
    """Verifying with a different public key fails."""
    priv1, pub1 = generate_keypair()
    _, pub2 = generate_keypair()

    payload = {"errand": "groceries"}
    sig = sign_canonical_payload(payload, priv1)

    assert verify_canonical_payload(payload, sig, pub1) is True
    assert verify_canonical_payload(payload, sig, pub2) is False


def test_mandate_model_lifecycle() -> None:
    """Mandate model hashing, signature verification, and expiration."""
    priv, pub = generate_keypair()
    now = datetime.now(UTC)

    mandate = Mandate.create_and_sign(
        mandate_id="mandate-001",
        version=1,
        owner_id="owner-alice",
        agent_id="agent-bob",
        issued_at=now,
        expires_at=now + timedelta(days=30),
        currency="USD",
        per_payment_cap_minor=10000,
        daily_cap_minor=50000,
        max_payments_per_hour=5,
        approval_threshold_minor=2500,
        allowed_payees=[
            AllowedPayee(
                payee_id="seller-carol",
                display_name="Carol Supplies",
                paypal_email="carol@example.com",
            )
        ],
        allowed_purposes=["OFFICE_SUPPLIES", "ERRANDS"],
        new_payee_policy="BLOCK",
        red_tier_policy="ASK_OWNER",
        key_id="key-alice-1",
        private_key_hex=priv,
    )

    assert mandate.verify_signature(pub) is True

    assert len(mandate.compute_hash()) == 64
    assert mandate.is_expired(now + timedelta(days=10)) is False
    assert mandate.is_expired(now + timedelta(days=31)) is True


def test_intent_model_lifecycle() -> None:
    """Intent model hashing, signature verification, and expiration."""
    priv, pub = generate_keypair()
    now = datetime.now(UTC)

    intent = Intent.create_and_sign(
        intent_id="intent-001",
        mandate_id="mandate-001",
        description="Buy printer paper",
        max_total_minor=3000,
        items=[IntentItem(sku="PAPER-A4", qty=2, max_unit_price_minor=1500)],
        deadline=now + timedelta(hours=2),
        private_key_hex=priv,
    )

    assert intent.verify_signature(pub) is True

    assert len(intent.compute_hash()) == 64
    assert intent.is_expired(now + timedelta(hours=1)) is False
    assert intent.is_expired(now + timedelta(hours=3)) is True


def test_deal_terms_hash() -> None:
    """Deal terms_hash computation and tamper detection."""
    items = [DealItem(sku="PAPER-A4", qty=2, unit_price_minor=1000, title="Paper")]
    terms_hash = Deal.compute_terms_hash(
        intent_id="intent-001",
        payee_id="seller-carol",
        payee_email="carol@example.com",
        items=items,
        total_minor=2000,
        currency="USD",
    )

    deal = Deal(
        deal_id="deal-001",
        intent_id="intent-001",
        payee_id="seller-carol",
        payee_email="carol@example.com",
        items=items,
        total_minor=2000,
        currency="USD",
        terms_hash=terms_hash,
    )

    assert deal.verify_terms_hash() is True

    # Tamper with total
    bad_deal = Deal(
        deal_id="deal-001",
        intent_id="intent-001",
        payee_id="seller-carol",
        payee_email="carol@example.com",
        items=items,
        total_minor=2500,  # tampered
        currency="USD",
        terms_hash=terms_hash,
    )
    assert bad_deal.verify_terms_hash() is False


def test_payment_request_hashing() -> None:
    """PaymentRequest canonical hashing is deterministic."""
    now = datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)
    req1 = PaymentRequest(
        request_id="req-1",
        mandate_id="mandate-1",
        intent_id="intent-1",
        deal_id="deal-1",
        tool_name="payouts",
        payee=PayeeInfo(id="p-1", email="seller@example.com"),
        amount_minor=2000,
        currency="USD",
        purpose="OFFICE_SUPPLIES",
        idempotency_key="idemp-1",
        created_at=now,
    )

    req2 = PaymentRequest(
        request_id="req-1",
        mandate_id="mandate-1",
        intent_id="intent-1",
        deal_id="deal-1",
        tool_name="payouts",
        payee=PayeeInfo(id="p-1", email="seller@example.com"),
        amount_minor=2000,
        currency="USD",
        purpose="OFFICE_SUPPLIES",
        idempotency_key="idemp-1",
        created_at=now,
    )

    assert req1.compute_hash() == req2.compute_hash()
    assert len(req1.compute_hash()) == 64
