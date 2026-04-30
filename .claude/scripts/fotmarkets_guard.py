#!/usr/bin/env python3
"""Cross-platform port of fotmarkets_guard.sh — Lite Guardian for fotmarkets profile.

Validations (executed in order):
  0. Active profile is fotmarkets
  1. CR time window 07:00-10:55
  2. Not weekend (Sat/Sun in Costa Rica)
  3. Phase detection succeeds
  4. trades_today < max_trades_per_phase
  5. NOT max_sl_consecutive consecutive SLs in last N trades

Output:
  PASS\n  → exit 0
  BLOCK: <reason>\n → exit 1
"""
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).resolve().parent
PROFILE_DIR = SCRIPT_DIR.parent / "profiles" / "fotmarkets"
LOG_FILE = PROFILE_DIR / "memory" / "trading_log.md"
CR_TZ = ZoneInfo("America/Costa_Rica")

PHASE_LIMITS = {
    1: {"max_trades": 1, "max_sl_consec": 1},
    2: {"max_trades": 2, "max_sl_consec": 2},
    3: {"max_trades": 3, "max_sl_consec": 2},
}


def fail(reason: str) -> int:
    print(f"BLOCK: {reason}")
    return 1


def passed() -> int:
    print("PASS")
    return 0


def get_active_profile() -> str:
    """Read active profile via profile.py canonical."""
    if os.environ.get("WALLY_PROFILE"):
        return os.environ["WALLY_PROFILE"].strip()
    flag = SCRIPT_DIR.parent / "active_profile"
    if flag.exists():
        return flag.read_text().strip().split("|", 1)[0].strip()
    return ""


def get_phase() -> int:
    """Run fotmarkets_phase.py to determine phase."""
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "fotmarkets_phase.py")],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())
        return int(result.stdout.strip())
    except Exception as e:
        raise RuntimeError(f"Phase detection failed: {e}")


def count_trades_today() -> int:
    """Count today's trades in trading_log.md (lines starting `| YYYY-MM-DD `)."""
    if not LOG_FILE.exists():
        return 0
    today = datetime.now(CR_TZ).strftime("%Y-%m-%d")
    pattern = re.compile(rf"^\| {re.escape(today)} ", re.MULTILINE)
    return len(pattern.findall(LOG_FILE.read_text()))


def get_last_n_results(n: int) -> list:
    """Get column 'Resultado' (column 9 zero-indexed in `|...|...|...|`) for last N today's trades."""
    if not LOG_FILE.exists():
        return []
    today = datetime.now(CR_TZ).strftime("%Y-%m-%d")
    pattern = re.compile(rf"^\| {re.escape(today)} ", re.MULTILINE)

    matching_lines = [
        line for line in LOG_FILE.read_text().splitlines()
        if pattern.match(line)
    ]
    if not matching_lines:
        return []

    last_n = matching_lines[-n:]
    results = []
    for line in last_n:
        # split by | — markdown table format
        cols = [c.strip() for c in line.split("|")]
        # Index 9 corresponds to bash $10 (leading | creates empty $1)
        if len(cols) > 9:
            results.append(cols[9].lower())
    return results


def main() -> int:
    # Check 0: profile = fotmarkets
    active = get_active_profile()
    if active != "fotmarkets":
        return fail(f"profile activo es '{active}' (no fotmarkets). Este guard solo aplica cuando fotmarkets está activo.")

    # Check 1: CR time window 07:00–10:55
    now_cr = datetime.now(CR_TZ)
    hhmm = now_cr.hour * 100 + now_cr.minute
    if hhmm < 700 or hhmm > 1055:
        return fail(f"Fuera de ventana operativa CR 07:00-10:55 (hora actual: {now_cr.hour:02d}:{now_cr.minute:02d})")

    # Check 2: Weekend
    if now_cr.weekday() >= 5:  # Mon=0, Sat=5, Sun=6
        return fail(f"Weekend: mercados Forex cerrados (día {now_cr.weekday() + 1})")

    # Check 3: Phase
    try:
        phase = get_phase()
    except RuntimeError as e:
        return fail(str(e))
    if phase not in PHASE_LIMITS:
        return fail(f"Fase desconocida: {phase}")

    max_trades = PHASE_LIMITS[phase]["max_trades"]
    max_sl_consec = PHASE_LIMITS[phase]["max_sl_consec"]

    # Check 4: Trades today
    trades_today = count_trades_today()
    if trades_today >= max_trades:
        return fail(f"Max trades/día alcanzado en Fase {phase}: {trades_today}/{max_trades}")

    # Check 5: Consecutive SLs
    if trades_today >= max_sl_consec:
        last_n = get_last_n_results(max_sl_consec)
        if last_n and all(r == "sl" for r in last_n):
            return fail(f"Stop día: {max_sl_consec} SL consecutivos en Fase {phase}")

    return passed()


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "check":
        print("Uso: fotmarkets_guard.py check", file=sys.stderr)
        sys.exit(2)
    sys.exit(main())
