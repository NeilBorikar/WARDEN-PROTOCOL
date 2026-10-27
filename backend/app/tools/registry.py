"""Tool risk tier registry.

WHY: Check C2 classifies tools by financial risk:
- GREEN: Read-only queries. Safe to ALLOW immediately.
- YELLOW: Money-moving operations (orders, payouts, invoices). Proceed to full policy checks.
- RED: High-risk actions (refunds, dispute acceptances, invoice cancellations).
  Must trigger ASK_OWNER or BLOCK based on mandate.red_tier_policy.
"""

from __future__ import annotations

from enum import StrEnum


class ToolRiskTier(StrEnum):
    """Risk tier classifications for agent-callable tools."""

    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


# Map tool name -> risk tier
TOOL_TIERS: dict[str, ToolRiskTier] = {
    # GREEN: Read-only queries
    "get_invoice": ToolRiskTier.GREEN,
    "list_invoices": ToolRiskTier.GREEN,
    "get_order": ToolRiskTier.GREEN,
    "show_order": ToolRiskTier.GREEN,
    "get_payout_batch": ToolRiskTier.GREEN,
    "get_payout_item": ToolRiskTier.GREEN,
    "get_balance": ToolRiskTier.GREEN,
    "list_transactions": ToolRiskTier.GREEN,
    "show_catalog_items": ToolRiskTier.GREEN,
    "get_dispute": ToolRiskTier.GREEN,
    "list_disputes": ToolRiskTier.GREEN,
    "get_tracking_info": ToolRiskTier.GREEN,
    # YELLOW: Money-moving operations
    "payouts": ToolRiskTier.YELLOW,
    "create_order": ToolRiskTier.YELLOW,
    "pay_order": ToolRiskTier.YELLOW,
    "capture_order": ToolRiskTier.YELLOW,
    "create_invoice": ToolRiskTier.YELLOW,
    "send_invoice": ToolRiskTier.YELLOW,
    # RED: Sensitive / administrative / reversals
    "accept_dispute_claim": ToolRiskTier.RED,
    "create_refund": ToolRiskTier.RED,
    "record_refund_for_invoice": ToolRiskTier.RED,
    "cancel_sent_invoice": ToolRiskTier.RED,
    "delete_invoice": ToolRiskTier.RED,
    "record_payment_for_invoice": ToolRiskTier.RED,
    "cancel_subscription": ToolRiskTier.RED,
    "update_subscription": ToolRiskTier.RED,
}


def get_tool_tier(tool_name: str) -> ToolRiskTier:
    """Return risk tier for a tool. Unrecognized tools fail closed to RED.

    WHY: Fail closed (P4). If an unknown tool is invoked, it must never be
    treated as GREEN or YELLOW.
    """
    return TOOL_TIERS.get(tool_name.lower().strip(), ToolRiskTier.RED)
