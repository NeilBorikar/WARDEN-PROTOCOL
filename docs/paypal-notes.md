# PayPal Sandbox Notes

Verified findings from `scripts/spike_paypal.py` and official PayPal API documentation.

---

## 1. OAuth2 Authentication

- **Endpoint**: `POST https://api-m.sandbox.paypal.com/v1/oauth2/token`
- **Auth**: HTTP Basic Auth (`PAYPAL_CLIENT_ID:PAYPAL_CLIENT_SECRET`)
- **Headers**:
  - `Accept: application/json`
  - `Accept-Language: en_US`
  - `Content-Type: application/x-www-form-urlencoded`
- **Body**: `grant_type=client_credentials`
- **Response**:
  - `access_token`: Bearer token string
  - `token_type`: `Bearer`
  - `expires_in`: `32400` seconds (~9 hours)
- **Token Management**:
  - Sandbox tokens expire after 9 hours.
  - Implemented in `app.payments.token.PayPalTokenManager` with deterministic clock injection (`Clock` protocol).
  - Refresh triggered automatically 5 minutes (300s) before expiry.
  - Never log credentials or tokens (P2, P6).

---

## 2. Invoicing API (v2)

- **Create Draft Invoice**: `POST https://api-m.sandbox.paypal.com/v2/invoicing/invoices`
- **Read Invoice**: `GET https://api-m.sandbox.paypal.com/v2/invoicing/invoices/{invoice_id}`
- **Send Invoice**: `POST https://api-m.sandbox.paypal.com/v2/invoicing/invoices/{invoice_id}/send`
- **Record External Payment**: `POST https://api-m.sandbox.paypal.com/v2/invoicing/invoices/{invoice_id}/record-payment`
- **Key Parameters**:
  - `detail.invoice_number`: Unique invoice number per merchant
  - `detail.currency_code`: ISO 4217 code (e.g. `USD`)
  - `primary_recipients[].billing_info.email_address`: Recipient email
  - `items[].name`, `items[].quantity`, `items[].unit_amount`
- **Agent Usage**:
  - Ideal for Seller Agent requesting payment from Buyer Agent.
  - Read-only tools (viewing invoice) are Tier GREEN.
  - Creating/sending invoices are Tier YELLOW.
  - Cancelling or deleting invoices are Tier RED.

---

## 3. Payouts API (v1 Batch Payouts)

- **Create Batch Payout**: `POST https://api-m.sandbox.paypal.com/v1/payments/payouts`
- **Check Payout Status**: `GET https://api-m.sandbox.paypal.com/v1/payments/payouts/{payout_batch_id}`
- **Check Payout Item Status**: `GET https://api-m.sandbox.paypal.com/v1/payments/payouts-item/{payout_item_id}`
- **Idempotency**:
  - Sent via `PayPal-Request-Id` HTTP header.
  - `sender_batch_header.sender_batch_id` must also be unique.
- **Payload Structure**:
  ```json
  {
    "sender_batch_header": {
      "sender_batch_id": "<uuid>",
      "email_subject": "Errand Payment via Mandate Arena",
      "email_message": "Automated payment approved by Mandate policy."
    },
    "items": [
      {
        "recipient_type": "EMAIL",
        "amount": {
          "value": "20.00",
          "currency": "USD"
        },
        "receiver": "seller@example.com",
        "note": "Payment for Errand #123",
        "sender_item_id": "<uuid>"
      }
    ]
  }
  ```
- **Autonomous Execution**:
  - **Does NOT require a human/payer browser click at execution time.**
  - Sender account disburses funds directly to recipient email / PayPal ID.
  - Status is asynchronous: initial response is `201 Created` with batch status `PENDING`.
  - Batch transitions to `SUCCESS` or `DENIED` within seconds in sandbox.
- **Limits & Sandbox Requirements**:
  - Payouts feature must be active on the business account.
  - Minor units conversion: PayPal expects decimal string format (e.g. `2000` minor units -> `"20.00"`).

---

## 4. Orders API (v2 Checkout)

- **Create Order**: `POST https://api-m.sandbox.paypal.com/v2/checkout/orders`
- **Capture Order**: `POST https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture`
- **Findings on No-Human-Click**:
  - Attempting to capture an order immediately after creation yields `422 UNPROCESSABLE_ENTITY` with error `ORDER_NOT_APPROVED`.
  - PayPal Orders require payer authentication through the web redirect approval link (`rel="payer-action"` or `rel="approve"`).
  - Payer-less capture without a web session is only possible via Vault / Reference Transactions, which requires merchant underwriting not generally enabled in standard sandbox apps.
- **Agent Usage**:
  - Cannot serve as an autonomous payer-less agent payment rail.
  - Useful if human buyer clicks approval link, but fails the autonomous errand agent requirement.

---

## 5. Architectural Verdict

| API | Autonomous Execution? | Best Used For | Risk Tier |
|---|---|---|---|
| **Payouts API** (`/v1/payments/payouts`) | **Yes (Payer-less)** | **Primary Rail: Autonomous Errand Payments** | YELLOW |
| **Invoicing API** (`/v2/invoicing/invoices`) | Request-only (needs payment) | Seller Errand Invoicing & Record Keeping | YELLOW / RED |
| **Orders API** (`/v2/checkout/orders`) | No (requires payer click) | Human-interactive Checkout | YELLOW |
| **MockRail** (In-memory / SQLite) | Yes | Deterministic Tests, CI, Local Dev, Eval Harness | N/A |
