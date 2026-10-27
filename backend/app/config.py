"""Mandate Arena configuration.

WHY: All config comes from environment variables (P6, engineering rules).
Secrets are never logged or committed. This module is the single source
of truth for runtime configuration.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ─── PayPal Sandbox ───
    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    paypal_base_url: str = "https://api-m.sandbox.paypal.com"

    # ─── Database ───
    database_url: str = "sqlite:///./mandate_arena.db"

    # ─── App ───
    app_env: str = "development"
    log_level: str = "INFO"
    secret_key: str = "change-me-to-a-random-string"

    # ─── Arena ───
    arena_rate_limit_per_ip: int = 60
    arena_session_ttl_seconds: int = 1800
    arena_max_input_length: int = 2000
    arena_model_spend_limit_usd: float = 50.0
    arena_kill_switch: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def get_settings() -> Settings:
    """Factory for settings. Allows test overrides via dependency injection."""
    return Settings()
