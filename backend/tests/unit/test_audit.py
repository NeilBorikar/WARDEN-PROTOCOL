"""Unit tests for tamper-evident audit log and hash chain verification.

WHY:
- Section 5: AuditEvent data contract and hash chain formula:
  hash = SHA-256(prev_hash + canonical_json({seq, ts, type, payload}))
- Section 7: "tampering with the audit chain is detected."
- Proves that any alteration, deletion, or reordering is immediately caught.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.audit.log import GENESIS_PREV_HASH, AuditEvent, AuditLog
from app.audit.verify import verify_chain


def test_audit_log_empty_chain_is_valid() -> None:
    log = AuditLog()
    assert len(log) == 0
    res = verify_chain(log.events)
    assert res.is_valid is True
    assert res.verified_count == 0


def test_audit_log_genesis_event() -> None:
    log = AuditLog()
    now = datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)
    ev = log.append("MANDATE_REGISTERED", {"mandate_id": "m-1"}, ts=now)

    assert ev.seq == 1
    assert ev.prev_hash == GENESIS_PREV_HASH
    assert len(ev.hash) == 64
    assert ev.verify_hash() is True

    res = verify_chain(log.events)
    assert res.is_valid is True
    assert res.verified_count == 1


def test_audit_log_chaining() -> None:
    log = AuditLog()
    now = datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)

    ev1 = log.append("MANDATE_REGISTERED", {"mandate_id": "m-1"}, ts=now)
    ev2 = log.append("PAYMENT_REQUESTED", {"request_id": "r-1"}, ts=now)
    ev3 = log.append("POLICY_EVALUATED", {"verdict": "ALLOW"}, ts=now)

    assert ev2.prev_hash == ev1.hash
    assert ev3.prev_hash == ev2.hash
    assert len(log) == 3

    res = verify_chain(log.events)
    assert res.is_valid is True
    assert res.verified_count == 3


def test_audit_log_tamper_payload_detected() -> None:
    log = AuditLog()
    now = datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)

    log.append("MANDATE_REGISTERED", {"mandate_id": "m-1"}, ts=now)
    log.append("PAYMENT_REQUESTED", {"amount_minor": 2000}, ts=now)

    events = log.events
    # Tamper with the payload of event 2 (change amount to 50000)
    tampered_event = AuditEvent(
        seq=events[1].seq,
        ts=events[1].ts,
        type=events[1].type,
        payload={"amount_minor": 50000},  # tampered!
        prev_hash=events[1].prev_hash,
        hash=events[1].hash,  # original hash, doesn't match new payload
    )
    tampered_chain = [events[0], tampered_event]

    res = verify_chain(tampered_chain)
    assert res.is_valid is False
    assert "Tampered payload detected" in (res.error or "")


def test_audit_log_tamper_prev_hash_breaks_chain() -> None:
    log = AuditLog()
    now = datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)

    log.append("EVENT_1", {"v": 1}, ts=now)
    log.append("EVENT_2", {"v": 2}, ts=now)

    events = log.events
    fake_prev_hash = "a" * 64
    fake_hash = AuditEvent.compute_event_hash(
        seq=2,
        ts=events[1].ts,
        type_="EVENT_2",
        payload={"v": 2},
        prev_hash=fake_prev_hash,
    )
    tampered_event = AuditEvent(
        seq=2,
        ts=events[1].ts,
        type="EVENT_2",
        payload={"v": 2},
        prev_hash=fake_prev_hash,
        hash=fake_hash,
    )

    tampered_chain = [events[0], tampered_event]
    res = verify_chain(tampered_chain)
    assert res.is_valid is False
    assert "Broken chain" in (res.error or "")


def test_audit_log_deletion_detected() -> None:
    log = AuditLog()
    now = datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)

    log.append("EVENT_1", {"v": 1}, ts=now)
    log.append("EVENT_2", {"v": 2}, ts=now)
    log.append("EVENT_3", {"v": 3}, ts=now)

    events = log.events
    # Drop middle event
    tampered_chain = [events[0], events[2]]

    res = verify_chain(tampered_chain)
    assert res.is_valid is False
    assert "Sequence gap" in (res.error or "")


def test_audit_log_reordering_detected() -> None:
    log = AuditLog()
    now = datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)

    log.append("EVENT_1", {"v": 1}, ts=now)
    log.append("EVENT_2", {"v": 2}, ts=now)

    events = log.events
    # Swap order
    tampered_chain = [events[1], events[0]]

    res = verify_chain(tampered_chain)
    assert res.is_valid is False
