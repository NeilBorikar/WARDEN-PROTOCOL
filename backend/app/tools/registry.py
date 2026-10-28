"""Tool risk tier registry for PayPal Agent Toolkit integration.

WHY: Check C2 classifies tools by financial risk:
- GREEN: Read-only queries. Safe to ALLOW immediately without policy checks.
- YELLOW: Money-moving operations (orders, payouts, invoices). Proceed to full policy checks.
- RED: High-risk sensitive actions (refunds, dispute acceptances, invoice cancellations,
  subscription modifications). Must trigger ASK_OWNER or BLOCK based on mandate.red_tier_policy.

Unrecognized tools always fail closed to RED (P4).
"""

from __future__ import annotations

from enum import StrEnum


class ToolRiskTier(StrEnum):
    """Risk tier classifications for agent-callable tools."""

    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


# Map tool name -> risk tier across all PayPal Agent Toolkit categories
TOOL_TIERS: dict[str, ToolRiskTier] = {
    # -------------------------------------------------------------
    # 1. INVOICES
    # -------------------------------------------------------------
    "get_invoice": ToolRiskTier.GREEN,
    "list_invoices": ToolRiskTier.GREEN,
    "generate_invoice_number": ToolRiskTier.GREEN,
    "create_invoice": ToolRiskTier.YELLOW,
    "send_invoice": ToolRiskTier.YELLOW,
    "send_invoice_reminder": ToolRiskTier.YELLOW,
    "cancel_sent_invoice": ToolRiskTier.RED,
    "delete_invoice": ToolRiskTier.RED,
    "record_payment_for_invoice": ToolRiskTier.RED,
    "record_refund_for_invoice": ToolRiskTier.RED,
    # -------------------------------------------------------------
    # 2. ORDERS & CHECKOUT
    # -------------------------------------------------------------
    "get_order": ToolRiskTier.GREEN,
    "show_order": ToolRiskTier.GREEN,
    "create_order": ToolRiskTier.YELLOW,
    "pay_order": ToolRiskTier.YELLOW,
    "capture_order": ToolRiskTier.YELLOW,
    "authorize_order": ToolRiskTier.YELLOW,
    # -------------------------------------------------------------
    # 3. PAYOUTS
    # -------------------------------------------------------------
    "get_payout_batch": ToolRiskTier.GREEN,
    "get_payout_item": ToolRiskTier.GREEN,
    "payouts": ToolRiskTier.YELLOW,
    "create_payout": ToolRiskTier.YELLOW,
    "request_payment": ToolRiskTier.YELLOW,
    # -------------------------------------------------------------
    # 4. BALANCE & REPORTING
    # -------------------------------------------------------------
    "get_balance": ToolRiskTier.GREEN,
    "list_balances": ToolRiskTier.GREEN,
    "list_transactions": ToolRiskTier.GREEN,
    # -------------------------------------------------------------
    # 5. CATALOG & PRODUCTS
    # -------------------------------------------------------------
    "show_catalog_items": ToolRiskTier.GREEN,
    "list_products": ToolRiskTier.GREEN,
    "get_product": ToolRiskTier.GREEN,
    "create_product": ToolRiskTier.YELLOW,
    # -------------------------------------------------------------
    # 6. DISPUTES
    # -------------------------------------------------------------
    "get_dispute": ToolRiskTier.GREEN,
    "list_disputes": ToolRiskTier.GREEN,
    "accept_dispute_claim": ToolRiskTier.RED,
    "provide_dispute_evidence": ToolRiskTier.RED,
    # -------------------------------------------------------------
    # 7. SHIPMENT TRACKING
    # -------------------------------------------------------------
    "get_tracking_info": ToolRiskTier.GREEN,
    "list_trackers": ToolRiskTier.GREEN,
    "add_tracking": ToolRiskTier.YELLOW,
    "update_tracking": ToolRiskTier.YELLOW,
    # -------------------------------------------------------------
    # 8. SUBSCRIPTIONS
    # -------------------------------------------------------------
    "get_subscription": ToolRiskTier.GREEN,
    "list_subscriptions": ToolRiskTier.GREEN,
    "create_subscription": ToolRiskTier.YELLOW,
    "cancel_subscription": ToolRiskTier.RED,
    "update_subscription": ToolRiskTier.RED,
    "suspend_subscription": ToolRiskTier.RED,
    # -------------------------------------------------------------
    # 9. REFUNDS
    # -------------------------------------------------------------
    "get_refund_details": ToolRiskTier.GREEN,
    "create_refund": ToolRiskTier.RED,
    "refund_captured_payment": ToolRiskTier.RED,
}


def get_tool_tier(tool_name: str) -> ToolRiskTier:
    """Return risk tier for a tool. Unrecognized tools fail closed to RED.

    WHY: Fail closed (P4). If an unknown tool is invoked, it must never be
    treated as GREEN or YELLOW.
    """
    return TOOL_TIERS.get(tool_name.lower().strip(), ToolRiskTier.RED)
