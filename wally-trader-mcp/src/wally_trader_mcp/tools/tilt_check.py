"""Tilt check MCP tool wrapper."""
from datetime import datetime, timezone
from wally_core.discipline import tilt_score, TradeRecord, cooldown_active


def tilt_check_tool(
    profile: str,
    recent_trades_json: str = "[]",
    cooldown_file: str = ".claude/cache/cooldowns.json",
) -> dict:
    """Compute tilt score from recent_trades JSON.

    recent_trades_json: JSON array of {timestamp_iso, symbol, side, pnl_usd, margin_usd, is_loss}
    """
    import json

    trades_data = json.loads(recent_trades_json) if isinstance(recent_trades_json, str) else recent_trades_json
    trades = [
        TradeRecord(
            timestamp=datetime.fromisoformat(t["timestamp_iso"].replace("Z", "+00:00")),
            symbol=t["symbol"],
            side=t["side"],
            pnl_usd=t["pnl_usd"],
            margin_usd=t.get("margin_usd", 0.0),
            is_loss=t["is_loss"],
        )
        for t in trades_data
    ]

    report = tilt_score(recent_trades=trades)
    cs = cooldown_active(profile=profile, cooldown_file=cooldown_file)

    return {
        "profile": profile,
        "score": report.score,
        "level": report.level.value,
        "flags": report.flags,
        "metrics": report.metrics,
        "cooldown_active": cs.active,
        "cooldown_minutes_remaining": cs.minutes_remaining,
        "cooldown_reason": cs.reason,
    }
