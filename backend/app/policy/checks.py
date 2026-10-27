"""Individual deterministic policy checks (C1 through C8).

WHY:
- Section 6: Evaluate ALL checks, collect all reasons, combine by most-restrictive-wins.
- Pure functions: no I/O, no network calls, no LLMs (P1).
- P3: Untrusted text can never change money-critical fields.
- P4: Fail closed.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import NamedTuple

from app.mandate.models import Deal, Intent, Mandate, PaymentRequest
from app.policy.provenance import (
    ProvenanceTag,
    is_trusted_provenance,
)
from app.policy.verdict import Reason, Verdict
from app.tools.registry import ToolRiskTier, get_tool_tier


class CheckResult(NamedTuple):
    """Output of a single policy check."""

    verdict: Verdict
    reason: Reason


def check_c1_mandate_validity(
    request: PaymentRequest,
    mandate: Mandate,
    intent: Intent | None,
    public_key_hex: str,
    revoked_mandate_ids: set[str] | None = None,
) -> CheckResult:
    """C1: Signatures and expiry of Mandate and Intent valid and not revoked."""
    # Check revocation
    if revoked_mandate_ids and mandate.mandate_id in revoked_mandate_ids:
        return CheckResult(
            Verdict.BLOCK,
            Reason(
                code="MANDATE_REVOKED",
                check_id="C1",
                message=f"Mandate {mandate.mandate_id} has been revoked.",
            ),
        )

    # Check mandate expiry
    if mandate.is_expired(request.created_at):
        return CheckResult(
            Verdict.BLOCK,
            Reason(
                code="MANDATE_EXPIRED",
                check_id="C1",
                message=f"Mandate expired at {mandate.expires_at.isoformat()}.",
            ),
        )

    # Check mandate signature
    if not mandate.verify_signature(public_key_hex):
        return CheckResult(
            Verdict.BLOCK,
            Reason(
                code="MANDATE_INVALID_SIGNATURE",
                check_id="C1",
                message="Mandate signature failed Ed25519 cryptographic verification.",
            ),
        )

    # Check request references this mandate
    if request.mandate_id != mandate.mandate_id:
        return CheckResult(
            Verdict.BLOCK,
            Reason(
                code="MANDATE_ID_MISMATCH",
                check_id="C1",
                message=(
                    f"Request mandate_id ({request.mandate_id}) does not match "
                    f"active mandate ({mandate.mandate_id})."
                ),
            ),
        )

    # Intent checks if present
    if intent is not None:
        if intent.mandate_id != mandate.mandate_id:
            return CheckResult(
                Verdict.BLOCK,
                Reason(
                    code="INTENT_MANDATE_MISMATCH",
                    check_id="C1",
                    message=(
                        f"Intent {intent.intent_id} references mandate {intent.mandate_id}, "
                        f"expected {mandate.mandate_id}."
                    ),
                ),
            )

        if intent.is_expired(request.created_at):
            return CheckResult(
                Verdict.BLOCK,
                Reason(
                    code="INTENT_EXPIRED",
                    check_id="C1",
                    message=f"Intent deadline was {intent.deadline.isoformat()}.",
                ),
            )

        if not intent.verify_signature(public_key_hex):
            return CheckResult(
                Verdict.BLOCK,
                Reason(
                    code="INTENT_INVALID_SIGNATURE",
                    check_id="C1",
                    message="Intent signature failed Ed25519 cryptographic verification.",
                ),
            )

        if request.intent_id != intent.intent_id:
            return CheckResult(
                Verdict.BLOCK,
                Reason(
                    code="INTENT_ID_MISMATCH",
                    check_id="C1",
                    message=(
                        f"Request intent_id ({request.intent_id}) does not match "
                        f"intent ({intent.intent_id})."
                    ),
                ),
            )

    return CheckResult(
        Verdict.ALLOW,
        Reason(
            code="MANDATE_AND_INTENT_VALID",
            check_id="C1",
            message="Mandate and Intent cryptographic signatures and validity confirmed.",
        ),
    )


def check_c2_tool_tier(request: PaymentRequest, mandate: Mandate) -> CheckResult:
    """C2: Tool tier check.

    GREEN: ALLOW immediately.
    YELLOW: ALLOW this check and continue to remaining checks.
    RED: Trigger ASK_OWNER or BLOCK per mandate.red_tier_policy.
    """
    tier = get_tool_tier(request.tool_name)
    if tier == ToolRiskTier.GREEN:
        return CheckResult(
            Verdict.ALLOW,
            Reason(
                code="TOOL_TIER_GREEN",
                check_id="C2",
                message=f"Tool '{request.tool_name}' is read-only (Tier GREEN). Safe to proceed.",
            ),
        )

    if tier == ToolRiskTier.YELLOW:
        return CheckResult(
            Verdict.ALLOW,
            Reason(
                code="TOOL_TIER_YELLOW",
                check_id="C2",
                message=(
                    f"Tool '{request.tool_name}' is money-moving (Tier YELLOW). "
                    "Proceeding with policy evaluation."
                ),
            ),
        )

    # RED tier
    action_verdict = Verdict.ASK_OWNER if mandate.red_tier_policy == "ASK_OWNER" else Verdict.BLOCK
    return CheckResult(
        action_verdict,
        Reason(
            code="TOOL_TIER_RED",
            check_id="C2",
            message=(
                f"Tool '{request.tool_name}' is high-risk administrative (Tier RED). "
                f"Mandate policy requires {mandate.red_tier_policy}."
            ),
        ),
    )


def check_c3_payee_allowlist(
    request: PaymentRequest, mandate: Mandate, deal: Deal | None
) -> CheckResult:
    """C3: Payee allow-list and deal payee match.

    Payee must match an allow-listed payee by verified email or ID, never by name in text.
    Payee differing from Deal gives BLOCK PAYEE_MISMATCH.
    Unlisted payee triggers mandate.new_payee_policy.
    """
    req_email = request.payee.email.strip().lower()
    req_id = request.payee.id.strip()

    # Deal payee lock
    if deal is not None and (
        req_email != deal.payee_email.strip().lower() or req_id != deal.payee_id.strip()
    ):
        return CheckResult(
                Verdict.BLOCK,
                Reason(
                    code="PAYEE_MISMATCH",
                    check_id="C3",
                    message=(
                        f"Requested payee ({req_email} / {req_id}) does not match "
                        f"agreed deal payee ({deal.payee_email} / {deal.payee_id})."
                    ),
                ),
            )

    # Check allow-list
    is_allowlisted = any(
        p.paypal_email.strip().lower() == req_email or p.payee_id.strip() == req_id
        for p in mandate.allowed_payees
    )

    if not is_allowlisted:
        action_verdict = (
            Verdict.ASK_OWNER if mandate.new_payee_policy == "ASK_OWNER" else Verdict.BLOCK
        )
        return CheckResult(
            action_verdict,
            Reason(
                code="NEW_PAYEE",
                check_id="C3",
                message=(
                    f"Payee '{req_email}' is not in allow-listed payees. "
                    f"Mandate policy requires {mandate.new_payee_policy}."
                ),
            ),
        )

    return CheckResult(
        Verdict.ALLOW,
        Reason(
            code="PAYEE_ALLOWLISTED",
            check_id="C3",
            message=f"Payee '{req_email}' is allow-listed and matches agreed terms.",
        ),
    )


def check_c4_amount_caps(request: PaymentRequest, mandate: Mandate) -> CheckResult:
    """C4: Amount above per_payment_cap gives BLOCK. Above approval_threshold gives ASK_OWNER."""
    # Check currency match first
    if request.currency != mandate.currency:
        return CheckResult(
            Verdict.BLOCK,
            Reason(
                code="CURRENCY_MISMATCH",
                check_id="C4",
                message=(
                    f"Requested currency '{request.currency}' does not match "
                    f"mandate currency '{mandate.currency}'."
                ),
            ),
        )

    if request.amount_minor > mandate.per_payment_cap_minor:
        return CheckResult(
            Verdict.BLOCK,
            Reason(
                code="PER_PAYMENT_CAP_EXCEEDED",
                check_id="C4",
                message=(
                    f"Amount {request.amount_minor} {request.currency} exceeds "
                    f"per-payment cap of {mandate.per_payment_cap_minor} {mandate.currency}."
                ),
            ),
        )

    if request.amount_minor > mandate.approval_threshold_minor:
        return CheckResult(
            Verdict.ASK_OWNER,
            Reason(
                code="APPROVAL_THRESHOLD_EXCEEDED",
                check_id="C4",
                message=(
                    f"Amount {request.amount_minor} {request.currency} exceeds approval "
                    f"threshold of {mandate.approval_threshold_minor} {mandate.currency}."
                ),
            ),
        )

    return CheckResult(
        Verdict.ALLOW,
        Reason(
            code="AMOUNT_WITHIN_CAPS",
            check_id="C4",
            message=f"Amount {request.amount_minor} {request.currency} is within all per-payment caps.",
        ),
    )


class HistoricalPayment(NamedTuple):
    """Historical payment record for velocity and rolling cap checks."""

    amount_minor: int
    executed_at: datetime


def check_c5_rolling_limits(
    request: PaymentRequest,
    mandate: Mandate,
    history: list[HistoricalPayment],
) -> CheckResult:
    """C5: Rolling 24-hour total including this request above daily_cap gives BLOCK.

    More than max_payments_per_hour in last 1 hour gives BLOCK.
    """
    now = request.created_at
    one_day_ago = now - timedelta(hours=24)
    one_hour_ago = now - timedelta(hours=1)

    # 24-hour rolling total
    rolling_24h_total = sum(p.amount_minor for p in history if p.executed_at >= one_day_ago)
    projected_24h_total = rolling_24h_total + request.amount_minor

    if projected_24h_total > mandate.daily_cap_minor:
        return CheckResult(
            Verdict.BLOCK,
            Reason(
                code="DAILY_CAP_EXCEEDED",
                check_id="C5",
                message=(
                    f"Projected 24h total ({projected_24h_total} {mandate.currency}) exceeds "
                    f"daily cap of {mandate.daily_cap_minor} {mandate.currency}."
                ),
            ),
        )

    # 1-hour velocity
    payments_last_hour = sum(1 for p in history if p.executed_at >= one_hour_ago)
    projected_hourly_count = payments_last_hour + 1

    if projected_hourly_count > mandate.max_payments_per_hour:
        return CheckResult(
            Verdict.BLOCK,
            Reason(
                code="HOURLY_VELOCITY_EXCEEDED",
                check_id="C5",
                message=(
                    f"Projected payments this hour ({projected_hourly_count}) exceeds "
                    f"hourly limit of {mandate.max_payments_per_hour}."
                ),
            ),
        )

    return CheckResult(
        Verdict.ALLOW,
        Reason(
            code="ROLLING_LIMITS_SATISFIED",
            check_id="C5",
            message=(
                f"Rolling 24h total ({projected_24h_total}/{mandate.daily_cap_minor}) "
                f"and hourly rate ({projected_hourly_count}/{mandate.max_payments_per_hour}) OK."
            ),
        ),
    )


def check_c6_deal_lock(
    request: PaymentRequest,
    intent: Intent | None,
    deal: Deal | None,
) -> CheckResult:
    """C6: Amount and currency must equal Deal total.

    Deal total must be at most Intent.max_total and unit prices within limits.
    Otherwise BLOCK.
    """
    if deal is None:
        return CheckResult(
            Verdict.BLOCK,
            Reason(
                code="DEAL_MISSING",
                check_id="C6",
                message="Payment request has no agreed Deal.",
            ),
        )

    # Check deal integrity
    if not deal.verify_terms_hash():
        return CheckResult(
            Verdict.BLOCK,
            Reason(
                code="DEAL_TERMS_TAMPERED",
                check_id="C6",
                message="Deal terms hash does not match computed hash of deal items.",
            ),
        )

    # Deal must match request amount and currency
    if request.amount_minor != deal.total_minor or request.currency != deal.currency:
        return CheckResult(
            Verdict.BLOCK,
            Reason(
                code="DEAL_MISMATCH",
                check_id="C6",
                message=(
                    f"Requested payment ({request.amount_minor} {request.currency}) does not match "
                    f"agreed deal ({deal.total_minor} {deal.currency})."
                ),
            ),
        )

    # Intent limits check
    if intent is not None:
        if deal.intent_id != intent.intent_id:
            return CheckResult(
                Verdict.BLOCK,
                Reason(
                    code="DEAL_INTENT_MISMATCH",
                    check_id="C6",
                    message=(
                        f"Deal intent_id ({deal.intent_id}) does not match "
                        f"intent ({intent.intent_id})."
                    ),
                ),
            )

        if deal.total_minor > intent.max_total_minor:
            return CheckResult(
                Verdict.BLOCK,
                Reason(
                    code="INTENT_MAX_TOTAL_EXCEEDED",
                    check_id="C6",
                    message=(
                        f"Deal total ({deal.total_minor}) exceeds Intent max total "
                        f"({intent.max_total_minor})."
                    ),
                ),
            )

        # Unit price caps per item
        intent_items_by_sku = {item.sku: item for item in intent.items}
        for item in deal.items:
            intent_item = intent_items_by_sku.get(item.sku)
            if intent_item is None:
                return CheckResult(
                    Verdict.BLOCK,
                    Reason(
                        code="UNAUTHORIZED_ITEM_SKU",
                        check_id="C6",
                        message=f"Deal item SKU '{item.sku}' was not authorized in Intent.",
                    ),
                )
            if item.unit_price_minor > intent_item.max_unit_price_minor:
                return CheckResult(
                    Verdict.BLOCK,
                    Reason(
                        code="ITEM_UNIT_PRICE_EXCEEDED",
                        check_id="C6",
                        message=(
                            f"Item '{item.sku}' unit price ({item.unit_price_minor}) exceeds "
                            f"authorized limit ({intent_item.max_unit_price_minor})."
                        ),
                    ),
                )

    return CheckResult(
        Verdict.ALLOW,
        Reason(
            code="DEAL_LOCK_SATISFIED",
            check_id="C6",
            message="Payment strictly matches agreed Deal terms, Intent caps, and unit prices.",
        ),
    )


def check_c7_provenance(
    request: PaymentRequest,
    deal: Deal | None,
) -> CheckResult:
    """C7: Provenance validation.

    A payee or amount from UNTRUSTED_EXTERNAL not validated against signed documents
    gives ASK_OWNER, or BLOCK if it conflicts with them.
    """
    amount_prov = request.provenance.get("amount_minor", ProvenanceTag.UNTRUSTED_EXTERNAL.value)
    payee_prov = request.provenance.get("payee", ProvenanceTag.UNTRUSTED_EXTERNAL.value)

    # Check for direct conflicts with signed Deal
    if deal is not None:
        if request.amount_minor != deal.total_minor:
            return CheckResult(
                Verdict.BLOCK,
                Reason(
                    code="UNTRUSTED_DATA_CONFLICT",
                    check_id="C7",
                    message="Requested amount conflicts with verified Deal total.",
                ),
            )
        if (
            request.payee.email.strip().lower() != deal.payee_email.strip().lower()
            or request.payee.id.strip() != deal.payee_id.strip()
        ):
            return CheckResult(
                Verdict.BLOCK,
                Reason(
                    code="UNTRUSTED_DATA_CONFLICT",
                    check_id="C7",
                    message="Requested payee conflicts with verified Deal payee.",
                ),
            )

    # If critical fields originated directly from untrusted sources without validation
    if not is_trusted_provenance(amount_prov) or not is_trusted_provenance(payee_prov):
        # If deal exists and matches, the agent derived/validated it against the record
        if deal is not None:
            return CheckResult(
                Verdict.ALLOW,
                Reason(
                    code="PROVENANCE_RECORD_VERIFIED",
                    check_id="C7",
                    message="Payment parameters verified against agreed Deal record.",
                ),
            )
        # Without a verified deal record or owner provenance, must ask owner
        return CheckResult(
            Verdict.ASK_OWNER,
            Reason(
                code="UNTRUSTED_DATA",
                check_id="C7",
                message=(
                    "Money-critical fields carry unverified provenance: "
                    f"amount={amount_prov}, payee={payee_prov}. Requires owner approval."
                ),
            ),
        )

    return CheckResult(
        Verdict.ALLOW,
        Reason(
            code="PROVENANCE_VERIFIED",
            check_id="C7",
            message="All money-critical fields carry trusted provenance.",
        ),
    )


def check_c8_purpose(request: PaymentRequest, mandate: Mandate) -> CheckResult:
    """C8: Purpose must be in allowed_purposes."""
    clean_purpose = request.purpose.strip()
    allowed_set = {p.strip().lower() for p in mandate.allowed_purposes}

    if clean_purpose.lower() not in allowed_set:
        return CheckResult(
            Verdict.BLOCK,
            Reason(
                code="PURPOSE_DISALLOWED",
                check_id="C8",
                message=(
                    f"Purpose '{clean_purpose}' is not in allowed purposes: "
                    f"{mandate.allowed_purposes}."
                ),
            ),
        )

    return CheckResult(
        Verdict.ALLOW,
        Reason(
            code="PURPOSE_ALLOWED",
            check_id="C8",
            message=f"Purpose '{clean_purpose}' is allow-listed in Mandate.",
        ),
    )
