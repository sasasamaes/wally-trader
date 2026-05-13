#!/usr/bin/env python3
"""autohunt_replay.py — Best-effort historical replay of /punk-autohunt scoring.

LIMITATIONS (read honestly):
  - The CSV `signals_received.csv` contains only the FINAL fields the operator
    logged (entry, sl, tp, outcome). It does NOT contain the analytics state
    at the time of the trade (multifactor score, liq magnet, OBV verdict, etc).
  - To truly replay, we'd need to re-fetch historical 15m bars at each trade's
    timestamp and recompute every analytic. That's possible but expensive.
  - This MVP version is the *cheap path*: it computes WR / PF / avg PnL on the
    existing logged outcomes, grouped by origin, and surfaces what the
    autohunt formula WOULD HAVE rejected based on logged R:R and tier signals
    (validation_score column when available).

Use this as a coarse sanity check, NOT as proof of edge. Real validation
requires accumulating ≥20 paper picks via /punk-autohunt --paper.

Output:
  - Per-origin breakdown (community / autohunt / autohunt-paper / manual)
  - WR, PF, avg $, median $, max win, max loss, profit factor
  - "Autohunt-counterfactual": rows that autohunt WOULD have rejected (R:R < 1
    or score < 60) — calculate the missed/avoided PnL.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path


CSV_DEFAULT = (Path(__file__).resolve().parent.parent
               / "profiles" / "bitunix" / "memory" / "signals_received.csv")


def _f(v: str, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _classify_origin(row: dict) -> str:
    decision = (row.get("decision") or "").upper()
    if "AUTOHUNT-PAPER" in decision or "AUTOHUNT_PAPER" in decision:
        return "autohunt-paper"
    if "AUTOHUNT" in decision:
        return "autohunt"
    if "EXECUTED" in decision:
        return "community"  # manually-executed signal from Discord
    return "other"


def metrics(rows: list[dict]) -> dict:
    """Compute WR / PF / avg / median / max from a list of closed rows.

    Skips cosmetic-zero rows (manual cleanup / pre-execution cancels) so they
    don't contaminate the WR.
    """
    pnls: list[float] = []
    for r in rows:
        if not r.get("exit_price"):
            continue
        p = _f(r.get("pnl_usd"))
        reason = (r.get("exit_reason") or "").lower()
        # Skip cosmetic closes (manual cleanup pre-execution cancels)
        if p == 0 and reason.startswith("cleanup"):
            continue
        pnls.append(p)
    if not pnls:
        return {"n": 0, "wr": 0, "pf": 0, "avg": 0, "median": 0,
                "max_win": 0, "max_loss": 0, "total_pnl": 0}
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    total_w = sum(wins)
    total_l = abs(sum(losses)) if losses else 0
    return {
        "n": len(pnls),
        "wr": round(len(wins) / len(pnls) * 100, 1),
        "pf": round(total_w / total_l, 2) if total_l > 0 else float("inf"),
        "avg": round(statistics.mean(pnls), 2),
        "median": round(statistics.median(pnls), 2),
        "max_win": round(max(pnls), 2) if pnls else 0,
        "max_loss": round(min(pnls), 2) if pnls else 0,
        "total_pnl": round(sum(pnls), 2),
    }


def counterfactual_filter(row: dict) -> dict:
    """For a row that was executed, would autohunt have approved it?

    Returns {"approved": bool, "reason": str}.
    """
    score = _f(row.get("multifactor"), default=None) or 0
    sl = _f(row.get("sl"))
    entry = _f(row.get("entry"))
    tp = _f(row.get("tp"))
    if entry == 0 or sl == 0 or tp == 0:
        return {"approved": False, "reason": "missing entry/sl/tp"}
    rr = abs(tp - entry) / abs(sl - entry) if entry != sl else 0
    if rr < 1.0:
        return {"approved": False, "reason": f"R:R {rr:.2f} < 1.0"}
    # validation_score column not in current schema; fall back to multifactor
    # Score < 60 → DROP per autohunt tier system
    if score and abs(score) < 60:
        return {"approved": False, "reason": f"|multifactor| {abs(score)} < 60 (autohunt DROP)"}
    return {"approved": True, "reason": "would pass autohunt gates"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", default=str(CSV_DEFAULT))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    path = Path(args.csv)
    if not path.exists():
        print(f"replay: CSV not found at {path}", file=sys.stderr)
        return 1

    with path.open() as f:
        rows = list(csv.DictReader(f))

    by_origin: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        origin = _classify_origin(r)
        by_origin[origin].append(r)

    # Counterfactual on community trades — would autohunt have taken them?
    community_closed = [r for r in by_origin.get("community", [])
                        if r.get("exit_price")]
    cf_approved = []
    cf_rejected = []
    for r in community_closed:
        verdict = counterfactual_filter(r)
        if verdict["approved"]:
            cf_approved.append((r, verdict))
        else:
            cf_rejected.append((r, verdict))

    cf_approved_pnl = sum(_f(r.get("pnl_usd")) for r, _ in cf_approved)
    cf_rejected_pnl = sum(_f(r.get("pnl_usd")) for r, _ in cf_rejected)

    report = {
        "csv_path": str(path),
        "total_rows": len(rows),
        "by_origin": {origin: metrics(rrows) for origin, rrows in by_origin.items()},
        "autohunt_counterfactual_on_community": {
            "would_approve": {
                "n": len(cf_approved),
                "sum_pnl_usd": round(cf_approved_pnl, 2),
            },
            "would_reject": {
                "n": len(cf_rejected),
                "sum_pnl_usd_avoided_or_missed": round(cf_rejected_pnl, 2),
                "examples": [
                    {"symbol": r.get("symbol"), "pnl": _f(r.get("pnl_usd")),
                     "reason": v["reason"]}
                    for r, v in cf_rejected[:5]
                ],
            },
        },
        "limitations": [
            "Counterfactual uses only logged R:R + |multifactor| — no live recompute.",
            "Real autohunt also evaluates 9 more components (liq_magnet, fib_zone, "
            "OBV, pump_score, on-chain, smart_money_ls, USDT.D, sentiment, session). "
            "Most aren't in the historical CSV.",
            "Treat as a sanity check, not a proof of edge. ≥20 paper picks needed.",
        ],
    }

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(f"\n{'='*72}\nAUTOHUNT REPLAY — coarse historical analysis")
    print(f"  CSV: {path}  ({len(rows)} rows)\n{'='*72}\n")
    print(f"{'Origin':20s} {'N':>4s} {'WR':>6s} {'PF':>7s} {'Avg$':>8s} {'Total$':>10s}")
    print("-" * 72)
    for origin, m in report["by_origin"].items():
        if m["n"] == 0:
            continue
        pf_str = "inf" if m["pf"] == float("inf") else f"{m['pf']:.2f}"
        print(f"{origin:20s} {m['n']:>4d} {m['wr']:>5.1f}% {pf_str:>7s} "
              f"${m['avg']:>+7.2f} ${m['total_pnl']:>+9.2f}")

    cf = report["autohunt_counterfactual_on_community"]
    print(f"\n{'─'*72}")
    print("Counterfactual: would autohunt have taken community signals?")
    print(f"  WOULD APPROVE: {cf['would_approve']['n']} signals, "
          f"sum PnL ${cf['would_approve']['sum_pnl_usd']:+.2f}")
    print(f"  WOULD REJECT:  {cf['would_reject']['n']} signals, "
          f"PnL avoided/missed ${cf['would_reject']['sum_pnl_usd_avoided_or_missed']:+.2f}")
    for ex in cf["would_reject"]["examples"]:
        sign = "+" if ex["pnl"] >= 0 else ""
        print(f"    - {ex['symbol']:14s} PnL {sign}${ex['pnl']:.2f}  → {ex['reason']}")

    print(f"\n{'─'*72}")
    print("Limitations:")
    for lim in report["limitations"]:
        print(f"  • {lim}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
