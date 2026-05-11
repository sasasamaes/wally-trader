# Live Insights Bundle (2026-05-10) — Design

**Date:** 2026-05-10
**Status:** Draft
**Source:** Live stream by Dragno community master (YouTube `Be8IYJLgdYA`, 25 min, 2026-05-10)
**Author:** wally-trader project

## Context

The Dragno community live laid out a coherent multi-asset macro framework that wally-trader
partially implements. Five concrete gaps were identified:

1. **USDT.D dominance** is used by the master as a leading inverse signal for BTC — wally
   does not track it.
2. **Macro-event aversion** extends 2-3 days before high-impact releases — wally's gate is
   ±30 min HARD + ±4h WARN only.
3. **Price/volume divergence** is the master's core veto ("subiendo sin fuerza, no es
   creíble") — wally has a `divergence-analysis` skill but no programmatic pre-entry check.
4. **MUGRES (micro-cap memecoins)** are the master's go-to on uncertain macro days because
   they decouple from BTC — wally's `/punk-hunt --tier-0` exists but is not auto-triggered.
5. **Fib extension exhaustion** (150%/200% weekly extension) is the master's standard
   profit-taking / fade trigger for indices — wally has the `fibonacci-tools` skill but no
   programmatic alert.

This bundle implements all five as small, composable improvements following the existing
"Discipline & Observability Bundle" pattern from 2026-05-04.

## Goals

For each gap, deliver a minimal helper + integration into an existing agent or command.
No new agents. No new slash commands beyond what's strictly necessary.

## Non-Goals (YAGNI)

- ❌ Replicating the master's full discretionary process (we add signals, not replace edge)
- ❌ Auto-trading on these signals (everything is informational / guard)
- ❌ Multi-broker support (Bitunix only for asset-specific helpers)
- ❌ Real-time WebSocket streams (REST + cache is sufficient)
- ❌ Backtesting these features over historical data (would be valuable but out of scope here)

## Feature A — USDT.D Inverse-Correlation Tracker

**Insight:** Master tracks USDT.D 4H + daily oscillator. USDT.D losing trendline = capital
rotating out of stables = bullish BTC. USDT.D X reversal pattern = bearish BTC.

**Implementation:**
- New script `.claude/scripts/usdtd_tracker.py`
- Pulls USDT.D price via CoinGecko (no auth required, free tier)
- Computes: current value, 24h change, 7d change, simple trend label (`UP`/`DOWN`/`FLAT`)
- Optional: pull Bitcoin Dominance (BTC.D) for context
- CLI: `python3 .claude/scripts/usdtd_tracker.py [--json] [--quick]`

**Integration:**
- `regime-detector` agent reads USDT.D label and adds a `usdtd_bias` field to its output
- `signal-validator` agent: if signal direction conflicts with USDT.D bias by 7-day trend
  (e.g. LONG signal but USDT.D 7d UP), surface as **WARN** (not block)

**Output schema (JSON):**
```json
{
  "ts": "2026-05-10T20:45:00-06:00",
  "usdtd": 6.92,
  "change_24h_pct": 0.15,
  "change_7d_pct": -0.42,
  "trend_label": "DOWN",
  "btcd": 58.31,
  "btc_inverse_bias": "BULLISH"
}
```

**Exit codes:** 0=OK, 2=stale_data, 1=error.

## Feature B — Macro Soft-Blackout (Multi-Tier)

**Insight:** Master refuses serious trading 2-3 days before FOMC / CPI / NFP. Wally's
`macro_gate.py` only has HARD (±30 min) and WARN (±4h via `--next-events --days 1`).

**Implementation:**
- Extend `.claude/scripts/macro_gate.py` with a new subcommand `--check-tier`
- Returns one of: `OK` | `SOFT` | `WARN` | `HARD`
- Tier definitions:
  - `HARD`: within ±30 min of high-impact event (existing logic)
  - `WARN`: within ±4 hours
  - `SOFT`: within next 48 hours (i.e., we're 2 days out)
  - `OK`: nothing high-impact in next 48 hours

**Integration:**
- `trade-validator` and `signal-validator` agents: read tier before 4-filter validation
  - `HARD` → NO-GO (existing)
  - `WARN` → WARN reduce size 50%
  - `SOFT` → INFO message, suggest tier-0 MUGRES alternative
  - `OK` → proceed normally

**Output (JSON):**
```json
{
  "tier": "SOFT",
  "next_event": {
    "name": "FOMC Rate Decision",
    "country": "US",
    "datetime_cr": "2026-05-13T13:00:00-06:00",
    "hours_until": 41.2
  },
  "recommended_action": "reduce_size_or_use_tier_0_mugres"
}
```

## Feature C — Volume/Oscillator Divergence Pre-Entry Check

**Insight:** Master's repeated veto: "el precio sube sin fuerza, el oscilador cae → no es
creíble". When price rises but volume oscillator drops, the move is not backed by genuine
flow.

**Implementation:**
- New script `.claude/scripts/volume_divergence.py`
- Pulls 50 bars of OHLCV (configurable timeframe, default 1H) from Binance public API
- Computes:
  - Price change pct over last N bars (default 10)
  - Volume change pct over last N bars
  - OBV (On-Balance Volume) slope
  - Divergence flag if `(price_slope > 0 AND obv_slope < 0)` or inverse
- CLI: `python3 .claude/scripts/volume_divergence.py --symbol BTCUSDT [--tf 1h] [--bars 50]`

**Integration:**
- `trade-validator` agent: as a FASE 0.7 (after `session_quality` FASE 0.5, before 4-filter)
  - Divergence detected against the proposed direction → **WARN** (size 50%)
  - No divergence → silent
  - Insufficient data (< 30 bars) → INFO

**Output (JSON):**
```json
{
  "symbol": "BTCUSDT",
  "tf": "1h",
  "price_change_pct": 1.42,
  "volume_change_pct": -18.3,
  "obv_slope": -0.0023,
  "divergence": "BEARISH",
  "confidence": 0.74,
  "verdict": "WARN_DIVERGENCE_AGAINST_LONG"
}
```

## Feature D — Auto-MUGRE Switch on Macro SOFT Days

**Insight:** Master switches to memecoins on uncertain macro days because they decouple
from BTC. Wally has `/punk-hunt --tier-0` but it must be invoked manually.

**Implementation:**
- Modify `.claude/commands/punk-hunt.md` to instruct the agent:
  1. First run `macro_gate.py --check-tier` (depends on Feature B being implemented)
  2. If tier is `SOFT` or `WARN` AND user did not pass `--tier-0` explicitly:
     - Print INFO message: "Macro SOFT detected — auto-engaging tier-0 (MUGRES) mode"
     - Run scan with `--tier-0` flag effectively enabled
  3. If tier is `HARD`: refuse to scan at all (blackout)
  4. If tier is `OK` or user passed explicit flag: proceed as today

**No new scripts. Pure command-instructions change.**

**Behavioral test:** Force a SOFT tier (mock event 24h away) and run `/punk-hunt` → must
auto-switch to tier-0 with a printed notice.

## Feature E — Fib Extension Exhaustion Alert

**Insight:** Master flags 150% and 200% weekly Fibonacci extensions as profit-taking /
reversal zones for indices (SP500 hit 150%, NASDAQ near 200% → "ya toca corrección").

**Implementation:**
- New script `.claude/scripts/fib_extension.py`
- Takes a symbol, a timeframe (default 1W), and pulls recent OHLCV
- Auto-detects the most recent valid impulse swing (highest high → lowest low in last N bars,
  or vice versa)
- Computes Fibonacci extension levels (127.2%, 150%, 161.8%, 200%, 261.8%)
- Reports current price's position relative to those levels:
  - At/past 150% → `EXHAUSTION_MILD`
  - At/past 200% → `EXHAUSTION_HIGH`
  - At/past 261.8% → `EXHAUSTION_EXTREME`
  - Below 127.2% → `OK`
- CLI: `python3 .claude/scripts/fib_extension.py --symbol SPX --tf 1w [--bars 100]`

**Integration:**
- `morning-analyst` and `morning-analyst-ftmo` agents: append a "Fib Extension Status"
  paragraph for each watchlist asset when status != `OK`
- No automatic block — purely informational, surfaces a "fade candidate" flag

**Output (JSON):**
```json
{
  "symbol": "SPX",
  "tf": "1w",
  "swing_low": 4980,
  "swing_high": 6420,
  "current_price": 7424,
  "current_extension_pct": 169.7,
  "level_label": "EXHAUSTION_MILD",
  "next_level": {"pct": 200.0, "price": 7860}
}
```

## Cross-Feature Constraints

- All scripts must be **stdlib-only or use existing wally_core/.venv deps** (no new pips).
  Currently available: `requests`, `pandas`, `numpy`, `yt_dlp`, `xgboost`, `vaderSentiment`.
- All scripts must run in **< 5 seconds** typical case (timeout = 30 s hard).
- All scripts must support **`--quick`** mode that prints a single status line for use
  in agent prompts (matches existing helper conventions).
- All scripts must support **`--json`** for programmatic consumption.

## File Layout

```
.claude/scripts/
  usdtd_tracker.py            # Feature A
  macro_gate.py               # Feature B (modified, not new)
  volume_divergence.py        # Feature C
  fib_extension.py            # Feature E

.claude/commands/
  punk-hunt.md                # Feature D (modified)

.claude/agents/
  regime-detector.md          # Feature A wiring
  signal-validator.md         # Features A, B, C wiring
  trade-validator.md          # Features B, C wiring
  morning-analyst.md          # Feature E wiring
  morning-analyst-ftmo.md     # Feature E wiring

.claude/scripts/tests/
  test_usdtd_tracker.py
  test_macro_gate.py          # extend existing
  test_volume_divergence.py
  test_fib_extension.py
```

## Test Strategy

- Each new helper has ≥ 3 unit tests (happy path, edge case, error).
- Mock HTTP responses with `responses` library if available, otherwise inject a `_fetcher`
  callable for testability.
- For Feature B (macro_gate extension), reuse the existing test fixtures pattern.
- For Feature D, no automated test — manual smoke test only (verify the SOFT tier branch
  triggers the tier-0 default).

## Rollout / Backward Compatibility

- Features are **additive**. No existing behavior is removed.
- Agents reading new fields gracefully handle missing data (every helper exits 0 even on
  network failure, with a documented `stale=true` flag).
- The `--check-tier` subcommand in `macro_gate.py` is new; existing `--check-now` and
  `--next-events` remain unchanged.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| CoinGecko rate limits (Feature A) | Cache USDT.D for 10 min in `.claude/cache/usdtd.json` |
| Binance API blocked (Feature C) | Fallback to OKX public API; on dual failure return `INFO_NO_DATA` |
| False-positive divergence in chop (Feature C) | Require `volume_change_pct` < -10% to trigger (not just OBV slope) |
| Fib auto-swing detects wrong swing (Feature E) | Always print the detected swing in output so user can sanity-check; mark `confidence: low` if swing range < 5% |
| Feature D auto-MUGRE surprises user | Print explicit INFO line every time it engages; users can override with `--no-auto` flag |

## Decisions Log

- **One bundle spec** (not 5 separate) since features share theme (live insights) and
  follow the same agent-integration pattern. Matches the existing 2026-05-04 bundle precedent.
- **No new slash commands.** Reuses `regime-detector`, `morning-analyst`, `trade-validator`,
  `signal-validator`, `punk-hunt`. Less surface to maintain.
- **No backtesting in this bundle.** These features are guardrails, not strategies. A
  separate effort could backtest the WARN/SOFT thresholds in 30 days.
- **Feature B's SOFT tier = 48 hours.** Master mentioned "2-3 days" but 48h is a safe lower
  bound that doesn't choke off too much trading. Configurable via `--soft-hours` flag.

## Open Questions (Resolved by user)

- **Q: USDT.D source?** A: CoinGecko (free, no auth, well-documented JSON).
- **Q: Should SOFT tier suggest MUGRES even in retail profile?** A: No — keep MUGRES
  suggestion bitunix-only; retail gets a plain "consider reducing size or skipping".
- **Q: Fib extension auto-detect swing or require user input?** A: Auto-detect for now;
  log the detected swing for sanity check.

## Out of Scope (Explicitly Deferred)

- Backtesting WARN/SOFT thresholds vs hold-out PnL
- Multi-exchange consensus for Feature C divergence
- Daily/weekly USDT.D delta alerts via macOS notify
- Cross-asset correlation auto-detection (which assets decouple from BTC and which don't)
