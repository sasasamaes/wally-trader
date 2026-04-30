"""Tests for profile.py canonical."""
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import profile as profile_mod


def test_get_no_profile_set(tmp_active_profile, capsys):
    """Empty flag file → exit 1, prints empty."""
    rc = profile_mod.cmd_get()
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out.strip() == ""


def test_set_and_get(tmp_active_profile, capsys):
    """Set then get returns the same name."""
    rc = profile_mod.cmd_set("retail")
    assert rc == 0
    capsys.readouterr()  # clear

    rc = profile_mod.cmd_get()
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out.strip() == "retail"


def test_set_invalid_profile(tmp_active_profile, capsys):
    """Setting non-existent profile fails with exit 3."""
    rc = profile_mod.cmd_set("nonexistent")
    captured = capsys.readouterr()
    assert rc == 3
    assert "not found" in captured.err


def test_set_empty_name(tmp_active_profile, capsys):
    """Empty name → exit 2."""
    rc = profile_mod.cmd_set("")
    captured = capsys.readouterr()
    assert rc == 2
    assert "required" in captured.err


def test_env_override_get(tmp_active_profile, monkeypatch, capsys):
    """WALLY_PROFILE env var overrides file."""
    monkeypatch.setenv("WALLY_PROFILE", "ftmo")
    rc = profile_mod.cmd_get()
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out.strip() == "ftmo"


def test_env_override_blocks_set(tmp_active_profile, monkeypatch, capsys):
    """When WALLY_PROFILE is set, 'set' is blocked with exit 4."""
    monkeypatch.setenv("WALLY_PROFILE", "retail")
    rc = profile_mod.cmd_set("ftmo")
    captured = capsys.readouterr()
    assert rc == 4
    assert "WALLY_PROFILE" in captured.err


def test_show_with_no_profile(tmp_active_profile, capsys):
    """Show without flag file → 'no profile set'."""
    rc = profile_mod.cmd_show()
    captured = capsys.readouterr()
    assert rc == 1
    assert "no profile" in captured.out


def test_show_with_profile(tmp_active_profile, capsys):
    """Show after set → 'name | timestamp'."""
    profile_mod.cmd_set("retail")
    capsys.readouterr()
    rc = profile_mod.cmd_show()
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out.strip().startswith("retail |")


def test_stale_no_flag(tmp_active_profile):
    """No flag file → stale (exit 0)."""
    assert profile_mod.cmd_stale() == 0


def test_stale_fresh_after_set(tmp_active_profile):
    """Just set → fresh (exit 1)."""
    profile_mod.cmd_set("retail")
    assert profile_mod.cmd_stale() == 1


def test_stale_env_override_is_fresh(tmp_active_profile, monkeypatch):
    """WALLY_PROFILE set → fresh by definition (exit 1)."""
    monkeypatch.setenv("WALLY_PROFILE", "retail")
    assert profile_mod.cmd_stale() == 1
