"""Mandate, Intent, Deal, and PaymentRequest data models.

WHY:
- Section 5 & Engineering Rules: Strict typed models with Pydantic v2.
- Money is integer minor units plus an ISO currency code. Never floats (Section 3).
- Untrusted text can never change money-critical fields (P3).
- Canonical JSON is used for all hashing and signature verification.
- Packages mandate/, policy/, and audit/ must never import LLM or agent code (P1).
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.mandate.signing import (
    canonical_json_bytes,
    sign_canonical_payload,
    verify_canonical_payload,
)

PolicyAction = Literal["ASK_OWNER", "BLOCK"]


class AllowedPayee(BaseModel):
    """Allow-listed payee specified in owner-signed mandate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    payee_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    paypal_email: str = Field(min_length=3)


class Mandate(BaseModel):
    """Owner-signed standing spending rules."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mandate_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    owner_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    issued_at: datetime
    expires_at: datetime
    currency: str = Field(min_length=3, max_length=3)
    per_payment_cap_minor: int = Field(gt=0)
    daily_cap_minor: int = Field(gt=0)
    max_payments_per_hour: int = Field(gt=0)
    approval_threshold_minor: int = Field(gt=0)
    allowed_payees: list[AllowedPayee]
    allowed_purposes: list[str]
    new_payee_policy: PolicyAction
    red_tier_policy: PolicyAction
    key_id: str = Field(min_length=1)
    signature: str = Field(min_length=1)

    def to_canonical_dict(self) -> dict[str, Any]:
        """Convert mandate fields to serializable dict for canonical hashing."""
        return {
            "mandate_id": self.mandate_id,
            "version": self.version,
            "owner_id": self.owner_id,
            "agent_id": self.agent_id,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "currency": self.currency,
            "per_payment_cap_minor": self.per_payment_cap_minor,
            "daily_cap_minor": self.daily_cap_minor,
            "max_payments_per_hour": self.max_payments_per_hour,
            "approval_threshold_minor": self.approval_threshold_minor,
            "allowed_payees": [
                {
                    "payee_id": p.payee_id,
                    "display_name": p.display_name,
                    "paypal_email": p.paypal_email,
                }
                for p in self.allowed_payees
            ],
            "allowed_purposes": sorted(self.allowed_purposes),
            "new_payee_policy": self.new_payee_policy,
            "red_tier_policy": self.red_tier_policy,
            "key_id": self.key_id,
        }

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of canonical representation."""
        canonical = canonical_json_bytes(self.to_canonical_dict())
        return hashlib.sha256(canonical).hexdigest()

    def is_expired(self, at: datetime) -> bool:
        """Check if mandate is expired at given datetime."""
        return at >= self.expires_at

    def verify_signature(self, public_key_hex: str) -> bool:
        """Verify Ed25519 signature against owner public key."""
        return verify_canonical_payload(
            self.to_canonical_dict(),
            self.signature,
            public_key_hex,
        )

    @classmethod
    def create_and_sign(
        cls,
        *,
        mandate_id: str,
        version: int,
        owner_id: str,
        agent_id: str,
        issued_at: datetime,
        expires_at: datetime,
        currency: str,
        per_payment_cap_minor: int,
        daily_cap_minor: int,
        max_payments_per_hour: int,
        approval_threshold_minor: int,
        allowed_payees: list[AllowedPayee],
        allowed_purposes: list[str],
        new_payee_policy: PolicyAction,
        red_tier_policy: PolicyAction,
        key_id: str,
        private_key_hex: str,
    ) -> Mandate:
        """Construct a validated Mandate and compute its Ed25519 signature."""
        temp = cls(
            mandate_id=mandate_id,
            version=version,
            owner_id=owner_id,
            agent_id=agent_id,
            issued_at=issued_at,
            expires_at=expires_at,
            currency=currency,
            per_payment_cap_minor=per_payment_cap_minor,
            daily_cap_minor=daily_cap_minor,
            max_payments_per_hour=max_payments_per_hour,
            approval_threshold_minor=approval_threshold_minor,
            allowed_payees=allowed_payees,
            allowed_purposes=allowed_purposes,
            new_payee_policy=new_payee_policy,
            red_tier_policy=red_tier_policy,
            key_id=key_id,
            signature="placeholder",
        )
        sig = sign_canonical_payload(temp.to_canonical_dict(), private_key_hex)
        return temp.model_copy(update={"signature": sig})


class IntentItem(BaseModel):
    """Item specification in owner-signed intent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sku: str = Field(min_length=1)
    qty: int = Field(gt=0)
    max_unit_price_minor: int = Field(ge=0)


class Intent(BaseModel):
    """Owner-signed specific errand instructions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    intent_id: str = Field(min_length=1)
    mandate_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    max_total_minor: int = Field(gt=0)
    items: list[IntentItem]
    deadline: datetime
    signature: str = Field(min_length=1)

    def to_canonical_dict(self) -> dict[str, Any]:
        """Convert intent fields to serializable dict for canonical hashing."""
        return {
            "intent_id": self.intent_id,
            "mandate_id": self.mandate_id,
            "description": self.description,
            "max_total_minor": self.max_total_minor,
            "items": [
                {
                    "sku": item.sku,
                    "qty": item.qty,
                    "max_unit_price_minor": item.max_unit_price_minor,
                }
                for item in self.items
            ],
            "deadline": self.deadline.isoformat(),
        }

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of canonical representation."""
        canonical = canonical_json_bytes(self.to_canonical_dict())
        return hashlib.sha256(canonical).hexdigest()

    def is_expired(self, at: datetime) -> bool:
        """Check if intent deadline has passed."""
        return at >= self.deadline

    def verify_signature(self, public_key_hex: str) -> bool:
        """Verify Ed25519 signature against owner public key."""
        return verify_canonical_payload(
            self.to_canonical_dict(),
            self.signature,
            public_key_hex,
        )

    @classmethod
    def create_and_sign(
        cls,
        *,
        intent_id: str,
        mandate_id: str,
        description: str,
        max_total_minor: int,
        items: list[IntentItem],
        deadline: datetime,
        private_key_hex: str,
    ) -> Intent:
        """Construct a validated Intent and compute its Ed25519 signature."""
        temp = cls(
            intent_id=intent_id,
            mandate_id=mandate_id,
            description=description,
            max_total_minor=max_total_minor,
            items=items,
            deadline=deadline,
            signature="placeholder",
        )
        sig = sign_canonical_payload(temp.to_canonical_dict(), private_key_hex)
        return temp.model_copy(update={"signature": sig})


class DealItem(BaseModel):
    """Item agreed between buyer and seller."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sku: str = Field(min_length=1)
    qty: int = Field(gt=0)
    unit_price_minor: int = Field(ge=0)
    title: str = Field(min_length=1)


class Deal(BaseModel):
    """Agreed transaction terms between buyer and seller."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    deal_id: str = Field(min_length=1)
    intent_id: str = Field(min_length=1)
    payee_id: str = Field(min_length=1)
    payee_email: str = Field(min_length=3)
    items: list[DealItem]
    total_minor: int = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    terms_hash: str = Field(min_length=64, max_length=64)

    @classmethod
    def compute_terms_hash(
        cls,
        intent_id: str,
        payee_id: str,
        payee_email: str,
        items: list[DealItem],
        total_minor: int,
        currency: str,
    ) -> str:
        """Compute SHA-256 hash of canonical deal terms."""
        payload = {
            "intent_id": intent_id,
            "payee_id": payee_id,
            "payee_email": payee_email,
            "items": [
                {
                    "sku": item.sku,
                    "qty": item.qty,
                    "unit_price_minor": item.unit_price_minor,
                    "title": item.title,
                }
                for item in items
            ],
            "total_minor": total_minor,
            "currency": currency,
        }
        return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()

    def verify_terms_hash(self) -> bool:
        """Verify that stored terms_hash matches agreed terms."""
        expected = self.compute_terms_hash(
            intent_id=self.intent_id,
            payee_id=self.payee_id,
            payee_email=self.payee_email,
            items=self.items,
            total_minor=self.total_minor,
            currency=self.currency,
        )
        return self.terms_hash == expected


class PayeeInfo(BaseModel):
    """Payment recipient identity."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    email: str = Field(min_length=3)


class PaymentRequest(BaseModel):
    """Payment proposed by buyer agent for Bouncer evaluation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str = Field(min_length=1)
    mandate_id: str = Field(min_length=1)
    intent_id: str = Field(min_length=1)
    deal_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    payee: PayeeInfo
    amount_minor: int = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    purpose: str = Field(min_length=1)
    memo: str = ""
    provenance: dict[str, str] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=1)
    created_at: datetime

    def to_canonical_dict(self) -> dict[str, Any]:
        """Convert request to serializable dict for canonical hashing."""
        return {
            "request_id": self.request_id,
            "mandate_id": self.mandate_id,
            "intent_id": self.intent_id,
            "deal_id": self.deal_id,
            "tool_name": self.tool_name,
            "payee": {"id": self.payee.id, "email": self.payee.email},
            "amount_minor": self.amount_minor,
            "currency": self.currency,
            "purpose": self.purpose,
            "memo": self.memo,
            "provenance": self.provenance,
            "idempotency_key": self.idempotency_key,
            "created_at": self.created_at.isoformat(),
        }

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of canonical representation."""
        return hashlib.sha256(canonical_json_bytes(self.to_canonical_dict())).hexdigest()
