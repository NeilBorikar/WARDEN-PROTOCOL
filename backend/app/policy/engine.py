"""Deterministic Policy Engine (The Bouncer).

WHY:
- Section 6: Evaluate ALL checks, collect all reasons, combine by most-restrictive-wins.
- Pure evaluation: no I/O, no database queries, no network calls, no LLMs (P1).
- Fail closed: any error during evaluation results in BLOCK (P4).
- Cryptographically binds decision to mandate_hash and request_hash.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.mandate.models import Deal, Intent, Mandate, PaymentRequest
from app.policy.checks import (
    CheckResult,
    HistoricalPayment,
    check_c1_mandate_validity,
    check_c2_tool_tier,
    check_c3_payee_allowlist,
    check_c4_amount_caps,
    check_c5_rolling_limits,
    check_c6_deal_lock,
    check_c7_provenance,
    check_c8_purpose,
)
from app.policy.verdict import Decision, Reason, Verdict, combine_verdicts
from app.tools.registry import ToolRiskTier, get_tool_tier

POLICY_ENGINE_VERSION = "1.0.0"


class PolicyEngine:
    """Pure, deterministic policy engine implementing Section 6 checks."""

    @classmethod
    def evaluate(
        cls,
        request: PaymentRequest,
        mandate: Mandate,
        intent: Intent | None,
        deal: Deal | None,
        owner_public_key_hex: str | bytes,
        history: list[HistoricalPayment] | None = None,
        revoked_mandate_ids: set[str] | None = None,
        evaluated_at: datetime | None = None,
    ) -> Decision:
        """Evaluate payment request against Mandate, Intent, Deal and history.

        Evaluates ALL applicable checks and aggregates reasons.
        Most restrictive verdict wins (P5: BLOCK > ASK_OWNER > ALLOW).
        """
        pub_hex = (
            owner_public_key_hex.hex()
            if isinstance(owner_public_key_hex, (bytes, bytearray))
            else owner_public_key_hex
        )
        now = evaluated_at or datetime.now(UTC)
        history_list = history or []
        revoked_set = revoked_mandate_ids or set()

        mandate_hash = mandate.compute_hash()
        request_hash = request.compute_hash()

        # Gather results from all checks
        results: list[CheckResult] = []

        try:
            # C1: Mandate & Intent validity
            results.append(
                check_c1_mandate_validity(
                    request,
                    mandate,
                    intent,
                    pub_hex,
                    revoked_mandate_ids=revoked_set,
                )
            )

            # C2: Tool tier
            c2_result = check_c2_tool_tier(request, mandate)
            results.append(c2_result)

            # If tool is purely read-only GREEN, evaluate C1 and C2 only
            if get_tool_tier(request.tool_name) == ToolRiskTier.GREEN:
                verdicts = [r.verdict for r in results]
                final_verdict = combine_verdicts(verdicts)
                return Decision(
                    verdict=final_verdict,
                    reasons=[r.reason for r in results],
                    policy_version=POLICY_ENGINE_VERSION,
                    mandate_hash=mandate_hash,
                    request_hash=request_hash,
                    evaluated_at=now,
                )

            # C3: Payee allow-list & deal payee lock
            results.append(check_c3_payee_allowlist(request, mandate, deal))

            # C4: Amount caps & approval threshold
            results.append(check_c4_amount_caps(request, mandate))

            # C5: Rolling 24h & hourly limits
            results.append(check_c5_rolling_limits(request, mandate, history_list))

            # C6: Deal lock & intent caps
            results.append(check_c6_deal_lock(request, intent, deal))

            # C7: Provenance validation
            results.append(check_c7_provenance(request, deal))

            # C8: Purpose allow-list
            results.append(check_c8_purpose(request, mandate))

        except Exception as exc:
            # Principle P4: Fail closed. Errors produce BLOCK, never ALLOW.
            return Decision(
                verdict=Verdict.BLOCK,
                reasons=[
                    Reason(
                        code="EVALUATION_ERROR",
                        check_id="ENGINE",
                        message=f"Policy evaluation encountered unexpected error: {exc!s}",
                    )
                ],
                policy_version=POLICY_ENGINE_VERSION,
                mandate_hash=mandate_hash,
                request_hash=request_hash,
                evaluated_at=now,
            )

        # Combine verdicts: BLOCK > ASK_OWNER > ALLOW (P5)
        verdicts = [r.verdict for r in results]
        final_verdict = combine_verdicts(verdicts)

        return Decision(
            verdict=final_verdict,
            reasons=[r.reason for r in results],
            policy_version=POLICY_ENGINE_VERSION,
            mandate_hash=mandate_hash,
            request_hash=request_hash,
            evaluated_at=now,
        )


def evaluate_payment_request(
    request: PaymentRequest,
    mandate: Mandate,
    intent: Intent | None = None,
    deal: Deal | None = None,
    owner_public_key: str | bytes | None = None,
    history: list[HistoricalPayment] | None = None,
    revoked_mandate_ids: set[str] | None = None,
    evaluated_at: datetime | None = None,
) -> Decision:
    """Convenience functional wrapper around PolicyEngine.evaluate."""
    pub_key: str | bytes = owner_public_key or ""
    return PolicyEngine.evaluate(
        request=request,
        mandate=mandate,
        intent=intent,
        deal=deal,
        owner_public_key_hex=pub_key,
        history=history,
        revoked_mandate_ids=revoked_mandate_ids,
        evaluated_at=evaluated_at,
    )
