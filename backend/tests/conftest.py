"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path
from dotenv import load_dotenv

env_file = Path(__file__).resolve().parents[1] / ".env"
if env_file.exists():
    load_dotenv(str(env_file))

