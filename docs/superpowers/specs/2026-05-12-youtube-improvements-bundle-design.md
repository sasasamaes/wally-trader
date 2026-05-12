# YouTube Improvements Bundle (2026-05-12) — Design

**Date:** 2026-05-12
**Status:** Draft
**Source:** Four Alex Ruiz YouTube videos (es):
- V1 `G63K9vBN7eg` — Cómo Crear Una Estrategia De Trading Rentable [4 Pasos] (26 min)
- V2 `Cdhqu6rIvb0` — Creo La Estrategia De Trading Definitiva Con Claude (30 min)
- V3 `zH3Kpd7EYdQ` — Esta Es La Estrategia De Trading Que Seguiría Si Solo Tuviera $100 (23 min)
- V4 `lrHgnF0eSfM` — Curso Gratis De Trading Con Inteligencia Artificial (3h08m, no transcript)

**Author:** wally-trader project

## Context

Four YouTube videos analyzed via transcripts (V1-V3) and chapter description (V4). Each
report was produced by an isolated subagent reading the actual transcript content (after
relocating files inside the repo to clear sandbox restrictions). Honest extraction filtered
the marketing/motivational content; what remains is six concrete, testable improvements.

The videos are uneven in operational value:
- **V1** is 70% beginner-level didactic content; 30% useful reminders. The 4-step framework
  ("patrón + filosofía + normas") is already implemented across wally's slash commands and
  agents. Three concrete additions emerged: a pullback strategy detector, a dynamic min-R:R
  gate based on rolling WR, and a fib retracement zones helper.
- **V2** is mostly misleading — title says "Claude" but the workflow shown uses Claude.ai
  web with an artifact (no Claude Code, no MCP, no infra). Author's *own* conclusion at the
  end is that HMM should **not** be used to retune params (which his demo nominally does)
  but to activate/deactivate strategies entirely — exactly what `regime_mapping.json` +
  `punk-smart` v2 already do. **HMM excluded from this bundle.**
- **V3** is 50% mindset, 3 min of real technique. The technique (Asian Range
  breakout/fakeout EURUSD 5m) is generic ICT but fits cleanly into the existing
  `fotmarkets` profile (already forex-first, already CR 07-11). Adopted as a secondary
  strategy doc, not a replacement.
- **V4** is a 3h08m course with ~46 min of non-operational content (IA history, regulation)
  upfront. Five chapters identified as potentially useful (timestamps 1:21, 1:36, 1:53,
  2:06, 2:30) but require manual viewing — no transcript available. **Out of scope.**

User selected scope: four quick wins (B, C, F, G) plus two new strategies (A pullback,
E Asian Range), both standalone-first (no router wire-in until backtest validation).

## Goals

For each of six improvements, deliver minimal helper or doc change with tests where the
logic is non-trivial. Follow the existing "Discipline & Observability Bundle"
(2026-05-04) and "Live Insights Bundle" (2026-05-10) patterns — small, composable, each
gated independently.

## Non-Goals (YAGNI)

- ❌ HMM regime detector (V2) — author himself walked back his own demo; existing
  `regime_mapping.json` already does what HMM would activate.
- ❌ Manual extraction from V4's 3-hour course (out of scope; left for a future ad-hoc session).
- ❌ Wire-in of Pullback to `regime_mapping.json` — standalone-first, integration after
  backtest comparison vs MA Crossover.
- ❌ Replacement of Fotmarkets-Micro by Asian Range — Asian Range is secondary only.
- ❌ A new `small-account` profile (V3 inspiration) — `retail`, `retail-bingx`, `fotmarkets`
  already cover this niche; adding another would fragment attention.
- ❌ Real-time alerts beyond what existing helpers already emit.

## Feature B — Dynamic Min-R:R Gate (from V1)

**Insight:** Alex's WR↔R:R table — a 50% WR strategy needs ≥1.5:1 R:R to be profitable
(with fees); a 30% WR strategy needs ≥3:1. wally has no programmatic enforcement of this
adapted to the *current* profile's rolling WR.

**Implementation:**
- New helper: `.claude/scripts/min_rr_gate.py`
- Reads the active profile's rolling 30-day WR from `memory/trading_log.md` (or per-profile
  log structure) using a small parser. If profile already exposes WR via a stats file
  (e.g. journal output), prefer that.
- Formula: `min_rr = ((1 - wr) / wr) * 1.2` with `wr` clamped to `[0.20, 0.80]` to avoid
  pathological outputs.
- Insufficient-data fallback: if rolling 30d trades < 10 → return legacy `min_rr = 1.5`
  with `INSUFFICIENT_DATA` flag.
- CLI: `python3 .claude/scripts/min_rr_gate.py --profile <name> --setup-rr <ratio> [--json]`
- Exit codes: `0=OK 2=WARN (setup_rr < min_rr)`. Never blocks (conservative — user can
  override visually).

**Integration:**
- `trade-validator` agent: FASE 0.9 (after macro_gate FASE 0.6, volume_divergence FASE 0.7),
  reads setup's proposed R:R and gates against the dynamic minimum.
- `signal-validator` agent: same check, warns if Bitunix signal proposes R:R below the
  dynamic minimum for the bitunix profile.

**Tests:** `shared/wally_core/tests/test_min_rr_gate.py`
- happy path: WR 0.55, setup R:R 1.5 → OK
- warning path: WR 0.40, setup R:R 1.2 → WARN (needs ≥1.8)
- insufficient data: 5 trades → INSUFFICIENT_DATA + fallback min_rr=1.5
- boundary: WR 0.50, setup R:R exactly 1.2 → OK (no off-by-one)

## Feature C — Fib Retracement Zones (from V1)

**Insight:** Alex maps entries to fib 0.382/0.5/0.618 of the previous swing with SL at
0.75 and TP at swing extreme. wally has `fib_extension.py` (extension/projection only) and
the `fibonacci-tools` skill but no helper that returns *retracement entry zones*.

**Implementation:**
- Modify `.claude/scripts/fib_extension.py` — add `--mode retracement` (existing default
  remains `extension`).
- Output (retracement mode):
  ```json
  {
    "swing_high": 78285,
    "swing_low": 73500,
    "direction": "long" | "short",
    "entry_zones": {
      "382": 76256,
      "500": 75893,
      "618": 75530
    },
    "sl_075": 75303,
    "tp_swing": 78285
  }
  ```
- Auto-detect direction from the most recent swing (if last close > midpoint → long bias).
- CLI: `python3 .claude/scripts/fib_extension.py --symbol BTCUSDT --tf 1h --mode retracement [--quick] [--json]`

**Integration:**
- Pulled in by Feature A (Pullback detector) for entry zone computation.
- Available standalone for `/punk-watch` and `/signal` when the user wants to derive
  TPs/SLs from structure rather than from the signal's spec.

**Tests:** extend `shared/wally_core/tests/test_fib_extension.py`
- retracement mode with explicit swing high/low → assert all 5 levels match expected
  Fibonacci ratios within ε
- retracement on a synthetic bar series with one clean swing → assert direction auto-detect

## Feature F — Three-Months-Positive Challenge Gate (from V3)

**Insight:** Alex's scaling rule — wait until you have 3 months positive, 6 months stable,
or 12 months with ≤3 negative months before buying another funded challenge. wally already
has FundingPips ($99) and a stated plan to buy more FTMO; the gate prevents repeating
the impulse-buy when the current profile is not yet profitable.

**Implementation:**
- New helper: `.claude/scripts/challenge_readiness.py`
- Reads the active profile's monthly P&L from `memory/trading_log.md` (or per-profile
  monthly aggregation if available).
- Returns one of: `READY` (3+ consecutive positive months), `BORDERLINE` (1-2 positive),
  `NOT_READY` (last month negative or no track record).
- CLI: `python3 .claude/scripts/challenge_readiness.py --profile <name> [--json]`
- Exit codes: `0=READY 2=WARN(BORDERLINE) 1=NOT_READY`.

**Integration:**
- Modify `.claude/commands/challenge.md` (slash `/challenge`) — show the readiness verdict
  in the FTMO dashboard footer.
- Optional later: have `/journal` surface a yellow/red banner if the user has logged
  intent to buy a new challenge within the past 7 days while NOT_READY.

**Tests:** none (logic is a thin reducer over months; visual review on the slash command
output is enough). If the parser is reused across helpers we will add tests later.

## Feature G — Document Operational Costs in retail-bingx (from V3)

**Insight:** With $0.93 capital, BingX taker fee 0.05% × leverage 10x = ~$0.0023 per
side. Round-trip cost on a 2% sized trade ($0.0186 margin × 10 = $0.186 notional) is
$0.0002 — proportionally tiny in absolute terms, but the *minimum tick* and slippage make
real execution nearly impossible. The profile is pedagogical only.

**Implementation:**
- Modify `.claude/profiles/retail-bingx/config.md` — add a "Cost Reality" section that
  documents the round-trip cost in % of capital and the explicit recommendation: **do not
  execute real trades on this profile**; use it for replay/observation only.
- No code, no tests.

## Feature A — Pullback Detector (from V1)

**Insight:** Mean Reversion fails in TRENDING regimes (backtest 2026-04-30 showed -34.83%
without ADX gate). MA Crossover is wally's only TRENDING-day strategy, and it underfits the
common "impulse → pullback → continuation" pattern that price-action traders rely on.

**Implementation:**
- New helper: `.claude/scripts/pullback_detector.py`
- Algorithm:
  1. Detect *impulse*: 3+ consecutive same-color candles with ATR > rolling-mean ATR.
  2. Detect *pullback*: subsequent retrace to 0.382-0.618 fib of impulse (uses Feature C),
     with EMA(20) holding as soft support/resistance.
  3. Detect *continuation*: first impulse-coloured candle after pullback closes within fib
     zone.
- Reuses `.claude/scripts/adx_calc.py` to require ADX ≥ 25 (gate — no pullback signal in
  chop).
- Reuses `fib_extension.py --mode retracement` (Feature C) for zone computation.
- Output: entry price, SL (fib 0.75), three TPs derived from impulse magnitude, plus a
  `confidence` score 0-100 combining ADX, impulse strength, and pullback depth.
- CLI: `python3 .claude/scripts/pullback_detector.py --symbol BTCUSDT --tf 15m [--quick] [--json]`
- Slash command: `.claude/commands/pullback.md` invoking the helper for the active profile's
  default symbol.

**Integration:**
- **None automatic.** Standalone helper + slash command only.
- Decision (Q1): backtest the strategy first against the existing MA Crossover on TRENDING
  periods; only then update `regime_mapping.json` if there is a measurable edge. The
  backtest itself is a separate session.

**Tests:** `shared/wally_core/tests/test_pullback_detector.py`
- synthetic impulse (5 green candles, big ATR) + pullback (3 red candles into 0.5 fib) +
  continuation (1 green candle) → returns valid signal with confidence > 60
- chop regime (ADX < 20, no impulse) → returns no signal
- impulse without sufficient pullback (only retraces to 0.2 fib) → no signal
- pullback that breaks fib 0.786 (invalidation) → no signal

## Feature E — Asian Range Strategy (from V3)

**Insight:** During the Asian session (Tokyo, low volatility), price coils inside a small
range. Stops accumulate just outside that range. The London open frequently sweeps one
side then reverses — a classic ICT liquidity grab pattern. Alex frames this as an order
limit at the swept level with SL beyond and TP at the opposite range bound.

**Implementation:**
- New helper: `.claude/scripts/asian_range.py`
- Algorithm:
  1. Identify Asian session bars: UTC 23:00-08:00 (CR 17:00-02:00). Compute session
     high/low from 5m bars.
  2. At London open (CR 02:00 / fotmarkets window CR 07:00-11:00): detect breakout side
     (price closes outside the range).
  3. Detect grab/fakeout: subsequent close back inside the range within 4 bars → trigger
     a reversal signal in the opposite direction of the initial break.
  4. Entry: market on grab confirmation. SL: beyond the swept extreme + 2 pips buffer.
     TP: opposite side of the Asian range.
- Symbol scope: EURUSD primarily (fotmarkets default). GBPUSD optional.
- CLI: `python3 .claude/scripts/asian_range.py --symbol EURUSD --check-grab [--quick] [--json]`
- Slash command: `.claude/commands/asian-range.md` invoking the helper.

**Integration:**
- **None automatic** for execution flow.
- Documentation: new `.claude/profiles/fotmarkets/strategy_asian_range.md` describing the
  strategy as **secondary** to Fotmarkets-Micro. Primary strategy remains unchanged.
- Decision (Q2): Asian Range is informational only until manual evidence shows it adds
  value beyond Fotmarkets-Micro.

**Tests:** `shared/wally_core/tests/test_asian_range.py`
- synthetic Asian session with clean high/low + London-open break-and-reverse → signal
- Asian session with one-sided trend (no range) → no signal
- break without grab (price continues away from range) → no signal
- grab confirmation timing — must be within 4 bars of break; bar 5 onward = no signal

## Implementation Order

One commit per improvement, each passing `uv run pytest` and `uv run ruff check`:

1. **G** (doc retail-bingx) — warm-up, no tests
2. **C** (fib_retracement_zones) — extends existing script, needed by A
3. **B** (min-R:R gate) — wire into both validator agents at end of step
4. **F** (challenge readiness) — slash command modification
5. **A** (Pullback detector) — consumes C, larger tests
6. **E** (Asian Range) — independent, fixture-driven tests

## Test Discipline

Per `superpowers:test-driven-development`: tests-first for B, C, A, E (logic-heavy
helpers). Fixtures are synthetic OHLCV arrays — no live data in unit tests. F and G are
exempt (policy/doc).

## Error Handling

Standard project pattern:
- Insufficient data → `INSUFFICIENT_DATA` flag in JSON output, exit code 0 (informational).
- External fetch failure → fallback to local cache under `.claude/cache/` where applicable;
  otherwise return `DATA_UNAVAILABLE` with exit code 0.
- Never raise unhandled exceptions to the slash-command layer — agents must show a clean
  WARN if a helper fails.

## Out of Scope (Explicit)

- HMM regime detector (V2 ask)
- Manual viewing of V4 chapters
- Wire-in of Pullback (A) to `regime_mapping.json`
- Replacement of Fotmarkets-Micro by Asian Range (E)
- New `small-account` profile
- Any change to existing strategies' parameters (Mean Reversion 15m stays as-is)

## Acceptance Criteria

- Six commits land, each green on `pytest` + `ruff`.
- The two new slash commands (`/pullback`, `/asian-range`) plus updated `/challenge` are
  invokable and produce sensible output on synthetic input.
- Both validator agents (`trade-validator`, `signal-validator`) include the Min-R:R gate
  step in their documented flow.
- Spec file references survive the existing weekly-digest run (no broken links).
