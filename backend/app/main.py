"""Mandate Arena - FastAPI application entry point.

WHY: Thin entry point that wires together routers. Business logic
lives in domain packages, not here.
"""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(
    title="Mandate Arena",
    description="Safety layer for AI agent spending via PayPal",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check. No auth required."""
    return {"status": "ok"}
