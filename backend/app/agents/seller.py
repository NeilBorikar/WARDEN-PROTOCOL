"""Seller Agent - AI-powered product supplier in negotiation scenarios.

WHY:
- Section 7: "All Seller content is UNTRUSTED_EXTERNAL."
- The Seller responds to buyer queries with product listings, pricing,
  and final offers. Its outputs are always tagged as UNTRUSTED_EXTERNAL
  and can never directly influence money-critical fields.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from app.llm.client import (
    LLMClient,
    LLMMessage,
    LLMResponse,
    ToolDefinition,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProductListing:
    """A product offered by the seller."""

    sku: str
    title: str
    unit_price_minor: int
    currency: str
    description: str = ""
    in_stock: bool = True


@dataclass
class SellerState:
    """Mutable state tracking seller's negotiation position."""

    catalog: list[ProductListing] = field(default_factory=list)
    offered_total_minor: int = 0
    offered_items: list[dict[str, Any]] = field(default_factory=list)
    negotiation_complete: bool = False
    final_offer_made: bool = False


DEFAULT_CATALOG: list[ProductListing] = [
    ProductListing(
        sku="PAPER-A4",
        title="A4 Copy Paper (500 sheets)",
        unit_price_minor=1500,
        currency="USD",
        description="Standard white copy paper",
    ),
    ProductListing(
        sku="TONER-BLK",
        title="Black Laser Toner Cartridge",
        unit_price_minor=3500,
        currency="USD",
        description="High yield replacement black toner",
    ),
    ProductListing(
        sku="PENS-BOX",
        title="Ballpoint Pens Box of 50",
        unit_price_minor=1200,
        currency="USD",
        description="Smooth writing black ballpoint pens",
    ),
]


SELLER_SYSTEM_PROMPT = """You are a Seller AI agent in a commercial negotiation.

Your role:
1. Present products from your catalog when asked.
2. Negotiate pricing within your pricing guidelines.
3. When terms are agreed, produce a final offer using the `make_offer` tool.

Guidelines:
- Be professional and helpful.
- You may offer small discounts (up to 10%) to close deals.
- Always include SKU, quantity, and unit price in your offer.
- Never misrepresent your products.

Your catalog will be provided in the conversation."""


class SellerAgent:
    """AI Seller agent for negotiation scenarios.

    WHY: Produces product listings and negotiated offers that are always
    treated as UNTRUSTED_EXTERNAL by the Bouncer. This ensures that even
    a compromised or adversarial seller cannot bypass policy checks.
    """

    TOOLS: list[ToolDefinition] = [
        ToolDefinition(
            name="make_offer",
            description=(
                "Submit a final offer to the buyer with agreed items and pricing. "
                "This finalizes the negotiation from the seller's side."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "sku": {"type": "string"},
                                "title": {"type": "string"},
                                "qty": {"type": "integer"},
                                "unit_price_minor": {"type": "integer"},
                            },
                            "required": ["sku", "title", "qty", "unit_price_minor"],
                        },
                    },
                    "total_minor": {"type": "integer"},
                    "currency": {"type": "string"},
                    "payee_email": {"type": "string"},
                    "payee_id": {"type": "string"},
                },
                "required": ["items", "total_minor", "currency", "payee_email", "payee_id"],
            },
        ),
    ]

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        catalog: list[ProductListing] | None = None,
        payee_email: str = "seller@example.com",
        payee_id: str = "seller-1",
    ) -> None:
        from app.llm.fake import FakeLLMClient

        self.llm = llm_client if llm_client is not None else FakeLLMClient()
        self.state = SellerState(catalog=list(catalog if catalog is not None else DEFAULT_CATALOG))
        self.payee_email = payee_email
        self.payee_id = payee_id
        self._messages: list[LLMMessage] = []
        self._init_conversation()

    def _init_conversation(self) -> None:
        """Initialize seller with system prompt and catalog context."""
        catalog_text = self._format_catalog()
        system_content = (
            f"{SELLER_SYSTEM_PROMPT}\n\n"
            f"Your payee email: {self.payee_email}\n"
            f"Your payee ID: {self.payee_id}\n\n"
            f"CATALOG:\n{catalog_text}"
        )
        self._messages = [LLMMessage(role="system", content=system_content)]

    def _format_catalog(self) -> str:
        """Format catalog for system prompt."""
        if not self.state.catalog:
            return "No products configured."
        lines = []
        for p in self.state.catalog:
            price_str = f"{p.unit_price_minor / 100:.2f} {p.currency}"
            stock = "In stock" if p.in_stock else "Out of stock"
            lines.append(f"- {p.sku}: {p.title} | {price_str} | {stock}")
            if p.description:
                lines.append(f"  {p.description}")
        return "\n".join(lines)

    def respond(self, buyer_message: str) -> tuple[str, dict[str, Any] | None]:
        """Process a buyer message and return seller's response.

        Returns:
            Tuple of (text_response, offer_dict_or_none).
            offer_dict is non-None when seller calls make_offer tool.
        """
        self._messages.append(LLMMessage(role="user", content=buyer_message))

        response: LLMResponse = self.llm.chat(
            messages=self._messages,
            tools=self.TOOLS,
        )

        # Handle tool calls (make_offer)
        offer: dict[str, Any] | None = None
        if response.has_tool_calls:
            for tc in response.tool_calls:
                if tc.tool_name == "make_offer":
                    offer = tc.arguments
                    self.state.final_offer_made = True
                    self.state.negotiation_complete = True
                    if "items" in offer:
                        self.state.offered_items = offer["items"]
                    if "total_minor" in offer:
                        self.state.offered_total_minor = offer["total_minor"]

        text = response.content or ""
        if offer and not text:
            text = f"Here's my final offer: {json.dumps(offer, indent=2)}"

        self._messages.append(LLMMessage(role="assistant", content=text))
        return text, offer

    def respond_scripted(
        self,
        text: str,
        offer: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any] | None]:
        """Bypass LLM and return a scripted response.

        WHY: Enables deterministic testing without fake LLM configuration.
        """
        if offer:
            self.state.final_offer_made = True
            self.state.negotiation_complete = True
            self.state.offered_items = offer.get("items", [])
            self.state.offered_total_minor = offer.get("total_minor", 0)
        return text, offer

    def create_offer_scripted(
        self,
        sku: str,
        quantity: int,
        unit_price_minor: int,
        currency: str = "USD",
        payee_email: str | None = None,
        payee_id: str | None = None,
        title: str = "",
    ) -> dict[str, Any]:
        """Convenience method to generate and record a scripted offer."""
        total_minor = quantity * unit_price_minor
        offer = {
            "sku": sku,
            "title": title or sku,
            "quantity": quantity,
            "unit_price_minor": unit_price_minor,
            "total_minor": total_minor,
            "currency": currency,
            "payee_email": payee_email or self.payee_email,
            "payee_id": payee_id or self.payee_id,
            "items": [
                {
                    "sku": sku,
                    "title": title or sku,
                    "qty": quantity,
                    "unit_price_minor": unit_price_minor,
                }
            ],
        }
        self.state.final_offer_made = True
        self.state.negotiation_complete = True
        self.state.offered_items = offer["items"]
        self.state.offered_total_minor = total_minor
        return offer
