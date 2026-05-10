"""Discipline engine — tilt detection, cooldown, pre-trade checklist."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional


class TiltLevel(str, Enum):
    CALM = "CALM"          # 0-30
    ALERT = "ALERT"        # 31-50
    ELEVATED = "ELEVATED"  # 51-70
    HIGH = "HIGH"          # 71+ → block trades


@dataclass
class TiltReport:
    score: int  # 0-100
    level: TiltLevel
    flags: list[str]
    metrics: dict
    cooldown_until: Optional[str] = None  # ISO timestamp if cooldown active


@dataclass
class TradeRecord:
    """Slim trade representation for tilt analysis."""
    timestamp: datetime
    symbol: str
    side: str
    pnl_usd: float
    margin_usd: float
    is_loss: bool


def tilt_score(
    *,
    recent_trades: list[TradeRecord],
    baseline_avg_size: Optional[float] = None,
    now: Optional[datetime] = None,
) -> TiltReport:
    """Detect tilt from recent trade patterns.

    Score components (each 0-25):
    - overtrading: trade frequency 2x baseline → +20
    - revenge: trade opened within 30min of last close → +15
    - size_escalation: avg size 1.5x baseline → +20
    - loss_streak: 2+ losses in a row → +25
    - counter_trend: >30% trades counter-trend (would need flag) → not counted by default

    Returns TiltReport with score 0-100 and TiltLevel category.
    """
    now = now or datetime.now(timezone.utc)
    metrics: dict = {}
    flags: list[str] = []
    score = 0

    if not recent_trades:
        return TiltReport(
            score=0, level=TiltLevel.CALM, flags=[],
            metrics={"n_trades": 0},
        )

    # Sort by time
    sorted_trades = sorted(recent_trades, key=lambda t: t.timestamp)
    n = len(sorted_trades)
    metrics["n_trades_analyzed"] = n

    # 1. Overtrading: trades in last 4h vs baseline (1 trade/h max)
    last_4h = [t for t in sorted_trades if (now - t.timestamp) <= timedelta(hours=4)]
    metrics["trades_last_4h"] = len(last_4h)
    if len(last_4h) >= 5:
        score += 20
        flags.append(f"overtrading: {len(last_4h)} trades in last 4h (>4 = elevated)")

    # 2. Revenge trade: opened within 30min of last loss close
    revenge_count = 0
    for i in range(1, len(sorted_trades)):
        prev = sorted_trades[i - 1]
        curr = sorted_trades[i]
        if prev.is_loss and (curr.timestamp - prev.timestamp) <= timedelta(minutes=30):
            revenge_count += 1
    metrics["revenge_trades"] = revenge_count
    if revenge_count >= 1:
        score += 15
        flags.append(f"revenge_trading: {revenge_count} trade(s) opened <30min after a loss")

    # 3. Size escalation
    if baseline_avg_size and len(sorted_trades) >= 3:
        recent_avg = sum(t.margin_usd for t in sorted_trades[-3:]) / 3
        ratio = recent_avg / baseline_avg_size if baseline_avg_size > 0 else 1.0
        metrics["recent_avg_size"] = round(recent_avg, 2)
        metrics["baseline_avg_size"] = baseline_avg_size
        metrics["size_ratio"] = round(ratio, 2)
        if ratio >= 1.5:
            score += 20
            flags.append(
                f"size_escalation: recent avg ${recent_avg:.0f} vs baseline "
                f"${baseline_avg_size:.0f} ({ratio:.1f}x)"
            )

    # 4. Loss streak
    streak = 0
    for t in reversed(sorted_trades):
        if t.is_loss:
            streak += 1
        else:
            break
    metrics["loss_streak"] = streak
    if streak >= 3:
        score += 35  # extra weight for long streak
        flags.append(f"loss_streak: {streak} consecutive losses")
    elif streak >= 2:
        score += 25
        flags.append(f"loss_streak: {streak} consecutive losses")

    # Clamp
    score = min(100, score)

    # Categorize
    if score >= 71:
        level = TiltLevel.HIGH
    elif score >= 51:
        level = TiltLevel.ELEVATED
    elif score >= 31:
        level = TiltLevel.ALERT
    else:
        level = TiltLevel.CALM

    return TiltReport(score=score, level=level, flags=flags, metrics=metrics)


@dataclass
class ChecklistQuestion:
    key: str
    text: str
    is_blocker: bool = True  # if True, must answer YES to proceed


def pre_trade_checklist() -> list[ChecklistQuestion]:
    """Return the 6 pre-trade questions."""
    return [
        ChecklistQuestion(
            key="signal_validated",
            text="Did this signal pass /signal validation (>=60 score)?",
            is_blocker=True,
        ),
        ChecklistQuestion(
            key="regime_aligned",
            text="Is the trade direction aligned with the asset's current regime?",
            is_blocker=False,  # warn but allow override
        ),
        ChecklistQuestion(
            key="sl_tp_set",
            text="Will SL and TP be configured BEFORE confirming the trade?",
            is_blocker=True,
        ),
        ChecklistQuestion(
            key="size_ok",
            text="Is position size <= 2% capital at risk (within profile rules)?",
            is_blocker=True,
        ),
        ChecklistQuestion(
            key="not_revenge",
            text="Is this trade NOT motivated by a recent loss / FOMO?",
            is_blocker=True,
        ),
        ChecklistQuestion(
            key="macro_clear",
            text="Confirmed no high-impact macro event in next 30min?",
            is_blocker=False,
        ),
    ]


@dataclass
class CooldownState:
    active: bool
    until: Optional[str] = None  # ISO timestamp
    reason: Optional[str] = None
    minutes_remaining: int = 0


def cooldown_active(
    *,
    profile: str,
    cooldown_file: str,
    now: Optional[datetime] = None,
) -> CooldownState:
    """Check if profile is in forced cooldown.

    Reads from `cooldown_file` (JSON: {profile: {until_iso, reason}}).
    """
    import json
    from pathlib import Path

    now = now or datetime.now(timezone.utc)
    p = Path(cooldown_file)
    if not p.exists():
        return CooldownState(active=False)

    try:
        data = json.loads(p.read_text())
    except Exception:
        return CooldownState(active=False)

    entry = data.get(profile)
    if not entry:
        return CooldownState(active=False)

    until = entry.get("until")
    if not until:
        return CooldownState(active=False)

    until_dt = datetime.fromisoformat(until.replace("Z", "+00:00"))
    if now >= until_dt:
        return CooldownState(active=False)

    remaining = (until_dt - now).total_seconds() / 60
    return CooldownState(
        active=True,
        until=until,
        reason=entry.get("reason"),
        minutes_remaining=int(remaining),
    )


def trigger_cooldown(
    *,
    profile: str,
    minutes: int,
    reason: str,
    cooldown_file: str,
    now: Optional[datetime] = None,
) -> str:
    """Set cooldown for a profile. Returns ISO timestamp of expiration."""
    import json
    from pathlib import Path

    now = now or datetime.now(timezone.utc)
    until = now + timedelta(minutes=minutes)
    until_iso = until.isoformat()

    p = Path(cooldown_file)
    p.parent.mkdir(parents=True, exist_ok=True)

    data: dict = {}
    if p.exists():
        try:
            data = json.loads(p.read_text())
        except Exception:
            data = {}

    data[profile] = {"until": until_iso, "reason": reason, "set_at": now.isoformat()}
    p.write_text(json.dumps(data, indent=2))

    return until_iso


def discipline_scorecard(
    *,
    recent_trades: list[TradeRecord],
    cooldown_breaches: int = 0,
    checklist_overrides: int = 0,
) -> dict:
    """Compute discipline metrics over recent trades."""
    if not recent_trades:
        return {"score": 100, "n_trades": 0, "metrics": {}}

    n = len(recent_trades)
    losses = [t for t in recent_trades if t.is_loss]
    wins = [t for t in recent_trades if not t.is_loss]

    return {
        "n_trades": n,
        "wr": round(len(wins) / n * 100, 1) if n else 0,
        "n_losses": len(losses),
        "n_cooldown_breaches": cooldown_breaches,
        "n_checklist_overrides": checklist_overrides,
        "avg_pnl_usd": round(sum(t.pnl_usd for t in recent_trades) / n, 2),
        "score": max(0, 100 - cooldown_breaches * 20 - checklist_overrides * 10),
    }


# -----------------------------------------------------------------------------
# Win-streak detection — overconfidence prevention (added 2026-05-10)
# -----------------------------------------------------------------------------


@dataclass
class WinStreakAdvice:
    """Advice based on consecutive win count."""
    consecutive_wins: int
    advice: str  # NORMAL_SIZE | HALF_SIZE | SKIP_DAY
    reason: str
    size_multiplier: float  # 1.0 normal, 0.5 half, 0.0 skip


def win_streak_advice(recent_trades: list[TradeRecord]) -> WinStreakAdvice:
    """Detect win streaks and recommend size reduction to prevent overconfidence.

    Mirror of tilt detection but for the OPPOSITE bias — after multiple wins,
    traders often increase size, get sloppy, give back profits.

    Rules:
      - 0-2 wins streak: NORMAL_SIZE (no change)
      - 3-4 wins streak: HALF_SIZE (reduce 50%) — disciplinary brake
      - 5+ wins streak: SKIP_DAY (close session) — take the W, don't push luck

    Considers ONLY consecutive wins from most recent trade backwards. A loss
    or BE between wins resets the counter.
    """
    if not recent_trades:
        return WinStreakAdvice(0, "NORMAL_SIZE", "No recent trades", 1.0)

    # Sort by timestamp descending; count consecutive non-losses from most recent
    sorted_trades = sorted(recent_trades, key=lambda t: t.timestamp, reverse=True)
    streak = 0
    for t in sorted_trades:
        if t.is_loss:
            break
        # Only count actual wins (positive PnL), not BE
        if t.pnl_usd > 0:
            streak += 1
        else:
            break  # BE counts as streak-breaker too (no win)

    if streak >= 5:
        return WinStreakAdvice(
            streak,
            "SKIP_DAY",
            f"{streak} consecutive wins — overconfidence zone. Close session, "
            f"book the W, fresh mind tomorrow.",
            0.0,
        )
    if streak >= 3:
        return WinStreakAdvice(
            streak,
            "HALF_SIZE",
            f"{streak} consecutive wins — bias toward overconfidence. "
            f"Take next trade at HALF size as disciplinary brake.",
            0.5,
        )
    return WinStreakAdvice(streak, "NORMAL_SIZE", "Streak normal range", 1.0)
