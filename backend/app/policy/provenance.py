"""Provenance tracking for payment-critical fields.

WHY:
- Principle P3: "Untrusted text can never change money-critical fields. Payee and
  amount come only from owner-signed documents or verified records, or are
  validated against them. Every field carries provenance:
  OWNER | VERIFIED_RECORD | AGENT_DERIVED | UNTRUSTED_EXTERNAL."
- Packages mandate/, policy/, and audit/ must never import LLM or agent code (P1).
"""

from __future__ import annotations

from enum import StrEnum


class ProvenanceTag(StrEnum):
    """Provenance origin of a data field."""

    OWNER = "OWNER"
    VERIFIED_RECORD = "VERIFIED_RECORD"
    AGENT_DERIVED = "AGENT_DERIVED"
    UNTRUSTED_EXTERNAL = "UNTRUSTED_EXTERNAL"


# Critical fields that MUST NOT originate directly from untrusted sources
# without validation against owner-signed documents or verified records.
MONEY_CRITICAL_FIELDS: frozenset[str] = frozenset(
    {"payee", "payee.id", "payee.email", "amount_minor", "currency"}
)


def is_trusted_provenance(tag: str | ProvenanceTag) -> bool:
    """Return True if provenance origin is trusted (OWNER or VERIFIED_RECORD)."""
    val = tag.value if isinstance(tag, ProvenanceTag) else tag
    return val in (ProvenanceTag.OWNER.value, ProvenanceTag.VERIFIED_RECORD.value)
