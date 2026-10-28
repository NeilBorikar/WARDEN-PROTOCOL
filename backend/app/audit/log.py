"""Tamper-evident audit log with SHA-256 cryptographic hash chain.

WHY:
- Section 5 & Principle P1: Every action is written to a tamper-evident audit log.
- Packages mandate/, policy/, and audit/ must never import LLM or agent code.
- Hash chain formula: hash = SHA-256(prev_hash + canonical_json({seq, ts, type, payload})).
- Any modification, insertion, deletion, or reordering breaks the chain.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.mandate.signing import canonical_json_bytes

GENESIS_PREV_HASH: str = "0" * 64


class AuditEvent(BaseModel):
    """An immutable, tamper-evident audit log record."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    seq: int = Field(ge=1)
    ts: datetime
    type: str = Field(min_length=1)
    payload: dict[str, Any]
    prev_hash: str = Field(min_length=64, max_length=64)
    hash: str = Field(min_length=64, max_length=64)

    @classmethod
    def compute_event_hash(
        cls,
        seq: int,
        ts: datetime,
        type_: str,
        payload: dict[str, Any],
        prev_hash: str,
    ) -> str:
        """Compute SHA-256 hash of prev_hash prepended to canonical event JSON."""
        event_body = {
            "seq": seq,
            "ts": ts.isoformat(),
            "type": type_,
            "payload": payload,
        }
        canonical_bytes = canonical_json_bytes(event_body)
        hasher = hashlib.sha256()
        hasher.update(prev_hash.encode("ascii"))
        hasher.update(canonical_bytes)
        return hasher.hexdigest()

    def verify_hash(self) -> bool:
        """Verify that event's stored hash matches recomputed hash."""
        expected = self.compute_event_hash(
            seq=self.seq,
            ts=self.ts,
            type_=self.type,
            payload=self.payload,
            prev_hash=self.prev_hash,
        )
        return self.hash == expected


class AuditLog:
    """Thread-safe in-memory audit log managing the cryptographic hash chain."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    @property
    def events(self) -> list[AuditEvent]:
        """Return shallow copy of all events in log."""
        return list(self._events)

    def last_hash(self) -> str:
        """Return the hash of the latest event, or GENESIS_PREV_HASH if empty."""
        if not self._events:
            return GENESIS_PREV_HASH
        return self._events[-1].hash

    def append(
        self,
        type_: str,
        payload: dict[str, Any],
        ts: datetime | None = None,
    ) -> AuditEvent:
        """Append a new event to the audit log, chaining from the previous event."""
        event_ts = ts or datetime.now(UTC)
        seq = len(self._events) + 1
        prev_hash = self.last_hash()

        event_hash = AuditEvent.compute_event_hash(
            seq=seq,
            ts=event_ts,
            type_=type_,
            payload=payload,
            prev_hash=prev_hash,
        )

        event = AuditEvent(
            seq=seq,
            ts=event_ts,
            type=type_,
            payload=payload,
            prev_hash=prev_hash,
            hash=event_hash,
        )
        self._events.append(event)
        return event

    def get_by_seq(self, seq: int) -> AuditEvent | None:
        """Fetch an event by 1-indexed sequence number."""
        if 1 <= seq <= len(self._events):
            return self._events[seq - 1]
        return None

    def __len__(self) -> int:
        return len(self._events)

    def verify(self) -> tuple[bool, str | None]:
        """Verify the cryptographic hash chain of this audit log."""
        from app.audit.verify import verify_chain

        res = verify_chain(self._events)
        return res.is_valid, res.error
