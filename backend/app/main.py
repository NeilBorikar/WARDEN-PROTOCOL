"""Mandate Arena - FastAPI application entry point.

WHY: Thin entry point that wires together routers and middleware. Business logic
lives in domain packages, not here.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.approvals import router as approvals_router
from app.api.arena import router as arena_router
from app.api.audit import router as audit_router
from app.api.mandates import router as mandates_router
from app.api.results import router as results_router
from app.api.runs import router as runs_router

app = FastAPI(
    title="Warden Protocol",
    description="Deterministic safety layer for AI agent spending via PayPal",
    version="0.1.0",
)

# Enable CORS for React frontend (Vite default: http://localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(runs_router)
app.include_router(approvals_router)
app.include_router(audit_router)
app.include_router(mandates_router)
app.include_router(arena_router)
app.include_router(results_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check. No auth required."""
    return {"status": "ok"}


# Mount static frontend in production / Docker if dist exists
dist_dir = Path(__file__).resolve().parents[2] / "web" / "dist"
if dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="static")
