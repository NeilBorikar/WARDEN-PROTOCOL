"""Payment rail abstractions, protocols, and data structures.

WHY:
P1: AI proposes, deterministic code decides.
P2: Agents never see PayPal credentials. Only the payment adapter holds them.
P4: Fail closed. Errors, timeouts, or non-ALLOW verdicts must never move money.
Idempotency: Every payment carries an idempotency key. Retries must be safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from app.mandate.models import PaymentRequest
from app.policy.verdict import Decision


class RailPaymentStatus(StrEnum):
    """Lifecycle status of a payment on the rail."""

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class RailError(Exception):
    """Base exception for payment rail errors."""


class PaymentNotAllowedError(RailError):
    """Raised when an attempt is made to execute a payment without an ALLOW verdict.

    WHY: P4/P1: Money must never move unless the Bouncer's deterministic verdict
    is strictly ALLOW.
    """


class RailTransientError(RailError):
    """Raised on network timeouts or 5xx responses that can be safely retried."""


class RailPermanentError(RailError):
    """Raised on 4xx errors, invalid recipient, insufficient funds, etc."""


@dataclass(frozen=True)
class PaymentResult:
    """The outcome of a payment execution on a rail."""

    status: RailPaymentStatus
    rail_payment_id: str
    idempotency_key: str
    amount_minor: int
    currency: str
    payee_email: str
    raw_response: dict[str, Any] = field(default_factory=dict)
    executed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    fee_minor: int = 0
    error_message: str | None = None


class PaymentRail(Protocol):
    """Protocol for payment execution adapters.

    All implementations (MockRail, PayPalPayoutsRail, etc.) must conform to
    this protocol.
    """

    def execute_payment(
        self,
        request: PaymentRequest,
        decision: Decision,
    ) -> PaymentResult:
        """Execute the payment request if and only if decision.verdict is ALLOW.

        Args:
            request: The money-moving PaymentRequest.
            decision: The Bouncer's evaluated Decision.

        Raises:
            PaymentNotAllowedError: If decision.verdict != Verdict.ALLOW.
            RailPermanentError: On fatal payment failures.
            RailTransientError: On retriable network errors.
        """
        ...

    def get_payment_status(self, rail_payment_id: str) -> RailPaymentStatus:
        """Query the status of a previously submitted payment."""
        ...
