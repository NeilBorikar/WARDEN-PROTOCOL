"""Negotiation loop orchestrating Buyer ↔ Seller turns.

WHY:
- Section 7: "Max 8 negotiation turns, per-call token caps, per-run budget."
- The negotiation loop coordinates turn-based interaction between Buyer and Seller,
  culminating in a Deal confirmation and PaymentRequest submission.
- All seller output is UNTRUSTED_EXTERNAL.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from app.agents.buyer import BuyerAgent
from app.agents.seller import SellerAgent
from app.agents.verifier import VerifierAgent, VerifierOpinion
from app.audit.log import AuditLog
from app.mandate.models import Deal, PaymentRequest
from app.payments.gateway import GatewayOutcome, PaymentGateway
from app.policy.verdict import Verdict

logger = logging.getLogger(__name__)

MAX_TURNS = 8


class NegotiationStatus(StrEnum):
    """Current status of a negotiation run."""

    IN_PROGRESS = "IN_PROGRESS"
    DEAL_CONFIRMED = "DEAL_CONFIRMED"
    PAYMENT_REQUESTED = "PAYMENT_REQUESTED"
    PAYMENT_EXECUTED = "PAYMENT_EXECUTED"
    PAYMENT_BLOCKED = "PAYMENT_BLOCKED"
    PAYMENT_NEEDS_APPROVAL = "PAYMENT_NEEDS_APPROVAL"
    MAX_TURNS_REACHED = "MAX_TURNS_REACHED"
    ERROR = "ERROR"


@dataclass
class NegotiationTurn:
    """Record of a single turn in the negotiation."""

    turn_number: int
    seller_message: str
    buyer_message: str
    seller_offer: dict[str, Any] | None = None
    buyer_action: dict[str, Any] | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class NegotiationResult:
    """Complete result of a negotiation run."""

    run_id: str
    status: NegotiationStatus
    turns: list[NegotiationTurn]
    deal: Deal | None = None
    payment_request: PaymentRequest | None = None
    gateway_outcome: GatewayOutcome | None = None
    verifier_opinion: VerifierOpinion | None = None
    error: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    @property
    def total_turns(self) -> int:
        return len(self.turns)


class NegotiationLoop:
    """Orchestrates a complete Buyer ↔ Seller negotiation with Bouncer-gated payment.

    Flow:
    1. Seller presents products, Buyer negotiates (up to MAX_TURNS rounds).
    2. When terms are agreed, Buyer creates a Deal (locking payee, items, total).
    3. Buyer creates a PaymentRequest from the Deal.
    4. Verifier provides Second Opinion (can only escalate).
    5. PaymentGateway evaluates through Bouncer and executes on payment rail if ALLOW.
    6. Everything is logged to the tamper-evident audit chain.
    """

    def __init__(
        self,
        buyer: BuyerAgent,
        seller: SellerAgent,
        gateway: PaymentGateway,
        audit_log: AuditLog,
        verifier: VerifierAgent | None = None,
        max_turns: int = MAX_TURNS,
    ) -> None:
        self.buyer = buyer
        self.seller = seller
        self.gateway = gateway
        self.audit_log = audit_log
        self.verifier = verifier
        self.max_turns = max_turns

    def run(
        self,
        initial_buyer_message: str = "Hello, I'd like to purchase some items.",
        owner_public_key_hex: str = "",
    ) -> NegotiationResult:
        """Execute a complete negotiation run.

        Returns NegotiationResult with status, turns, deal, payment, etc.
        """
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        result = NegotiationResult(
            run_id=run_id,
            status=NegotiationStatus.IN_PROGRESS,
            turns=[],
        )

        # Log run start
        self.audit_log.append(
            type_="NEGOTIATION_STARTED",
            payload={
                "run_id": run_id,
                "mandate_id": self.buyer.mandate.mandate_id,
                "intent_id": self.buyer.intent.intent_id,
            },
        )

        try:
            # Initial buyer message to seller
            current_buyer_msg = initial_buyer_message

            for turn_num in range(1, self.max_turns + 1):
                # Seller responds
                seller_text, seller_offer = self.seller.respond(current_buyer_msg)

                # Buyer processes seller response
                buyer_text, buyer_action = self.buyer.negotiate(seller_text)

                turn = NegotiationTurn(
                    turn_number=turn_num,
                    seller_message=seller_text,
                    buyer_message=buyer_text,
                    seller_offer=seller_offer,
                    buyer_action=buyer_action,
                )
                result.turns.append(turn)

                # Log the turn
                self.audit_log.append(
                    type_="NEGOTIATION_TURN",
                    payload={
                        "run_id": run_id,
                        "turn": turn_num,
                        "seller_text": seller_text[:500],
                        "buyer_text": buyer_text[:500],
                        "has_offer": seller_offer is not None,
                        "has_action": buyer_action is not None,
                    },
                )

                # Normalize buyer actions to a list
                action_list: list[dict[str, Any]] = (
                    buyer_action
                    if isinstance(buyer_action, list)
                    else ([buyer_action] if buyer_action else [])
                )

                # Process deal confirmation first if present
                for act in action_list:
                    if act.get("type") == "deal":
                        deal = self.buyer.create_deal_from_offer(act)
                        result.deal = deal
                        result.status = NegotiationStatus.DEAL_CONFIRMED

                        self.audit_log.append(
                            type_="DEAL_CONFIRMED",
                            payload={
                                "run_id": run_id,
                                "deal_id": deal.deal_id,
                                "payee_id": deal.payee_id,
                                "total_minor": deal.total_minor,
                                "currency": deal.currency,
                                "terms_hash": deal.terms_hash,
                            },
                        )

                # Then process payment request if present
                payment_processed = False
                for act in action_list:
                    if act.get("type") == "payment_request":
                        if result.deal is None:
                            result.status = NegotiationStatus.ERROR
                            result.error = "Payment requested without confirmed Deal"
                            payment_processed = True
                            break

                        purpose = act.get("purpose", "SUPPLIES")
                        memo = act.get("memo", "")
                        payment_req = self.buyer.create_payment_request(
                            result.deal, purpose=purpose, memo=memo
                        )
                        result.payment_request = payment_req
                        result.status = NegotiationStatus.PAYMENT_REQUESTED

                        # Execute payment through gateway
                        outcome = self._execute_payment(
                            payment_req,
                            result.deal,
                            owner_public_key_hex,
                            run_id,
                        )
                        result.gateway_outcome = outcome

                        if outcome.decision.verdict == Verdict.ALLOW and outcome.executed:
                            result.status = NegotiationStatus.PAYMENT_EXECUTED
                        elif outcome.decision.verdict == Verdict.ASK_OWNER:
                            result.status = NegotiationStatus.PAYMENT_NEEDS_APPROVAL
                        else:
                            result.status = NegotiationStatus.PAYMENT_BLOCKED

                        payment_processed = True
                        break

                if payment_processed:
                    break

                # Check if negotiation ended naturally
                if self.seller.state.negotiation_complete and not buyer_action:
                    break

                current_buyer_msg = buyer_text

            if result.status == NegotiationStatus.IN_PROGRESS:
                result.status = NegotiationStatus.MAX_TURNS_REACHED

        except Exception as exc:
            logger.error("Negotiation error in run %s: %s", run_id, exc)
            result.status = NegotiationStatus.ERROR
            result.error = str(exc)

        result.completed_at = datetime.now(UTC)

        self.audit_log.append(
            type_="NEGOTIATION_COMPLETED",
            payload={
                "run_id": run_id,
                "status": result.status.value,
                "total_turns": result.total_turns,
                "has_deal": result.deal is not None,
                "has_payment": result.payment_request is not None,
            },
        )

        return result

    def _execute_payment(
        self,
        payment_req: PaymentRequest,
        deal: Deal,
        owner_public_key_hex: str,
        run_id: str,
    ) -> GatewayOutcome:
        """Execute payment through verifier and gateway."""
        # Step 1: Optional Second Opinion from Verifier
        if self.verifier is not None:
            try:
                opinion = self.verifier.review(
                    payment_request=payment_req,
                    intent=self.buyer.intent,
                    deal=deal,
                    current_verdict=Verdict.ALLOW,  # Pre-policy verdict
                    negotiation_summary=self._build_negotiation_summary(),
                )

                self.audit_log.append(
                    type_="VERIFIER_OPINION",
                    payload={
                        "run_id": run_id,
                        "consistent": opinion.consistent,
                        "concerns": opinion.concerns,
                        "suggested_verdict": opinion.suggested_verdict.value,
                    },
                )

                # If verifier escalates, we don't short-circuit - the gateway
                # will re-evaluate through the full Bouncer policy engine
                if opinion.suggested_verdict != Verdict.ALLOW:
                    logger.info(
                        "Verifier escalated to %s: %s",
                        opinion.suggested_verdict.value,
                        opinion.concerns,
                    )

            except Exception as exc:
                logger.warning("Verifier error: %s, proceeding with Bouncer only", exc)

        # Step 2: Gateway (Bouncer policy + rail execution)
        return self.gateway.process_payment(
            request=payment_req,
            mandate=self.buyer.mandate,
            owner_public_key_hex=owner_public_key_hex,
            intent=self.buyer.intent,
            deal=deal,
        )

    def _build_negotiation_summary(self) -> str:
        """Build a summary of the negotiation for the verifier."""
        lines = []
        for turn in self.buyer.state.transcript[-4:]:  # Last 4 messages
            lines.append(f"[{turn['role'].upper()}]: {turn['content'][:200]}")
        return "\n".join(lines)


def run_scripted_negotiation(
    buyer: BuyerAgent,
    seller: SellerAgent,
    gateway: PaymentGateway,
    audit_log: AuditLog,
    offer: dict[str, Any],
    purpose: str,
    owner_public_key_hex: str,
    memo: str = "",
    verifier: VerifierAgent | None = None,
) -> NegotiationResult:
    """Run a fully scripted negotiation with predetermined offer.

    WHY: Enables deterministic demos and tests without LLM calls.
    The "negotiation" is a single turn where terms are immediately agreed.
    """
    run_id = f"run-scripted-{uuid.uuid4().hex[:8]}"

    # Create deal and payment request directly
    deal, payment_req = buyer.create_deal_and_payment_scripted(
        offer=offer, purpose=purpose, memo=memo
    )

    audit_log.append(
        type_="SCRIPTED_NEGOTIATION_STARTED",
        payload={"run_id": run_id, "deal_id": deal.deal_id},
    )

    # Run through gateway
    loop = NegotiationLoop(
        buyer=buyer,
        seller=seller,
        gateway=gateway,
        audit_log=audit_log,
        verifier=verifier,
    )

    outcome = loop._execute_payment(payment_req, deal, owner_public_key_hex, run_id)

    status: NegotiationStatus
    if outcome.decision.verdict == Verdict.ALLOW and outcome.executed:
        status = NegotiationStatus.PAYMENT_EXECUTED
    elif outcome.decision.verdict == Verdict.ASK_OWNER:
        status = NegotiationStatus.PAYMENT_NEEDS_APPROVAL
    else:
        status = NegotiationStatus.PAYMENT_BLOCKED

    result = NegotiationResult(
        run_id=run_id,
        status=status,
        turns=[],
        deal=deal,
        payment_request=payment_req,
        gateway_outcome=outcome,
        completed_at=datetime.now(UTC),
    )

    audit_log.append(
        type_="SCRIPTED_NEGOTIATION_COMPLETED",
        payload={"run_id": run_id, "status": status.value},
    )

    return result
