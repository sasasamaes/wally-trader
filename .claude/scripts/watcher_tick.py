#!/usr/bin/env python3
"""Hourly watcher tick — called by launchd.

1. Load pending_orders from all profiles
2. Apply whitelist matrix → (active, suspended_policy)
3. Fetch prices for all unique (profile, asset) pairs
4. Evaluate invalidations (TTL/price/stopday/force_exit) — no MCP required
5. For pendings still alive:
     distance_pct = |price - entry| / entry * 100
     if <= 0.3% → spawn claude -p "/watch-deep <id>" headless
     else → compute next_recheck and just heartbeat
6. Write status.json + dashboard.md
7. notify_hub for each event

Exit codes: 0 ok, 1 partial (some asset prices missing), 2 fatal.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from pending_lib import (
    PROFILES,
    TERMINAL_STATUSES,
    load_all_pendings,
    load_pendings,
    save_pendings,
    update_status,
    apply_whitelist_matrix,
    evaluate_invalidation,
    stopday_triggered_profiles,
    _repo_root,
)
from price_feeds import price_for, PriceFeedError
from notify_hub import notify, Urgency


ESCALATE_DISTANCE_PCT = 0.3  # spawn Claude validation if within 0.3%


@dataclass
class TickResult:
    ok: bool
    pendings_checked: int = 0
    actions: list = field(default_factory=list)
    errors: list = field(default_factory=list)


def spawn_escalate(order_id: str) -> None:
    """Run watcher_escalate.sh in background. No blocking."""
    script = _repo_root() / ".claude" / "scripts" / "watcher_escalate.sh"
    if not script.exists():
        # degraded: just log — escalate script not yet installed
        return
    subprocess.Popen(
        ["/bin/bash", str(script), order_id],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _distance_pct(price: float, entry: float) -> float:
    if entry == 0:
        return float("inf")
    return abs(price - entry) / entry * 100


def _next_recheck_from_distance(dist_pct: float) -> str:
    """Heuristic: far price = longer next check."""
    now = datetime.now().astimezone()
    if dist_pct < 0.5:
        delta = timedelta(minutes=15)
    elif dist_pct < 2.0:
        delta = timedelta(hours=1)
    else:
        delta = timedelta(hours=2)
    return (now + delta).isoformat(timespec="seconds")


def _write_status(result: TickResult, duration_ms: int) -> None:
    path = _repo_root() / ".claude" / "watcher" / "status.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "last_tick_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duration_ms": duration_ms,
        "pendings_checked": result.pendings_checked,
        "actions": result.actions,
        "errors": result.errors,
        "next_tick_eta_utc": (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat(timespec="seconds"),
    }
    path.write_text(json.dumps(data, indent=2))


def _render_dashboard(active: list, suspended: list, prices: dict) -> None:
    path = _repo_root() / ".claude" / "watcher" / "dashboard.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    mx_now = (datetime.now(timezone.utc) - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M CR")

    lines = [
        f"# Watcher Dashboard — {mx_now}",
        "",
        f"Last tick: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"Active pendings: {len(active)} | Suspended: {len(suspended)}",
        "",
        "## Active pendings",
        "",
    ]
    if not active:
        lines.append("_(none)_")
    for o in active:
        key = (o["profile"], o["asset"])
        cur = prices.get(key)
        dist = _distance_pct(cur, o["entry"]) if cur else None
        lines.append(
            f"### `{o['id']}` — {o['profile']} {o['asset']} {o.get('side','')} @ {o.get('entry','?')}"
        )
        if dist is not None:
            lines.append(
                f"Status: **{o.get('status','?')}** | "
                f"Price now: {cur} | "
                f"Distance: {dist:.2f}%"
            )
        else:
            lines.append(f"Status: **{o.get('status','?')}**")
        lines.append(f"TTL: {o.get('expires_at','?')} | Invalid @: {o.get('invalidation_price','?')}")
        lines.append("")

    lines += ["## Suspended", ""]
    if not suspended:
        lines.append("_(none)_")
    for o in suspended:
        lines.append(f"- `{o['id']}` — {o['profile']} {o['asset']} (status: {o.get('status','?')})")

    lines.append("")
    lines.append("## Recent events")
    lines.append("")
    path.write_text("\n".join(lines))


def run_tick() -> TickResult:
    """Run one tick cycle. Returns TickResult."""
    start = datetime.now()
    result = TickResult(ok=True)

    try:
        # Step 1: Load all pendings
        all_pendings = load_all_pendings()

        # Step 2: Whitelist matrix
        active, suspended_new = apply_whitelist_matrix(all_pendings)

        # Apply suspensions to storage
        for o in suspended_new:
            if o.get("status") != "suspended_policy":
                try:
                    update_status(
                        o["profile"], o["id"], "suspended_policy",
                        note="whitelist matrix: conflicting pending active",
                    )
                    notify(
                        Urgency.INFO,
                        "suspended_policy",
                        {"order_id": o["id"], "profile": o["profile"], "asset": o.get("asset", "-")},
                    )
                except KeyError:
                    pass

        # Step 3: Fetch prices for active pendings' unique assets
        prices: dict = {}
        for o in active:
            key = (o["profile"], o["asset"])
            if key not in prices:
                try:
                    prices[key] = price_for(*key)
                except PriceFeedError as e:
                    result.errors.append(f"price fail {key}: {e}")
                    result.ok = False

        # Step 4: Invalidations
        stopday = stopday_triggered_profiles()
        survivors: list = []
        for o in active:
            key = (o["profile"], o["asset"])
            price = prices.get(key)
            if price is None:
                survivors.append(o)
                continue
            inv = evaluate_invalidation(o, price, stopday)
            if inv.invalidated:
                update_status(o["profile"], o["id"], inv.new_status, note=inv.reason or "")
                result.actions.append({
                    "order_id": o["id"], "action": "invalidated",
                    "new_status": inv.new_status, "reason": inv.reason,
                })
                urgency = (
                    Urgency.WARN
                    if inv.new_status in ("invalidated_price", "invalidated_stopday")
                    else Urgency.INFO
                )
                notify(urgency, inv.new_status, {
                    "order_id": o["id"], "profile": o["profile"], "asset": o.get("asset", "-"),
                    "invalidation_price": o.get("invalidation_price"),
                })
            else:
                survivors.append(o)

        # Step 5: Distance check + escalate/heartbeat
        for o in survivors:
            key = (o["profile"], o["asset"])
            price = prices.get(key)
            if price is None:
                continue
            dist_pct = _distance_pct(price, o["entry"])
            if dist_pct <= ESCALATE_DISTANCE_PCT:
                if o.get("status") != "triggered_validating":
                    update_status(
                        o["profile"], o["id"], "triggered_validating",
                        note=f"price {price} dist {dist_pct:.3f}% — escalating to Claude",
                    )
                spawn_escalate(o["id"])
                result.actions.append({
                    "order_id": o["id"], "action": "escalated",
                    "distance_pct": round(dist_pct, 3),
                })
                notify(Urgency.WARN, "near_entry", {
                    "order_id": o["id"], "profile": o["profile"], "asset": o.get("asset", "-"),
                    "side": o.get("side"), "entry": o["entry"],
                    "distance_pct": round(dist_pct, 3),
                })
            else:
                # heartbeat — update next_recheck_suggested_mx in place
                next_check = _next_recheck_from_distance(dist_pct)
                all_in = load_pendings(o["profile"])
                for it in all_in:
                    if it["id"] == o["id"]:
                        it["next_recheck_suggested_mx"] = next_check
                save_pendings(o["profile"], all_in)
                result.actions.append({
                    "order_id": o["id"], "action": "heartbeat",
                    "distance_pct": round(dist_pct, 3),
                })

        result.pendings_checked = len(active)

        # Step 6: Render dashboard + status.json
        _render_dashboard(active, suspended_new, prices)

    except Exception as e:
        result.ok = False
        result.errors.append(f"fatal: {e!r}")

    duration_ms = int((datetime.now() - start).total_seconds() * 1000)
    _write_status(result, duration_ms)

    return result


def main():
    import argparse
    p = argparse.ArgumentParser(description="Watcher tick — evaluates all pending orders.")
    p.add_argument("--dry-run", action="store_true", help="Print what would happen (sets WALLY_DRY_RUN=1)")
    args = p.parse_args()

    if args.dry_run:
        os.environ["WALLY_DRY_RUN"] = "1"

    result = run_tick()
    print(json.dumps(asdict(result), indent=2, default=str))
    sys.exit(0 if result.ok else 1 if result.errors else 2)


if __name__ == "__main__":
    main()
