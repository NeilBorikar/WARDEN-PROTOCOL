# Warden Protocol — Formal Threat Model & STRIDE Analysis

> **Principle P7:** *"Honest evidence. Never claim unbreakable; state residual risks in the threat model."*

This document defines the formal threat model, adversary assumptions, attack vectors, STRIDE security analysis, and residual risks for Warden Protocol.

---

## 1. Adversary Capabilities & Threat Actors

We evaluate the system against three distinct adversary tiers:

1. **Adversary A: Malicious External Supplier (Evil Seller)**
   - Controls all text sent to the Buyer agent in chat.
   - Crafts invoice PDFs, item memos, and catalog descriptions.
   - Goal: Trick the Buyer into sending funds to an unlisted PayPal account or paying an inflated price.

2. **Adversary B: Fully Compromised Buyer Agent (Worst-Case)**
   - The Buyer LLM has succumbed to direct prompt injection or jailbreaking.
   - The agent blindly crafts adversarial `PaymentRequest` payloads per attacker instructions.
   - Goal: Exfiltrate arbitrary funds from the owner's PayPal balance.

3. **Adversary C: Network / Man-in-the-Middle (MitM)**
   - Intercepts or tampers with HTTP communication between agents and Bouncer.
   - Replays old payment requests.

---

## 2. STRIDE Threat Analysis & Mitigations

| Category | Potential Attack Vector | Warden Protocol Defense Mechanism |
| :--- | :--- | :--- |
| **Spoofing** | Adversary attempts to forge an owner Mandate or Intent. | **Ed25519 Cryptographic Signatures:** Every Mandate and Intent requires a valid Ed25519 signature from the owner. Unsigned or corrupted documents fail Check C1 (`BLOCK MANDATE_INVALID`). |
| **Tampering** | Adversary alters invoice amount or payee in transit. | **Deal Lock (Check C6) & Payee Validation (Check C3):** The Bouncer compares the payment request against both the signed Intent and agreed Deal hash. Any mismatch triggers `BLOCK`. |
| **Repudiation** | An owner claims an autonomous transaction was unauthorized. | **Cryptographic Audit Log:** Every request, decision reason, and rail execution ID is chained into an immutable SHA-256 hash chain with nanosecond timestamps. |
| **Information Disclosure** | Adversary attempts to extract PayPal client credentials via LLM prompt leaking. | **Credential Isolation (Principle P2):** Agents have zero access to PayPal OAuth credentials. Only the Payment Gateway adapter holds secrets. |
| **Denial of Service** | Adversary spams high-frequency payment requests to exhaust funds or quota. | **Velocity Controls (Check C5):** Hard limit on payments per hour (`max_payments_per_hour`) and 24-hour rolling cap (`daily_cap_minor`). |
| **Elevation of Privilege** | Adversary attempts to invoke destructive refund/dispute tools via agent chat. | **Tool Risk Tiering (Check C2):** Destructive operations (accept dispute, issue refund) are classified RED tier, requiring explicit owner escalation (`ASK_OWNER`) or outright `BLOCK`. |

---

## 3. Defense Against Evaluated Attack Categories

| Attack Category | Threat Mechanism | Bouncer Enforcement Defense |
| :--- | :--- | :--- |
| **Bank Detail Swap** | Attacker claims PayPal account was updated. | **Check C3:** Compares payee against signed allowlist. Unlisted payees are blocked or escalated per `new_payee_policy`. |
| **Prompt Injection** | `[OVERRIDE]` text in seller message commands agent to pay attacker. | **Principle P1 & P3:** AI proposes, deterministic code decides. Untrusted external text carries `UNTRUSTED_EXTERNAL` provenance and cannot alter caps or payees. |
| **Fake Urgency / Authority** | Attacker impersonates CEO demanding immediate remittance. | **Check C4 & C8:** Standing caps and approved purposes cannot be relaxed by chat. Transactions exceeding threshold require owner approval. |
| **Salami Slicing** | Rapid series of micro-payments under the per-payment cap. | **Check C5:** 24-hour rolling cap aggregates all payments across the window; velocity limiter caps requests per hour. |
| **Inflated Invoice** | Merchant inflates unit price beyond market agreement. | **Check C6:** Compares each item unit price against the owner's signed `IntentItem.max_unit_price_minor`. |
| **Poisoned Catalogue** | Executable injection inside invoice memos (`{{...}}`). | **XSS Escaping & Static Schemas:** Memos are validated as pure text; UI sanitizes all rendered payload text. |

---

## 4. Honest Residual Risks & Attack Surface

No security architecture is immune to all vectors. We document four honest residual risks:

1. **Owner Private Key Exfiltration:**
   - *Risk:* If the owner's Ed25519 private key is compromised on the owner's workstation, an adversary can sign fraudulent Mandates.
   - *Mitigation:* Hardware security module (HSM) or enclave storage for owner keys.

2. **Colluding Allowlisted Merchant:**
   - *Risk:* If a legitimate allowlisted vendor (e.g. `office@supplies.test`) turns rogue, they can charge up to the daily cap until the owner revokes the mandate.
   - *Residual Exposure:* Loss is strictly bounded by `daily_cap_minor` (e.g. $500.00).

3. **Careless Human Approval on Escalation (`ASK_OWNER`):**
   - *Risk:* If an owner receives an `ASK_OWNER` push notification and blindly clicks "Approve" without reading the escalation reasons, an attack may succeed.
   - *Mitigation:* Clear plain-English reasons displayed in high-contrast modal; hard caps re-checked at execution even after approval.

4. **PayPal Sandbox Token Expiry:**
   - *Risk:* Sandbox OAuth tokens expire after 9 hours.
   - *Mitigation:* Handled via automatic token refresh in `app/payments/token.py`.
