#!/usr/bin/env python3
"""challenge_readiness.py — Are you ready to buy another funded challenge?

Per Alex Ruiz V3 rule: wait until 3 consecutive positive months on your current
profile before paying for a new $99-$199 challenge.

Status:
- READY      : last 3 months all positive
- BORDERLINE : 1-2 positive in last 3 (or all flat)
- NOT_READY  : last month negative OR no track record

Usage:
    python3 challenge_readiness.py --profile retail
    python3 challenge_readiness.py --profile retail --json

Exit codes: 0=READY 2=BORDERLINE 1=NOT_READY.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent.parent  # scripts/ → .claude/ → repo root


def _previous_n_months(today: date, n: int) -> list[str]:
    """Return ['2026-02', '2026-03', '2026-04'] for today=2026-05-15, n=3."""
    out = []
    y, m = today.year, today.month
    for _ in range(n):
        m -= 1
        if m == 0:
            m = 12
            y -= 1
        out.append(f"{y:04d}-{m:02d}")
    return list(reversed(out))


def classify(monthly_pnl: dict[str, float], today: str | date) -> dict:
    """monthly_pnl is {"YYYY-MM": float_usd}. today is ISO date or date object."""
    if isinstance(today, str):
        today_d = datetime.strptime(today, "%Y-%m-%d").date()
    else:
        today_d = today

    flags: list[str] = []
    if not monthly_pnl:
        return {
            "status": "NOT_READY",
            "months_checked": [],
            "monthly_pnl_usd": {},
            "months_positive": 0,
            "flags": ["NO_DATA"],
        }

    last3 = _previous_n_months(today_d, 3)
    values = [monthly_pnl.get(m) for m in last3]
    positives = sum(1 for v in values if v is not None and v > 0)
    last_month = values[-1]

    if last_month is None or last_month <= 0:
        status = "NOT_READY"
    elif positives == 3:
        status = "READY"
    else:
        status = "BORDERLINE"

    if any(v is None for v in values):
        flags.append("PARTIAL_DATA")

    return {
        "status": status,
        "months_checked": last3,
        "monthly_pnl_usd": {m: monthly_pnl.get(m) for m in last3},
        "months_positive": positives,
        "flags": flags,
    }


def _parse_monthly_from_log(log_path: Path) -> dict[str, float]:
    """Sum PnL$ rows from a trading_log.md markdown table grouped by YYYY-MM."""
    if not log_path.exists():
        return {}
    text = log_path.read_text()
    monthly: dict[str, float] = {}
    row_re = re.compile(
        r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|.*?\|\s*([+\-]?\$?\d+\.?\d*)\s*\|",
        re.MULTILINE,
    )
    for match in row_re.finditer(text):
        date_str, pnl_str = match.group(1), match.group(2)
        pnl_clean = pnl_str.replace("$", "").replace("+", "")
        try:
            pnl = float(pnl_clean)
        except ValueError:
            continue
        ym = date_str[:7]
        monthly[ym] = monthly.get(ym, 0.0) + pnl
    return monthly


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--profile", required=True)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    log_path = REPO_ROOT / ".claude" / "profiles" / args.profile / "memory" / "trading_log.md"
    monthly = _parse_monthly_from_log(log_path)
    today = date.today().isoformat()
    out = classify(monthly, today=today)
    out["profile"] = args.profile

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"Profile: {args.profile}")
        print(f"Status:  {out['status']}")
        print(f"Months checked: {out['months_checked']}")
        for m, v in out["monthly_pnl_usd"].items():
            v_str = f"${v:+.2f}" if v is not None else "—"
            print(f"  {m}: {v_str}")
        if out["flags"]:
            print(f"flags: {', '.join(out['flags'])}")

    return 0 if out["status"] == "READY" else (2 if out["status"] == "BORDERLINE" else 1)


if __name__ == "__main__":
    sys.exit(main())
