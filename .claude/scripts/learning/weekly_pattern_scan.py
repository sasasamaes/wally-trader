#!/usr/bin/env python3
"""CLI for L2 — weekly pattern scan.

Usage:
  weekly_pattern_scan.py --profile bitunix [--days 90] [--min-n 5]
"""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared/wally_core/src"))

from wally_core.learning.pattern_miner import mine_patterns, pattern_to_recommendation


def main() -> None:
    parser = argparse.ArgumentParser(description="Weekly pattern scan (L2)")
    parser.add_argument("--profile", default="bitunix", help="Profile to scan")
    parser.add_argument("--days", type=int, default=90, help="Days lookback")
    parser.add_argument("--min-n", dest="min_n", type=int, default=5, help="Min trades per pattern")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    patterns = mine_patterns(args.profile, days=args.days, min_n=args.min_n)
    suggestions = pattern_to_recommendation(patterns)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if args.json:
        print(json.dumps(patterns, indent=2))
        return

    # Write to memory/learning/
    output_dir = Path(f".claude/profiles/{args.profile}/memory/learning")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"pattern_findings_{today}.md"

    lines = [
        f"# Pattern Findings — {today}",
        f"Profile: `{args.profile}` | Days: {args.days} | Min N: {args.min_n}",
        f"Total trades analyzed: {patterns['total_trades']} | Combos: {patterns['combos_analyzed']}",
        "",
        "## Top Winning Patterns",
    ]
    for p in patterns["winning"]:
        lines.append(
            f"- **{p['side']}** / {p['regime']} / {p['asset_type']} / "
            f"{p['hour_bucket']} {p['day_of_week']} — "
            f"WR {p['wr']:.0f}% / avg PnL ${p['avg_pnl']:.2f} (n={p['n']})"
        )

    lines += ["", "## Top Losing Patterns"]
    for p in patterns["losing"]:
        lines.append(
            f"- **{p['side']}** / {p['regime']} / {p['asset_type']} / "
            f"{p['hour_bucket']} {p['day_of_week']} — "
            f"WR {p['wr']:.0f}% / avg PnL ${p['avg_pnl']:.2f} (n={p['n']})"
        )

    lines += ["", "## Actionable Suggestions"]
    for s in suggestions:
        lines.append(f"- {s}")

    output_file.write_text("\n".join(lines))
    print(f"Pattern scan complete → {output_file}")
    print(f"Combos: {patterns['combos_analyzed']} | Winning: {len(patterns['winning'])} | Losing: {len(patterns['losing'])}")

    if suggestions:
        print("\nTop suggestions:")
        for s in suggestions[:5]:
            print(f"  {s}")


if __name__ == "__main__":
    main()
