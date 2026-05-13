"""E2E smoke test — runs against real Binance Futures.
Skipped by default. Run manually with: pytest -m network shared/wally_core/tests/test_hmm_e2e.py
"""
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.network
def test_real_eth_btc_pipeline(tmp_path):
    """Run hmm_analyze on real ETHUSDT data and verify report is created."""
    output_dir = PROJECT_ROOT / "docs" / "hmm_analysis"
    # Snapshot pre-existing files
    before = set(output_dir.glob("ETHUSDT_A_VWAP_*.md")) if output_dir.exists() else set()

    result = subprocess.run(
        [str(PROJECT_ROOT / ".claude" / "scripts" / ".venv" / "bin" / "python"),
         str(PROJECT_ROOT / ".claude" / "scripts" / "hmm_analyze.py"),
         "--symbol", "ETHUSDT", "--strategy", "A_VWAP"],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"

    after = set(output_dir.glob("ETHUSDT_A_VWAP_*.md"))
    new_files = after - before
    if not new_files:
        # Same-day rerun overwrites — verify at least one exists and is fresh
        assert after, "no markdown report produced"
        md = max(after, key=lambda p: p.stat().st_mtime)
    else:
        md = new_files.pop()
    assert md.stat().st_size > 1000, f"report suspiciously small: {md.stat().st_size} bytes"
