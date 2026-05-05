#!/usr/bin/env python3
"""weekly_digest.py — generate cross-profile weekly digest.

Reads each profile's config.md + memory/trading_log.md (via per-profile parser),
optionally reads macro cache for next-week lookahead, writes markdown to
memory/weekly_digests/YYYY-Wnn.md, and fires a macOS notification.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

CR_OFFSET = timezone(timedelta(hours=-6))
PROFILES_DIR_REL = Path(".claude/profiles")
DIGEST_DIR_REL = Path("memory/weekly_digests")
MACRO_CACHE_REL = Path(".claude/cache/macro_events.json")


def repo_root() -> Path:
    cur = Path.cwd()
    while cur != cur.parent:
        if (cur / ".claude").is_dir():
            return cur
        cur = cur.parent
    return Path.cwd()


def iso_week_bounds(week_str: str) -> tuple[date, date]:
    """`'2026-W18'` → (Mon date, Sun date)."""
    year_s, week_s = week_str.split("-W")
    year = int(year_s)
    week = int(week_s)
    monday = date.fromisocalendar(year, week, 1)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def current_week_str(now: datetime | None = None) -> str:
    now = now or datetime.now(CR_OFFSET)
    iy, iw, _ = now.isocalendar()
    return f"{iy}-W{iw:02d}"


def extract_capital(config_text: str) -> str:
    m = re.search(r"Capital actual.*?(\$[\d,.]+|\d+(?:\.\d+)?\s*BTC)", config_text)
    return m.group(1) if m else "—"


# ---------- Profile parsers ----------

def parse_retail_log(text: str, week_start: date, week_end: date) -> dict:
    """Parse retail/retail-bingx trading log: ## YYYY-MM-DD blocks with `- Trade N: ... PnL +/-$X`."""
    pnl_week = 0.0
    pnl_month = 0.0
    trades_week = 0
    wins_week = 0
    month_start = week_start.replace(day=1)
    blocks = re.split(r"^## (\d{4}-\d{2}-\d{2})", text, flags=re.MULTILINE)
    for i in range(1, len(blocks), 2):
        try:
            d = date.fromisoformat(blocks[i])
        except ValueError:
            continue
        body = blocks[i + 1] if i + 1 < len(blocks) else ""
        for trade_match in re.finditer(r"PnL\s+([+\-])\s*\$([\d.]+)", body):
            sign = 1 if trade_match.group(1) == "+" else -1
            amount = sign * float(trade_match.group(2))
            if month_start <= d:
                pnl_month += amount
            if week_start <= d <= week_end:
                pnl_week += amount
                trades_week += 1
                if amount > 0:
                    wins_week += 1
    wr = (100 * wins_week / trades_week) if trades_week else 0
    return {
        "pnl_week": f"{pnl_week:+.2f}" if pnl_week else "$0",
        "pnl_month": f"{pnl_month:+.2f}" if pnl_month else "$0",
        "trades": trades_week,
        "wr": f"{wr:.0f}%" if trades_week else "—",
    }


def parse_ftmo_log(text: str, week_start: date, week_end: date) -> dict:
    """FTMO log uses similar `## YYYY-MM-DD` headers with looser body format."""
    return parse_retail_log(text, week_start, week_end)  # same regex catches `+$30` / `-$50`


# Registry: maps profile name to parser
PROFILE_PARSERS: dict[str, Callable] = {
    "retail": parse_retail_log,
    "retail-bingx": parse_retail_log,
    "ftmo": parse_ftmo_log,
    "fundingpips": parse_ftmo_log,
    "fotmarkets": parse_ftmo_log,
    "bitunix": parse_retail_log,
    # quantfury intentionally absent → "parser pending"
}


def gather_profile_metrics(root: Path, week_start: date, week_end: date) -> list[dict]:
    """For each profile under .claude/profiles/, produce one row of metrics."""
    rows = []
    profiles_dir = root / PROFILES_DIR_REL
    if not profiles_dir.exists():
        return rows
    for p in sorted(profiles_dir.iterdir()):
        if not p.is_dir():
            continue
        name = p.name
        config_path = p / "config.md"
        log_path = p / "memory" / "trading_log.md"
        capital = extract_capital(config_path.read_text()) if config_path.exists() else "—"
        if name not in PROFILE_PARSERS:
            rows.append({
                "profile": name, "capital": capital,
                "pnl_week": "—", "pnl_month": "—",
                "trades": "—", "wr": "—", "status": "parser pending",
            })
            continue
        if not log_path.exists():
            rows.append({
                "profile": name, "capital": capital,
                "pnl_week": "—", "pnl_month": "—",
                "trades": 0, "wr": "—", "status": "not started",
            })
            continue
        m = PROFILE_PARSERS[name](log_path.read_text(), week_start, week_end)
        rows.append({
            "profile": name, "capital": capital,
            "pnl_week": m["pnl_week"], "pnl_month": m["pnl_month"],
            "trades": m["trades"], "wr": m["wr"],
            "status": "active" if m["trades"] else "dormant",
        })
    return rows


def render_cross_profile_table(rows: list[dict]) -> str:
    if not rows:
        return "_(no profiles found)_\n"
    out = ["| Profile | Capital | PnL semana | PnL mes | Trades | WR | Status |",
           "|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['profile']} | {r['capital']} | {r['pnl_week']} | "
                   f"{r['pnl_month']} | {r['trades']} | {r['wr']} | {r['status']} |")
    return "\n".join(out) + "\n"


# ---------- Macro lookahead (Task 3.2) ----------
# stub for now; implemented in 3.2

def render_macro_lookahead(root: Path, week_start: date) -> str:
    return "_(macro cache unavailable — refresh: bash .claude/scripts/macro_calendar.py)_\n"


# ---------- Disciplina + suggestions (Task 3.3) ----------

def render_disciplina(rows: list[dict]) -> str:
    return "_(disciplina checks pending implementation)_\n"


def render_suggestions(rows: list[dict], macro_section: str) -> str:
    return "_(suggestions pending)_\n"


# ---------- Notification ----------

def send_notification(message: str, title: str = "Wally Trader",
                      subtitle: str = "") -> None:
    """Best-effort macOS notification. No-op if osascript unavailable."""
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{message}" with title "{title}" subtitle "{subtitle}"'],
            check=False, capture_output=True, timeout=5
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        print("notification skipped (no osascript)", file=sys.stderr)


# ---------- Entry point ----------

def run(week_str: str, cwd: Path, no_notif: bool) -> int:
    week_start, week_end = iso_week_bounds(week_str)
    rows = gather_profile_metrics(cwd, week_start, week_end)
    table = render_cross_profile_table(rows)
    macro = render_macro_lookahead(cwd, week_end + timedelta(days=1))
    disciplina = render_disciplina(rows)
    suggestions = render_suggestions(rows, macro)

    now = datetime.now(CR_OFFSET)
    md = f"""# Weekly Digest — {week_str} ({week_start} → {week_end})

Generated: {now.isoformat()}

## Cross-profile summary

{table}

## 🔴 Macro week ahead

{macro}

## Highlights y disciplina

{disciplina}

## Próxima semana — sugerencias

{suggestions}
"""
    out_dir = cwd / DIGEST_DIR_REL
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{week_str}.md"
    out_path.write_text(md)
    print(f"weekly_digest: wrote {out_path}")

    if not no_notif:
        active_count = sum(1 for r in rows if r["status"] == "active")
        send_notification(
            f"Weekly digest ready: {active_count} active profiles",
            subtitle=f"Week {week_str.split('-W')[1]}"
        )
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--week", default="current",
                   help="ISO week string like 2026-W18, or 'current'.")
    p.add_argument("--no-notif", action="store_true")
    args = p.parse_args()
    week = current_week_str() if args.week == "current" else args.week
    return run(week, cwd=Path.cwd(), no_notif=args.no_notif)


if __name__ == "__main__":
    sys.exit(main())
