"""Shared pytest fixtures for canonical script tests."""
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def tmp_active_profile(tmp_path, monkeypatch):
    """Isolated active_profile + profiles/ dir for profile.py tests."""
    fake_claude = tmp_path / ".claude"
    profiles_dir = fake_claude / "profiles"
    profiles_dir.mkdir(parents=True)
    for name in ("retail", "ftmo", "fotmarkets"):
        (profiles_dir / name).mkdir()

    flag_file = fake_claude / "active_profile"

    # Patch profile module's globals
    import profile as profile_mod
    monkeypatch.setattr(profile_mod, "FLAG_FILE", flag_file)
    monkeypatch.setattr(profile_mod, "PROFILES_DIR", profiles_dir)

    # Clear env override
    monkeypatch.delenv("WALLY_PROFILE", raising=False)

    return {"flag": flag_file, "profiles_dir": profiles_dir}


@pytest.fixture
def tmp_phase_progress(tmp_path, monkeypatch):
    """Isolated phase_progress.md for fotmarkets_phase.py tests."""
    fake = tmp_path / ".claude" / "profiles" / "fotmarkets" / "memory"
    fake.mkdir(parents=True)
    progress = fake / "phase_progress.md"

    import fotmarkets_phase as fp
    monkeypatch.setattr(fp, "PROGRESS_FILE", progress)
    return progress


@pytest.fixture
def tmp_fx_cache(monkeypatch, tmp_path):
    """Redirect tempfile.gettempdir to tmp_path for fx_rate tests."""
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    return tmp_path


@pytest.fixture
def tmp_chainlink_cache(monkeypatch, tmp_path):
    """Redirect tempfile.gettempdir for chainlink_price tests."""
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    return tmp_path
