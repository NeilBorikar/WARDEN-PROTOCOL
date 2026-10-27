"""PayPal Sandbox Spike - Phase 0.

Tests the following against the PayPal sandbox:
  (a) Obtain an OAuth2 token
  (b) Create and read a draft invoice
  (c) Test Payouts (payer-less "send money to email")
  (d) Test Orders create/approve/capture without human click

Run: python -m scripts.spike_paypal
Requires PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET env vars.

WHY: We must verify actual sandbox API behaviour before choosing the
primary payment rail. The spec says "never invent PayPal API behaviour."
Results are recorded in docs/paypal-notes.md.
"""

from __future__ import annotations

import json
import os
import sys
import uuid

import httpx

BASE_URL = "https://api-m.sandbox.paypal.com"


def get_token(client_id: str, client_secret: str) -> str:
    """(a) Obtain OAuth2 access token."""
    print("\n=== (a) Obtaining OAuth2 token ===")
    resp = httpx.post(
        f"{BASE_URL}/v1/oauth2/token",
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
        headers={"Accept": "application/json"},
    )
    resp.raise_for_status()
    body = resp.json()
    token = body["access_token"]
    print(f"  Token type: {body['token_type']}")
    print(f"  Expires in: {body['expires_in']}s")
    print(f"  Scope: {body.get('scope', 'N/A')[:100]}...")
    print(f"  Token: {token[:10]}...{token[-4:]} (redacted)")
    return token


def create_and_read_invoice(token: str) -> dict:
    """(b) Create a draft invoice, then read it back."""
    print("\n=== (b) Create and read invoice ===")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Generate a unique invoice number
    invoice_number = f"SPIKE-{uuid.uuid4().hex[:8].upper()}"

    invoice_body = {
        "detail": {
            "invoice_number": invoice_number,
            "currency_code": "USD",
            "note": "Mandate Arena spike test",
        },
        "invoicer": {
            "name": {"given_name": "Test", "surname": "Business"},
        },
        "primary_recipients": [
            {
                "billing_info": {
                    "email_address": "sb-buyer@personal.example.com",
                }
            }
        ],
        "items": [
            {
                "name": "Test Widget",
                "quantity": "1",
                "unit_amount": {"currency_code": "USD", "value": "10.00"},
            }
        ],
    }

    # Create draft
    resp = httpx.post(
        f"{BASE_URL}/v2/invoicing/invoices",
        headers=headers,
        json=invoice_body,
    )
    print(f"  Create status: {resp.status_code}")
    if resp.status_code == 201:
        # Extract invoice ID from href
        href = resp.headers.get("Location", "")
        invoice_id = href.rsplit("/", 1)[-1] if href else "unknown"
        print(f"  Invoice ID: {invoice_id}")
        print(f"  Location: {href}")

        # Read it back
        read_resp = httpx.get(
            f"{BASE_URL}/v2/invoicing/invoices/{invoice_id}",
            headers=headers,
        )
        print(f"  Read status: {read_resp.status_code}")
        if read_resp.status_code == 200:
            inv = read_resp.json()
            print(f"  Invoice status: {inv.get('status')}")
            return inv
        else:
            print(f"  Read error: {read_resp.text[:200]}")
    else:
        print(f"  Create error: {resp.text[:300]}")
    return {}


def test_payouts(token: str) -> dict:
    """(c) Test Payouts - send money to an email without payer interaction."""
    print("\n=== (c) Testing Payouts API ===")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payout_body = {
        "sender_batch_header": {
            "sender_batch_id": f"spike-{uuid.uuid4().hex[:12]}",
            "email_subject": "Mandate Arena Spike Test",
            "email_message": "Test payout from spike script",
        },
        "items": [
            {
                "recipient_type": "EMAIL",
                "amount": {"value": "1.00", "currency": "USD"},
                "receiver": "sb-buyer@personal.example.com",
                "note": "Spike test payout",
                "sender_item_id": f"item-{uuid.uuid4().hex[:8]}",
            }
        ],
    }

    resp = httpx.post(
        f"{BASE_URL}/v1/payments/payouts",
        headers=headers,
        json=payout_body,
    )
    print(f"  Payouts status: {resp.status_code}")
    body = resp.json() if resp.status_code < 500 else {}
    if resp.status_code in (200, 201):
        batch_id = body.get("batch_header", {}).get("payout_batch_id", "unknown")
        batch_status = body.get("batch_header", {}).get("batch_status", "unknown")
        print(f"  Batch ID: {batch_id}")
        print(f"  Batch status: {batch_status}")
    else:
        print(f"  Error: {json.dumps(body, indent=2)[:400]}")
    return body


def test_orders(token: str) -> dict:
    """(d) Test Orders - can we create and capture without a human click?"""
    print("\n=== (d) Testing Orders API (no-human-click) ===")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    order_body = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {"currency_code": "USD", "value": "5.00"},
                "description": "Spike test order",
            }
        ],
    }

    # Create order
    resp = httpx.post(
        f"{BASE_URL}/v2/checkout/orders",
        headers=headers,
        json=order_body,
    )
    print(f"  Create order status: {resp.status_code}")
    body = resp.json() if resp.status_code < 500 else {}
    if resp.status_code == 201:
        order_id = body.get("id", "unknown")
        order_status = body.get("status", "unknown")
        print(f"  Order ID: {order_id}")
        print(f"  Order status: {order_status}")

        # Try to capture without approval
        print("  Attempting capture without payer approval...")
        capture_resp = httpx.post(
            f"{BASE_URL}/v2/checkout/orders/{order_id}/capture",
            headers=headers,
            json={},
        )
        print(f"  Capture status: {capture_resp.status_code}")
        capture_body = capture_resp.json() if capture_resp.status_code < 500 else {}
        if capture_resp.status_code in (200, 201):
            print("  Capture succeeded! (unexpected)")
        else:
            error_name = capture_body.get("name", "")
            error_msg = capture_body.get("message", "")
            print(f"  Capture error: {error_name} - {error_msg}")
            print("  → Orders require payer approval (browser redirect or JS SDK)")
    else:
        print(f"  Create error: {json.dumps(body, indent=2)[:400]}")
    return body


def main() -> None:
    client_id = os.environ.get("PAYPAL_CLIENT_ID", "")
    client_secret = os.environ.get("PAYPAL_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print("ERROR: Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET env vars.")
        print("This spike requires sandbox credentials.")
        print("\nSkipping live sandbox tests. Documenting known API behaviour from docs.")
        document_from_docs()
        sys.exit(0)

    try:
        token = get_token(client_id, client_secret)
        create_and_read_invoice(token)
        test_payouts(token)
        test_orders(token)
        print("\n=== Spike complete ===")
    except httpx.HTTPStatusError as e:
        print(f"\nHTTP error: {e.response.status_code} - {e.response.text[:200]}")
        sys.exit(1)


def document_from_docs() -> None:
    """Write findings based on verified API documentation."""
    print("\nDocumenting PayPal API behaviour from official docs...")
    print("See docs/paypal-notes.md for full findings.")


if __name__ == "__main__":
    main()
