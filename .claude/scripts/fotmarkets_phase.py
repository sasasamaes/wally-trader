#!/usr/bin/env python3
"""Cross-platform port of fotmarkets_phase.sh.

Usage:
  python fotmarkets_phase.py [phase]    — current phase (1|2|3) — default
  python fotmarkets_phase.py capital    — current capital
  python fotmarkets_phase.py detail     — phase + capital + range
  python fotmarkets_phase.py check <N>  — phase for given capital N
"""
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROGRESS_FILE = SCRIPT_DIR.parent / "profiles" / "fotmarkets" / "memory" / "phase_progress.md"


def get_capital() -> float:
    if not PROGRESS_FILE.exists():
        print(f"ERROR: phase_progress.md no encontrado en {PROGRESS_FILE}", file=sys.stderr)
        sys.exit(1)
    text = PROGRESS_FILE.read_text()
    # Match `capital_current: <number>` (with optional comment after)
    match = re.search(r"capital_current\s*:\s*(-?\d+(?:\.\d+)?)", text)
    if not match:
        print("ERROR: campo capital_current no encontrado o no numérico", file=sys.stderr)
        sys.exit(1)
    return float(match.group(1))


def phase_for_capital(cap: float) -> int:
    if cap < 100:
        return 1
    elif cap < 300:
        return 2
    else:
        return 3


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "phase"

    if cmd in ("phase", ""):
        print(phase_for_capital(get_capital()))
        return 0
    elif cmd == "capital":
        cap = get_capital()
        print(int(cap) if cap.is_integer() else cap)
        return 0
    elif cmd == "detail":
        cap = get_capital()
        phase = phase_for_capital(cap)
        ranges = {
            1: f"phase=1 capital={cap} range=[0,100) next_threshold=100",
            2: f"phase=2 capital={cap} range=[100,300) next_threshold=300",
            3: f"phase=3 capital={cap} range=[300,∞) next_threshold=none",
        }
        print(ranges[phase])
        return 0
    elif cmd == "check":
        if len(argv) < 3:
            print("ERROR: uso: fotmarkets_phase.py check <capital>", file=sys.stderr)
            return 2
        try:
            test_cap = float(argv[2])
        except ValueError:
            print(f"ERROR: capital '{argv[2]}' no numérico", file=sys.stderr)
            return 2
        print(phase_for_capital(test_cap))
        return 0
    else:
        print("Uso: fotmarkets_phase.py [phase|capital|detail|check <N>]", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
