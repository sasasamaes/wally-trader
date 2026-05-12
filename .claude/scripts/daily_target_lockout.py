"""Daily target lockout — fuerza `/journal` cuando hit el target del día.

Lección 2026-05-11: el día arrancó +$48 (LDO win = target cumplido) y siguió
operando hasta -$55 net (-31% capital). El sistema NO tenía guardrail técnico
para forzar el cierre del día tras hit el target.

Este script:
1. Lee `signals_received.csv` del profile bitunix
2. Calcula PnL realizado HOY (sum de trades con outcome closed today)
3. Compara contra target del profile
4. Devuelve action: CONTINUE / WARN / LOCKOUT

Hooks (TODO próxima fase): preprompt_check.sh y/o /signal y /punk-hunt
chequean este lockout antes de procesar entries nuevas.

Usage:
    python3 .claude/scripts/daily_target_lockout.py
    python3 .claude/scripts/daily_target_lockout.py --profile bitunix --target 30
    python3 .claude/scripts/daily_target_lockout.py --json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

REPO_ROOT = Path(__file__).parent.parent.parent
PROFILES_DIR = REPO_ROOT / ".claude" / "profiles"

# Per-profile defaults (tuned by trading reality)
DEFAULT_TARGETS = {
    "bitunix": 30.0,         # post 2026-05-11 reduced from 50 to 30 (recovery)
    "retail": 5.0,
    "ftmo": 50.0,
    "fundingpips": 30.0,
    "fotmarkets": 3.0,
    "quantfury": 0.0001,     # BTC-denominated
}


@dataclass
class LockoutDecision:
    action: Literal["CONTINUE", "WARN", "LOCKOUT"]
    realized_pnl_today: float
    target_usd: float
    pct_of_target: float
    closed_trade_count: int
    open_trade_count: int
    reason: str
    profile: str


def _today_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _today_realized_pnl(csv_path: Path, today: str) -> tuple[float, int, int]:
    """Returns (sum_pnl_today, closed_count, open_count_today)."""
    if not csv_path.exists():
        return 0.0, 0, 0
    sum_pnl = 0.0
    closed = 0
    open_today = 0
    with csv_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("date") != today:
                continue
            outcome = (row.get("hypothetical_outcome") or "").strip()
            pnl_str = (row.get("pnl_usd") or "").strip()
            if outcome and pnl_str:
                try:
                    pnl = float(pnl_str)
                except ValueError:
                    continue
                sum_pnl += pnl
                closed += 1
            else:
                open_today += 1
    return sum_pnl, closed, open_today


def evaluate(profile: str, target_usd: float | None = None) -> LockoutDecision:
    """Run the lockout decision for a given profile."""
    csv_path = PROFILES_DIR / profile / "memory" / "signals_received.csv"
    target = target_usd if target_usd is not None else DEFAULT_TARGETS.get(profile, 30.0)
    today = _today_iso()
    pnl, closed, open_count = _today_realized_pnl(csv_path, today)
    pct = (pnl / target * 100) if target > 0 else 0.0

    if pnl >= target:
        action: Literal["CONTINUE", "WARN", "LOCKOUT"] = "LOCKOUT"
        reason = (
            f"Daily target ${target:.2f} hit (realized ${pnl:.2f}, "
            f"{pct:.1f}% of target). LOCKOUT: cerrá día con `/journal` o "
            f"--force-override si hay setup A-grade verificable. "
            f"Lección 2026-05-11: SAGA -$103 después de LDO +$48."
        )
    elif pnl >= target * 0.7:
        action = "WARN"
        reason = (
            f"Aproaching daily target (${pnl:.2f} = {pct:.1f}% of "
            f"${target:.2f}). Considerá HALF size próximo trade y "
            f"`/journal` early."
        )
    elif pnl <= -abs(target):
        action = "LOCKOUT"
        reason = (
            f"Daily LOSS exceeds target (${pnl:.2f} ≤ -${target:.2f}). "
            f"LOCKOUT: stop loss del día. NO revenge trades."
        )
    else:
        action = "CONTINUE"
        reason = (
            f"PnL ${pnl:.2f} dentro de banda ({pct:.1f}% target). "
            f"Operación normal."
        )

    return LockoutDecision(
        action=action,
        realized_pnl_today=round(pnl, 4),
        target_usd=target,
        pct_of_target=round(pct, 2),
        closed_trade_count=closed,
        open_trade_count=open_count,
        reason=reason,
        profile=profile,
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile", default=None, help="Profile slug (default: active)")
    p.add_argument("--target", type=float, default=None, help="Override default target USD")
    p.add_argument("--json", action="store_true", help="Output JSON")
    args = p.parse_args()

    profile = args.profile
    if profile is None:
        # Resolve active profile
        active_file = REPO_ROOT / ".claude" / "active_profile"
        if active_file.exists():
            profile = active_file.read_text().split("|")[0].strip()
        else:
            profile = "bitunix"

    decision = evaluate(profile, args.target)

    if args.json:
        print(json.dumps(asdict(decision), indent=2))
    else:
        emoji = {"CONTINUE": "🟢", "WARN": "🟡", "LOCKOUT": "🔴"}[decision.action]
        print(f"{emoji} [{decision.profile}] {decision.action}")
        print(f"   PnL hoy: ${decision.realized_pnl_today:+.2f} "
              f"({decision.pct_of_target:+.1f}% of target ${decision.target_usd:.2f})")
        print(f"   Trades cerrados hoy: {decision.closed_trade_count} | "
              f"abiertos: {decision.open_trade_count}")
        print(f"   {decision.reason}")

    # Exit codes for shell pipelines:
    # 0 = CONTINUE, 1 = WARN, 2 = LOCKOUT
    return {"CONTINUE": 0, "WARN": 1, "LOCKOUT": 2}[decision.action]


if __name__ == "__main__":
    sys.exit(main())
