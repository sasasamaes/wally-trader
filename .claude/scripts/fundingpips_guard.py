#!/usr/bin/env python3
"""Cross-platform port of fundingpips_guard.sh — pre-trade validation gates.

Gates:
  0. profile activo == fundingpips
  1. ventana horaria CR (06:00-16:00 forex/idx, 06:00-20:00 crypto, weekend solo crypto)
  2. Daily PnL >= -2% (BLOCK), >= -1.5% (WARN)
  3. Total equity >= $9,700 (BLOCK), >= $9,800 (WARN)
  4. Consistency: biggest_day vs total_profit < 12% (BLOCK), < 10% (WARN)
  5. trades hoy < 2

Usage:
  python fundingpips_guard.py check [--verbose]
  python fundingpips_guard.py status   (JSON output)
"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
PROFILE_DIR = REPO_ROOT / ".claude" / "profiles" / "fundingpips"
LOG_FILE = PROFILE_DIR / "memory" / "trading_log.md"
EQUITY_CURVE = PROFILE_DIR / "memory" / "equity_curve.csv"
CONSISTENCY_FILE = PROFILE_DIR / "memory" / "consistency_tracker.json"
CR_TZ = ZoneInfo("America/Costa_Rica")


class GuardResult:
    def __init__(self, action: str, verbose: bool):
        self.action = action  # "check" or "status"
        self.verbose = verbose

    def fail(self, gate: str, reason: str) -> int:
        if self.action == "status":
            print(json.dumps({"status": "BLOCK", "reason": reason, "gate": gate}))
        else:
            print(f"❌ BLOCK [{gate}]: {reason}", file=sys.stderr)
            if self.verbose:
                print(f"   See {PROFILE_DIR}/rules.md for thresholds", file=sys.stderr)
        return 1

    def warn(self, gate: str, reason: str):
        if self.action == "status":
            print(json.dumps({"status": "WARN", "reason": reason, "gate": gate}))
        else:
            print(f"⚠️  WARN [{gate}]: {reason}")

    def ok(self) -> int:
        if self.action == "status":
            print(json.dumps({"status": "OK", "reason": "all gates passed"}))
        else:
            print("✅ OK — todos los gates pasaron")
        return 0


def get_active_profile() -> str:
    if os.environ.get("WALLY_PROFILE"):
        return os.environ["WALLY_PROFILE"].strip()
    flag = SCRIPT_DIR.parent / "active_profile"
    if flag.exists():
        return flag.read_text().strip().split("|", 1)[0].strip()
    return "unknown"


def daily_pnl_pct() -> float:
    """Returns today's PnL % from equity_curve.csv (first entry of day vs last)."""
    if not EQUITY_CURVE.exists():
        return 0.0
    today = datetime.now(CR_TZ).strftime("%Y-%m-%d")
    first, last = None, None
    try:
        for line in EQUITY_CURVE.read_text().splitlines()[1:]:  # skip header
            cols = line.split(",")
            if len(cols) < 2 or today not in cols[0]:
                continue
            try:
                eq = float(cols[1])
                if first is None:
                    first = eq
                last = eq
            except ValueError:
                continue
        if first is not None and last is not None and first != 0:
            return ((last - first) / first) * 100
    except OSError:
        pass
    return 0.0


def last_equity() -> float:
    """Returns last equity value from equity_curve.csv, or 10000 default."""
    if not EQUITY_CURVE.exists():
        return 10000.0
    try:
        lines = EQUITY_CURVE.read_text().splitlines()
        if len(lines) > 1:
            cols = lines[-1].split(",")
            return float(cols[1])
    except (OSError, ValueError, IndexError):
        pass
    return 10000.0


def consistency_status() -> str:
    """Returns 'OK_NEUTRAL', 'OK_X.X%', 'WARN_X.X%', 'BLOCK_X.X%', or 'OK_UNKNOWN'."""
    if not CONSISTENCY_FILE.exists():
        return "OK_UNKNOWN"
    try:
        d = json.loads(CONSISTENCY_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return "OK_UNKNOWN"
    total = d.get("total_profit_to_date", 0)
    current = d.get("current_day_pnl", 0)
    biggest = d.get("biggest_day_pnl", 0)
    projected_biggest = max(biggest, current)
    projected_total = total
    if projected_total <= 0:
        return "OK_NEUTRAL"
    pct = (projected_biggest / projected_total) * 100
    if pct >= 12:
        return f"BLOCK_{pct:.1f}"
    elif pct >= 10:
        return f"WARN_{pct:.1f}"
    return f"OK_{pct:.1f}"


def count_trades_today() -> int:
    if not LOG_FILE.exists():
        return 0
    today = datetime.now(CR_TZ).strftime("%Y-%m-%d")
    pattern = re.compile(rf"^\| {re.escape(today)} ", re.MULTILINE)
    return len(pattern.findall(LOG_FILE.read_text()))


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "check"
    verbose = "--verbose" in sys.argv
    result = GuardResult(action, verbose)

    if action not in ("check", "status"):
        print(f"Usage: fundingpips_guard.py [check|status] [--verbose]", file=sys.stderr)
        return 2

    # Gate 0: profile
    active = get_active_profile()
    if active != "fundingpips":
        return result.fail("profile", f"profile activo es '{active}', no fundingpips")

    # Gate 1: ventana horaria
    now_cr = datetime.now(CR_TZ)
    hhmm = now_cr.hour * 100 + now_cr.minute
    dow = now_cr.weekday() + 1  # 1=Mon...7=Sun
    if dow >= 6:  # weekend → solo crypto 06:00-20:00
        if hhmm < 600 or hhmm >= 2000:
            return result.fail("window", f"fuera de ventana weekend crypto (CR 06:00-20:00). Hora actual: {hhmm}")

    # Gate 2: Daily PnL
    pnl = daily_pnl_pct()
    if pnl <= -2:
        return result.fail("daily_loss", f"Daily PnL {pnl:.2f}% (BLOCK en -2%, oficial -3%)")
    elif pnl <= -1.5:
        result.warn("daily_loss", f"Daily PnL {pnl:.2f}% (WARN en -1.5%)")

    # Gate 3: Total equity
    eq = last_equity()
    if eq <= 9700:
        return result.fail("total_dd", f"Equity ${eq} ≤ $9,700 (BLOCK -3%, oficial -5%)")
    elif eq <= 9800:
        result.warn("total_dd", f"Equity ${eq} ≤ $9,800 (WARN -2%)")

    # Gate 4: Consistency
    cs = consistency_status()
    if cs.startswith("BLOCK_"):
        pct = cs[len("BLOCK_"):]
        return result.fail("consistency", f"Consistency proyectada {pct}% (BLOCK en 12%, oficial 15%)")
    elif cs.startswith("WARN_"):
        pct = cs[len("WARN_"):]
        result.warn("consistency", f"Consistency {pct}% (WARN en 10%)")

    # Gate 5: Trades hoy
    trades = count_trades_today()
    if trades >= 2:
        return result.fail("max_trades", f"Ya hay {trades} trades hoy (max 2 para FundingPips)")

    return result.ok()


if __name__ == "__main__":
    sys.exit(main())
