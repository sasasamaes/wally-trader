"""Dry-run regime_mapping.json patch. NEVER writes files."""
import difflib
import json
from pathlib import Path

from hmm_lib.backtest import RegimeBacktest


def _format_mapping_for_diff(mapping: dict) -> list[str]:
    return json.dumps(mapping, indent=2, sort_keys=True).splitlines(keepends=True)


def suggest_mapping_patch(
    backtests: list[RegimeBacktest],
    current_mapping_path: Path,
    symbol: str,
    strategy_name: str,
) -> str:
    """Returns a string. DRY-RUN ONLY. Never writes to file.

    The string is either an explanation message (when nothing to suggest)
    or a unified diff prefixed by a 'DRY-RUN' warning.
    """
    if not current_mapping_path.exists():
        return f"DRY-RUN: regime_mapping.json not found at {current_mapping_path}; skipping."

    mapping = json.loads(current_mapping_path.read_text())
    # Pick the regime where this strategy performs BEST (excluding GLOBAL + low-trade)
    candidates = [
        r for r in backtests
        if r.regime_label != "GLOBAL" and not r.low_trade_count and r.trades >= 10
    ]
    if not candidates:
        return "DRY-RUN: no regimes with sufficient trades to suggest a mapping change."

    best = max(candidates, key=lambda r: r.pf)
    if best.pf <= 1.0:
        return f"DRY-RUN: best regime {best.regime_label} has PF={best.pf:.2f} <= 1.0; no improvement to suggest."

    proposed = json.loads(json.dumps(mapping))  # deep copy
    proposed.setdefault("per_asset", {}).setdefault(symbol, {})[best.regime_label] = {
        "strategy": strategy_name,
        "wr": best.wr,
        "pnl_per_trade": best.net_pnl_pct / best.trades if best.trades else 0.0,
        "n_trades": best.trades,
        "source": "hmm_diagnostic_2026-05-13",
    }

    original_lines = _format_mapping_for_diff(mapping)
    proposed_lines = _format_mapping_for_diff(proposed)
    diff = "".join(difflib.unified_diff(
        original_lines, proposed_lines,
        fromfile="regime_mapping.json (current)",
        tofile="regime_mapping.json (proposed)",
        lineterm="",
    ))
    return (f"DRY-RUN — review manually before applying.\n"
            f"Symbol {symbol}, strategy {strategy_name} performs best in HMM regime "
            f"{best.regime_label} (PF={best.pf:.2f}, WR={best.wr:.1f}%, n={best.trades}).\n\n"
            f"{diff}")
