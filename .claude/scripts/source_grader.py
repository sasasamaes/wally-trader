#!/usr/bin/env python3
"""Grade signal sources by historical hit rate."""
import sys
import argparse
import csv
import json
import os
from collections import defaultdict
from pathlib import Path


def grade_source(source_id: str, profile: str, recent_n: int = 30) -> dict:
    """Compute grade A/B/C/F for a signal source based on recent N outcomes."""
    profiles_dir = Path(os.environ.get("WALLY_PROFILES_DIR", ".claude/profiles"))
    csv_path = profiles_dir / profile / "memory" / "signals_received.csv"

    if not csv_path.exists():
        return {"source": source_id, "grade": "N/A", "n": 0, "reason": "no_data"}

    matching = []
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            src = (row.get("source") or "").strip()
            if src == source_id:
                matching.append(row)

    matching = matching[-recent_n:]
    n = len(matching)

    if n < 5:
        return {"source": source_id, "grade": "N/A", "n": n, "reason": "insufficient_data"}

    wins = 0
    losses = 0
    for m in matching:
        outcome = (m.get("outcome") or "").upper()
        if outcome.startswith("TP"):
            wins += 1
        elif outcome == "SL":
            losses += 1

    closed = wins + losses
    if closed < 3:
        return {"source": source_id, "grade": "N/A", "n": n, "reason": "few_closed"}

    wr = wins / closed * 100

    if wr >= 60:
        grade = "A"
    elif wr >= 50:
        grade = "B"
    elif wr >= 40:
        grade = "C"
    else:
        grade = "F"

    return {
        "source": source_id,
        "grade": grade,
        "n_total": n,
        "n_closed": closed,
        "wr_pct": round(wr, 1),
        "wins": wins,
        "losses": losses,
    }


def grade_all_sources(profile: str, recent_n: int = 30) -> dict:
    """List all sources + their grades."""
    profiles_dir = Path(os.environ.get("WALLY_PROFILES_DIR", ".claude/profiles"))
    csv_path = profiles_dir / profile / "memory" / "signals_received.csv"

    if not csv_path.exists():
        return {"profile": profile, "sources": []}

    sources_seen = set()
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            src = (row.get("source") or "").strip()
            if src:
                sources_seen.add(src)

    grades = [grade_source(s, profile, recent_n) for s in sorted(sources_seen)]
    return {"profile": profile, "sources": grades}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--profile", default="bitunix")
    p.add_argument("--source", help="Specific source to grade")
    p.add_argument("--recent-n", type=int, default=30)
    p.add_argument("--all", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if args.all or not args.source:
        result = grade_all_sources(args.profile, args.recent_n)
    else:
        result = grade_source(args.source, args.profile, args.recent_n)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if "sources" in result:
            print(f"Source grades for {result['profile']}:")
            for s in result["sources"]:
                if s.get("grade") == "N/A":
                    print(f"  {s['source']:30s} N/A  (n={s['n']}, {s.get('reason', '')})")
                else:
                    print(f"  {s['source']:30s} {s['grade']}    WR={s['wr_pct']}%  ({s['wins']}/{s['n_closed']})")
        else:
            print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
