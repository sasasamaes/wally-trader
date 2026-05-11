"""Shared pytest fixtures."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Make `app/` importable when running tests from project root or api/
API_ROOT = Path(__file__).parent.parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

# Set required env vars BEFORE any app imports — Pydantic Settings reads at
# import time. Use dummy values; tests that need a real DB skip if Postgres
# isn't available.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://wally:wally@localhost:5432/wally_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("MASTER_KEK", "dGVzdC1tYXN0ZXIta2VrLTMyLWJ5dGVzLWxvbmctcGFkZGluZ2c=")


@pytest.fixture
def master_kek_b64() -> str:
    """Fresh 32-byte base64 KEK for tests that don't need to be deterministic."""
    from app.security.encryption import generate_master_kek
    return generate_master_kek()
