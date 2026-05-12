#!/usr/bin/env python3
"""min_rr_gate.py — Dynamic minimum-R:R gate based on rolling WR.

Formula: min_rr = ((1 - wr) / wr) * 1.2
- wr is clamped to [0.20, 0.80] to avoid pathological outputs.
- sample_size < 10 trades → fallback min_rr = 1.5 with INSUFFICIENT_DATA flag.

Usage:
    python3 min_rr_gate.py --wr 0.55 --setup-rr 1.5 --sample-size 30
    python3 min_rr_gate.py --profile retail --setup-rr 1.5

Exit codes: 0=OK 2=WARN 3=missing args.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

WR_CLAMP_MIN = 0.20
WR_CLAMP_MAX = 0.80
RR_BUFFER = 1.2
MIN_SAMPLE = 10
FALLBACK_MIN_RR = 1.5

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent.parent  # scripts/ → .claude/ → repo root


def compute_min_rr(*, wr: float) -> float:
    """Dynamic min-R:R from WR. WR is decimal (0-1)."""
    wr_clamped = max(WR_CLAMP_MIN, min(WR_CLAMP_MAX, wr))
    return round((1.0 - wr_clamped) / wr_clamped * RR_BUFFER, 4)


def evaluate(*, wr: float, setup_rr: float, sample_size: int) -> dict:
    flags: list[str] = []
    if sample_size < MIN_SAMPLE:
        min_rr = FALLBACK_MIN_RR
        flags.append("INSUFFICIENT_DATA")
    else:
        min_rr = compute_min_rr(wr=wr)

    status = "OK" if setup_rr >= min_rr else "WARN"
    return {
        "wr": round(wr, 4),
        "sample_size": sample_size,
        "min_rr": min_rr,
        "setup_rr": round(setup_rr, 4),
        "status": status,
        "flags": flags,
    }


def fetch_wr_for_profile(profile: str) -> tuple[float, int]:
    """Call journal_metrics.py on the profile log and return (wr_decimal, n_trades)."""
    log_path = REPO_ROOT / ".claude" / "profiles" / profile / "memory" / "trading_log.md"
    if not log_path.exists():
        return (0.0, 0)
    res = subprocess.run(
        [
            str(SCRIPTS_DIR / ".venv" / "bin" / "python"),
            str(SCRIPTS_DIR / "journal_metrics.py"),
            "--log",
            str(log_path),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        return (0.0, 0)
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError:
        return (0.0, 0)
    wr_pct = float(data.get("win_rate_pct", 0.0))
    n = int(data.get("trades_total", data.get("total_trades", data.get("n_trades", 0))))
    return (wr_pct / 100.0, n)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--wr", type=float, help="rolling WR (0.0-1.0)")
    p.add_argument("--sample-size", type=int, help="number of trades in WR window")
    p.add_argument("--profile", type=str, help="profile name (auto-loads WR from log)")
    p.add_argument("--setup-rr", type=float, required=True, help="proposed setup R:R")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if args.profile:
        wr, sample = fetch_wr_for_profile(args.profile)
    elif args.wr is not None and args.sample_size is not None:
        wr, sample = args.wr, args.sample_size
    else:
        print("ERROR: must pass --profile OR (--wr AND --sample-size)", file=sys.stderr)
        return 3

    out = evaluate(wr=wr, setup_rr=args.setup_rr, sample_size=sample)
    if args.json:
        print(json.dumps(out))
    else:
        print(f"WR={wr:.2%} (n={sample}) → min_rr={out['min_rr']:.2f}")
        print(f"setup_rr={args.setup_rr:.2f} → {out['status']}")
        if out["flags"]:
            print(f"flags: {', '.join(out['flags'])}")
    return 0 if out["status"] == "OK" else 2


if __name__ == "__main__":
    sys.exit(main())
