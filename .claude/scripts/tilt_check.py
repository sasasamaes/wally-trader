#!/usr/bin/env python3
"""Tilt detector CLI — reads bitunix_log or signals_received.csv, outputs tilt 0-100."""
import sys
import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

_SHARED = Path(__file__).resolve().parent.parent.parent / "shared/wally_core/src"
if _SHARED.exists() and str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from wally_core.discipline import tilt_score, TradeRecord, cooldown_active, trigger_cooldown


def load_recent_trades(profile: str, max_age_hours: int = 24) -> list[TradeRecord]:
    """Load recent trades from signals_received.csv (preferred) or bitunix_log.csv."""
    profiles_dir = Path(os.environ.get("WALLY_PROFILES_DIR", ".claude/profiles"))
    csv_path = profiles_dir / profile / "memory" / "signals_received.csv"

    if not csv_path.exists():
        return []

    trades = []
    cutoff = datetime.now(timezone.utc).timestamp() - max_age_hours * 3600

    try:
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Try to parse timestamp from various column names
                ts_str = row.get("ts") or row.get("timestamp") or row.get("date")
                if not ts_str:
                    continue
                try:
                    if "T" in ts_str:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    else:
                        # Date-only fallback (treat as midnight UTC)
                        ts = datetime.fromisoformat(ts_str + "T00:00:00+00:00")
                except Exception:
                    continue
                if ts.timestamp() < cutoff:
                    continue

                # Detect outcome
                outcome = (row.get("outcome") or "").upper()
                pnl_str = row.get("pnl_usd") or "0"
                try:
                    pnl = float(pnl_str) if pnl_str else 0.0
                except ValueError:
                    pnl = 0.0
                is_loss = outcome == "SL" or pnl < 0

                trades.append(TradeRecord(
                    timestamp=ts,
                    symbol=row.get("symbol", "?"),
                    side=row.get("side", "?"),
                    pnl_usd=pnl,
                    margin_usd=0.0,  # not always logged; TODO improve
                    is_loss=is_loss,
                ))
    except Exception as e:
        print(f"Warning: could not parse CSV: {e}", file=sys.stderr)

    return trades


def main():
    p = argparse.ArgumentParser(description="Tilt detector — reads signals CSV and scores discipline")
    p.add_argument("--profile", required=True)
    p.add_argument("--hours", type=int, default=24)
    p.add_argument("--cooldown-file", default=".claude/cache/cooldowns.json")
    p.add_argument("--check-cooldown-only", action="store_true")
    p.add_argument("--auto-cooldown", action="store_true",
                   help="Auto-trigger 60min cooldown if tilt level == HIGH")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    cs = cooldown_active(profile=args.profile, cooldown_file=args.cooldown_file)

    if args.check_cooldown_only:
        if args.json:
            print(json.dumps({
                "active": cs.active,
                "until": cs.until,
                "minutes_remaining": cs.minutes_remaining,
                "reason": cs.reason,
            }))
        else:
            if cs.active:
                print(f"Cooldown ACTIVE for {args.profile}: {cs.minutes_remaining} min remaining ({cs.reason})")
            else:
                print(f"No cooldown for {args.profile}")
        sys.exit(0 if not cs.active else 2)

    trades = load_recent_trades(args.profile, args.hours)
    report = tilt_score(recent_trades=trades)

    if args.auto_cooldown and report.level.value == "HIGH":
        until = trigger_cooldown(
            profile=args.profile, minutes=60,
            reason=f"auto_tilt_high_score_{report.score}",
            cooldown_file=args.cooldown_file,
        )
        print(f"Auto-cooldown 60min triggered: until {until}", file=sys.stderr)

    if args.json:
        out = {
            "profile": args.profile,
            "score": report.score,
            "level": report.level.value,
            "flags": report.flags,
            "metrics": report.metrics,
            "cooldown": {"active": cs.active, "until": cs.until, "reason": cs.reason},
        }
        print(json.dumps(out, indent=2))
    else:
        emoji = {"CALM": "OK", "ALERT": "WARN", "ELEVATED": "HIGH", "HIGH": "BLOCK"}[report.level.value]
        print(f"[{emoji}] Tilt: {report.score}/100 — {report.level.value}")
        for f in report.flags:
            print(f"  * {f}")
        if cs.active:
            print(f"Cooldown active: {cs.minutes_remaining} min remaining ({cs.reason})")


if __name__ == "__main__":
    main()
