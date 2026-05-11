# `/track-dragno` — External Bot Performance Tracker (Design)

**Date:** 2026-05-10
**Status:** Draft
**Author:** wally-trader project
**Profile:** bitunix (external bot validation)

## Context

The user is evaluating **Dragno AI**, an external copy-trading bot on Bitunix. On 2026-05-10
the bot executed 14 trades over ~7 hours producing +1.9% net on $50 capital (WR 57%, PF 1.69).
A counterfactual analysis showed that **applying a hard SL at -8% would have increased net
PnL by +80%** by clipping two outlier losses (VIRTUAL -15.28%, SUSDT -19.92%).

This spec captures a minimal tracking system to validate that insight over time, using
manually-submitted screenshots from the Bitunix UI as the data source.

## Goals

1. Persist Dragno AI's executed trades into a structured CSV for longitudinal analysis.
2. On every invocation, recompute rolling performance stats and the SL -8% counterfactual.
3. Stay fully manual (no scraping, no API) — Bitunix does not expose copy-trader stats
   programmatically, and the user prefers manual capture.

## Non-Goals (YAGNI)

- ❌ Automatic polling of the Bitunix website
- ❌ Multi-bot generalization (one CSV per bot if a second is ever added)
- ❌ Real-time notifications
- ❌ Auto-execution of trades based on the bot's signals
- ❌ Intra-trade OHLCV reconstruction (only entry/exit known; one-way move assumed)

## User Flow

### Mode A — Append new trades
```
Usuario: /track-dragno
         [drag-drops screenshots of Bitunix "Historial de posiciones" tab]

Claude:  1. Reads screenshots (multimodal vision).
         2. Extracts rows: symbol, side, leverage, entry, exit, pyg_pct, pyg_usd, time_open, time_close.
         3. Deduplicates against existing CSV (composite key: time_open + symbol).
         4. Appends only new rows.
         5. Regenerates dragno_ai.md summary.
         6. Prints: "Added N new trades. Total tracked: X trades over Y days."
```

### Mode B — Stats only (no screenshots in turn)
```
Usuario: /track-dragno

Claude:  1. Reads CSV.
         2. Computes stats (see "Reported Metrics" below).
         3. Prints dashboard.
         4. Does NOT modify the CSV.
```

Detection rule: if the current conversation turn includes one or more image attachments,
treat as Mode A. Otherwise Mode B.

## File Layout

```
.claude/commands/track-dragno.md           # Slash command frontmatter + instructions
.claude/scripts/dragno_track.py            # CLI: parse, append, dedup, stats, counterfactual
memory/external_traders/dragno_ai.csv      # Append-only log (one row per trade)
memory/external_traders/dragno_ai.md       # Human-readable summary (regenerated on each run)
```

The `memory/external_traders/` directory is new and dedicated to tracking external
traders/bots. Future expansion (other bots) follows the same `<name>.csv` + `<name>.md`
pattern but is out of scope for this spec.

## CSV Schema

```csv
date,time_open,time_close,symbol,side,leverage,entry,exit,pyg_pct,pyg_usd,margin_est,duration_min,source
```

Field definitions:

| Field | Type | Notes |
|---|---|---|
| `date` | YYYY-MM-DD | Date of opening (CR timezone, UTC-6) |
| `time_open` | HH:MM:SS | From "Abrir" column |
| `time_close` | HH:MM:SS | From "Hora de cierre" column |
| `symbol` | string | e.g. `KITEUSDT` (preserve uppercase) |
| `side` | `LONG` or `SHORT` | Translated from `Largo`/`Corto` |
| `leverage` | int | e.g. `10` |
| `entry` | float | "Precio de apertura" |
| `exit` | float | "Precio de cierre" |
| `pyg_pct` | float | Signed percentage from "PYG%" |
| `pyg_usd` | float | Signed USD from "Posición de PYG" |
| `margin_est` | float | Derived: `abs(pyg_usd) / (abs(pyg_pct)/100)` |
| `duration_min` | int | `time_close - time_open` in minutes |
| `source` | string | `manual_screenshot` (always for this version) |

Dedup key: `(date, time_open, symbol)`. If a row with the same key already exists,
skip it silently (do not overwrite — assume immutability of executed trades).

## Reported Metrics

The dashboard (printed by Mode B, and at end of Mode A) shows:

**Aggregate (all-time):**
- Trades total, days tracked, trades/day average
- Win Rate %
- Profit Factor
- Avg win $, Avg loss $
- Worst loss $, Best win $
- Net PnL $ (sum of `pyg_usd`) — gross, before the 10% copy-trading fee

**Counterfactual (SL -8% hard cap):**
- New PnL $ if all trades worse than -8% had closed at exactly -8%
- Delta $ and Delta %
- Number of trades that would have triggered SL

**Per-side breakdown:**
- LONG: count, WR, net PnL
- SHORT: count, WR, net PnL

**Top 3 winners / Top 3 losers** (by `pyg_usd`).

## Counterfactual Model Caveats (documented in output)

Each dashboard footer includes this disclaimer:

> Counterfactual assumes one-way price movement: trades that closed worse than -8%
> are assumed to have passed through -8% on the way down. Trades that closed positive
> are assumed to have NOT touched -8% intra-trade. Without 1m/5m OHLCV per trade,
> this model overestimates SL benefit for trades with deep drawdowns that later recovered.
> Validate periodically against intra-trade data when possible.

## Slash Command Definition

`.claude/commands/track-dragno.md`:

```markdown
---
description: Track Dragno AI (Bitunix copy bot) trades and compute stats + SL -8% counterfactual
---

# /track-dragno

If the current turn contains image attachments (Bitunix screenshots), parse them and
append new trades to `memory/external_traders/dragno_ai.csv` via
`python3 .claude/scripts/dragno_track.py --append-from-stdin`.

If no images, just run `python3 .claude/scripts/dragno_track.py --stats` and print
the dashboard.

After any append, regenerate `memory/external_traders/dragno_ai.md` summary via
`python3 .claude/scripts/dragno_track.py --regenerate-md`.

Parser instructions:
- Each screenshot shows the "Historial de posiciones" tab of a Bitunix copy-trader profile.
- Extract: symbol (e.g. CHIPUSDT), side (Largo→LONG, Corto→SHORT), leverage (10X→10),
  precio de apertura, precio de cierre, PYG%, Posición de PYG (USDT), Abrir time, Hora de cierre.
- Pass parsed rows as JSON array to dragno_track.py via stdin.
- Dedup is handled by the script.

Output: human-readable summary in Spanish (default project language).
```

## Python Helper API

`.claude/scripts/dragno_track.py` exposes three subcommands:

```bash
# Append from JSON stdin (Claude pipes parsed rows here)
python3 .claude/scripts/dragno_track.py --append-from-stdin

# Compute and print stats dashboard
python3 .claude/scripts/dragno_track.py --stats

# Regenerate the human-readable .md file from current CSV
python3 .claude/scripts/dragno_track.py --regenerate-md

# Optional: backtest with custom SL (default -8.0)
python3 .claude/scripts/dragno_track.py --stats --sl-cap -10.0
```

Exit codes:
- `0` — success
- `1` — CSV malformed / parse error
- `2` — no data yet (CSV empty or missing) when stats requested

## Testing Plan

Manual smoke test on initial deployment:

1. Run `/track-dragno` with today's 14 trades (already in conversation history) →
   verify CSV has 14 rows, stats match earlier hand-computed numbers
   (WR 57%, PF 1.69, +$1.08 realized).
2. Run `/track-dragno` again with NO screenshots → verify Mode B prints same stats
   and CSV is unchanged.
3. Re-submit the same 14 screenshots → verify dedup (0 new rows added).
4. Compare counterfactual delta to today's hand-computed +80% → must match within
   rounding (`new_realized` ≈ +$1.69, `delta` ≈ +$0.61).

Automated test (pytest) optional, only if usage grows: `tests/test_dragno_track.py`
with fixtures for parse/dedup/stats. Not required for v1.

## Risks & Open Questions

| Risk | Mitigation |
|---|---|
| Screenshot OCR may misread small numbers | Visual parsing by Claude is reliable for tabular UI; flag low-confidence values in append summary |
| User forgets to track for several days | Acceptable — system tolerates gaps |
| Bitunix changes UI / column names | Parser instructions in slash command reference column headers; update in one place if changed |
| Trades on the same symbol with identical `time_open` but different positions | Theoretically possible if bot opens 2 positions same second; dedup key needs `time_close` added if it happens. Address only when observed. |

## Decisions Log

- **Manual screenshot input** chosen over scraping (no public Bitunix copy-trader URL discovered) or API (Bitunix has no public API for copy-trading stats).
- **CSV over JSON** for the log: simpler diff, grep-friendly, fits trading_log.md project conventions.
- **One file per bot** instead of unified schema: avoids over-engineering. If a 2nd bot is tracked, the same script can be parameterized via `--bot dragno_ai`.
- **No commit hooks / launchd cron**: invocation is always manual by user, matching the manual data input flow.

## Out of Scope (Explicitly Deferred)

- Cross-bot comparison dashboard (`/track-bots compare`)
- Auto-fetch from Bitunix when/if they expose an API
- Side-by-side comparison vs `/punk-hunt` self-generated setups for the same day
- Notification on streak (e.g. "Dragno AI on 5-loss streak — pause copy?")

These are reasonable future extensions but not part of v1.
