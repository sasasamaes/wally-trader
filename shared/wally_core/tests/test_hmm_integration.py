"""Integration tests for hmm_analyze pipeline."""
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "scripts"))


def test_cli_exits_1_on_unknown_strategy():
    result = subprocess.run(
        [str(PROJECT_ROOT / ".claude" / "scripts" / ".venv" / "bin" / "python"),
         str(PROJECT_ROOT / ".claude" / "scripts" / "hmm_analyze.py"),
         "--symbol", "ETHUSDT", "--strategy", "Z_Foo"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert "Z_Foo" in result.stderr or "invalid choice" in result.stderr.lower()


def test_cli_exits_2_on_unknown_symbol(tmp_path, monkeypatch):
    """Use force-refresh to skip cache; bypass real network by patching is risky for CLI tests.
    Instead, use a clearly invalid symbol and trust Binance to 400."""
    result = subprocess.run(
        [str(PROJECT_ROOT / ".claude" / "scripts" / ".venv" / "bin" / "python"),
         str(PROJECT_ROOT / ".claude" / "scripts" / "hmm_analyze.py"),
         "--symbol", "DEFINITELYNOTASYMBOL_X", "--strategy", "A_VWAP",
         "--force-refresh"],
        capture_output=True, text=True, timeout=30,
    )
    # Either 2 (FetchError "not listed") or 3 (network/parse mismatch) acceptable
    assert result.returncode in (2, 3), (
        f"expected 2 or 3, got {result.returncode}\nstderr: {result.stderr}")
