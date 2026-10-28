"""Payment rails - PayPal adapters and mock rail."""

from app.payments.gateway import GatewayOutcome, PaymentGateway
from app.payments.mock_rail import MockRail
from app.payments.paypal_orders import PayPalOrdersRail
from app.payments.paypal_payouts import PayPalPayoutsRail
from app.payments.rail import (
    PaymentNotAllowedError,
    PaymentRail,
    PaymentResult,
    RailError,
    RailPaymentStatus,
    RailPermanentError,
    RailTransientError,
)
from app.payments.token import PayPalTokenManager
from app.payments.webhook import PayPalWebhookVerifier, WebhookVerificationResult

__all__ = [
    "GatewayOutcome",
    "MockRail",
    "PayPalOrdersRail",
    "PayPalPayoutsRail",
    "PayPalTokenManager",
    "PayPalWebhookVerifier",
    "PaymentGateway",
    "PaymentNotAllowedError",
    "PaymentRail",
    "PaymentResult",
    "RailError",
    "RailPaymentStatus",
    "RailPermanentError",
    "RailTransientError",
    "WebhookVerificationResult",
]
