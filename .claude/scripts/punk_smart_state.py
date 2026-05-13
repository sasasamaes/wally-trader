#!/usr/bin/env python3
"""punk_smart_state — file-backed state for /punk-smart v2.

Three state files inside the active profile's memory dir:
  asset_sl_streaks.json — per-asset SL count + blacklist_until
  sl_window.json        — recent SL events + kill_switch_active_until
  signals_received.csv  — read-only, used to derive open positions

Public API:
  record_sl(asset, ts, pnl_usd, memory_dir=None)
  record_tp(asset, ts, memory_dir=None)
  is_blacklisted(asset, now, memory_dir=None) -> bool
  is_kill_switch_active(now, memory_dir=None) -> (bool, str|None)
  open_positions(memory_dir=None) -> [{asset, side, bucket}]
  reset_killswitch(memory_dir=None)
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

CR_OFFSET = timezone(timedelta(hours=-6))


def _memory_dir(memory_dir: Path | None = None) -> Path:
    if memory_dir is not None:
        return Path(memory_dir)
    env = os.environ.get("WALLY_PROFILE_MEMORY_DIR")
    if env:
        return Path(env)
    profile = os.environ.get("WALLY_PROFILE", "bitunix")
    return Path(__file__).resolve().parents[1] / "profiles" / profile / "memory"


def _load(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return default


def _save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str))


def _next_cr_midnight(ts: datetime) -> datetime:
    cr_ts = ts.astimezone(CR_OFFSET)
    midnight = cr_ts.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return midnight


def _streaks_path(memory_dir: Path | None) -> Path:
    return _memory_dir(memory_dir) / "asset_sl_streaks.json"


def record_sl(asset: str, ts: datetime, pnl_usd: float,
              memory_dir: Path | None = None) -> None:
    """Record an SL on `asset`. After 2 SLs, asset is blacklisted until next CR 00:00.

    Behavior on 3rd+ SL: the blacklist_until is updated to the new SL's next
    CR midnight (effectively keeping the asset blacklisted as long as SLs continue).

    `pnl_usd` is persisted to sl_window.json for the kill-switch tracker.
    """
    p = _streaks_path(memory_dir)
    data = _load(p, {"version": 1, "as_of_cr_date": None, "assets": {}})
    cell = data["assets"].get(asset, {"sl_count": 0, "last_sl_ts": None,
                                       "blacklist_until": None})
    cell["sl_count"] = cell["sl_count"] + 1
    cell["last_sl_ts"] = ts.isoformat()
    if cell["sl_count"] >= 2:
        cell["blacklist_until"] = _next_cr_midnight(ts).isoformat()
    data["assets"][asset] = cell
    data["as_of_cr_date"] = ts.astimezone(CR_OFFSET).date().isoformat()
    _save(p, data)
    _record_sl_window(asset, ts, pnl_usd, memory_dir)


def record_tp(asset: str, ts: datetime, memory_dir: Path | None = None) -> None:
    p = _streaks_path(memory_dir)
    data = _load(p, {"version": 1, "as_of_cr_date": None, "assets": {}})
    if asset in data["assets"]:
        data["assets"][asset]["sl_count"] = 0
        data["assets"][asset]["blacklist_until"] = None
        data["as_of_cr_date"] = ts.astimezone(CR_OFFSET).date().isoformat()
        _save(p, data)


def is_blacklisted(asset: str, now: datetime,
                   memory_dir: Path | None = None) -> bool:
    p = _streaks_path(memory_dir)
    data = _load(p, {"assets": {}})
    cell = data.get("assets", {}).get(asset)
    if not cell or not cell.get("blacklist_until"):
        return False
    return now < datetime.fromisoformat(cell["blacklist_until"])


# ---------------------------------------------------------------------------
# Kill-switch: 2 SLs within any 4-hour rolling window → pause until CR 00:00
# ---------------------------------------------------------------------------

def _window_path(memory_dir: Path | None) -> Path:
    return _memory_dir(memory_dir) / "sl_window.json"


def _purge_old_events(events: list, now: datetime, hours: int = 4) -> list:
    cutoff = now - timedelta(hours=hours)
    return [ev for ev in events if datetime.fromisoformat(ev["ts"]) >= cutoff]


def _record_sl_window(asset: str, ts: datetime, pnl_usd: float,
                      memory_dir: Path | None = None) -> None:
    p = _window_path(memory_dir)
    data = _load(p, {"events": [], "kill_switch_active_until": None})
    data["events"].append({"ts": ts.isoformat(), "asset": asset, "pnl_usd": pnl_usd})
    data["events"] = _purge_old_events(data["events"], ts, hours=4)
    if len(data["events"]) >= 2:
        data["kill_switch_active_until"] = _next_cr_midnight(ts).isoformat()
    _save(p, data)


def is_kill_switch_active(now: datetime,
                          memory_dir: Path | None = None) -> tuple:
    """Return (active: bool, reason: str | None).

    The kill-switch is active when 2+ SLs occurred within a 4-hour rolling
    window. It persists until CR 00:00 of the day it was triggered.
    """
    p = _window_path(memory_dir)
    data = _load(p, {"events": [], "kill_switch_active_until": None})
    until = data.get("kill_switch_active_until")
    if not until:
        return False, None
    until_dt = datetime.fromisoformat(until)
    if now >= until_dt:
        return False, None
    return True, f"PAUSED: 2 SL kill-switch active until {until_dt.isoformat()}"


def reset_killswitch(memory_dir: Path | None = None) -> None:
    """Manually clear the kill-switch and purge the SL event window."""
    p = _window_path(memory_dir)
    data = _load(p, {"events": [], "kill_switch_active_until": None})
    data["kill_switch_active_until"] = None
    data["events"] = []
    _save(p, data)


# ---------------------------------------------------------------------------
# Open positions — derived from signals_received.csv
# ---------------------------------------------------------------------------

BUCKETS = {
    "btc_majors":  ["BTCUSDT", "ETHUSDT", "SOLUSDT", "MSTRUSDT"],
    "l1_alts":     ["AVAXUSDT", "INJUSDT", "ADAUSDT", "TRXUSDT", "LINKUSDT",
                    "SUIUSDT", "TONUSDT", "HBARUSDT"],
    "memes":       ["DOGEUSDT", "WIFUSDT", "FARTCOINUSDT", "PEPEUSDT"],
    "small_caps":  ["XLMUSDT", "ENJUSDT", "CHZUSDT", "AXSUSDT", "SEIUSDT",
                    "POLUSDT", "TIAUSDT", "ROSEUSDT", "RUNEUSDT"],
}


def bucket_of(asset: str) -> str | None:
    norm = asset.replace(".P", "").upper()
    for name, members in BUCKETS.items():
        if norm in members:
            return name
    return None


def open_positions(memory_dir: Path | None = None) -> list[dict]:
    p = _memory_dir(memory_dir) / "signals_received.csv"
    if not p.exists():
        return []
    with p.open() as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        if r.get("exit_price"):
            continue
        # Skip signals that never executed (REJECT verdicts or executed=no).
        # Without this filter a logged-but-rejected signal looks "open" and
        # falsely consumes a concurrent slot.
        decision = (r.get("decision") or "").strip().upper()
        if decision.startswith("REJECT"):
            continue
        executed = (r.get("executed") or "").strip().lower()
        if executed == "no":
            continue
        sym = r.get("symbol", "").replace(".P", "").upper()
        if not sym:
            continue
        out.append({
            "asset": sym,
            "side": r.get("side", "").upper(),
            "bucket": bucket_of(sym),
        })
    return out
