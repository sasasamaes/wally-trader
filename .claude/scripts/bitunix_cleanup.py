#!/usr/bin/env python3
"""bitunix_cleanup.py — Detect & close phantom-open rows in signals_received.csv.

A "phantom-open" row is one that has no exit_price (looks open) but should
not be consuming a concurrent-trade slot. The detected categories:

  REJECT     decision starts with "REJECT" — signal was validated and rejected,
             never executed.
  NOT_EXEC   executed field == "no" — explicitly marked as not executed.
  STALE      no exit_price + entered >N days ago (default 7). Even if it really
             was executed, after a week the trade is closed in the exchange
             whether we logged it or not.

Default behaviour is --dry-run: list candidates, do nothing. Pass --apply to
cosmetic-close them (exit_price=entry, exit_reason=cleanup-{category},
pnl_usd=0, learning column gets a note).

Exit codes:
  0  success (may or may not have found rows)
  1  CSV not found / not bitunix profile
  2  unexpected error
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CR_OFFSET = timezone(timedelta(hours=-6))
STALE_DAYS_DEFAULT = 7


def csv_path() -> Path:
    return (Path(__file__).resolve().parent.parent
            / "profiles" / "bitunix" / "memory" / "signals_received.csv")


def classify(row: dict, stale_cutoff: datetime) -> str | None:
    """Return one of REJECT / NOT_EXEC / STALE / None."""
    if row.get("exit_price"):
        return None
    decision = (row.get("decision") or "").strip().upper()
    executed = (row.get("executed") or "").strip().lower()
    if decision.startswith("REJECT"):
        return "REJECT"
    if executed == "no":
        return "NOT_EXEC"
    # STALE — try to parse the date/time
    try:
        ts = datetime.fromisoformat(
            f"{row['date']}T{row['time']}:00-06:00"
        )
        if ts < stale_cutoff:
            return "STALE"
    except (KeyError, ValueError):
        pass
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true",
                    help="Actually close the rows (default is dry-run)")
    ap.add_argument("--days", type=int, default=STALE_DAYS_DEFAULT,
                    help=f"STALE threshold in days (default {STALE_DAYS_DEFAULT})")
    ap.add_argument("--category", choices=["REJECT", "NOT_EXEC", "STALE", "all"],
                    default="all",
                    help="Limit cleanup to one category (default: all)")
    args = ap.parse_args()

    if os.environ.get("WALLY_PROFILE", "bitunix") != "bitunix":
        print("bitunix_cleanup: only valid for WALLY_PROFILE=bitunix", file=sys.stderr)
        return 1

    path = csv_path()
    if not path.exists():
        print(f"bitunix_cleanup: CSV not found at {path}", file=sys.stderr)
        return 1

    now = datetime.now(CR_OFFSET)
    cutoff = now - timedelta(days=args.days)

    with path.open() as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    candidates: list[tuple[int, dict, str]] = []
    for i, r in enumerate(rows):
        cat = classify(r, cutoff)
        if cat is None:
            continue
        if args.category != "all" and cat != args.category:
            continue
        candidates.append((i, r, cat))

    if not candidates:
        print("bitunix_cleanup: 0 phantom-open rows found. Clean.")
        return 0

    print(f"bitunix_cleanup: {len(candidates)} phantom-open row(s)"
          + (" (DRY-RUN — pass --apply to close them)" if not args.apply else ""))
    for i, r, cat in candidates:
        print(f"  [{cat:8s}] row #{i}  {r.get('date','?')} {r.get('time','?')}  "
              f"{r.get('symbol','?'):14s} {r.get('side','?'):5s} "
              f"entry={r.get('entry','?')}  decision={(r.get('decision') or '')[:60]}")

    if not args.apply:
        return 0

    # Apply: cosmetic-close
    for i, r, cat in candidates:
        entry_price = r.get("entry", "0") or "0"
        r["exit_price"] = entry_price
        r["exit_reason"] = f"cleanup-{cat.lower()}"
        r["pnl_usd"] = "0"
        r["duration_h"] = ""
        existing_learning = r.get("learning") or ""
        note = f"[{now.strftime('%Y-%m-%d')} cleanup={cat}]"
        r["learning"] = (existing_learning + " " + note).strip()

    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"bitunix_cleanup: closed {len(candidates)} row(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
