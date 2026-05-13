#!/usr/bin/env python3
"""autohunt_ab.py — A/B comparison: autohunt picks vs Discord-driven signals.

Reads both data sources and produces a head-to-head table:
  - autohunt_signals.csv / autohunt_paper_log.csv (autohunt origin)
  - signals_received.csv (community / manual origin)

For each origin: N, WR, PF, avg $, median $, total $, max win, max loss,
avg duration. Also computes overlap (same asset + same side within 1h window)
to flag confirmations.

Reasonable acceptance criteria for autohunt to "graduate":
  - autohunt-paper WR  >= 50%
  - autohunt-paper PF  >= 1.40
  - autohunt-paper avg >= $5
  - max consecutive losses <= 3

This script doesn't enforce — only reports. Operator decides on graduation.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


BITUNIX = (Path(__file__).resolve().parent.parent
           / "profiles" / "bitunix" / "memory")
CSV_COMMUNITY = BITUNIX / "signals_received.csv"
CSV_AUTOHUNT_LIVE = BITUNIX / "autohunt_signals.csv"
CSV_AUTOHUNT_PAPER = BITUNIX / "autohunt_paper_log.csv"
OVERLAP_WINDOW_MIN = 60


def _f(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _ts_community(row: dict) -> datetime | None:
    try:
        return datetime.fromisoformat(f"{row['date']}T{row['time']}:00-06:00")
    except (KeyError, ValueError):
        return None


def _ts_autohunt(row: dict) -> datetime | None:
    ts = row.get("tick_ts")
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def load_community() -> list[dict]:
    if not CSV_COMMUNITY.exists():
        return []
    with CSV_COMMUNITY.open() as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        if not r.get("exit_price"):
            continue
        # Skip cosmetic-closed rows
        reason = (r.get("exit_reason") or "").lower()
        pnl = _f(r.get("pnl_usd"))
        if pnl == 0 and reason.startswith("cleanup"):
            continue
        ts = _ts_community(r)
        if not ts:
            continue
        # Treat as community origin if executed
        decision = (r.get("decision") or "").upper()
        if "EXECUTED" in decision or "AUTOHUNT" not in decision:
            out.append({
                "ts": ts,
                "symbol": (r.get("symbol") or "").replace(".P", "").upper(),
                "side": (r.get("side") or "").upper(),
                "pnl": pnl,
                "exit_reason": reason,
                "origin": "community",
            })
    return out


def load_autohunt(path: Path, origin_tag: str) -> list[dict]:
    if not path.exists():
        return []
    with path.open() as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        if r.get("outcome", "").lower() == "pending":
            continue
        if not r.get("exit_price"):
            continue
        ts = _ts_autohunt(r)
        if not ts:
            continue
        out.append({
            "ts": ts,
            "symbol": (r.get("symbol") or "").replace(".P", "").upper(),
            "side": (r.get("side") or "").upper(),
            "pnl": _f(r.get("pnl_usd")),
            "exit_reason": (r.get("outcome") or "").lower(),
            "origin": origin_tag,
        })
    return out


def metrics(rows: list[dict]) -> dict:
    if not rows:
        return {"n": 0}
    pnls = [r["pnl"] for r in rows]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    total_w = sum(wins)
    total_l = abs(sum(losses)) if losses else 0
    # consecutive losses
    streak = max_streak = 0
    for p in pnls:
        if p < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "n": len(pnls),
        "wr": round(len(wins) / len(pnls) * 100, 1),
        "pf": round(total_w / total_l, 2) if total_l > 0 else (float("inf") if wins else 0),
        "avg": round(statistics.mean(pnls), 2),
        "median": round(statistics.median(pnls), 2),
        "total": round(sum(pnls), 2),
        "max_win": round(max(pnls), 2),
        "max_loss": round(min(pnls), 2),
        "max_loss_streak": max_streak,
    }


def find_overlaps(group_a: list[dict], group_b: list[dict],
                   window_min: int = OVERLAP_WINDOW_MIN) -> list[dict]:
    overlaps = []
    for a in group_a:
        for b in group_b:
            if a["symbol"] != b["symbol"]:
                continue
            if a["side"] != b["side"]:
                continue
            delta = abs((a["ts"] - b["ts"]).total_seconds()) / 60
            if delta <= window_min:
                overlaps.append({
                    "symbol": a["symbol"], "side": a["side"],
                    "delta_min": int(delta),
                    "a_origin": a["origin"], "a_pnl": a["pnl"],
                    "b_origin": b["origin"], "b_pnl": b["pnl"],
                })
    return overlaps


def acceptance_check(autohunt_paper_m: dict) -> dict:
    """Compare paper metrics against graduation criteria."""
    if autohunt_paper_m.get("n", 0) < 20:
        return {"ready": False, "reason": f"need 20+ picks, have {autohunt_paper_m.get('n', 0)}"}
    checks = {
        "wr_50": autohunt_paper_m["wr"] >= 50,
        "pf_140": autohunt_paper_m["pf"] >= 1.4,
        "avg_5": autohunt_paper_m["avg"] >= 5,
        "streak_3": autohunt_paper_m["max_loss_streak"] <= 3,
    }
    passed_count = sum(checks.values())
    return {
        "ready": all(checks.values()),
        "checks": checks,
        "passed": passed_count,
        "total": len(checks),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    community = load_community()
    autohunt_live = load_autohunt(CSV_AUTOHUNT_LIVE, "autohunt")
    autohunt_paper = load_autohunt(CSV_AUTOHUNT_PAPER, "autohunt-paper")

    m_community = metrics(community)
    m_live = metrics(autohunt_live)
    m_paper = metrics(autohunt_paper)

    overlaps = find_overlaps(autohunt_paper + autohunt_live, community)
    acceptance = acceptance_check(m_paper)

    report = {
        "community":      m_community,
        "autohunt":       m_live,
        "autohunt_paper": m_paper,
        "overlaps_count": len(overlaps),
        "overlaps_sample": overlaps[:5],
        "acceptance":     acceptance,
    }

    if args.json:
        print(json.dumps(report, indent=2, default=str))
        return 0

    print(f"\n{'='*72}\nAUTOHUNT A/B vs Community\n{'='*72}\n")
    print(f"{'Origin':22s} {'N':>4s} {'WR':>6s} {'PF':>7s} {'Avg$':>8s} "
          f"{'Total$':>10s} {'Streak':>8s}")
    print("-" * 72)
    for label, m in [("community", m_community), ("autohunt-paper", m_paper),
                      ("autohunt (live)", m_live)]:
        if m.get("n", 0) == 0:
            print(f"{label:22s} {'—':>4s} {'—':>6s} {'—':>7s} {'—':>8s} "
                  f"{'—':>10s} {'—':>8s}  (no data yet)")
            continue
        pf = "inf" if m["pf"] == float("inf") else f"{m['pf']:.2f}"
        print(f"{label:22s} {m['n']:>4d} {m['wr']:>5.1f}% {pf:>7s} "
              f"${m['avg']:>+7.2f} ${m['total']:>+9.2f} {m['max_loss_streak']:>8d}")

    print(f"\n{'─'*72}\nOverlaps (same asset+side within {OVERLAP_WINDOW_MIN}min):")
    if not overlaps:
        print("  none yet (autohunt hasn't produced picks that match community signals)")
    else:
        for o in overlaps[:5]:
            print(f"  {o['symbol']:14s} {o['side']:5s}  Δ{o['delta_min']:>3d}min  "
                  f"{o['a_origin']}({o['a_pnl']:+.2f}) vs {o['b_origin']}({o['b_pnl']:+.2f})")

    print(f"\n{'─'*72}\nAcceptance criteria for autohunt-paper graduation:")
    if not acceptance["ready"]:
        if "reason" in acceptance:
            print(f"  NOT READY — {acceptance['reason']}")
        else:
            print(f"  NOT READY — {acceptance['passed']}/{acceptance['total']} checks passed")
            for k, v in acceptance.get("checks", {}).items():
                mark = "✓" if v else "✗"
                print(f"    {mark} {k}")
    else:
        print("  READY ✓ — all 4 criteria met. Operator can graduate /punk-autohunt to live.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
