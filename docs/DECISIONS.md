# Decision Log

Each entry: date, decision, one-line reasoning.

| Date       | Decision | Reasoning |
|------------|----------|-----------|
| 2026-10-27 | Use `uv` for Python package management | Faster than pip, deterministic lockfile, recommended for modern Python projects. |
| 2026-10-27 | SQLite as default DB, switchable via DATABASE_URL | Simplest for MVP and local dev; Postgres swap is a one-line env change per spec. |
| 2026-10-27 | Ed25519 via PyNaCl for mandate/intent signing | Spec requires PyNaCl; Ed25519 is fast, safe, and has no footgun parameters. |
| 2026-10-27 | Primary rail: PayPal Payouts API + MockRail | Payouts enables payer-less autonomous execution without browser clicks; MockRail ensures offline CI and determinism. |

