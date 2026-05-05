# /punk-smart v2 — Higher win rate + lower DD

**Author:** Francisco Campos
**Date:** 2026-05-05
**Status:** Design (pending implementation plan)
**Profile:** bitunix
**Prior art:** `.claude/scripts/punk_smart_router.py` v1 (2026-05-04), `backtest_regime_matrix.py`, `regime_mapping.json` v1

## Problem

The current `/punk-smart` router selects, for each market regime, the strategy with the highest aggregate PnL across all assets. Backtest baseline reports WR 49.4%, +$157.61 over 15 days, 5.1 trades/day. Two structural weaknesses:

1. **Win rate is low for psychological/disciplinary purposes.** A 49% WR with positive expectancy is mathematically fine but produces choppy equity curves and tilt risk.
2. **Max drawdown is unmeasured and likely large.** Some regimes (MIXED, SQUEEZE, WEAK_TREND_DOWN) are only marginally +EV (pnl_per_trade between +$0.22 and +$0.63); their losing streaks contribute disproportionately to drawdown.

Live behavior also diverges from backtest: at the moment of writing this spec, `/punk-smart` returns 0 setups across 9 assets while backtest expects 5/day. The strategy entry conditions appear miscalibrated for production.

## Goals

Make `/punk-smart` produce fewer but higher-quality setups, with explicit drawdown controls. Concretely:

- **Win rate target:** ≥55% (gate minimum 53%)
- **Max-DD target:** ≤15% capital (gate minimum ≤20%)
- **Trades/day:** 3-4 (gate minimum 2.5)
- **Profit factor target:** ≥1.6 (gate minimum 1.4)
- **PnL/day target:** ≥+$8.5 (gate minimum +$6.5)

These are evaluated by running the backtest matrix on a **60-day Binance dataset** (paginated fetch — see "Backtest dataset extension" section below). The v1 baseline used 15 days; v2 extends to 60 days for more robust per-asset cell statistics.

## Non-goals

- Adding new strategies (A through E in `backtest_regime_matrix.py` remain unchanged in scope).
- Re-training the regime mapping with real user trades (only 1 historical trade in `signals_received.csv`; not enough signal). Postponed until 30+ real trades are accumulated.
- Real-time webhook integration with Bitunix exchange (no public API).
- UI changes beyond the dashboard text rendering.
- Changing the underlying regime classifier (`classify_regime` stays identical to v1).

## Architecture

`/punk-smart` becomes a five-stage pipeline. Stages 0 and 3 are gates (can reject); stages 1, 2, 4, 5 are computational. Each stage is a separate Python module so failures are isolated and rollback is granular.

```
INPUT: list of assets (24 Bitunix tradeables)
  │
  ▼
[STAGE 0] Kill-switch check (global state)
  │  └─ If active (2 SLs/4h) → EXIT "PAUSED"
  ▼
[STAGE 1] Per-asset: detect regime + lookup strategy
  │  └─ Schema v2: per-asset mapping with global fallback
  ▼
[STAGE 2] Run strategy → tentative setup (entry/SL/TP1/TP2)
  │  └─ If NO_SETUP → asset discarded, skip to next
  ▼
[STAGE 3] Veto layer (6 checks in order, first NO vetoes)
  │  ├─ 3a. Macro events ±30 min        ← skill macro_gate
  │  ├─ 3b. Asset blacklist 2-SL streak  ← state file
  │  ├─ 3c. Concurrent correlation       ← signals_received.csv open
  │  ├─ 3d. Sentiment extreme contrarian ← F&G
  │  ├─ 3e. Funding extreme contrarian   ← OKX API
  │  └─ 3f. Time-of-day weak window      ← CR 22:00-05:00 (soft veto)
  ▼
[STAGE 4] Position sizing by regime confidence
  │  └─ size_mult ∈ [0.3, 1.5] from backtest pnl_per_trade
  ▼
[STAGE 5] Annotate trailing SL hint
  │  └─ "TP1 hit → move SL to entry+0.2×ATR (not BE)"
  ▼
OUTPUT: dashboard with APPROVED setups + VETOED setups (with reason)
```

**Key architectural decisions:**

- Vetoes evaluated **before** sizing — no compute on a setup that will be rejected.
- State persists in JSON files inside the bitunix profile (`asset_sl_streaks.json`, `sl_window.json`, `kill_switch.json`). State is updated from `/log-outcome` SL events. Daily reset at CR 00:00 via launchd.
- Vetoes are **transparent**: dashboard shows vetoed setups too, with the reason. The user learns *why* setups die.
- Backwards compatible: if `regime_mapping.json` lacks `per_asset` section, router falls back to global v1 mapping. If state files don't exist, system assumes "no kill-switch / no blacklist / no open positions". Flags allow individual veto disable without code changes.
- Minimal modification of `punk_smart_router.py`. New auxiliary modules (`punk_smart_vetos.py`, `punk_smart_state.py`, `regime_confidence.py`) are imported and composed; the router orchestrates.

## Components

### C1. Per-asset regime mapping (schema v2)

Replaces the flat regime → strategy mapping with a two-tier structure: per-asset overrides preferred, global as fallback.

**File:** `.claude/scripts/regime_mapping.json`

```json
{
  "version": 2,
  "vetos_enabled": ["macro", "blacklist", "correlation", "sentiment", "funding", "time_of_day"],
  "dynamic_sizing": true,
  "trail_sl_offset_atr": 0.2,
  "global": {
    "STRONG_TREND_UP": {"strategy": "A_VWAP", "wr": 53.8, "pnl_per_trade": 2.54, "n_trades": 13},
    "RANGING":         {"strategy": "A_VWAP", "wr": 55.6, "pnl_per_trade": 2.68, "n_trades": 9},
    "MIXED":           {"strategy": "A_VWAP", "wr": 44.8, "pnl_per_trade": 0.63, "n_trades": 29},
    "SQUEEZE":         {"strategy": "B_TrendPullback", "wr": 45.5, "pnl_per_trade": 0.54, "n_trades": 11},
    "WEAK_TREND_DOWN": {"strategy": "B_TrendPullback", "wr": 53.3, "pnl_per_trade": 0.22, "n_trades": 15},
    "_disabled": ["VOLATILE", "UNKNOWN", "STRONG_TREND_DOWN", "WEAK_TREND_UP"]
  },
  "per_asset": {
    "BTCUSDT": {
      "RANGING": {"strategy": "A_VWAP", "wr": 60.0, "pnl_per_trade": 3.10, "n_trades": 5}
    }
  }
}
```

**Lookup order in router (for given asset+regime):**
1. `per_asset[asset][regime]` with `n_trades >= 10` and `pnl_per_trade > 0` → use it
2. `per_asset[asset][regime]` with `n_trades >= 10` and `pnl_per_trade <= 0` → STAND_ASIDE per-asset
3. `global[regime]` if not in `_disabled` → use global
4. Otherwise → STAND_ASIDE

**Modification to `backtest_regime_matrix.py`:**
- Add `fetch_paginated(symbol, interval, days)` to bypass the 1500-bar cap (60d × 15m = 5760 bars → 4 calls per asset per TF, with retry/backoff on Binance rate limits).
- In addition to `cells[regime][strategy]`, also populate `cells_per_asset[asset][regime][strategy]`.
- Output mapping JSON includes both `global` and `per_asset` sections.
- Per-asset cell only promoted to `per_asset[asset][regime]` if `n_trades >= 10` and `pnl_per_trade > 0` (raised threshold from 5 thanks to longer dataset).

### C2. Veto layer

Six pre-approve checks centralized in `.claude/scripts/punk_smart_vetos.py`. Each veto returns `{passed: bool, reason: str, source: str}`.

| # | Veto | Threshold | Data source | Type |
|---|---|---|---|---|
| 1 | macro events | HIGH-impact event ±30 min | `macro_gate.py --check-now` (cache) | hard |
| 2 | asset blacklist | 2 SLs in 24h on same asset | `asset_sl_streaks.json` | hard until CR 00:00 |
| 3 | concurrent correlation | Same side+bucket already open | `signals_received.csv` filtered to `outcome=open` | hard |
| 4 | sentiment contrarian | F&G ≥80 + LONG **or** F&G ≤20 + SHORT | `api.alternative.me/fng` 1h cache | hard |
| 5 | funding contrarian | Funding ≥+0.05% + LONG **or** ≤-0.05% + SHORT | OKX `public/funding-rate` 30min cache | hard |
| 6 | time-of-day weak window | Hour CR ∈ [22:00, 05:00] | local clock | soft (override if `pnl_per_trade ≥ 2.0`) |

**Family buckets for veto #3:**
```python
BUCKETS = {
  "btc_majors":  ["BTCUSDT", "ETHUSDT", "SOLUSDT", "MSTRUSDT"],
  "l1_alts":     ["AVAXUSDT", "INJUSDT", "ADAUSDT", "TRXUSDT", "LINKUSDT", "SUIUSDT", "TONUSDT", "HBARUSDT"],
  "memes":       ["DOGEUSDT", "WIFUSDT", "FARTCOINUSDT", "PEPEUSDT"],
  "small_caps":  ["XLMUSDT", "ENJUSDT", "CHZUSDT", "AXSUSDT", "SEIUSDT", "POLUSDT", "TIAUSDT", "ROSEUSDT", "RUNEUSDT"]
}
```
Rule: max 1 LONG and max 1 SHORT per bucket open simultaneously.

**Output of each veto in dashboard:**
```
#1 ETHUSDT LONG (regime: RANGING)  ❌ VETOED
   ✓ macro: clear
   ✓ blacklist: clean
   ✗ correlation: BTCUSDT LONG already open in btc_majors bucket → REJECT
```

### C3. Position sizing by regime confidence

**File:** `.claude/scripts/regime_confidence.py`

**Formula:** `size_mult = clip(pnl_per_trade / 2.0, min=0.3, max=1.5)`

Applied to base margin of $4 (2% of $200):

| Regime | BT pnl_per_trade | size_mult | Margin USD | Notional 10x |
|---|---|---|---|---|
| RANGING | +$2.68 | 1.34 | $5.36 | $53.60 |
| STRONG_TREND_UP | +$2.54 | 1.27 | $5.08 | $50.80 |
| MIXED | +$0.63 | 0.30 (cap) | $1.20 | $12.00 |
| SQUEEZE | +$0.54 | 0.30 (cap) | $1.20 | $12.00 |
| WEAK_TREND_DOWN | +$0.22 | 0.30 (cap) | $1.20 | $12.00 |

CLI: `python3 .claude/scripts/regime_confidence.py --regime RANGING --base-margin 4 --json` → `{size_mult: 1.34, margin_usd: 5.36, notional_10x: 53.60}`

If `dynamic_sizing: false` in mapping JSON, the helper short-circuits to size_mult=1.0.

### C4. State machine

**File:** `.claude/scripts/punk_smart_state.py` — read/write helper for three state files.

**`asset_sl_streaks.json`** — per-asset blacklist tracking:
```json
{
  "version": 1,
  "as_of_cr_date": "2026-05-05",
  "assets": {
    "XLMUSDT": {"sl_count": 2, "last_sl_ts": "2026-05-05T11:23", "blacklist_until": "2026-05-06T00:00"},
    "AVAXUSDT": {"sl_count": 1, "last_sl_ts": "2026-05-05T09:14", "blacklist_until": null}
  }
}
```

**Update rules:**
- `/log-outcome ASSET SL` → increment `sl_count`. If `sl_count == 2`, set `blacklist_until = next CR 00:00`.
- `/log-outcome ASSET TPx` (any TP) → reset `sl_count = 0` for that asset.
- Daily reset CR 00:00 via launchd clears the file.

**`sl_window.json`** — global kill-switch tracker:
```json
{
  "events": [
    {"ts": "2026-05-05T10:15", "asset": "ETHUSDT", "pnl_usd": -3.85},
    {"ts": "2026-05-05T11:50", "asset": "AVAXUSDT", "pnl_usd": -4.10}
  ],
  "kill_switch_active_until": "2026-05-06T00:00"
}
```

**Update rules:**
- Each SL appended to `events`.
- Auto-purge events >4h on read.
- If `len(events_within_4h) >= 2` after append, set `kill_switch_active_until = next CR 00:00`.
- Stage 0 of router reads this; if `now < kill_switch_active_until`, exit with PAUSED message.
- Manual override: `python3 .claude/scripts/punk_smart_state.py --reset-killswitch` (conscious decision, not automatic).

**State updates are triggered by `/log-outcome`.** If user forgets to log, state desynchronizes. Accepted risk; the existing watcher emits a macOS notification when an open trade has no outcome logged.

### C5. Trailing SL annotation

The system does not execute trades (manual in Bitunix). The change is in the **textual recommendation**:

**Before:**
```
ETHUSDT LONG  Entry: 2375.40  SL: 2370.20  TP1: 2382.10  TP2: 2389.50
DUREX trigger: TP1 hit → move SL to BE (2375.40)
```

**After:**
```
ETHUSDT LONG  Entry: 2375.40  SL: 2370.20  TP1: 2382.10  TP2: 2389.50
ATR(14) 15m: $5.20
DUREX trigger: TP1 hit → move SL to 2376.44 (BE + 0.2×ATR = +$1.04 lock)
```

**In the backtest:** `simulate()` in `backtest_regime_matrix.py` adopts the same rule — when TP1 hit, the SL "trails" to BE+0.2×ATR. This shifts cell stats slightly; recalibrated in v2 backtest run.

Offset is configurable via `trail_sl_offset_atr` in mapping JSON. `0.0` falls back to BE.

## File layout

```
.claude/scripts/
├── punk_smart_router.py          [MODIFIED]   v1 reorganized as 5-stage pipeline
├── punk_smart_vetos.py           [NEW]        6 vetos centralized
├── punk_smart_state.py           [NEW]        read/write state files
├── regime_confidence.py          [NEW]        sizing helper
├── backtest_regime_matrix.py     [MODIFIED]   per-asset cells + trail SL in simulate()
└── regime_mapping.json           [SCHEMA v2]  with backup as regime_mapping.v1.backup

.claude/profiles/bitunix/memory/
├── asset_sl_streaks.json         [NEW]        runtime state
└── sl_window.json                [NEW]        runtime state (includes kill_switch_active_until)

.claude/launchd/
└── com.wally.bitunix-daily-reset.plist  [NEW]   reset state files at CR 00:00

tests/punk_smart/
├── test_vetos.py                 [NEW]
├── test_state.py                 [NEW]
└── test_regime_confidence.py     [NEW]

docs/
└── backtest_findings_2026-05-05_punk_smart_v2.md  [NEW, after backtest run]
```

## Data flow

```
User invokes /punk-smart
  │
  ▼
Skill loads → dispatches to bash chain or punk-smart-analyst agent
  │
  ▼
punk_smart_router.main()
  │
  ├─ STAGE 0: punk_smart_state.is_kill_switch_active()
  │   └─ if active → print "PAUSED until X" → exit
  │
  ├─ For each asset in ASSETS_24:
  │   │
  │   ├─ STAGE 1a: fetch(asset, 15m), fetch(asset, 1h)
  │   ├─ STAGE 1b: classify_regime(bars_15m, bars_1h, last_idx)
  │   ├─ STAGE 1c: regime_info = lookup_mapping(asset, regime)
  │   │   └─ if STAND_ASIDE → record + skip
  │   │
  │   ├─ STAGE 2: setup = STRATEGY_FNS[regime_info.strategy](bars_15m, bars_1h, last_idx)
  │   │   └─ if None → record NO_SETUP + skip
  │   │
  │   ├─ STAGE 3: vetos = punk_smart_vetos.evaluate(setup, asset, side, mapping_config)
  │   │   ├─ For each enabled veto, check + collect reason
  │   │   └─ if any hard veto failed → record VETOED + skip
  │   │
  │   ├─ STAGE 4: sizing = regime_confidence.compute(regime_info, base_margin=4)
  │   │
  │   ├─ STAGE 5: trail = compute_trail_hint(setup, atr, offset_atr)
  │   │
  │   └─ Append to APPROVED list with all annotations
  │
  └─ Render dashboard:
     ├─ APPROVED setups (sorted by R:R TP2)
     ├─ VETOED setups (with reason per veto)
     ├─ NO_SETUP / STAND_ASIDE (when --show-all)
     └─ Auto-log top setup to signals_received.md/csv if APPROVED
```

## Validation

### Backtest gate (must pass before merge)

Run `backtest_regime_matrix.py` on **60-day Binance dataset** (paginated fetch) with all v2 changes active. Compare to v1 baseline normalized to per-day metrics.

| Metric | Baseline v1 (per-day basis) | Target v2 | Gate minimum |
|---|---|---|---|
| WR | 49.4% | ≥55% | ≥53% |
| Profit factor | (not measured) | ≥1.6 | ≥1.4 |
| Max-DD | (not measured) | ≤15% capital | ≤20% |
| Trades/day | 5.1 | 3-4 | ≥2.5 |
| PnL/day | +$10.5 | ≥+$8.5 | ≥+$6.5 |
| PnL absolute 60d | +$628 (extrapolated) | ≥+$510 | ≥+$390 |

Reported in `docs/backtest_findings_2026-05-05_punk_smart_v2.md` with veto-kill matrix (how many setups died per veto type).

### Out-of-sample anti-overfit

`backtest_split.py` 70/30 split on the 60-day window:
- **Train (42d):** build per-asset mapping
- **Test (18d):** apply mapping, measure WR/PnL/DD

Gate: if Test metrics drop >30% vs Train → WARN, manual review before merge. <15% drop → PASS.

### Unit tests (must pass)

| Module | Test | Case |
|---|---|---|
| `punk_smart_vetos.py` | test_macro_veto | Mock event ±15 min → veto active |
| `punk_smart_vetos.py` | test_correlation_veto | BTC LONG open + ETH LONG new → veto |
| `punk_smart_vetos.py` | test_blacklist_veto | XLM with sl_count=2 → veto |
| `punk_smart_state.py` | test_kill_switch_2sl_4h | 2 SL events <4h apart → active |
| `punk_smart_state.py` | test_killswitch_purge_old | Event 5h ago → not counted |
| `regime_confidence.py` | test_sizing_clip | pnl=$5 → cap 1.5x. pnl=-$1 → cap 0.3x |
| `backtest_regime_matrix.py` | test_per_asset_fallback | (BTC, RANGING) with 3 trades → fallback global |

Run: `pytest tests/punk_smart/ -v`. Hooked into `preprompt_check.sh`.

### Definition of done

- [ ] Backtest v2 passes all 6 acceptance gates
- [ ] Out-of-sample test PASS (no WARN)
- [ ] All 7 unit tests pass
- [ ] `docs/backtest_findings_2026-05-05_punk_smart_v2.md` committed
- [ ] `/punk-smart` runs live once with no runtime error
- [ ] Rollback verified (set `version: 1` in mapping → behavior matches v1)

If any fails, stays in branch `feat/punk-smart-v2` until resolved.

## Rollback

Each change is backwards-compatible by design:

1. **Schema v2 mapping** → if `version != 2` or `per_asset` absent, router uses global. Restore v1: `cp regime_mapping.v1.backup regime_mapping.json`.
2. **State files missing** → router treats as empty (no veto). Delete files = fresh start.
3. **Vetoes individually** → flag in mapping JSON: `vetos_enabled: ["macro", ...]`. Remove veto name from array to disable without code change.
4. **Sizing dynamic** → flag `dynamic_sizing: true|false`. False = fixed $4 margin.
5. **Trail SL** → flag `trail_sl_offset_atr: 0.2 | 0.0`. 0.0 = original BE behavior.

Enables A/B in production: run new system 2 weeks, if metrics underperform → flip flags one by one to isolate offender.

## Backtest dataset extension

The v1 baseline used 15 days, which leaves several per-asset regime cells with n=4-5 trades — too fragile to trust. **v2 extends the backtest window to 60 days** to give per-asset cells more samples (target: ≥10 trades per (asset, regime) pair before trusting the per-asset override over the global fallback).

Binance Futures `klines` endpoint caps at 1500 bars per call. 60 days × 96 bars/day (15m) = 5760 bars → requires 4 paginated calls per asset per timeframe. New helper `fetch_paginated(symbol, interval, days)` in `backtest_regime_matrix.py` replaces the single-call `fetch()`.

**Implications:**
- `regime_mapping.json` v2 will have larger `n_trades` values than the example shown earlier in this spec (those are v1 figures shown for reference). The actual counts come from the v2 backtest run.
- Acceptance gates (WR, profit factor, max-DD) are evaluated against the 60-day v2 backtest. The v1 numbers (49.4% WR / +$157 / 15d) extrapolate to ~+$628 / 60d as a rough comparator.
- Out-of-sample 70/30 split now means train=42d / test=18d — much more robust signal.
- Refactor cost: 1-2h for paginated fetch + retry/backoff on Binance rate limits.

A future re-train cycle (mixing live trades from `signals_received.csv` once 30+ accumulate) remains out of scope for this v2.

## Out of scope for this spec

- Real-time SL streak detection without `/log-outcome` (option ii from Section 3 brainstorm) — requires CSV scanner, future enhancement.
- New strategies beyond A-E. The matrix is fixed.
- Multi-profile generalization (this is bitunix-specific by design).
- UI/TV chart drawing changes.
