"""Verdict combination and decision models.

WHY:
- Principle P4: "Fail closed. Errors, timeouts or missing data produce BLOCK or ASK_OWNER,
  never ALLOW."
- Principle P5: "Most restrictive verdict wins: BLOCK > ASK_OWNER > ALLOW. The Second Opinion
  model may only escalate, never relax."
- Plain-English reasons with stable error codes enable clear user communication (P8).
- Packages mandate/, policy/, and audit/ must never import LLM or agent code (P1).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Verdict(StrEnum):
    """Bouncer policy evaluation verdict."""

    ALLOW = "ALLOW"
    ASK_OWNER = "ASK_OWNER"
    BLOCK = "BLOCK"


# Priority ordering: higher number is more restrictive.
# BLOCK (3) > ASK_OWNER (2) > ALLOW (1)
_VERDICT_RESTRICTIVENESS: dict[Verdict, int] = {
    Verdict.ALLOW: 1,
    Verdict.ASK_OWNER: 2,
    Verdict.BLOCK: 3,
}


def combine_verdicts(verdicts: list[Verdict]) -> Verdict:
    """Combine multiple verdicts according to P5 (most restrictive wins).

    If no verdicts provided, fail closed to BLOCK (P4).
    """
    if not verdicts:
        return Verdict.BLOCK

    most_restrictive = Verdict.ALLOW
    for v in verdicts:
        if _VERDICT_RESTRICTIVENESS[v] > _VERDICT_RESTRICTIVENESS[most_restrictive]:
            most_restrictive = v
            if most_restrictive == Verdict.BLOCK:
                # Shortcut: nothing is more restrictive than BLOCK
                return Verdict.BLOCK

    return most_restrictive


def can_escalate(current: Verdict, proposed: Verdict) -> bool:
    """Return True if proposed verdict is equal to or more restrictive than current.

    WHY: Second Opinion or approval flow may only escalate, never relax (P5).
    """
    return _VERDICT_RESTRICTIVENESS[proposed] >= _VERDICT_RESTRICTIVENESS[current]


class Reason(BaseModel):
    """Structured rationale for a check evaluation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(min_length=1)
    check_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


class Decision(BaseModel):
    """Full decision produced by the Bouncer policy engine."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    verdict: Verdict
    reasons: list[Reason]
    policy_version: str = Field(default="1.0.0")
    mandate_hash: str = Field(min_length=64, max_length=64)
    request_hash: str = Field(min_length=64, max_length=64)
    evaluated_at: datetime

    @property
    def is_allowed(self) -> bool:
        """Helper to test if decision is an ALLOW."""
        return self.verdict == Verdict.ALLOW

    @property
    def is_blocked(self) -> bool:
        """Helper to test if decision is a BLOCK."""
        return self.verdict == Verdict.BLOCK

    @property
    def requires_approval(self) -> bool:
        """Helper to test if decision requires owner approval."""
        return self.verdict == Verdict.ASK_OWNER
