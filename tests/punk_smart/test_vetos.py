"""Tests for punk_smart_vetos."""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude" / "scripts"))

import punk_smart_vetos as vetos


class TestMacroVeto:
    def test_clear_when_no_event(self, monkeypatch):
        monkeypatch.setattr(vetos, "_macro_check",
                            lambda: {"blocked": False, "reason": None})
        result = vetos.veto_macro({"side": "LONG"})
        assert result.passed is True
        assert "clear" in result.reason.lower()

    def test_blocked_when_event_within_30min(self, monkeypatch):
        monkeypatch.setattr(vetos, "_macro_check",
                            lambda: {"blocked": True, "reason": "FOMC in 22 min"})
        result = vetos.veto_macro({"side": "LONG"})
        assert result.passed is False
        assert "FOMC" in result.reason
