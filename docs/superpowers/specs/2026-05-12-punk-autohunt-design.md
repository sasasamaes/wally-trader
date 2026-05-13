# `/punk-autohunt` — Design & Feasibility Spec

**Status:** Draft for review — NO code written.
**Profile:** `bitunix` only (capital $200, sizing $50 margin × up to 20x).
**Cadence:** hourly (manual or via `/loop 60m /punk-autohunt`).
**Deliverable per tick:** **at most 1** executable Bitunix setup. The honest output is "no setup this hour" if confluence is weak.
**PnL target spec:** $10 floor, fully dynamic upper bound (range $3 fallback to $70+ on strong confluence). The floor check determines whether the asset is even worth proposing.

---

## 1. Helper inventory (existing assets)

All paths relative to repo root `/Users/josecampos/Documents/wally-trader`.

| # | Capability | Status | File / location |
|---|---|---|---|
| 1 | macro_gate (tiered HARD / WARN / SOFT) | **EXISTS** | `.claude/scripts/macro_gate.py` (delegates to `wally_core.macro`); cache `.claude/cache/macro_events.json`; tiers via `--check-tier`, blocking via `--check-now` |
| 2 | regime detection per-asset (mapping v2) | **EXISTS** | `.claude/scripts/regime_mapping.json` (schema v2 with `per_asset` + `global` fallback); `.claude/scripts/punk_smart_router.py::evaluate_asset` (calls `backtest_regime_matrix.classify_regime`) |
| 3 | session quality (VWAP-flat detector) | **EXISTS** | `.claude/scripts/session_quality.py` (BLOCK / WARN / OK exit codes) |
| 4 | ADX trend strength | **EXISTS** | `.claude/scripts/adx_calc.py` (returns ADX, +DI, -DI, regime label) |
| 5 | SMC/ICT analysis (4-Pilar OB/FVG/BOS/ChoCH/sweeps) | **PARTIAL** | No Python helper. Available as: (a) skill `smart-money-ict`, (b) skill `punkchainer-playbook`, (c) Neptune `SMC` indicator on TV chart (`mcp__tradingview__data_get_pine_*`). Detection done by Claude reading chart, not by code. |
| 6 | multifactor score (momentum + vol + trend + volume) | **EXISTS** | `.claude/scripts/multifactor_score.py` (RSI+ADX+EMA + ATR pct + EMA alignment + volume spike → −100..+100) |
| 7 | ML XGBoost TP-first probability | **EXISTS** | `scripts/ml_system/supervised/predict.py --auto` (returns LONG/SHORT score 0-100). **Model trained only on BTCUSDT 15m**; needs retraining per-asset for full universe support |
| 8 | sentiment NLP (F&G + Reddit + News + Funding) | **EXISTS** | `scripts/ml_system/sentiment/aggregator.py` (composite); slash `/sentiment` |
| 9 | USDT.D dominance + BTC.D inverse bias | **EXISTS** | `.claude/scripts/usdtd_tracker.py` (CoinGecko `/global`, 10-min cache) |
| 10 | volume / OBV divergence | **EXISTS** | `.claude/scripts/volume_divergence.py` (`--symbol X --direction LONG --quick`) |
| 11 | liquidation heatmap clusters | **EXISTS** | `.claude/scripts/liq_heatmap.py` (returns top clusters + heat scores + "magnet" cluster) |
| 12 | fib extension exhaustion + retracement zones | **EXISTS** | `.claude/scripts/fib_extension.py` (`--mode extension|retracement`) |
| 13 | chainlink cross-check oracle | **EXISTS** | `.claude/scripts/chainlink_price.py` (compares TV price vs on-chain oracle; only BTC/ETH/LINK/MATIC/SOL/BNB feeds available) |
| 14 | on-chain BTC metrics (hashrate, MVRV, SOPR, exchange flows, whales) | **MISSING** (no helper). Skill `btc-on-chain` documents the *playbook* but no Python helper exists. |
| 15 | Smart Money L/S ratio | **PARTIAL** | Implemented inline in `.claude/scripts/extreme_momentum_fade.py` (lines 96-107) using `topLongShortPositionRatio` + `globalLongShortAccountRatio` from Binance Futures Data. Not extracted to a standalone helper. |
| 16 | pump detection (vol spike + OI surge + funding extreme) | **PARTIAL** | `extreme_momentum_fade.py` fades extreme momentum but is *reversal*-biased (fades pumps, doesn't *catch* them). Funding alerts in `.claude/scripts/funding_alerts.py`. No unified "pump-in-progress" detector. |
| 17 | wallet tracking / whale alerts | **MISSING** |
| 18 | TradingView MCP drawing primitives | **EXISTS** | `mcp__tradingview__draw_shape` (horizontal_line, trend_line, rectangle, text), `draw_clear`, `chart_set_symbol`, `chart_set_timeframe`, `chart_manage_indicator`. Caveat: `draw_clear` often fails with `"getChartApi is not defined"` — workaround via context-menu UI clicks documented in `.claude/agents/chart-drafter.md`. |
| 19 | signal logging (`signals_received.csv` + `/log-outcome`) | **EXISTS** | `.claude/scripts/bitunix_log.py::cmd_append_signal` + `.claude/scripts/log_outcome_v2.py`. CSV schema confirmed at `.claude/profiles/bitunix/memory/signals_received.csv` (27 columns incl. `tier`, `verdict`, `decision`, `outcome`, `pnl_usd`). |
| 20 | kill-switch + per-asset SL streak + concurrent slot state | **EXISTS** | `.claude/scripts/punk_smart_state.py` (`is_kill_switch_active`, `is_blacklisted`, `record_sl`, `record_tp`); daily reset launchd `com.wally.bitunix-daily-reset`. |
| 21 | portfolio breach guard (correlation/heat) | **EXISTS** | `shared/wally_core/portfolio.py::would_breach` (loaded conditionally in router) |
| 22 | veto layer (6 vetos) | **EXISTS** | `.claude/scripts/punk_smart_vetos.py` (macro, blacklist, correlation, sentiment, funding, time_of_day) |
| 23 | dynamic sizing | **EXISTS** | `.claude/scripts/regime_confidence.py::compute` (base_margin × multiplier clipped [0.3, 1.5]) |
| 24 | market context (global F&G, per-asset funding/24h) | **EXISTS** | `.claude/scripts/market_context.py::fetch_global_context` + `fetch_asset_context` (10-min cache) |
| 25 | dynamic universe discovery | **EXISTS** | `market_context.py::fetch_top_volume_binance` / `fetch_top_movers_binance` / `fetch_trending_coingecko` + `filter_tradeable_bitunix` (used by `punk_smart_router.py --dynamic`) |
| 26 | chart-drafter agent for TV drawings | **EXISTS** | `.claude/agents/chart-drafter.md` (already has `draw_shape`, `draw_clear` workaround, label conventions) |

**Verdict:** ~70% of what `/punk-autohunt` needs is already wired or one-call-away. The novel parts are (a) dynamic TP formula, (b) the *single-best-pick* selector logic, (c) the $10-PnL-floor gate, (d) on-chain + wallet-tracking integration (genuinely missing). Everything else is glue.

---

## 2. Gap research — FREE API feasibility

### 2.1 On-chain BTC real-time

| Source | Free? | What we get | Rate limit | Recommend? |
|---|---|---|---|---|
| `mempool.space/api` | YES | mempool stats, difficulty-adjustment ETA, fees | Generous (no key) | **YES** — already cited in `CLAUDE.md` and skill `btc-on-chain` |
| `blockchain.info/charts` | YES | n-transactions, estimated-volume-usd, active addresses (timespan 7d / 30d / 1y) | Friendly | **YES** for slow-moving structural signals (cached 1h) |
| `blockchair.com/bitcoin/stats` | YES | tx count, blocks, mempool size, hashrate (computed) | Rate-limited (~1 req/sec) | **YES** as backup |
| `bitinfocharts.com` | YES (HTML scrape) | hashrate, top-100 wallet concentration | No API, must scrape | **NO** — fragile (HTML), heavy for a per-hour helper |
| Glassnode / CryptoQuant / Santiment (MVRV, SOPR, exchange flows) | **NO** | Premium metrics | Paid tiers $30-$500/mo | **NO** — out of scope. Approximate MVRV-Z via `price / 200d_ma` (mentioned in skill). |
| `intotheblock.com` | Limited free | Some on-chain | Aggressive paywall | NOT viable for automation |

**Honest take:** real exchange flows + true MVRV + SOPR are paid only. We can approximate with mempool.space + blockchain.info + a synthetic MVRV-Z (`price / 200d_sma`) at the cost of accuracy. For the hourly autohunt, on-chain is **slow signal** (lag 1-4h per `btc-on-chain` skill) — it should be a confluence multiplier on BTC/ETH only, not a primary trigger. Recommend wrapping into a `.claude/scripts/btc_onchain.py` helper with 1h cache that returns a single `bias` enum (`BULL` / `NEUTRAL` / `BEAR`) and `confidence` (0-100). Anything more granular is overkill given the latency.

### 2.2 Whale wallet alerts

| Source | Free? | Recommend? |
|---|---|---|
| Whale Alert Twitter (@whale_alert) | YES (read scraping or RSS) | **MAYBE** — Twitter API requires paid key now; scraping fragile |
| Whale Alert free API | YES but **only $10M+ alerts**, 60 req/min, 7-day history | **MARGINAL** — needs free signup, no token; for hourly tick it's fine |
| `bitinfocharts.com/top-100-richest-bitcoin-addresses.html` | YES via HTML scrape | **NO** — top-100 movement is structural (days), not hourly |

**Honest take:** whale tracking at hourly cadence is a low-quality signal for BTC perp trading. Real whale activity that matters (exchange deposits >1k BTC) shows up in funding rate + L/S smart-money imbalance much faster than in whale-alert RSS. **Recommendation: skip whale tracking. Use the existing Smart Money L/S ratio from Binance Futures Data as the proxy.** It's already implemented in `extreme_momentum_fade.py` and refreshes hourly.

### 2.3 Exchange flows

Paid only with any usable resolution. **Skip.** The retail-vs-smart L/S divergence in `extreme_momentum_fade.py` is the free proxy for "is institutional money positioning differently than retail." That's the meaningful signal.

### 2.4 Pump detector heuristic

Combine existing components — no new external data needed:

```
pump_score = w1 * vol_spike_ratio   (last 1h vol / 24h avg)
           + w2 * oi_surge_pct      (OI change last 1h vs 24h ago via Binance openInterestHist)
           + w3 * funding_extreme   (|funding_8h| in pct, capped at 0.1)
           + w4 * chg_24h_abs       (|24h% change| from market_context)
           - w5 * retail_ls_skew    (penalise if retail already heavily one-sided)
```

All inputs already pulled by `market_context.py` and `extreme_momentum_fade.py`. Just need an extraction into `.claude/scripts/pump_detector.py` returning `{score: 0..100, side_bias: LONG|SHORT|NONE}`.

### 2.5 Smart Money L/S (CONFIRM)

Endpoints confirmed working in `extreme_momentum_fade.py`:
- `https://fapi.binance.com/futures/data/topLongShortPositionRatio?symbol={X}&period=1h&limit=1` (smart money / top traders by position)
- `https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={X}&period=1h&limit=1` (retail by account count)

Free, no auth, rate-limited but adequate for hourly per-asset polls of a 10-asset universe (≤30 calls/hour).

---

## 3. End-to-end pipeline design

The hourly tick is decomposed into **9 stages**. Stage names borrow from existing `punk_smart_router.py` Stage labels for compatibility.

```
┌────────────────────────────────────────────────────────────────────────────┐
│  PUNK-AUTOHUNT — hourly tick (target ≤ 90 sec wall clock)                  │
└────────────────────────────────────────────────────────────────────────────┘

STAGE 0  PROFILE + KILL-SWITCH GUARD
  ├─ profile.py get == "bitunix" else exit 1
  ├─ punk_smart_state.is_kill_switch_active(now) → if active, emit PAUSED + exit
  ├─ daily counter: signals_received.csv count today >= 7 → exit
  └─ concurrent slot counter: count(outcome=pending) >= 2 → exit

STAGE 1  MACRO TIER + SESSION QUALITY (BTC-anchored)
  ├─ macro_gate --check-tier
  │     HARD  → emit NO-GO, exit
  │     WARN  → force tier-0 universe (MUGRES), reduce size 50%
  │     SOFT  → suggest tier-0, info banner
  │     OK    → continue full universe
  └─ session_quality --symbol BTCUSDT --quick
        BLOCK (exit 1) → emit NO-GO "dead session", exit
        WARN  (exit 2) → reduce size 50%
        OK    (exit 0) → continue

STAGE 2  UNIVERSE BUILD
  ├─ if WARN/SOFT tier-0 forced → 9-asset MUGRE subset
  ├─ if --dynamic → market_context.fetch_top_volume_binance(n=10) +
  │                 filter_tradeable_bitunix
  └─ else → static 24-asset Bitunix watchlist (capped at top 12 by 24h vol
            to fit time budget)

STAGE 3  PER-ASSET ANALYTICS FAN-OUT (parallel; cached where possible)
  For each asset in universe:
    a) bars_15m + bars_1h (Binance fapi/v1/klines, 100 + 80 bars)
    b) regime → classify_regime(bars_15m, bars_1h)
    c) strategy lookup → regime_mapping.json → if STAND_ASIDE, drop
    d) strategy fn (A_VWAP / B_TrendPullback / etc.) → tentative {entry, sl, tp1, tp2, side}
    e) multifactor_score on bars_1h → score −100..+100
    f) volume_divergence --direction {side} → OBV-vs-price slope check
    g) liq_heatmap --symbol X → magnet + clusters
    h) fib_extension --mode extension --tf 1h → exhaustion label
    i) market_context.fetch_asset_context → 24h chg, funding_8h
    j) smart_money_ls + retail_ls (Binance futures data, inline)
    k) pump_detector → 0-100 score
    l) BTC + ETH only: btc_onchain bias (cached 1h)
    m) BTC only: chainlink_price delta% (sanity check; >1% delta → skip asset)

STAGE 4  VETO LAYER (existing 6 vetos + new ones)
  punk_smart_vetos.evaluate({asset, side}, ctx)
    macro / blacklist / correlation / sentiment / funding / time_of_day
  NEW veto: stale_chainlink_delta > 1.0% (BTC/ETH only)
  NEW veto: volume_divergence == "BEARISH_DIVERGENCE_vs_{side}"
  Drop vetoed assets.

STAGE 5  CONFLUENCE SCORING (the new piece)
  Each surviving asset gets a single confluence score 0-100 fused from:

    Component                                 Weight  Source
    ─────────────────────────────────────────  ─────  ────────────────────
    Backtest pnl_per_trade (from mapping)        20   regime_mapping.json
    Multifactor score (sign-matched to side)     20   multifactor_score.py
    R:R TP1 (clamped 1.0..3.0)                   10   from strat_fn output
    Liquidation magnet alignment (TP1 ≤ magnet)  10   liq_heatmap.py
    Fib retracement quality (0.382-0.618 zone)   10   fib_extension.py
    OBV slope alignment (NOT divergence)          5   volume_divergence.py
    Smart Money L/S alignment with side           5   inline Binance call
    Pump detector alignment                       5   pump_detector.py
    Sentiment + funding contrarian or neutral     5   sentiment + funding
    USDT.D inverse bias (BTC/ETH only)           5   usdtd_tracker.py
    On-chain bias (BTC/ETH only)                  5   btc_onchain.py (NEW)
    ─────────────────────────────────────────  ─────
                                       TOTAL    100

  Notes:
  - "Sign-matched to side": if side=LONG and multifactor=+60 → +20 weight.
    If side=LONG and multifactor=-40 → 0 weight (or negative, penalising).
  - Components 9 + 10 + 11 (15pts) are BTC/ETH-only. For altcoins, these
    weights redistribute proportionally to components 1-8.

  Threshold tiers:
    score >= 80  → A-GRADE (force proposal even if PnL floor borderline)
    70 <= score < 80 → B-GRADE (propose if PnL floor passes)
    60 <= score < 70 → C-GRADE (only propose if NO higher-tier asset exists
                                AND macro tier is OK)
    < 60 → drop

STAGE 6  PnL FLOOR FILTER  (see §4 for details)
  For each surviving asset:
    compute expected_move_pct → expected_$ at TP1 / TP2 / TP3
    if max_expected_$ at any TP < $10 floor → drop asset
    else attach tp_plan = {tp1, tp2, tp3, close_pct, expected_$}

STAGE 7  SINGLE-BEST-PICK SELECTION
  Among survivors (sorted by score DESC, then expected_$ DESC):
    pick top 1
  If 0 survivors → emit "no setup this hour" with diagnostic table

STAGE 8  TRADINGVIEW DRAW SEQUENCE (only if pick exists)
  Idempotent draw policy:
    1. chart_set_symbol(BITUNIX:{symbol})  (or fallback exchange if not on Bitunix)
    2. chart_set_timeframe("15")
    3. Best-effort draw_clear, else context-menu UI workaround
    4. draw_shape rectangle ENTRY ZONE (entry ± 0.05%)  color=yellow
    5. draw_shape horizontal_line SL  color=red  thick   label="SL <price>"
    6. draw_shape horizontal_line TP1 color=lightgreen   label="TP1 <price> +$<expected>"
    7. draw_shape horizontal_line TP2 color=green        label="TP2 <price> +$<expected>"
    8. draw_shape horizontal_line TP3 color=darkgreen    label="TP3 <price> +$<expected>"
    9. draw_shape horizontal_line LIQ_MAGNET color=orange dashed label="MAGNET <price>"
   10. draw_shape trend_line vertical at now+4h dashed  label="90min time-out"
  All drawings tagged with prefix "autohunt:" in label for later draw_remove_one cleanup.

STAGE 9  AUTO-LOG + OUTPUT
  ├─ bitunix_log cmd_append_signal with fields:
  │   origin=autohunt, decision=APPROVED_AUTOHUNT, verdict=B-GRADE-{score},
  │   tier={standard|tier-0}, entry/sl/tp1/tp2/tp3, sizing margin_usd/leverage
  ├─ emit user-facing report (see "Output examples" in §3.2)
  └─ if score < 70 anywhere → emit "no setup" report (still write a synthetic
     diagnostic row to signals_received.csv with decision=NO_PICK for journaling)

EXIT CONDITIONS (any → emit reason + exit non-zero):
  - profile != bitunix
  - kill-switch active
  - daily cap reached (7)
  - concurrent slot full (2)
  - macro HARD
  - session BLOCK
  - 0 confluence-survivors after vetos
  - 0 PnL-floor survivors
```

### 3.2 Output examples

**Pick found (A-GRADE):**

```
🎯 PUNK-AUTOHUNT — hourly tick 14:00 CR  |  pick #5/7 today, 1/2 concurrent

ASSET: SOLUSDT.P  SIDE: SHORT  CONFLUENCE: 82/100  TIER: A-GRADE
Regime: STRONG_TREND_DOWN 15m  |  Strategy: B_TrendPullback (BT WR 54%, +$1.19/trade)

  Entry: 145.20  SL: 146.95 (-1.21%)  R-unit: $5.25
  TP1:   143.10 (+1.45%, +$10.55)   close 50%   ← floor satisfied
  TP2:   141.00 (+2.89%, +$21.10)   close 30%
  TP3:   137.40 (+5.37%, +$39.20)   close 20%   ← magnet @ 137.20

  Expected $ if all TPs hit: $52.40  (1.05x of $50 margin)
  Risk: $4.20 (2.1% of $200 cap)  |  Sizing: $50 margin × 15x
  Smart Money L/S 0.62 (bearish ✓)  |  Funding -0.018% (slightly contrarian ✓)
  OBV slope: matches direction ✓  |  Fib: at 0.5 retracement of pullback ✓

⏱ 90-min time-out: 15:30 CR  |  DUREX trigger: TP1 hit → SL → 145.00

📤 Logged to signals_received.csv (origin=autohunt, decision=APPROVED_AUTOHUNT)
🎨 TV drawings refreshed on BITUNIX:SOLUSDT.P 15m
```

**No pick (honest output):**

```
⏳ PUNK-AUTOHUNT — no A/B-grade setup at 14:00 CR

Top-5 evaluated (all dropped):
  1. BTCUSDT  LONG  score 64  → C-GRADE only, no asset above 70
  2. INJUSDT  SHORT score 61  → expected $ TP1 = $4.20 < $10 floor
  3. AVAXUSDT LONG  score 58  → multifactor -32 vs side LONG (penalised)
  4. DOGEUSDT SHORT score 55  → VETOED (sentiment contrarian)
  5. SOLUSDT  LONG  score 51  → regime STAND_ASIDE per mapping

Reason summary: weak confluence + dead 14:00 hour (CR 13:00-15:00 historically thin)
Next tick: 15:00 CR
```

**Pre-flight abort:**

```
🚫 PUNK-AUTOHUNT — blocked

Reason: MACRO HARD — FOMC in 22 min (CR 13:00)
Next window: CR 14:00 +30 min after release
```

---

## 4. Dynamic TP spec (CRITICAL)

This is the core piece. The goal: each pick must offer at least $10 expected PnL at *some* TP given $50 margin × leverage, with the upper bound (TP3) adapting from ~$15 (weak regime) up to $70+ (strong confluence + clear runway to magnet).

### 4.1 Inputs available per asset

```
atr_15m      — from punk_smart_router (already calculated)
atr_pct_15m  — atr_15m / entry * 100
entry, sl    — from strat_fn
side         — LONG | SHORT
regime       — STRONG_TREND_{UP,DOWN} | WEAK_TREND_{UP,DOWN} | RANGING | SQUEEZE | MIXED | VOLATILE
liq_magnet   — closest cluster on the move-toward side (from liq_heatmap)
fib_targets  — 1.272, 1.618, 2.0 extensions from current swing (from fib_extension)
bb_width_pct — BB(20,2) (upper-lower)/middle (from chart_state or recomputed)
session_q    — OK | WARN (BLOCK already exited)
confluence   — 0-100 (from Stage 5)
margin_usd   — $50 default (subject to sizing multiplier)
leverage     — signal leverage capped at 20x
```

### 4.2 Step 1 — compute `expected_move_pct`

The expected favourable move from entry (absolute %), capped by the nearest *real* obstacle (liquidity, BB extreme, fib extension).

```python
# Pseudocode

# baseline: how much can ATR realistically deliver in the next 90 min?
# 15m bars × 6 bars / hour = 24 bars in 6 hours typical autohunt holding window
# but trader cuts at 90 min, so n_bars ≈ 6
# expected travel ≈ sqrt(n_bars) * atr (random-walk fair value)
baseline_move_pct = sqrt(6) * atr_pct_15m  # ~2.45 × atr_pct_15m

# regime multiplier
regime_mult = {
    "STRONG_TREND_UP":   1.6 if side=="LONG"  else 0.6,
    "STRONG_TREND_DOWN": 1.6 if side=="SHORT" else 0.6,
    "WEAK_TREND_UP":     1.1 if side=="LONG"  else 0.8,
    "WEAK_TREND_DOWN":   1.1 if side=="SHORT" else 0.8,
    "RANGING":           0.9,
    "SQUEEZE":           1.3,        # breakout potential
    "MIXED":             0.8,
    "VOLATILE":          0.7,        # don't trust direction
}[regime]

# confluence multiplier (linear 0.7 .. 1.3 across score 60..100)
conf_mult = 0.7 + (confluence - 60) / 40 * 0.6        # clamp at [0.7, 1.3]
conf_mult = clamp(conf_mult, 0.7, 1.3)

# session quality penalty
sess_mult = 1.0 if session_q == "OK" else 0.7         # WARN reduces ambition

# raw expected move
expected_move_pct = baseline_move_pct * regime_mult * conf_mult * sess_mult

# cap at structural obstacles
magnet_dist_pct = abs(liq_magnet - entry) / entry * 100  # if magnet exists toward side
fib_1618_dist_pct = abs(fib_targets["1.618"] - entry) / entry * 100  # toward side

# the cap is the smaller of: liq magnet, fib 1.618 extension (the natural stop)
structural_cap_pct = min_nonzero(magnet_dist_pct, fib_1618_dist_pct, 5.0)
                     # absolute hard ceiling 5% for 15m-1h horizon

expected_move_pct = min(expected_move_pct, structural_cap_pct * 1.05)
                                                       # allow 5% overshoot
```

**Example numbers (validation sanity check):**
- SOLUSDT, atr_pct_15m=0.45%, regime=STRONG_TREND_DOWN, side=SHORT, confluence=82, session OK
  - baseline = 2.45 × 0.45 = 1.10%
  - regime_mult = 1.6, conf_mult = 1.03, sess_mult = 1.0
  - raw = 1.10 × 1.6 × 1.03 × 1.0 = 1.81%
  - if magnet at -5.0% and fib 1.618 at -3.2%, cap = 3.2 × 1.05 = 3.36%
  - **expected_move_pct = 1.81%** (below cap, no clipping)
- BTCUSDT range chop, atr_pct_15m=0.18%, regime=RANGING, side=LONG, confluence=65, session WARN
  - baseline = 2.45 × 0.18 = 0.44%
  - regime_mult = 0.9, conf_mult = 0.78, sess_mult = 0.7
  - raw = 0.44 × 0.9 × 0.78 × 0.7 = 0.22%
  - **expected_move_pct = 0.22%**

### 4.3 Step 2 — map `expected_move_pct` → TP1 / TP2 / TP3 distances

TPs are spaced as ladder. The structure depends on regime:

| Regime | TP1 / TP2 / TP3 multipliers of `expected_move_pct` | Close % at each TP |
|---|---|---|
| STRONG_TREND_{X} | 0.30 / 0.65 / 1.00 | 40% / 30% / 30% |
| WEAK_TREND_{X}   | 0.40 / 0.75 / 1.00 | 50% / 30% / 20% |
| SQUEEZE          | 0.35 / 0.70 / 1.10 | 40% / 30% / 30% (slightly past expected) |
| RANGING          | 0.50 / 0.85 / 1.00 | 60% / 30% / 10% (fast TP1) |
| MIXED / VOLATILE | 0.55 / 0.85 / 1.00 | 70% / 20% / 10% (lock fast) |

```python
tp1_pct = expected_move_pct * tp1_mult
tp2_pct = expected_move_pct * tp2_mult
tp3_pct = expected_move_pct * tp3_mult

# convert to price
sign = +1 if side=="LONG" else -1
tp1 = entry * (1 + sign * tp1_pct / 100)
tp2 = entry * (1 + sign * tp2_pct / 100)
tp3 = entry * (1 + sign * tp3_pct / 100)
```

### 4.4 Step 3 — convert to $ PnL

```python
notional = margin_usd * leverage   # e.g., $50 × 15 = $750
# % gain on margin = pct_move × leverage
expected_$ = (pct_move / 100) * notional

tp1_$ = (tp1_pct / 100) * notional
tp2_$ = (tp2_pct / 100) * notional
tp3_$ = (tp3_pct / 100) * notional
```

**Sanity numbers:**
- $50 × 15x = $750 notional, 1.81% move:
  - tp1_pct = 1.81 × 0.30 = 0.54%   → $4.05
  - tp2_pct = 1.81 × 0.65 = 1.18%   → $8.85
  - tp3_pct = 1.81 × 1.00 = 1.81%   → **$13.55**
- $50 × 20x = $1000 notional, 1.81% move:
  - tp3_$ = **$18.10**
- $50 × 20x, 3.5% move (strong trend + close-to-magnet runway):
  - tp1_pct = 1.05% → $10.50
  - tp2_pct = 2.28% → $22.80
  - tp3_pct = 3.50% → **$35.00**
- $50 × 20x, 5% move (rare, only on extreme momentum-fade with deep magnet):
  - tp3_$ = **$50** — and with partial close 30%, that's $15 from the last leg + earlier locks → total realised ~$32 across the ladder. Reaching $70 requires either >5% move OR a higher margin override.

### 4.5 Step 4 — the $10 floor check

```python
# If even TP3 < $10, the asset can't deliver. Skip.
if tp3_$ < 10.0:
    return DROP_BELOW_FLOOR

# If TP1 >= $10 → great, lock fast.
# If TP2 >= $10 but TP1 < $10 → propose with note "TP1 partial, $ realisation at TP2".
# If only TP3 >= $10 → propose only if confluence A-GRADE (>= 80) AND
#                      session_q == OK AND regime in {STRONG_TREND_*, SQUEEZE}
```

This rule prevents proposing "wait 4 hours for $10" trades in chop regimes. If the only way to hit $10 is at TP3 in a RANGING regime, the trade fails the patience-cost test.

### 4.6 Step 5 — when to widen vs take fast TP1

Two governance rules:

**Widen rule (only via strong confluence):**
- If confluence >= 85 AND regime in STRONG_TREND AND magnet is far (>3% away):
  - Add an internal `tp4` at `magnet * 0.98` (the "stretch goal"), close 10% there.
  - Move TP1/TP2/TP3 close % to 40/30/20 (leaves 10 for tp4).

**Fast-TP1 rule (auto-trigger):**
- If session_q == WARN OR confluence in [60, 70] (C-GRADE):
  - Force close_pct of TP1 = 60% (lock fast).
  - This is built into the regime table for MIXED / VOLATILE but should also fire on score-tier downgrade.

### 4.7 Step 6 — sizing override for $10 floor edge cases

If asset passes Stage 5 with score >= 80 BUT `tp3_$ < $10` at default margin/leverage, the helper may *propose* a margin bump:

```python
if score >= 80 and tp3_$ < 10:
    needed_notional = 10 / (expected_move_pct / 100)
    needed_margin   = needed_notional / leverage
    if needed_margin <= 75 and needed_margin / 200 <= 0.40:   # cap 40% capital
        margin_usd = ceil(needed_margin / 5) * 5              # round to nearest $5
        # recompute $; if still < 10, drop
```

Note: this is *only* allowed for A-GRADE. B-GRADE and C-GRADE keep the default $50.

### 4.8 Behaviour when expected_move < $10 floor

- Asset is **dropped silently from the candidate list** but logged in the diagnostic "Top-5 evaluated" output with reason `EXPECTED_DOLLAR_TP3_BELOW_FLOOR ($X.XX)`.
- Move to next-best asset.

---

## 5. Risk / antipatterns

### 5.1 Forcing setups during dead hours
**Mitigation:** Stage 1 session_quality is already there. **Enforce it as a hard gate (BLOCK exit code 1 = abort).** Plus a soft penalty: if `--quick` returns "compressed" (BB width <0.3% of price), apply `sess_mult = 0.7` in Step 1.

### 5.2 Overfitting to recent winners
**Concrete failure:** PIPPINUSDT mapping shows `pnl_per_trade=15.74` — that's a single rip captured by the matrix backtest. If autohunt fires on PIPPIN whenever STRONG_TREND_UP it'll keep referencing that historical number.
**Mitigation:**
- Reject mapping cells with `n_trades < 10` (already in router).
- Decay the BT pnl_per_trade weight in Stage 5 by `min(1.0, n_trades / 30)` so a cell with n=10 is half-weighted vs n=30.
- Re-train `regime_mapping.json` weekly (manual via `python3 .claude/scripts/backtest_regime_matrix.py`, or scheduled launchd).

### 5.3 Correlated concurrent trades
**Mitigation:**
- `punk_smart_state` already tracks concurrent (max 2) — keep.
- `punk_smart_vetos.correlation` already evaluates correlation bucket — keep.
- Plus: **autohunt-specific rule**: if an open position exists on BTC and the autohunt pick is on an asset with 30d correlation > 0.7 vs BTC, drop unless side is *opposite* (intentional hedge).

### 5.4 Auto-draw spam on TV
**Mitigation:**
- All autohunt drawings carry `"autohunt:"` prefix in their label.
- At Stage 8 start, list existing drawings via `draw_list`, remove ones with this prefix via `draw_remove_one`. Fallback to context-menu workaround if `draw_clear` API throws.
- Only redraw if the *picked symbol* differs from the previous tick. If same symbol with adjusted TPs, refresh in place.

### 5.5 Dynamic TP that becomes excuse to chase
**The guardrail rule:** `expected_move_pct` is upper-bounded by `structural_cap_pct * 1.05` (Step 1). The cap itself is the smaller of `liq_magnet_dist_pct`, `fib_1618_dist_pct`, and a hard 5% ceiling. **There is no way the formula returns >5% move at the entry timeframe.** This is the anti-greed bound.

Additionally: if the user backs into the formula seeing "TP3 = $70 wow", remember:
- TP3 close% is at most 30% of position, so $70 at TP3 = $21 realised on that leg.
- Total realised across the ladder when all hit = roughly `(tp1$ × 0.4) + (tp2$ × 0.3) + (tp3$ × 0.3) ≈ tp2$`. The "$70 ceiling" is the gross at the last TP, not the take-home.

### 5.6 Cost of API calls per hour × 24h × 7d
Per tick (assuming 10-asset universe after macro/session filter):

| API | Calls per tick | Rate-limit safe? |
|---|---|---|
| Binance fapi `/klines` (bars_15m + bars_1h) | 20 | YES (weight ~1 each; 1200/min limit) |
| Binance fapi `/openInterestHist` | 10 | YES |
| Binance fapi `/futures/data/{top,global}LongShortRatio` | 20 | YES |
| Binance fapi `/premiumIndex` (funding) | 10 | YES |
| CoinGecko `/global` (USDT.D) | 1 (10-min cached) | YES |
| Chainlink Data Feeds (BTC only) | 1 | YES |
| mempool.space (on-chain BTC) | 1 (1-hour cached) | YES |
| Fear & Greed (alternative.me/fng) | 1 (10-min cached) | YES |
| MCP `quote_get`, `chart_*`, `data_get_ohlcv` | ~5 | Local, free |
| MCP `draw_shape` × ~7 | 7 | Local, free |

**Total ~75 external HTTP calls per tick.** At 24 ticks/day × 7 days = ~12,600 calls/week. All well within free tier limits (Binance is by far the biggest user; their public futures-data endpoints allow ~1200 req/min/IP).

**Time budget:** with parallel asyncio, 10-asset fan-out completes in ~30-45 sec; total wall clock per tick ~60-90 sec. Acceptable.

### 5.7 Stale on-chain or sentiment data invalidating the score
**Mitigation:** every helper used in Stage 5 *must* return a `freshness_sec` field. If freshness > 2× expected TTL, Stage 5 sets that component's weight to 0 (graceful degradation). Particularly important for sentiment NLP (depends on Reddit + RSS which can stall).

### 5.8 The "every hour I see a green light" failure mode
The user, seeing autohunt's hourly cadence, may interpret no-pick output as "the system is being too strict, let me trade off Discord." **Mitigation:** the no-pick output should explicitly say `next tick: HH:00 CR` and *also* surface the Discord signal slot status (X/2 concurrent) and daily cap (X/7). Show that the *floor* is the constraint, not the system's pickiness.

---

## 6. Validation plan

Backtesting a self-generated signal stream against itself is meaningless (lookahead bias). The honest path is paper trading.

### 6.1 Paper-trade mode

Launch the command with `--paper` flag for N=20 ticks (≈ one trading week of CR 06:00-23:59 daily activity = 18 hours × 7 days = 126 ticks max, target the first 20 picks).

```
/punk-autohunt --paper
```

- Sets `origin=autohunt-paper` in the CSV row.
- No TradingView drawing.
- No real trade execution suggestion.
- Outcome is auto-tracked by `log_outcome_v2.py` reading bars 4h after entry (or sooner if SL/TP hit per bars).

### 6.2 Acceptance criteria to graduate to live

After 20 paper picks:

| Metric | Threshold |
|---|---|
| Win rate (TP1 hit before SL) | ≥ 50% |
| Profit factor (sum wins / sum losses) | ≥ 1.40 |
| Average $ PnL per pick | ≥ $5 (50% of $10 floor — accounts for losses) |
| Max consecutive losses | ≤ 3 |
| Drawdown (peak-to-trough on synthetic equity) | ≤ 15% |
| Score-vs-outcome correlation | confluence ≥ 80 picks must win ≥ 60% |

If ALL pass → graduate to `origin=autohunt` (live recommendations). If ANY fail → tune weights or formulas and re-paper.

### 6.3 A/B comparison: autohunt vs Discord-driven `/signal`

For 30 days post-graduation, log both:
- All `/signal` entries (Discord origin, marked `origin=community` in CSV)
- All `/punk-autohunt` picks (`origin=autohunt`)

Compare:
- WR, PF, avg $ PnL, time-to-TP1
- Setup quality breakdown (regime, score distribution, asset distribution)
- Overlap rate (when autohunt picks same asset+side as a Discord signal within 1h window — that's confirmation)

This becomes a feedback loop: if autohunt outperforms community signals, raise allocation. If community wins, raise the autohunt score threshold or retire the command.

### 6.4 Kill-switch on the command itself

```python
# In autohunt.py main(), before Stage 5:
recent_paper = load_signals_csv(origin="autohunt-paper", last_n=10)
if len(recent_paper) == 10 and recent_paper.win_rate < 0.40:
    print("🚫 PUNK-AUTOHUNT FROZEN — first 10 paper signals WR < 40%. "
          "Re-tune confluence weights before unfreezing.")
    return
```

Honest: this is *the* most important safety. The command must self-disable if the paper run is bad. Manual unfreeze via `--force-unfreeze` flag with explicit operator acknowledgement.

---

## 7. Implementation hand-off (files to create / modify)

### New files

- [ ] `.claude/scripts/autohunt.py` — main entry point. Stages 0-9 orchestrator. CLI: `--paper`, `--asset SYMBOL` (force single), `--dry-run` (no TV draw, no CSV append), `--force-unfreeze`. Imports from `punk_smart_router`, `punk_smart_state`, `punk_smart_vetos`, `market_context`, `regime_confidence`, plus new modules below.
- [ ] `.claude/scripts/autohunt_tp.py` — pure-function module implementing the §4 dynamic TP formula. Inputs: dict of analytics; output: `{tp1, tp2, tp3, close_pcts, expected_$, expected_move_pct, floor_passed: bool}`. Side-effect free (no I/O), unit-testable.
- [ ] `.claude/scripts/autohunt_score.py` — pure-function module implementing the §3 Stage 5 confluence fusion. Same shape: inputs are analytics dict, output is `{score: 0..100, components: {...}, tier: A|B|C|DROP}`.
- [ ] `.claude/scripts/pump_detector.py` — extract pump scoring inline-code from `extreme_momentum_fade.py` into a reusable module with CLI `--symbol X --quick`. Returns `{score, side_bias, components}`.
- [ ] `.claude/scripts/btc_onchain.py` — new helper for BTC/ETH on-chain bias. Pulls mempool.space difficulty-adjustment + blockchain.info n-transactions + synthetic MVRV-Z (price/200d_sma). 1-hour file cache at `.claude/cache/btc_onchain.json`. Returns `{bias: BULL|NEUTRAL|BEAR, confidence: 0-100, freshness_sec}`.
- [ ] `.claude/scripts/smart_money_ls.py` — extract the Binance Futures Data L/S calls from `extreme_momentum_fade.py` into a reusable helper. CLI: `--symbol X [--json]`. Returns `{retail_ls, smart_ls, divergence_flag}`.
- [ ] `.claude/commands/punk-autohunt.md` — slash command markdown (mirror `/punk-hunt` structure, but documenting paper mode, $10 floor, single-pick policy, draw policy, A/B comparison).
- [ ] `.claude/agents/punk-autohunt-analyst.md` — agent definition (optional; could keep logic in autohunt.py only). If we want Claude to summarise the picks in natural language, this agent receives the JSON from autohunt.py and produces the human-friendly report block.
- [ ] `.claude/scripts/tests/test_autohunt_tp.py` — unit tests for the TP formula. Validate the sanity numbers in §4.4. Edge cases: zero ATR, negative regime mult, structural cap clip.
- [ ] `.claude/scripts/tests/test_autohunt_score.py` — unit tests for the fusion formula. Validate weights sum to 100, BTC vs altcoin redistribution, missing-component graceful degradation.
- [ ] `.claude/scripts/tests/test_pump_detector.py` — unit tests for pump_detector.
- [ ] `.claude/scripts/tests/test_btc_onchain.py` — unit tests with mocked HTTP.
- [ ] `.claude/scripts/tests/test_smart_money_ls.py` — unit tests with mocked Binance responses.
- [ ] `docs/superpowers/specs/2026-05-12-punk-autohunt-design.md` — copy this file into the spec ledger.
- [ ] `docs/superpowers/plans/2026-05-12-punk-autohunt-implementation.md` — implementation plan with task-by-task breakdown (paper-trade phase → graduation criteria → live cutover).

### Modified files

- [ ] `.claude/profiles/bitunix/config.md` — add a "Hourly autonomous hunt" subsection explaining `/punk-autohunt` vs `/punk-hunt` vs `/signal` (the 3 are conceptually different: external validation / heuristic scan / autonomous selector).
- [ ] `.claude/profiles/bitunix/rules.md` — add the autohunt-specific rules: PnL floor $10, score thresholds 80/70/60, drawdown limit on autohunt sub-stream (kill-switch at 10 paper WR<40%), paper-first graduation.
- [ ] `.claude/scripts/regime_mapping.json` — no schema change required. The Stage 5 weight on `pnl_per_trade` should be decayed by `min(1.0, n_trades / 30)` (done in scoring module, no JSON change).
- [ ] `.claude/scripts/punk_smart_state.py` — add optional `record_autohunt_outcome(asset, ts, pnl_usd)` to separately track the autohunt sub-stream's WR for the §6.4 kill-switch.
- [ ] `.claude/launchd/com.wally.punk-autohunt.plist` — **optional** launchd plist for true scheduled hourly auto-run (CR 06:00-23:00). User can choose to enable; default off (manual via `/loop`).
- [ ] `CLAUDE.md` — add a "Bundle 4" subsection at end describing this feature, with a single sentence note in the Profile system table that bitunix now has 3 trade-discovery modes (`/signal`, `/punk-hunt`, `/punk-smart`, `/punk-autohunt`).
- [ ] `.claude/profiles/bitunix/memory/signals_received.csv` — no schema change; the existing `origin` / `decision` / `verdict` columns accommodate `origin=autohunt` and `origin=autohunt-paper`. (Confirmed by inspecting the live CSV — 27 columns are flexible enough.)

### Out of scope (intentional)

- No whale-tracking integration (low signal-to-noise at hourly cadence; Smart Money L/S already proxies the same idea cheaper).
- No CryptoQuant / Glassnode / Santiment paid integration.
- No Pine Script indicator generation for autohunt overlay on TV — drawings via `draw_shape` are enough.
- No autonomous *execution* on Bitunix (the profile is always manual-execute by design; autohunt only proposes).
- No ML retraining per-asset — the existing BTC-only XGBoost is used as a confluence component for BTC/ETH picks only; altcoin picks skip the ML component (weight redistributes).

---

## Appendix A — Why not just extend `/punk-smart`?

`/punk-smart v2` already does Stages 0-4 + a simplified Stage 5 (just `pnl_per_trade` ranking) + draws nothing. Adding the dynamic TP formula and the $10 floor *inside* `punk_smart_router.py` would bloat that script.

Cleaner split:
- `/punk-smart` = backtest-mapping router; outputs N approved setups by RR.
- `/punk-autohunt` = uses `/punk-smart` internally as a candidate generator, then layers the confluence fusion + dynamic TP + single-pick + draw + log.

This keeps `/punk-smart` lean and gives `/punk-autohunt` a clear single responsibility: **the hourly autonomous best-pick selector with adaptive PnL targeting.**

## Appendix B — Honest assessment of the $10 floor / dynamic ceiling

**Realistic?** Mostly yes, conditionally.

**The $10 floor is feasible** because $50 margin × 20x leverage × 1.0% favourable move = $10 exactly. Any setup with `expected_move_pct >= 1.0%` at the lower bound clears the floor. Given typical 15m ATR for liquid Bitunix alts (0.30-0.60% per bar), the formula's `baseline = sqrt(6) * atr_pct ≈ 0.75-1.5%` already meets the floor on its own for most setups. **The floor is a sanity check, not a stretch goal.**

**The $70+ ceiling is rarer**:
- Requires expected_move >= 4.7% (`= $70 / $1500 notional` at 20x×$75 margin override).
- 4.7% in <90 min on a single asset = top 5% of moves. Realistic only in:
  - Extreme momentum-fade setups (post-pump alts with deep liquidation cluster magnets, like the LDO +100% margin on 2026-05-11)
  - Major-event-driven moves (CPI/FOMC reactions — but those are gated by macro_gate HARD)
  - Strong-trend continuation after a clean BOS

So `$70+ ceiling` is a *theoretical envelope*, not a routine expectation. **Honest median expected $ PnL** at TP3 with default $50×15x sizing is around $15-25 across the typical Bitunix universe.

**The biggest risk to the spec:** the dynamic TP formula assumes ATR-based fair-value extrapolation. In genuinely violent regimes (e.g., the 2026-05-11 SAGA pump that ate $103 of margin), ATR understates the move and the formula will set TPs too close. The `structural_cap_pct` (liq magnet + fib 1.618) is the safety on the *upside*, but there's no safety on **the SL side** — the strat_fn from `punk_smart_router` decides SL distance, and a fixed 1.5×ATR SL in a 5×-normal-vol asset is suicidal. **Strongly recommend** wiring an ATR-percentile gate (drop asset if `atr_15m` is in top 5% of last 200 bars) before Stage 4. This isn't currently in the design above but should be added; it's a single line in `evaluate_asset`.

That's the spec.
