## 1. PRODUCT IN PLAIN WORDS
An owner signs a Mandate (standing spending rules) and an Intent (this specific errand). A Buyer AI agent negotiates with a Seller AI agent and then asks the Bouncer to pay. The Bouncer is deterministic code that sits between the agents and PayPal. The agent never holds PayPal credentials. The Bouncer checks every request against the Mandate, Intent and agreed Deal, and returns ALLOW, ASK_OWNER or BLOCK. Everything is written to a tamper-evident audit log. An Attacker bot, a public arena and an evaluation harness measure how well it holds up.
Headline claim, which tests must prove: even if the AI is fully compromised, money cannot leave outside the Mandate, so worst-case loss is capped at the daily cap.

## 2. NON-NEGOTIABLE PRINCIPLES
P1. AI proposes, deterministic code decides. The packages mandate/, policy/ and audit/ must never import LLM or agent code. Enforce with an automated import-boundary test.
P2. Agents never see PayPal credentials. Only the payment adapter holds them.
P3. Untrusted text can never change money-critical fields. Payee and amount come only from owner-signed documents or verified records, or are validated against them. Every field carries provenance: OWNER | VERIFIED_RECORD | AGENT_DERIVED | UNTRUSTED_EXTERNAL.
P4. Fail closed. Errors, timeouts or missing data produce BLOCK or ASK_OWNER, never ALLOW.
P5. Most restrictive verdict wins: BLOCK > ASK_OWNER > ALLOW. The Second Opinion model may only escalate, never relax.
P6. Sandbox only. No real money, no real personal data, no secrets in git.
P7. Honest evidence. Metrics come from real runs. Never claim "unbreakable"; state residual risks in the threat model.
P8. Boring and legible. Typed, small modules, explicit errors, no cleverness.

## 3. ENGINEERING RULES
- Backend: Python 3.11+, FastAPI, Pydantic v2 (strict), SQLModel with SQLite (switchable to Postgres via DATABASE_URL), httpx, PyNaCl (Ed25519), pydantic-settings.
- Quality: pytest + hypothesis, ruff, mypy --strict on mandate/, policy/, audit/. GitHub Actions CI: lint, types, tests, secret scan (gitleaks).
- Money is integer minor units plus an ISO currency code. Never floats.
- Canonical JSON (sorted keys, no whitespace) before any hashing or signing.
- Every payment carries an idempotency key. Retries must be safe.
- Config via env. Commit .env.example, ignore .env. Redact secrets in logs.
- No TODO stubs counted as done. No swallowed exceptions. No file over about 400 lines. Docstrings explain WHY.
- Frontend: React + Vite + TypeScript + Tailwind. Escape ALL untrusted text rendered in the UI, because attack payloads are displayed to users and must be XSS-safe.

## 4. REPOSITORY LAYOUT
mandate-arena/
  AGENTS.md  README.md  LICENSE (MIT)  Makefile  docker-compose.yml  render.yaml  .env.example
  docs/  SPEC.md  ARCHITECTURE.md  THREAT_MODEL.md  RESULTS.md (generated)  DEMO_SCRIPT.md  DECISIONS.md  paypal-notes.md
  backend/app/
    config.py  main.py
    mandate/    models.py  signing.py        (Mandate, Intent, canonicalisation, Ed25519 verify)
    policy/     engine.py  checks.py  verdict.py  provenance.py   (pure: no I/O, no LLM)
    audit/      log.py  verify.py            (hash chain)
    payments/   rail.py (PaymentRail protocol)  paypal_payouts.py  paypal_orders.py  mock_rail.py  token.py
    tools/      registry.py (tool -> risk tier)
    llm/        client.py (OpenAI-compatible, per-role model config)  fake.py (scripted)  cassette.py (record/replay)
    agents/     buyer.py  seller.py  attacker.py  verifier.py  negotiation.py
    approvals/  service.py
    api/        runs, approvals, audit, results, arena routes
    eval/       corpus/ (YAML)  runner.py  metrics.py  report.py
  backend/tests/  unit/  property/  integration/  e2e/
  web/            (React app)
  scripts/        spike_paypal.py  seed_demo.py

## 5. DATA CONTRACTS
- Mandate (owner-signed standing rules): mandate_id, version, owner_id, agent_id, issued_at, expires_at, currency, per_payment_cap_minor, daily_cap_minor, max_payments_per_hour, approval_threshold_minor, allowed_payees[{payee_id, display_name, paypal_email}], allowed_purposes[], new_payee_policy (ASK_OWNER|BLOCK), red_tier_policy (ASK_OWNER|BLOCK), key_id, signature.
- Intent (owner-signed, per errand, references mandate_id): intent_id, description, max_total_minor, items[{sku, qty, max_unit_price_minor}], deadline, signature.
- Deal (created only when Buyer and Seller confirm identical terms): deal_id, intent_id, payee_id, items, total_minor, terms_hash.
- PaymentRequest: request_id, mandate_id, intent_id, deal_id, tool_name, payee{id, email}, amount_minor, currency, purpose, memo, provenance{field->tag}, idempotency_key, created_at.
- Decision: verdict, reasons[{code, check_id, message}], policy_version, mandate_hash, request_hash, evaluated_at.
- AuditEvent: seq, ts, type, payload, prev_hash, hash (hash = SHA-256 of prev_hash plus canonical event JSON).

## 6. THE BOUNCER
Evaluate ALL checks, collect all reasons, then combine by most-restrictive-wins. Every reason has a stable code and a plain-English message.
- C1 Signatures and expiry of Mandate and Intent valid and not revoked, else BLOCK MANDATE_INVALID.
- C2 Tool tier. GREEN (read-only: get/list/show tools): ALLOW. YELLOW (money-moving: create_order, pay_order, payouts, create_invoice, send_invoice): continue checks. RED (accept_dispute_claim, create_refund, record_refund_for_invoice, cancel_sent_invoice, delete_invoice, record_payment_for_invoice, cancel/update subscription): ASK_OWNER or BLOCK per mandate.red_tier_policy.
- C3 Payee must match an allow-listed payee by verified PayPal email or ID, never by a name in text. Unlisted payee gives NEW_PAYEE (per new_payee_policy). Payee differing from the Deal's payee gives BLOCK PAYEE_MISMATCH.
- C4 Amount above per_payment_cap gives BLOCK. Above approval_threshold gives ASK_OWNER.
- C5 Rolling 24-hour total including this request above daily_cap gives BLOCK. More than max_payments_per_hour gives BLOCK.
- C6 Deal lock: amount and currency must equal Deal total. Deal total must be at most Intent.max_total and unit prices within limits. Otherwise BLOCK DEAL_MISMATCH.
- C7 Provenance: a payee or amount from UNTRUSTED_EXTERNAL not validated against signed documents gives ASK_OWNER, or BLOCK if it conflicts with them.
- C8 Purpose must be in allowed_purposes.
Approvals: ASK_OWNER creates an ApprovalRequest bound to the hash of the exact PaymentRequest. It expires in 15 minutes, is single-use, and the owner cannot approve a BLOCK. After approval, hard caps are re-checked at execution.
Second Opinion (agents/verifier.py): runs after policy. Input is trusted material (owner's instruction, Intent, Deal summary, proposed payment) plus untrusted material in clearly delimited data blocks. Output is strict JSON {consistent, concerns[], suggested_verdict}. Timeout or parse failure gives ASK_OWNER. It can only escalate.

## 7. AGENTS, ATTACKER, EVALUATION
Agents use tool-calling through LLMClient with per-role model config from env (buyer, seller, attacker, verifier use separate settings so different vendors can be used). The Buyer's only money tool is request_payment, which goes to the Bouncer. Max 8 negotiation turns, per-call token caps, per-run budget. All Seller content is UNTRUSTED_EXTERNAL. The Buyer loads the Mandate fresh each task and never accepts rule changes from chat.
Attack categories (at least 8, at least 5 variants each, in YAML): memo injection; bank-detail swap (business email compromise); fake urgency or authority; salami slicing; inflated invoice; poisoned catalogue or tool output; dispute or refund trap; slow-burn multi-turn "policy update"; plus unicode, obfuscated and hidden-text variants.
Two test modes, both mandatory:
A. Worst-case: a "compromised agent" stub blindly submits the attack's adversarial PaymentRequests. This proves the guarantees independent of any LLM. Property tests (hypothesis): for any request sequence, the approved total in any 24-hour window is at most daily_cap; no ALLOW to a non-allow-listed payee; every ALLOW has amount equal to the Deal total; the verifier never relaxes a verdict; tampering with the audit chain is detected.
B. Realistic: live LLM Buyer vs Attacker with enforcement ON vs OFF. OFF is allowed only with MockRail or the sandbox, never in the public arena.
Legit corpus: at least 100 normal tasks (varied items, quantities, prices, suppliers), including some that SHOULD escalate (above threshold, new payee), so false-alarm and interruption rates are meaningful.
Metrics, overall and per category: break_in_rate, money_lost_minor, false_alarm_rate, owner_interruption_rate, p50 and p95 added latency (excluding human time), plus run metadata (git SHA, seed, models, date). `make eval` writes results/results.json and generates docs/RESULTS.md. Reproducible with a fixed seed and cassette replay.

## 8. UI AND ARENA
Design direction: calm, trustworthy security-console look. Not a generic template. One accent colour, strong typography, light and dark modes, responsive, accessible (keyboard navigation, contrast, ARIA; decisions shown as icon plus text chips, never colour alone), real loading, empty and error states.
Screens: (1) Live Run: negotiation transcript left, decision timeline with plain-English reasons right. (2) Approvals: mobile-friendly approve and deny. (3) Mandate and Intent: view, edit, sign. (4) Audit: searchable table with a "verify chain" button. (5) Results: tables and charts from results.json with a naive-vs-protected toggle.
Arena (public): each visitor gets a session-scoped sandbox wallet and a victim Buyer agent, and plays the evil seller (types messages, crafts invoice memos). Live decision feed. Leaderboard (attempts, blocks, "money stolen: $X"). Abuse controls: per-IP and per-session rate limits, input length caps, global model-spend circuit breaker, kill switch, session TTL and reset, no file execution, all output escaped.
Demo mode: record/replay cassettes so the video recording is deterministic and works offline.

## 9. PHASES (execute only the phase I name; stop at its exit criteria)
Phase 0, Foundations + PayPal spike: scaffold per section 4, MIT licence, Makefile (setup, test, lint, run, eval, demo), CI, .env.example, pre-commit. scripts/spike_paypal.py against the PayPal sandbox: (a) obtain a token, (b) create and read an invoice, (c) test whether a payer-less "send money to an email" path (Payouts) works with my sandbox business account, (d) test whether Orders create/approve/capture can run without a human click. Record exact endpoints, findings and limits in docs/paypal-notes.md and choose the primary rail in DECISIONS.md. Exit: make test and make lint green, spike documented, token auto-refresh implemented and tested with a fake clock (sandbox tokens expire after a few hours).
Phase 1, Core engine: mandate/intent models and signing, canonical JSON, policy engine with all checks, verdict combination, provenance, audit hash chain, approvals service. Unit and property tests, import-boundary test, at least 90% coverage on policy/, mandate/, audit/. Exit: a script demonstrates $20 ALLOW, $500 BLOCK, split payments BLOCK, payee swap blocked or escalated, tamper detected.
Phase 2, PayPal rail + tool registry: PaymentRail implementations (primary from the spike, plus MockRail), idempotency, safe retries, optional webhook receiver with signature verification, tool registry mapping every PayPal Agent Toolkit tool (invoices, orders, refunds, disputes, shipment tracking, catalog, subscriptions, reporting) to GREEN/YELLOW/RED. Sandbox integration tests (skipped without creds). Exit: money moves in the sandbox only via the Bouncer.
Phase 3, Agents: LLMClient (plus fake and cassette), Buyer, Seller, negotiation loop, Deal creation, request_payment to Bouncer to rail, Second Opinion, owner approvals via API. Exit: scripted happy path end to end in the sandbox, with transcripts in the audit log.
Phase 4, Attacker + evaluation: corpus, runner, metrics, both test modes, report generator. Exit: make eval produces RESULTS.md. Fix every hole found, add a regression test for each, and note it in docs/THREAT_MODEL.md.
Phase 5, Web UI + Arena: exit per section 8, verified in the browser with screenshots saved to docs/img/.
Phase 6, Ship: Dockerfile, render.yaml, deployment notes, README (quickstart of at most 5 commands, mermaid architecture diagram, "AI tools used" listing each model and its role, PayPal products used, honest limitations), ARCHITECTURE, THREAT_MODEL, DEMO_SCRIPT, secret scan, fresh-clone test. Exit: a fresh clone runs.
Cut list if time is short, in this order: voice features, disputes and shipment demos, leaderboard polish, webhooks. Never cut: Bouncer, signed Mandate and Intent, happy path, attack demo, results table, README, licence.

## 10. REPORT FORMAT (end of every phase)
(1) What was built. (2) How to run it. (3) Evidence: test, lint and type-check output, screenshots. (4) What is verified versus assumed. (5) Deviations and DECISIONS entries. (6) Risks and blockers. (7) Proposed plan for the next phase.

## 11. DEFINITION OF DONE
Fresh clone to happy path in at most 5 commands (MockRail by default; PayPal sandbox with credentials). All tests, lint, types and CI green. No secrets in git history. RESULTS.md generated from a real run. Both test modes pass and the worst-case guarantee is demonstrated by property tests. All UI screens exist and are browser-verified. README and docs complete and honest.

## 12. DECISIONS THAT NEED ME
Only: PayPal sandbox client ID and secret (I will put them in .env myself; never ask me to paste secrets into chat), AI provider base URL, model names and keys (also in .env), and the payment rail choice if the spike is inconclusive.
