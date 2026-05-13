"""Tests for hmm_lib.suggest — dry-run regime_mapping.json patch."""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "scripts"))

from hmm_lib import suggest
from hmm_lib.backtest import RegimeBacktest


def _sample_mapping(tmp_path):
    mapping = {
        "version": 2,
        "global": {
            "RANGING": {"strategy": "A_VWAP", "wr": 33.3, "pnl_per_trade": 0.93}
        },
        "per_asset": {
            "ETHUSDT": {
                "STRONG_TREND_DOWN": {"strategy": "E_RangeBounce", "wr": 25.9,
                                       "pnl_per_trade": 0.05}
            }
        }
    }
    path = tmp_path / "regime_mapping.json"
    path.write_text(json.dumps(mapping, indent=2))
    return path


def test_suggest_returns_diff_when_strategy_outperforms(tmp_path):
    mapping_path = _sample_mapping(tmp_path)
    backtests = [
        RegimeBacktest("GLOBAL", 4360, 1.0, 147, 51.7, 1.18, 8.3, 11.2, False),
        RegimeBacktest("CHOP", 2224, 0.51, 78, 61.5, 1.74, 12.8, 4.2, False),
    ]
    diff = suggest.suggest_mapping_patch(backtests, mapping_path, "ETHUSDT", "A_VWAP")
    assert "DRY-RUN" in diff
    assert "ETHUSDT" in diff
    assert "A_VWAP" in diff


def test_suggest_skips_low_trade_count_regimes(tmp_path):
    mapping_path = _sample_mapping(tmp_path)
    backtests = [
        RegimeBacktest("GLOBAL", 4360, 1.0, 147, 51.7, 1.18, 8.3, 11.2, False),
        RegimeBacktest("CHOP", 2224, 0.51, 5, 80.0, 5.0, 12.8, 4.2, True),  # low_trade
    ]
    diff = suggest.suggest_mapping_patch(backtests, mapping_path, "ETHUSDT", "A_VWAP")
    # CHOP should NOT be suggested because low_trade_count=True
    assert "CHOP" not in diff or "DRY-RUN" in diff
