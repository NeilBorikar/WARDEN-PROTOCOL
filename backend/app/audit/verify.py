"""Cryptographic verification of audit log hash chains.

WHY:
- Section 8: "searchable table with a 'verify chain' button."
- Section 7: "tampering with the audit chain is detected."
- Guarantees complete tamper-evidence: any mutated payload, altered timestamp,
  dropped entry, or inserted event breaks verification.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.audit.log import GENESIS_PREV_HASH, AuditEvent


class ChainVerificationResult:
    """Result of verifying an audit log hash chain."""

    def __init__(self, is_valid: bool, error: str | None = None, verified_count: int = 0) -> None:
        self.is_valid = is_valid
        self.error = error
        self.verified_count = verified_count

    def __bool__(self) -> bool:
        return self.is_valid

    def __repr__(self) -> str:
        if self.is_valid:
            return f"<ChainVerificationResult: VALID ({self.verified_count} events)>"
        return f"<ChainVerificationResult: INVALID - {self.error}>"


def verify_chain(events: Sequence[AuditEvent]) -> ChainVerificationResult:
    """Verify integrity of an audit event chain from genesis to end.

    Checks:
    1. Empty chain is trivially valid.
    2. Sequence numbers start at 1 and increment by exactly 1 without gaps or duplicates.
    3. Genesis event (seq=1) prev_hash matches GENESIS_PREV_HASH (64 zeros).
    4. Each event's prev_hash exactly equals the preceding event's hash.
    5. Each event's hash equals SHA-256(prev_hash + canonical_json(event_data)).

    Returns:
        ChainVerificationResult indicating whether chain is untampered.
    """
    if not events:
        return ChainVerificationResult(is_valid=True, verified_count=0)

    for i, event in enumerate(events):
        expected_seq = i + 1

        # Check sequence numbering
        if event.seq != expected_seq:
            return ChainVerificationResult(
                is_valid=False,
                error=f"Sequence gap at index {i}: expected seq {expected_seq}, got {event.seq}.",
                verified_count=i,
            )

        # Check genesis prev_hash
        if i == 0:
            if event.prev_hash != GENESIS_PREV_HASH:
                return ChainVerificationResult(
                    is_valid=False,
                    error=(
                        f"Genesis event (seq 1) prev_hash mismatch: expected "
                        f"{GENESIS_PREV_HASH}, got {event.prev_hash}."
                    ),
                    verified_count=0,
                )
        else:
            prev_event = events[i - 1]
            if event.prev_hash != prev_event.hash:
                return ChainVerificationResult(
                    is_valid=False,
                    error=(
                        f"Broken chain at seq {event.seq}: event.prev_hash ({event.prev_hash}) "
                        f"does not match preceding hash ({prev_event.hash})."
                    ),
                    verified_count=i,
                )

        # Recompute hash
        if not event.verify_hash():
            return ChainVerificationResult(
                is_valid=False,
                error=(
                    f"Tampered payload detected at seq {event.seq}: "
                    f"stored hash {event.hash} does not match computed content hash."
                ),
                verified_count=i,
            )

    return ChainVerificationResult(is_valid=True, verified_count=len(events))
