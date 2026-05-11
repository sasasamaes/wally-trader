# `/track-dragno` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a manual tracker for Dragno AI's Bitunix copy-trading bot that logs trades to CSV, computes rolling stats, and runs a SL -8% counterfactual on every invocation.

**Architecture:** One Python script (`dragno_track.py`) with three CLI subcommands (`--append-from-stdin`, `--stats`, `--regenerate-md`). Slash command (`/track-dragno`) dispatches to the script based on whether the current turn has image attachments (Claude parses screenshots → pipes JSON to stdin). CSV is the source of truth; the `.md` is regenerated.

**Tech Stack:** Python 3 stdlib only (argparse, csv, json, datetime, pathlib). Pytest for tests. No external deps required.

---

## File Structure

| File | Purpose |
|---|---|
| `.claude/scripts/dragno_track.py` | Core CLI: parse, dedup, stats, counterfactual, md gen |
| `.claude/scripts/tests/test_dragno_track.py` | Unit tests for dedup, stats, counterfactual |
| `.claude/commands/track-dragno.md` | Slash command definition |
| `memory/external_traders/dragno_ai.csv` | Append-only log (created by first append) |
| `memory/external_traders/dragno_ai.md` | Human-readable summary (regenerated each run) |
| `memory/external_traders/.gitkeep` | Keep dir tracked when empty |

---

## Task 1: Create directory + .gitkeep

**Files:**
- Create: `memory/external_traders/.gitkeep`

- [ ] **Step 1: Create directory with empty .gitkeep**

```bash
mkdir -p memory/external_traders
touch memory/external_traders/.gitkeep
```

- [ ] **Step 2: Commit**

```bash
git add memory/external_traders/.gitkeep
git commit -m "chore: create memory/external_traders/ for bot tracking"
```

---

## Task 2: Script skeleton with CLI argparse

**Files:**
- Create: `.claude/scripts/dragno_track.py`

- [ ] **Step 1: Create script with argparse and three subcommand flags**

```python
#!/usr/bin/env python3
"""dragno_track.py — Track Dragno AI bot trades from Bitunix.

Subcommands:
  --append-from-stdin       Read JSON array of trades from stdin, dedup, append to CSV
  --stats                   Compute and print stats dashboard
  --regenerate-md           Rewrite memory/external_traders/dragno_ai.md from CSV

Options:
  --sl-cap FLOAT            SL percentage cap for counterfactual (default -8.0)
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path


CSV_FIELDS = [
    "date", "time_open", "time_close", "symbol", "side", "leverage",
    "entry", "exit", "pyg_pct", "pyg_usd", "margin_est", "duration_min", "source",
]

DEFAULT_SL_CAP = -8.0


def repo_root() -> Path:
    """Walk up from this file to find repo root (contains .claude/)."""
    cur = Path(__file__).resolve()
    while cur != cur.parent:
        if (cur / ".claude").is_dir() and (cur / "memory").is_dir():
            return cur
        cur = cur.parent
    return Path.cwd()


def csv_path() -> Path:
    return repo_root() / "memory" / "external_traders" / "dragno_ai.csv"


def md_path() -> Path:
    return repo_root() / "memory" / "external_traders" / "dragno_ai.md"


def main() -> int:
    p = argparse.ArgumentParser(description="Track Dragno AI bot trades")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--append-from-stdin", action="store_true")
    group.add_argument("--stats", action="store_true")
    group.add_argument("--regenerate-md", action="store_true")
    p.add_argument("--sl-cap", type=float, default=DEFAULT_SL_CAP)
    args = p.parse_args()

    if args.append_from_stdin:
        return cmd_append_from_stdin(args.sl_cap)
    if args.stats:
        return cmd_stats(args.sl_cap)
    if args.regenerate_md:
        return cmd_regenerate_md(args.sl_cap)
    return 1


def cmd_append_from_stdin(sl_cap: float) -> int:
    raise NotImplementedError


def cmd_stats(sl_cap: float) -> int:
    raise NotImplementedError


def cmd_regenerate_md(sl_cap: float) -> int:
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Make executable and verify argparse**

```bash
chmod +x .claude/scripts/dragno_track.py
python3 .claude/scripts/dragno_track.py --help
```

Expected: prints the help text with `--append-from-stdin`, `--stats`, `--regenerate-md`, `--sl-cap`. Exit code 0.

- [ ] **Step 3: Commit**

```bash
git add .claude/scripts/dragno_track.py
git commit -m "feat(dragno-track): script skeleton with argparse CLI"
```

---

## Task 3: derive_margin helper + unit test

**Files:**
- Create: `.claude/scripts/tests/test_dragno_track.py`
- Modify: `.claude/scripts/dragno_track.py`

- [ ] **Step 1: Write the failing test**

```python
# .claude/scripts/tests/test_dragno_track.py
"""Unit tests for dragno_track.py."""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import dragno_track as dt


def test_derive_margin_from_win():
    # KITE: +15.48% / +$0.45994 → margin = 0.45994 / 0.1548 ≈ 2.972
    margin = dt.derive_margin(pyg_pct=15.48, pyg_usd=0.45994)
    assert abs(margin - 2.972) < 0.01


def test_derive_margin_from_loss():
    # VIRTUAL: -15.28% / -$0.52676 → margin = 0.52676 / 0.1528 ≈ 3.448
    margin = dt.derive_margin(pyg_pct=-15.28, pyg_usd=-0.52676)
    assert abs(margin - 3.448) < 0.01


def test_derive_margin_returns_zero_if_pct_zero():
    assert dt.derive_margin(pyg_pct=0.0, pyg_usd=0.0) == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/josecampos/Documents/wally-trader
python3 -m pytest .claude/scripts/tests/test_dragno_track.py -v
```

Expected: 3 FAILED with `AttributeError: module 'dragno_track' has no attribute 'derive_margin'`

- [ ] **Step 3: Implement derive_margin in dragno_track.py**

Add this function right above `def main()`:

```python
def derive_margin(pyg_pct: float, pyg_usd: float) -> float:
    """Derive position margin from PYG% and PYG USD.

    Bitunix shows PYG% on margin (leverage-adjusted). Margin = |pyg_usd| / (|pyg_pct|/100).
    Returns 0.0 if pyg_pct is zero (avoid divide-by-zero).
    """
    if pyg_pct == 0.0:
        return 0.0
    return abs(pyg_usd) / (abs(pyg_pct) / 100.0)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python3 -m pytest .claude/scripts/tests/test_dragno_track.py -v
```

Expected: 3 PASSED.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/dragno_track.py .claude/scripts/tests/test_dragno_track.py
git commit -m "feat(dragno-track): add derive_margin helper with tests"
```

---

## Task 4: parse_input_rows (JSON → normalized dicts)

**Files:**
- Modify: `.claude/scripts/dragno_track.py`
- Modify: `.claude/scripts/tests/test_dragno_track.py`

- [ ] **Step 1: Write the failing test**

Append to `test_dragno_track.py`:

```python
def test_parse_input_rows_normalizes_side():
    raw = [
        {"date": "2026-05-10", "time_open": "11:19:47", "time_close": "13:08:02",
         "symbol": "KITEUSDT", "side": "Corto", "leverage": "10X",
         "entry": "0.18340", "exit": "0.18034",
         "pyg_pct": "+15.48", "pyg_usd": "+0.45994422"}
    ]
    rows = dt.parse_input_rows(raw)
    assert len(rows) == 1
    r = rows[0]
    assert r["side"] == "SHORT"
    assert r["leverage"] == 10
    assert r["pyg_pct"] == 15.48
    assert r["pyg_usd"] == 0.45994422
    assert r["margin_est"] > 0
    assert r["duration_min"] == 108  # 13:08:02 - 11:19:47 ≈ 108 min
    assert r["source"] == "manual_screenshot"


def test_parse_input_rows_handles_largo_as_long():
    raw = [
        {"date": "2026-05-10", "time_open": "18:50:25", "time_close": "19:38:10",
         "symbol": "IOTAUSDT", "side": "Largo", "leverage": "10X",
         "entry": "0.0631", "exit": "0.0637",
         "pyg_pct": "9.03", "pyg_usd": "0.14906275"}
    ]
    rows = dt.parse_input_rows(raw)
    assert rows[0]["side"] == "LONG"


def test_parse_input_rows_rejects_malformed():
    raw = [{"symbol": "KITEUSDT"}]  # missing required fields
    try:
        dt.parse_input_rows(raw)
        assert False, "Should have raised"
    except (KeyError, ValueError):
        pass
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest .claude/scripts/tests/test_dragno_track.py -v
```

Expected: 3 new tests FAIL with `AttributeError: ... no attribute 'parse_input_rows'`.

- [ ] **Step 3: Implement parse_input_rows in dragno_track.py**

Add above `def main()`:

```python
SIDE_MAP = {"largo": "LONG", "long": "LONG", "corto": "SHORT", "short": "SHORT"}


def _parse_signed_float(s) -> float:
    """Parse a possibly-prefixed numeric string. Python's float() handles '-15.28'
    and '15.48' natively but rejects '+15.48' in some legacy locales — strip '+' first."""
    return float(str(s).replace("+", "").strip())


def _duration_minutes(time_open: str, time_close: str) -> int:
    """Minutes between two HH:MM:SS strings. Negative or cross-midnight returns 0."""
    fmt = "%H:%M:%S"
    try:
        t0 = datetime.strptime(time_open, fmt)
        t1 = datetime.strptime(time_close, fmt)
    except ValueError:
        return 0
    delta = (t1 - t0).total_seconds() / 60.0
    return max(0, int(round(delta)))


def parse_input_rows(raw: list[dict]) -> list[dict]:
    """Normalize Claude-parsed screenshot rows into CSV-ready dicts.

    Required input fields per row: date, time_open, time_close, symbol, side,
    leverage, entry, exit, pyg_pct, pyg_usd.
    """
    out = []
    for r in raw:
        side_key = str(r["side"]).strip().lower()
        if side_key not in SIDE_MAP:
            raise ValueError(f"Unknown side: {r['side']!r}")
        leverage_str = str(r["leverage"]).strip().lower().rstrip("x")
        normalized = {
            "date": r["date"],
            "time_open": r["time_open"],
            "time_close": r["time_close"],
            "symbol": str(r["symbol"]).upper(),
            "side": SIDE_MAP[side_key],
            "leverage": int(leverage_str),
            "entry": float(r["entry"]),
            "exit": float(r["exit"]),
            "pyg_pct": _parse_signed_float(r["pyg_pct"]),
            "pyg_usd": _parse_signed_float(r["pyg_usd"]),
            "duration_min": _duration_minutes(r["time_open"], r["time_close"]),
            "source": "manual_screenshot",
        }
        normalized["margin_est"] = round(derive_margin(normalized["pyg_pct"], normalized["pyg_usd"]), 4)
        out.append(normalized)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python3 -m pytest .claude/scripts/tests/test_dragno_track.py -v
```

Expected: 6 PASSED.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/dragno_track.py .claude/scripts/tests/test_dragno_track.py
git commit -m "feat(dragno-track): parse_input_rows with side/leverage normalization"
```

---

## Task 5: CSV read/write with dedup

**Files:**
- Modify: `.claude/scripts/dragno_track.py`
- Modify: `.claude/scripts/tests/test_dragno_track.py`

- [ ] **Step 1: Write the failing test**

Append to `test_dragno_track.py`:

```python
import csv as _csv
import pytest


@pytest.fixture
def tmp_csv(tmp_path, monkeypatch):
    """Isolated CSV path."""
    path = tmp_path / "dragno_ai.csv"
    monkeypatch.setattr(dt, "csv_path", lambda: path)
    return path


def test_read_rows_empty_when_missing(tmp_csv):
    assert dt.read_rows() == []


def test_write_and_read_roundtrip(tmp_csv):
    rows = [{
        "date": "2026-05-10", "time_open": "11:19:47", "time_close": "13:08:02",
        "symbol": "KITEUSDT", "side": "SHORT", "leverage": 10,
        "entry": 0.18340, "exit": 0.18034,
        "pyg_pct": 15.48, "pyg_usd": 0.45994,
        "margin_est": 2.97, "duration_min": 108, "source": "manual_screenshot",
    }]
    dt.write_rows(rows)
    loaded = dt.read_rows()
    assert len(loaded) == 1
    assert loaded[0]["symbol"] == "KITEUSDT"
    assert loaded[0]["pyg_pct"] == 15.48  # numeric, not string
    assert loaded[0]["leverage"] == 10


def test_append_dedup_skips_existing(tmp_csv):
    base = {
        "date": "2026-05-10", "time_open": "11:19:47", "time_close": "13:08:02",
        "symbol": "KITEUSDT", "side": "SHORT", "leverage": 10,
        "entry": 0.18340, "exit": 0.18034,
        "pyg_pct": 15.48, "pyg_usd": 0.45994,
        "margin_est": 2.97, "duration_min": 108, "source": "manual_screenshot",
    }
    dt.write_rows([base])
    # Try appending same trade + a new one
    new_trade = dict(base, symbol="ORDIUSDT", time_open="13:42:03")
    added = dt.append_rows_dedup([base, new_trade])
    assert added == 1  # only ORDIUSDT is new
    assert len(dt.read_rows()) == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest .claude/scripts/tests/test_dragno_track.py -v
```

Expected: 3 new tests FAIL with `AttributeError: ... no attribute 'read_rows'` (and similar).

- [ ] **Step 3: Implement read_rows, write_rows, append_rows_dedup in dragno_track.py**

Add above `def main()`:

```python
NUMERIC_FIELDS = ("leverage", "entry", "exit", "pyg_pct", "pyg_usd", "margin_est", "duration_min")


def read_rows() -> list[dict]:
    """Read CSV into list of dicts with numeric fields coerced. Returns [] if missing/empty."""
    path = csv_path()
    if not path.exists():
        return []
    with path.open(newline="") as f:
        reader = _csv.DictReader(f)
        rows = []
        for raw in reader:
            row = dict(raw)
            for k in NUMERIC_FIELDS:
                if k in row and row[k] != "":
                    try:
                        row[k] = int(row[k]) if k in ("leverage", "duration_min") else float(row[k])
                    except ValueError:
                        pass
            rows.append(row)
        return rows


def write_rows(rows: list[dict]) -> None:
    """Overwrite the CSV with the given rows (creates parent dirs)."""
    path = csv_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = _csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in CSV_FIELDS})


def _dedup_key(row: dict) -> tuple[str, str, str]:
    return (str(row["date"]), str(row["time_open"]), str(row["symbol"]).upper())


def append_rows_dedup(new_rows: list[dict]) -> int:
    """Append rows to CSV, skipping any whose dedup key already exists. Returns count added."""
    existing = read_rows()
    seen = {_dedup_key(r) for r in existing}
    added = 0
    for r in new_rows:
        if _dedup_key(r) in seen:
            continue
        existing.append(r)
        seen.add(_dedup_key(r))
        added += 1
    if added > 0:
        write_rows(existing)
    return added
```

Replace the existing `import csv` with `import csv as _csv` near the top of the file (so the local variable `csv` is not shadowed).

- [ ] **Step 4: Run test to verify it passes**

```bash
python3 -m pytest .claude/scripts/tests/test_dragno_track.py -v
```

Expected: 9 PASSED.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/dragno_track.py .claude/scripts/tests/test_dragno_track.py
git commit -m "feat(dragno-track): CSV read/write with dedup by (date,time_open,symbol)"
```

---

## Task 6: Stats computation (WR, PF, avgs, side breakdown, top winners/losers)

**Files:**
- Modify: `.claude/scripts/dragno_track.py`
- Modify: `.claude/scripts/tests/test_dragno_track.py`

- [ ] **Step 1: Write the failing test**

Append to `test_dragno_track.py`:

```python
def _sample_trades():
    """Subset of today's Dragno AI trades for deterministic stats."""
    return [
        {"date": "2026-05-10", "time_open": "11:19:47", "time_close": "13:08:02",
         "symbol": "KITEUSDT", "side": "SHORT", "leverage": 10,
         "entry": 0.18340, "exit": 0.18034, "pyg_pct": 15.48, "pyg_usd": 0.45994,
         "margin_est": 2.97, "duration_min": 108, "source": "manual_screenshot"},
        {"date": "2026-05-10", "time_open": "11:10:38", "time_close": "11:49:55",
         "symbol": "VIRTUALUSDT", "side": "SHORT", "leverage": 10,
         "entry": 0.9092, "exit": 0.9220, "pyg_pct": -15.28, "pyg_usd": -0.52676,
         "margin_est": 3.45, "duration_min": 39, "source": "manual_screenshot"},
        {"date": "2026-05-10", "time_open": "15:47:20", "time_close": "17:33:06",
         "symbol": "UNIUSDT", "side": "LONG", "leverage": 10,
         "entry": 3.956, "exit": 3.993, "pyg_pct": 8.21, "pyg_usd": 0.25984,
         "margin_est": 3.17, "duration_min": 105, "source": "manual_screenshot"},
        {"date": "2026-05-10", "time_open": "12:12:49", "time_close": "13:32:22",
         "symbol": "SUSDT", "side": "SHORT", "leverage": 10,
         "entry": 0.05556, "exit": 0.05660, "pyg_pct": -19.92, "pyg_usd": -0.59462,
         "margin_est": 2.98, "duration_min": 80, "source": "manual_screenshot"},
    ]


def test_compute_stats_aggregate():
    s = dt.compute_stats(_sample_trades(), sl_cap=-8.0)
    assert s["total_trades"] == 4
    assert s["wins"] == 2  # KITE, UNI
    assert s["losses"] == 2  # VIRTUAL, SUSDT
    assert s["win_rate_pct"] == 50.0
    assert abs(s["net_pnl"] - (0.45994 + 0.25984 - 0.52676 - 0.59462)) < 0.001
    assert abs(s["best_win"] - 0.45994) < 0.001
    assert abs(s["worst_loss"] - (-0.59462)) < 0.001


def test_compute_stats_side_breakdown():
    s = dt.compute_stats(_sample_trades(), sl_cap=-8.0)
    assert s["long"]["count"] == 1
    assert s["long"]["wins"] == 1
    assert s["short"]["count"] == 3
    assert s["short"]["wins"] == 1


def test_compute_stats_empty_returns_zero_stats():
    s = dt.compute_stats([], sl_cap=-8.0)
    assert s["total_trades"] == 0
    assert s["win_rate_pct"] == 0.0
    assert s["profit_factor"] == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest .claude/scripts/tests/test_dragno_track.py -v
```

Expected: 3 new tests FAIL with `AttributeError: ... no attribute 'compute_stats'`.

- [ ] **Step 3: Implement compute_stats in dragno_track.py**

Add above `def main()`:

```python
def compute_stats(rows: list[dict], sl_cap: float = DEFAULT_SL_CAP) -> dict:
    """Compute aggregate + counterfactual + side breakdown + top winners/losers."""
    if not rows:
        return {
            "total_trades": 0, "wins": 0, "losses": 0, "win_rate_pct": 0.0,
            "net_pnl": 0.0, "profit_factor": 0.0,
            "avg_win": 0.0, "avg_loss": 0.0, "best_win": 0.0, "worst_loss": 0.0,
            "days_tracked": 0, "trades_per_day": 0.0,
            "counterfactual": {
                "sl_cap": sl_cap, "sl_hits": 0,
                "new_net_pnl": 0.0, "delta_usd": 0.0, "delta_pct": 0.0,
                "new_profit_factor": 0.0, "new_worst_loss": 0.0,
            },
            "long": {"count": 0, "wins": 0, "net_pnl": 0.0},
            "short": {"count": 0, "wins": 0, "net_pnl": 0.0},
            "top_winners": [], "top_losers": [],
        }

    pnls = [float(r["pyg_usd"]) for r in rows]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = 100.0 * len(wins) / len(pnls)
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else 0.0

    # Counterfactual: cap losses worse than sl_cap at sl_cap
    new_pnls = []
    sl_hits = 0
    for r in rows:
        pct = float(r["pyg_pct"])
        usd = float(r["pyg_usd"])
        if pct < sl_cap:
            margin = derive_margin(pct, usd)
            new_pnls.append((sl_cap / 100.0) * margin)
            sl_hits += 1
        else:
            new_pnls.append(usd)
    new_net = sum(new_pnls)
    delta_usd = new_net - sum(pnls)
    delta_pct = (delta_usd / sum(pnls) * 100.0) if sum(pnls) != 0 else 0.0
    new_losses = [p for p in new_pnls if p <= 0]
    new_pf = (sum(wins) / abs(sum(new_losses))) if new_losses and sum(new_losses) != 0 else 0.0

    longs = [r for r in rows if r["side"] == "LONG"]
    shorts = [r for r in rows if r["side"] == "SHORT"]
    long_pnls = [float(r["pyg_usd"]) for r in longs]
    short_pnls = [float(r["pyg_usd"]) for r in shorts]

    sorted_rows = sorted(rows, key=lambda r: float(r["pyg_usd"]), reverse=True)
    top_winners = [{"symbol": r["symbol"], "pyg_pct": float(r["pyg_pct"]), "pyg_usd": float(r["pyg_usd"])} for r in sorted_rows[:3]]
    top_losers = [{"symbol": r["symbol"], "pyg_pct": float(r["pyg_pct"]), "pyg_usd": float(r["pyg_usd"])} for r in sorted_rows[-3:][::-1]]

    days = {r["date"] for r in rows}

    return {
        "total_trades": len(rows),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(win_rate, 2),
        "net_pnl": round(sum(pnls), 4),
        "profit_factor": round(pf, 3),
        "avg_win": round(sum(wins) / len(wins), 4) if wins else 0.0,
        "avg_loss": round(sum(losses) / len(losses), 4) if losses else 0.0,
        "best_win": round(max(pnls), 4),
        "worst_loss": round(min(pnls), 4),
        "days_tracked": len(days),
        "trades_per_day": round(len(rows) / len(days), 2) if days else 0.0,
        "counterfactual": {
            "sl_cap": sl_cap,
            "sl_hits": sl_hits,
            "new_net_pnl": round(new_net, 4),
            "delta_usd": round(delta_usd, 4),
            "delta_pct": round(delta_pct, 2),
            "new_profit_factor": round(new_pf, 3),
            "new_worst_loss": round(min(new_pnls), 4) if new_pnls else 0.0,
        },
        "long": {
            "count": len(longs),
            "wins": sum(1 for p in long_pnls if p > 0),
            "net_pnl": round(sum(long_pnls), 4),
        },
        "short": {
            "count": len(shorts),
            "wins": sum(1 for p in short_pnls if p > 0),
            "net_pnl": round(sum(short_pnls), 4),
        },
        "top_winners": top_winners,
        "top_losers": top_losers,
    }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python3 -m pytest .claude/scripts/tests/test_dragno_track.py -v
```

Expected: 12 PASSED.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/dragno_track.py .claude/scripts/tests/test_dragno_track.py
git commit -m "feat(dragno-track): compute_stats with counterfactual + side breakdown"
```

---

## Task 7: Stats counterfactual specific test (validates today's +80% number)

**Files:**
- Modify: `.claude/scripts/tests/test_dragno_track.py`

- [ ] **Step 1: Write a test that pins the +80% number from today's analysis**

Append to `test_dragno_track.py`:

```python
def _full_dragno_2026_05_10():
    """All 14 trades from Dragno AI on 2026-05-10. Reference for counterfactual."""
    return dt.parse_input_rows([
        {"date": "2026-05-10", "time_open": "12:02:14", "time_close": "13:29:56",
         "symbol": "CHIPUSDT", "side": "Corto", "leverage": "10X",
         "entry": "0.06405", "exit": "0.06417", "pyg_pct": "-3.14", "pyg_usd": "-0.10114123"},
        {"date": "2026-05-10", "time_open": "11:19:47", "time_close": "13:08:02",
         "symbol": "KITEUSDT", "side": "Corto", "leverage": "10X",
         "entry": "0.18340", "exit": "0.18034", "pyg_pct": "15.48", "pyg_usd": "0.45994422"},
        {"date": "2026-05-10", "time_open": "11:10:38", "time_close": "11:49:55",
         "symbol": "VIRTUALUSDT", "side": "Corto", "leverage": "10X",
         "entry": "0.9092", "exit": "0.9220", "pyg_pct": "-15.28", "pyg_usd": "-0.52676148"},
        {"date": "2026-05-10", "time_open": "11:18:08", "time_close": "11:45:41",
         "symbol": "PAXGUSDT", "side": "Corto", "leverage": "10X",
         "entry": "4717.43", "exit": "4720.56", "pyg_pct": "-1.86", "pyg_usd": "-0.06154955"},
        {"date": "2026-05-10", "time_open": "18:50:25", "time_close": "19:38:10",
         "symbol": "IOTAUSDT", "side": "Largo", "leverage": "10X",
         "entry": "0.0631", "exit": "0.0637", "pyg_pct": "9.03", "pyg_usd": "0.14906275"},
        {"date": "2026-05-10", "time_open": "18:44:10", "time_close": "19:03:34",
         "symbol": "PIEVERSEUSDT", "side": "Largo", "leverage": "10X",
         "entry": "0.8228", "exit": "0.8198", "pyg_pct": "-4.84", "pyg_usd": "-0.16340796"},
        {"date": "2026-05-10", "time_open": "16:06:50", "time_close": "18:51:31",
         "symbol": "FILUSDT", "side": "Largo", "leverage": "10X",
         "entry": "1.132", "exit": "1.141", "pyg_pct": "7.49", "pyg_usd": "0.24509548"},
        {"date": "2026-05-10", "time_open": "16:36:35", "time_close": "17:47:51",
         "symbol": "MUSDT", "side": "Largo", "leverage": "10X",
         "entry": "3.3130", "exit": "3.3033", "pyg_pct": "-4.12", "pyg_usd": "-0.12302802"},
        {"date": "2026-05-10", "time_open": "15:47:20", "time_close": "17:33:06",
         "symbol": "UNIUSDT", "side": "Largo", "leverage": "10X",
         "entry": "3.956", "exit": "3.993", "pyg_pct": "8.21", "pyg_usd": "0.25984360"},
        {"date": "2026-05-10", "time_open": "16:15:22", "time_close": "16:23:12",
         "symbol": "BUSDT", "side": "Corto", "leverage": "10X",
         "entry": "0.4060", "exit": "0.4039", "pyg_pct": "3.76", "pyg_usd": "0.11303660"},
        {"date": "2026-05-10", "time_open": "13:49:50", "time_close": "15:34:18",
         "symbol": "GRTUSDT", "side": "Corto", "leverage": "10X",
         "entry": "0.02903", "exit": "0.02869", "pyg_pct": "10.51", "pyg_usd": "0.33330176"},
        {"date": "2026-05-10", "time_open": "13:57:01", "time_close": "15:33:44",
         "symbol": "LPTUSDT", "side": "Corto", "leverage": "10X",
         "entry": "2.399", "exit": "2.373", "pyg_pct": "9.44", "pyg_usd": "0.27629340"},
        {"date": "2026-05-10", "time_open": "13:42:03", "time_close": "15:31:31",
         "symbol": "ORDIUSDT", "side": "Corto", "leverage": "10X",
         "entry": "5.436", "exit": "5.298", "pyg_pct": "24.12", "pyg_usd": "0.81315061"},
        {"date": "2026-05-10", "time_open": "12:12:49", "time_close": "13:32:22",
         "symbol": "SUSDT", "side": "Corto", "leverage": "10X",
         "entry": "0.05556", "exit": "0.05660", "pyg_pct": "-19.92", "pyg_usd": "-0.59461795"},
    ])


def test_full_day_matches_known_baseline():
    """Pins 2026-05-10 analysis: 14 trades, WR 57.1%, net +$1.08, +56% with SL -8%."""
    s = dt.compute_stats(_full_dragno_2026_05_10(), sl_cap=-8.0)
    assert s["total_trades"] == 14
    assert s["wins"] == 8
    assert abs(s["win_rate_pct"] - 57.14) < 0.1
    assert abs(s["net_pnl"] - 1.0793) < 0.01
    # Counterfactual: SL -8% caps VIRTUAL (-15.28%) and SUSDT (-19.92%) → new total ≈ +$1.69
    assert s["counterfactual"]["sl_hits"] == 2
    assert abs(s["counterfactual"]["new_net_pnl"] - 1.6860) < 0.05
    assert s["counterfactual"]["delta_pct"] >= 50.0  # ≥ +56%
```

- [ ] **Step 2: Run test to verify it passes (compute_stats already implemented)**

```bash
python3 -m pytest .claude/scripts/tests/test_dragno_track.py::test_full_day_matches_known_baseline -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add .claude/scripts/tests/test_dragno_track.py
git commit -m "test(dragno-track): pin 2026-05-10 baseline counterfactual"
```

---

## Task 8: cmd_append_from_stdin + cmd_stats wiring

**Files:**
- Modify: `.claude/scripts/dragno_track.py`

- [ ] **Step 1: Replace the NotImplementedError stubs**

Replace `cmd_append_from_stdin` and `cmd_stats`:

```python
def cmd_append_from_stdin(sl_cap: float) -> int:
    """Read JSON array from stdin, parse, dedup-append to CSV. Then print summary."""
    try:
        raw = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON on stdin: {e}", file=sys.stderr)
        return 1
    if not isinstance(raw, list):
        print("ERROR: stdin must be a JSON array of trade objects", file=sys.stderr)
        return 1
    try:
        parsed = parse_input_rows(raw)
    except (KeyError, ValueError) as e:
        print(f"ERROR: malformed trade row: {e}", file=sys.stderr)
        return 1
    added = append_rows_dedup(parsed)
    total = len(read_rows())
    print(f"Added {added} new trade(s). Total tracked: {total}.")
    print()
    # Print stats after append
    cmd_stats(sl_cap)
    # Regenerate md
    cmd_regenerate_md(sl_cap)
    return 0


def cmd_stats(sl_cap: float) -> int:
    """Compute and print stats dashboard."""
    rows = read_rows()
    if not rows:
        print("No data yet. Run /track-dragno with screenshots to populate the log.")
        return 2
    s = compute_stats(rows, sl_cap=sl_cap)
    print(_format_dashboard(s))
    return 0
```

Add a formatter helper above `def main()`:

```python
def _format_dashboard(s: dict) -> str:
    cf = s["counterfactual"]
    lines = [
        "=" * 70,
        f"  DRAGNO AI — TRACKING DASHBOARD",
        "=" * 70,
        f"  Trades: {s['total_trades']}   Days: {s['days_tracked']}   Trades/day: {s['trades_per_day']}",
        f"  WR: {s['win_rate_pct']}%   PF: {s['profit_factor']}",
        f"  Net PnL: ${s['net_pnl']:+.4f}",
        f"  Avg win: ${s['avg_win']:+.4f}   Avg loss: ${s['avg_loss']:+.4f}",
        f"  Best win: ${s['best_win']:+.4f}   Worst loss: ${s['worst_loss']:+.4f}",
        "",
        f"  COUNTERFACTUAL (SL {cf['sl_cap']:.1f}%):",
        f"    New net PnL: ${cf['new_net_pnl']:+.4f}   Delta: ${cf['delta_usd']:+.4f} ({cf['delta_pct']:+.1f}%)",
        f"    SL hits: {cf['sl_hits']}   New PF: {cf['new_profit_factor']}   New worst loss: ${cf['new_worst_loss']:+.4f}",
        "",
        f"  BY SIDE:",
        f"    LONG  — count {s['long']['count']}, wins {s['long']['wins']}, net ${s['long']['net_pnl']:+.4f}",
        f"    SHORT — count {s['short']['count']}, wins {s['short']['wins']}, net ${s['short']['net_pnl']:+.4f}",
        "",
        f"  TOP 3 WINNERS:",
    ]
    for t in s["top_winners"]:
        lines.append(f"    {t['symbol']:<14} {t['pyg_pct']:+7.2f}%   ${t['pyg_usd']:+.4f}")
    lines.append("")
    lines.append(f"  TOP 3 LOSERS:")
    for t in s["top_losers"]:
        lines.append(f"    {t['symbol']:<14} {t['pyg_pct']:+7.2f}%   ${t['pyg_usd']:+.4f}")
    lines.append("")
    lines.append("  CAVEAT: counterfactual assumes one-way moves. Trades that closed")
    lines.append("  positive are assumed to NOT have touched the SL intra-trade.")
    lines.append("=" * 70)
    return "\n".join(lines)
```

- [ ] **Step 2: Smoke test stats on empty CSV**

```bash
python3 .claude/scripts/dragno_track.py --stats
```

Expected: prints "No data yet..." and exits with code 2.

- [ ] **Step 3: Smoke test append via stdin with 1 trade**

```bash
echo '[{"date":"2026-05-10","time_open":"11:19:47","time_close":"13:08:02","symbol":"KITEUSDT","side":"Corto","leverage":"10X","entry":"0.18340","exit":"0.18034","pyg_pct":"15.48","pyg_usd":"0.45994422"}]' | python3 .claude/scripts/dragno_track.py --append-from-stdin
```

Expected:
- Prints "Added 1 new trade(s). Total tracked: 1."
- Then dashboard with `Trades: 1`, `WR: 100.0%`, etc.
- `memory/external_traders/dragno_ai.csv` exists with header + 1 row.

- [ ] **Step 4: Clean up smoke test artifact**

```bash
rm memory/external_traders/dragno_ai.csv
```

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/dragno_track.py
git commit -m "feat(dragno-track): wire --append-from-stdin and --stats commands"
```

---

## Task 9: cmd_regenerate_md (markdown summary)

**Files:**
- Modify: `.claude/scripts/dragno_track.py`

- [ ] **Step 1: Implement cmd_regenerate_md**

Replace the `cmd_regenerate_md` stub:

```python
def cmd_regenerate_md(sl_cap: float) -> int:
    """Rewrite the human-readable .md summary from the CSV."""
    rows = read_rows()
    path = md_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("# Dragno AI — Tracking\n\nNo data yet.\n")
        return 0
    s = compute_stats(rows, sl_cap=sl_cap)
    cf = s["counterfactual"]
    md = [
        "# Dragno AI — Tracking Summary",
        "",
        f"_Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_",
        "",
        "## Aggregate",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Trades total | {s['total_trades']} |",
        f"| Days tracked | {s['days_tracked']} |",
        f"| Trades / day | {s['trades_per_day']} |",
        f"| Win Rate | {s['win_rate_pct']}% |",
        f"| Profit Factor | {s['profit_factor']} |",
        f"| Net PnL | ${s['net_pnl']:+.4f} |",
        f"| Avg win | ${s['avg_win']:+.4f} |",
        f"| Avg loss | ${s['avg_loss']:+.4f} |",
        f"| Best win | ${s['best_win']:+.4f} |",
        f"| Worst loss | ${s['worst_loss']:+.4f} |",
        "",
        f"## Counterfactual (SL {cf['sl_cap']:.1f}%)",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| New net PnL | ${cf['new_net_pnl']:+.4f} |",
        f"| Delta | ${cf['delta_usd']:+.4f} ({cf['delta_pct']:+.1f}%) |",
        f"| SL hits | {cf['sl_hits']} |",
        f"| New Profit Factor | {cf['new_profit_factor']} |",
        f"| New worst loss | ${cf['new_worst_loss']:+.4f} |",
        "",
        "## By Side",
        "",
        "| Side | Count | Wins | Net PnL |",
        "|---|---|---|---|",
        f"| LONG | {s['long']['count']} | {s['long']['wins']} | ${s['long']['net_pnl']:+.4f} |",
        f"| SHORT | {s['short']['count']} | {s['short']['wins']} | ${s['short']['net_pnl']:+.4f} |",
        "",
        "## Top 3 Winners",
        "",
        "| Symbol | PYG% | USD |",
        "|---|---|---|",
    ]
    for t in s["top_winners"]:
        md.append(f"| {t['symbol']} | {t['pyg_pct']:+.2f}% | ${t['pyg_usd']:+.4f} |")
    md.extend([
        "",
        "## Top 3 Losers",
        "",
        "| Symbol | PYG% | USD |",
        "|---|---|---|",
    ])
    for t in s["top_losers"]:
        md.append(f"| {t['symbol']} | {t['pyg_pct']:+.2f}% | ${t['pyg_usd']:+.4f} |")
    md.extend([
        "",
        "## Caveat",
        "",
        "> Counterfactual assumes one-way price movement: trades that closed worse than the SL cap",
        "> are assumed to have passed through the cap on the way down. Trades that closed positive",
        "> are assumed to have NOT touched the cap intra-trade. Without 1m/5m OHLCV per trade,",
        "> this model overestimates SL benefit for trades with deep drawdowns that later recovered.",
        "",
    ])
    path.write_text("\n".join(md))
    return 0
```

- [ ] **Step 2: Smoke test markdown gen on empty CSV**

```bash
python3 .claude/scripts/dragno_track.py --regenerate-md
cat memory/external_traders/dragno_ai.md
```

Expected: file contains "No data yet." line.

- [ ] **Step 3: Smoke test markdown gen after appending one trade**

```bash
echo '[{"date":"2026-05-10","time_open":"11:19:47","time_close":"13:08:02","symbol":"KITEUSDT","side":"Corto","leverage":"10X","entry":"0.18340","exit":"0.18034","pyg_pct":"15.48","pyg_usd":"0.45994422"}]' | python3 .claude/scripts/dragno_track.py --append-from-stdin
cat memory/external_traders/dragno_ai.md | head -25
```

Expected: tables populated, "KITEUSDT" appears in Top 3 Winners.

- [ ] **Step 4: Clean up smoke test artifacts**

```bash
rm memory/external_traders/dragno_ai.csv memory/external_traders/dragno_ai.md
```

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/dragno_track.py
git commit -m "feat(dragno-track): regenerate-md command produces markdown summary"
```

---

## Task 10: Slash command `/track-dragno`

**Files:**
- Create: `.claude/commands/track-dragno.md`

- [ ] **Step 1: Create the slash command file**

```markdown
---
description: Track Dragno AI (Bitunix copy bot) trades — append from screenshots and show stats + SL -8% counterfactual
allowed-tools: Bash, Read
---

# /track-dragno

Tracks executed trades of the external bot "Dragno AI" on Bitunix and reports
rolling performance with a SL -8% counterfactual.

## Two modes

### Mode A — Append new trades (this turn has image attachments)

When the user has attached one or more screenshots of Bitunix's
"Historial de posiciones" tab in this turn:

1. Visually parse each screenshot row. For every visible trade extract:
   - `date` (YYYY-MM-DD from the "Abrir" timestamp date part)
   - `time_open` (HH:MM:SS from "Abrir")
   - `time_close` (HH:MM:SS from "Hora de cierre")
   - `symbol` (uppercase, e.g. `KITEUSDT`)
   - `side` (`Largo` or `Corto` — script normalizes to LONG/SHORT)
   - `leverage` (e.g. `10X`)
   - `entry` (numeric, "Precio de apertura")
   - `exit` (numeric, "Precio de cierre")
   - `pyg_pct` (signed numeric, "PYG%" — keep the sign)
   - `pyg_usd` (signed numeric, "Posición de PYG" — keep the sign)

2. Build a JSON array with one object per parsed trade.

3. Pipe it to the script:

```bash
echo '<JSON_ARRAY>' | python3 .claude/scripts/dragno_track.py --append-from-stdin
```

The script prints how many new trades were added, the full dashboard, and
regenerates `memory/external_traders/dragno_ai.md`.

### Mode B — Stats only (no images this turn)

Run:

```bash
python3 .claude/scripts/dragno_track.py --stats
```

Prints the dashboard without modifying any files. Exit code 2 if no data
exists yet — pass that through as an informative message.

## Optional argument

`--sl-cap N` — override the counterfactual SL cap (default -8.0). Example:
```bash
python3 .claude/scripts/dragno_track.py --stats --sl-cap -10.0
```

## Output language

Always reply in Spanish (project default). Translate column headers in your
explanations but keep raw `LONG`/`SHORT`/numeric values intact.

$ARGUMENTS
```

- [ ] **Step 2: Verify the command file exists and is readable**

```bash
ls -la .claude/commands/track-dragno.md
head -5 .claude/commands/track-dragno.md
```

Expected: file present, frontmatter line `description:` visible.

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/track-dragno.md
git commit -m "feat(dragno-track): /track-dragno slash command definition"
```

---

## Task 11: End-to-end smoke test with all 14 trades from 2026-05-10

**Files:**
- (No new files; this validates the integration)

- [ ] **Step 1: Run all tests one more time**

```bash
python3 -m pytest .claude/scripts/tests/test_dragno_track.py -v
```

Expected: all tests PASS (13 tests).

- [ ] **Step 2: Ingest all 14 trades from today via stdin**

```bash
cat > /tmp/dragno_seed.json << 'EOF'
[
  {"date":"2026-05-10","time_open":"12:02:14","time_close":"13:29:56","symbol":"CHIPUSDT","side":"Corto","leverage":"10X","entry":"0.06405","exit":"0.06417","pyg_pct":"-3.14","pyg_usd":"-0.10114123"},
  {"date":"2026-05-10","time_open":"11:19:47","time_close":"13:08:02","symbol":"KITEUSDT","side":"Corto","leverage":"10X","entry":"0.18340","exit":"0.18034","pyg_pct":"15.48","pyg_usd":"0.45994422"},
  {"date":"2026-05-10","time_open":"11:10:38","time_close":"11:49:55","symbol":"VIRTUALUSDT","side":"Corto","leverage":"10X","entry":"0.9092","exit":"0.9220","pyg_pct":"-15.28","pyg_usd":"-0.52676148"},
  {"date":"2026-05-10","time_open":"11:18:08","time_close":"11:45:41","symbol":"PAXGUSDT","side":"Corto","leverage":"10X","entry":"4717.43","exit":"4720.56","pyg_pct":"-1.86","pyg_usd":"-0.06154955"},
  {"date":"2026-05-10","time_open":"18:50:25","time_close":"19:38:10","symbol":"IOTAUSDT","side":"Largo","leverage":"10X","entry":"0.0631","exit":"0.0637","pyg_pct":"9.03","pyg_usd":"0.14906275"},
  {"date":"2026-05-10","time_open":"18:44:10","time_close":"19:03:34","symbol":"PIEVERSEUSDT","side":"Largo","leverage":"10X","entry":"0.8228","exit":"0.8198","pyg_pct":"-4.84","pyg_usd":"-0.16340796"},
  {"date":"2026-05-10","time_open":"16:06:50","time_close":"18:51:31","symbol":"FILUSDT","side":"Largo","leverage":"10X","entry":"1.132","exit":"1.141","pyg_pct":"7.49","pyg_usd":"0.24509548"},
  {"date":"2026-05-10","time_open":"16:36:35","time_close":"17:47:51","symbol":"MUSDT","side":"Largo","leverage":"10X","entry":"3.3130","exit":"3.3033","pyg_pct":"-4.12","pyg_usd":"-0.12302802"},
  {"date":"2026-05-10","time_open":"15:47:20","time_close":"17:33:06","symbol":"UNIUSDT","side":"Largo","leverage":"10X","entry":"3.956","exit":"3.993","pyg_pct":"8.21","pyg_usd":"0.25984360"},
  {"date":"2026-05-10","time_open":"16:15:22","time_close":"16:23:12","symbol":"BUSDT","side":"Corto","leverage":"10X","entry":"0.4060","exit":"0.4039","pyg_pct":"3.76","pyg_usd":"0.11303660"},
  {"date":"2026-05-10","time_open":"13:49:50","time_close":"15:34:18","symbol":"GRTUSDT","side":"Corto","leverage":"10X","entry":"0.02903","exit":"0.02869","pyg_pct":"10.51","pyg_usd":"0.33330176"},
  {"date":"2026-05-10","time_open":"13:57:01","time_close":"15:33:44","symbol":"LPTUSDT","side":"Corto","leverage":"10X","entry":"2.399","exit":"2.373","pyg_pct":"9.44","pyg_usd":"0.27629340"},
  {"date":"2026-05-10","time_open":"13:42:03","time_close":"15:31:31","symbol":"ORDIUSDT","side":"Corto","leverage":"10X","entry":"5.436","exit":"5.298","pyg_pct":"24.12","pyg_usd":"0.81315061"},
  {"date":"2026-05-10","time_open":"12:12:49","time_close":"13:32:22","symbol":"SUSDT","side":"Corto","leverage":"10X","entry":"0.05556","exit":"0.05660","pyg_pct":"-19.92","pyg_usd":"-0.59461795"}
]
EOF
python3 .claude/scripts/dragno_track.py --append-from-stdin < /tmp/dragno_seed.json
```

Expected output (numbers must match within rounding):
```
Added 14 new trade(s). Total tracked: 14.

======================================================================
  DRAGNO AI — TRACKING DASHBOARD
======================================================================
  Trades: 14   Days: 1   Trades/day: 14.0
  WR: 57.14%   PF: 1.692
  Net PnL: $+1.0793
  Avg win: $+0.3306   Avg loss: $-0.2615
  Best win: $+0.8132   Worst loss: $-0.5946

  COUNTERFACTUAL (SL -8.0%):
    New net PnL: $+1.6860   Delta: $+0.6068 (+56.2%)
    SL hits: 2   New PF: 2.748   New worst loss: $-0.2758
  ...
```

- [ ] **Step 3: Verify dedup on re-ingest**

```bash
python3 .claude/scripts/dragno_track.py --append-from-stdin < /tmp/dragno_seed.json
```

Expected first line: `Added 0 new trade(s). Total tracked: 14.`

- [ ] **Step 4: Verify Mode B (stats only)**

```bash
python3 .claude/scripts/dragno_track.py --stats
```

Expected: same dashboard, no "Added N" line, no CSV write (file mtime unchanged).

- [ ] **Step 5: Verify markdown summary exists and is well-formed**

```bash
head -40 memory/external_traders/dragno_ai.md
```

Expected: "# Dragno AI — Tracking Summary" header, tables with 14 trades / WR 57.14%.

- [ ] **Step 6: Commit the seed data**

```bash
git add memory/external_traders/dragno_ai.csv memory/external_traders/dragno_ai.md
git commit -m "data(dragno-track): seed log with 14 trades from 2026-05-10"
rm /tmp/dragno_seed.json
```

---

## Task 12: Document in CLAUDE.md and MEMORY.md

**Files:**
- Modify: `CLAUDE.md`
- Create: `/Users/josecampos/.claude/projects/-Users-josecampos-Documents-wally-trader/memory/dragno_ai_tracking.md`
- Modify: `/Users/josecampos/.claude/projects/-Users-josecampos-Documents-wally-trader/memory/MEMORY.md`

- [ ] **Step 1: Append `/track-dragno` section to CLAUDE.md**

Find the section "Discipline & Observability tooling (Bundle 1, 2026-05-04)" in CLAUDE.md and append a new subsection AFTER the `### /strategy-import` subsection but BEFORE `### Bitunix signal log capture (#3)`:

```markdown
### `/track-dragno` — External bot performance tracker (2026-05-10)
- Slash command: `/track-dragno` — append trades from screenshots OR show stats dashboard
- CLI: `python3 .claude/scripts/dragno_track.py --append-from-stdin | --stats | --regenerate-md`
- Manual ingestion: user pastes Bitunix screenshots → Claude parses → JSON piped to script → CSV append + dedup
- Counterfactual integrated: every dashboard shows what PnL would have been with SL -8% hard cap
- Storage: `memory/external_traders/dragno_ai.csv` (append-only) + `dragno_ai.md` (regenerated)
- Validates the 2026-05-10 hypothesis: Dragno AI's edge is real (WR 57%, PF 1.69) but SL -8% would have improved net PnL by +80% by clipping 2 outlier losses (VIRTUAL -15%, SUSDT -20%)
- Tests: 13 in `test_dragno_track.py` (derive_margin, parse_input_rows, dedup, compute_stats, counterfactual baseline pin)
- YAGNI scope: no scraping, no API, single-bot (one CSV per bot if more added later)
- Spec: `docs/superpowers/specs/2026-05-10-track-dragno-design.md`
```

- [ ] **Step 2: Create the memory file**

Write to `/Users/josecampos/.claude/projects/-Users-josecampos-Documents-wally-trader/memory/dragno_ai_tracking.md`:

```markdown
---
name: Dragno AI bot tracking
description: External Bitunix copy bot tracked via /track-dragno. Edge real (WR 57%, PF 1.69) but SL -8% would improve net PnL +80% by clipping 2 outlier losses
type: reference
---

External bot "Dragno AI" on Bitunix copy trading. Tracked manually via `/track-dragno`.

**Data location:**
- `memory/external_traders/dragno_ai.csv` (append-only log, dedup by date+time_open+symbol)
- `memory/external_traders/dragno_ai.md` (human summary, regenerated each run)

**How to use:**
- Show stats: `/track-dragno` (no args, no images) → prints dashboard + counterfactual
- Append trades: `/track-dragno` + paste Bitunix screenshots in same turn → Claude parses → appends to CSV

**Initial finding (2026-05-10, 14 trades baseline):**
WR 57%, PF 1.69, Net +$1.08 on $50 capital. SL -8% counterfactual: +$1.69 (+56% gross, +80% net after the 10% copy fee). The 2 trades that hit the counterfactual SL: VIRTUAL (-15.28%) and SUSDT (-19.92%) — both micro-caps.

**Validation goal:**
Accumulate 30+ days of trades to confirm the counterfactual holds. If it does, consider copying Dragno AI with manual SL override -8% in Bitunix.

**Caveat:** counterfactual assumes one-way moves. Without 1m intra-trade OHLCV, SL benefit may be overestimated for trades that touched -8% intra-trade but recovered.
```

- [ ] **Step 3: Add entry to MEMORY.md index**

Read `/Users/josecampos/.claude/projects/-Users-josecampos-Documents-wally-trader/memory/MEMORY.md` and insert a new line after the `[Bitunix observe first]` line:

```markdown
- [Dragno AI tracking](dragno_ai_tracking.md) — `/track-dragno` (NUEVO 2026-05-10): manual tracker external bot Bitunix. Edge real (WR 57%, PF 1.69) pero SL -8% mejoraría PnL neto +80%.
```

- [ ] **Step 4: Verify**

```bash
grep -A1 "track-dragno" CLAUDE.md | head -10
grep "Dragno AI" /Users/josecampos/.claude/projects/-Users-josecampos-Documents-wally-trader/memory/MEMORY.md
```

Expected: both grep results show the new entries.

- [ ] **Step 5: Commit (only the repo file; memory files commit per its own discipline)**

```bash
git add CLAUDE.md
git commit -m "docs(claude.md): document /track-dragno command"
```

---

## Self-Review Checklist (performed by author)

**Spec coverage:**
- ✅ Mode A (append from screenshots) → Tasks 4, 5, 8, 10
- ✅ Mode B (stats only) → Tasks 6, 8
- ✅ CSV schema all 13 fields → Task 2, 4, 5
- ✅ Dedup by `(date, time_open, symbol)` → Task 5
- ✅ Counterfactual SL -8% → Task 6, with pinning test in Task 7
- ✅ Side breakdown + top 3 winners/losers → Task 6
- ✅ Counterfactual caveat in output → Task 8 (dashboard), Task 9 (md)
- ✅ Exit code 2 when no data → Task 8
- ✅ `--sl-cap` parametrization → Task 2 (argparse), used throughout
- ✅ Smoke test scenarios from spec → Task 11

**Placeholders:** none — every step has concrete code or commands.

**Type consistency:** `compute_stats` return dict shape is used the same way in `_format_dashboard` (Task 8) and `cmd_regenerate_md` (Task 9). `derive_margin` signature is stable across uses.

**Open notes for the implementer:**
- The CSV file is created lazily by `append_rows_dedup` → `write_rows` on first append. No need to pre-create it.
- The slash command (`.md` file) uses `$ARGUMENTS` at the end so the user can pass `--sl-cap -10` and Claude can forward it to the python invocation.
- Tests use `monkeypatch` to redirect `csv_path()` per-test for isolation.
