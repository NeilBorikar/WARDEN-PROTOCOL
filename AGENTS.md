# Mandate Arena – Agent Instructions

Read docs/SPEC.md and docs/DECISIONS.md before any task.

## NON-NEGOTIABLE PRINCIPLES
P1. AI proposes, deterministic code decides. The packages mandate/, policy/ and audit/ must never import LLM or agent code. Enforce with an automated import-boundary test.
P2. Agents never see PayPal credentials. Only the payment adapter holds them.
P3. Untrusted text can never change money-critical fields. Payee and amount come only from owner-signed documents or verified records, or are validated against them. Every field carries provenance: OWNER | VERIFIED_RECORD | AGENT_DERIVED | UNTRUSTED_EXTERNAL.
P4. Fail closed. Errors, timeouts or missing data produce BLOCK or ASK_OWNER, never ALLOW.
P5. Most restrictive verdict wins: BLOCK > ASK_OWNER > ALLOW. The Second Opinion model may only escalate, never relax.
P6. Sandbox only. No real money, no real personal data, no secrets in git.
P7. Honest evidence. Metrics come from real runs. Never claim "unbreakable"; state residual risks in the threat model.
P8. Boring and legible. Typed, small modules, explicit errors, no cleverness.

## ENGINEERING RULES
- Backend: Python 3.11+, FastAPI, Pydantic v2 (strict), SQLModel with SQLite (switchable to Postgres via DATABASE_URL), httpx, PyNaCl (Ed25519), pydantic-settings.
- Quality: pytest + hypothesis, ruff, mypy --strict on mandate/, policy/, audit/. GitHub Actions CI: lint, types, tests, secret scan (gitleaks).
- Money is integer minor units plus an ISO currency code. Never floats.
- Canonical JSON (sorted keys, no whitespace) before any hashing or signing.
- Every payment carries an idempotency key. Retries must be safe.
- Config via env. Commit .env.example, ignore .env. Redact secrets in logs.
- No TODO stubs counted as done. No swallowed exceptions. No file over about 400 lines. Docstrings explain WHY.
- Frontend: React + Vite + TypeScript + Tailwind. Escape ALL untrusted text rendered in the UI, because attack payloads are displayed to users and must be XSS-safe.
