"""Application state and dependencies for API endpoints.

WHY:
- Centralizes shared instances (AuditLog, ApprovalService, PaymentGateway, Rails).
- Enables clean dependency injection in FastAPI routers.
- Keeps router handlers thin, typed, and easily testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agents.negotiation import NegotiationResult
from app.approvals.service import ApprovalService
from app.audit.log import AuditLog
from app.config import Settings, get_settings
from app.mandate.models import Intent, Mandate
from app.payments.gateway import PaymentGateway
from app.payments.mock_rail import MockRail
from app.payments.paypal_payouts import PayPalPayoutsRail
from app.payments.rail import PaymentRail


@dataclass
class AppState:
    """In-memory state container for the Mandate Arena runtime."""

    settings: Settings = field(default_factory=get_settings)
    audit_log: AuditLog = field(default_factory=AuditLog)
    approval_service: ApprovalService = field(default_factory=ApprovalService)
    rail: PaymentRail = field(init=False)
    gateway: PaymentGateway = field(init=False)
    runs: dict[str, NegotiationResult] = field(default_factory=dict)
    mandates: dict[str, Mandate] = field(default_factory=dict)
    intents: dict[str, Intent] = field(default_factory=dict)
    owner_keys: dict[str, str] = field(default_factory=dict)  # owner_id -> public_key_hex
    arena_sessions: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Select rail based on PRIMARY_RAIL and credentials availability
        if (
            self.settings.primary_rail == "payouts"
            and self.settings.paypal_client_id
            and self.settings.paypal_client_secret
        ):
            from app.payments.token import PayPalTokenManager
            token_mgr = PayPalTokenManager(
                client_id=self.settings.paypal_client_id,
                client_secret=self.settings.paypal_client_secret,
                base_url=self.settings.paypal_base_url,
            )
            self.rail = PayPalPayoutsRail(
                token_manager=token_mgr,
                base_url=self.settings.paypal_base_url,
            )
        else:
            self.rail = MockRail()

        self.gateway = PaymentGateway(
            rail=self.rail,
            audit_log=self.audit_log,
            approval_service=self.approval_service,
        )


_global_state: AppState | None = None


def get_app_state() -> AppState:
    """Return the global AppState singleton."""
    global _global_state
    if _global_state is None:
        _global_state = AppState()
    return _global_state


def reset_app_state() -> AppState:
    """Reset the global state (used in testing)."""
    global _global_state
    _global_state = AppState()
    return _global_state
