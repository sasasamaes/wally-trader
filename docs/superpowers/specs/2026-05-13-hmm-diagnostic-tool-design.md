# HMM Diagnostic Tool — Design Spec

**Date:** 2026-05-13
**Status:** Approved (brainstorming complete, ready for implementation plan)
**Source:** YouTube "Creo La Estrategia De Trading Definitiva Con Claude" by Alex Ruiz (`Cdhqu6rIvb0`, 30 min)
**Scope decision:** Enfoque B — diagnostic tool with integration to existing stack, NO live trading wire-in

## Context & motivation

Bundle 3 (2026-05-12) explicitly rejected HMM-based regime detection:

> *HMM regime detector — Alex's own V2 conclusion walked back HMM-for-param-tuning; existing `regime_mapping.json` + ADX cover the use case.*

This new video (V5 in Alex's series) reinforces the same conclusion — **HMM should NOT tune strategy parameters dynamically** — but argues for a legitimate complementary use:

> *El verdadero valor del HMM está en la gestión del portfolio, no en el ajuste de las estrategias. Los parámetros se mantienen fijos y lo que va variando es qué estrategia se activa, cuándo se activa, con qué riesgo se activa.*

That portfolio-management framing is already what `punk_smart_router.py` + `regime_mapping.json` do, derived from ADX-based regime detection plus backtest matrix mapping.

The unfilled gap that this spec addresses: **diagnostic analysis of how each of the 5 existing strategies behaves under HMM-detected regimes for a given asset**, independent of the live ADX path. The output informs human review of `regime_mapping.json` without auto-modifying it.

User decisions (brainstorming session 2026-05-13):
- Scope: Diagnostic standalone, no live trading touched
- Strategies in scope: the 5 already in `punk_smart_router.py` (A_VWAP, B_TrendPullback, C_RangeBounce, D_MACDMomentum, E_Donchian)
- Universe: single asset per invocation
- Output: markdown by default, optional HTML via `--html`
- Timeframe: 1H bars, ~6 months lookback, auto-detect K ∈ {2,3,4,5} via BIC

## Goals

1. Replicate Alex's "private HMM tool" workflow (regime detection + per-regime backtest) in our stack
2. Surface honest discrepancies between HMM-detected regime and current `regime_mapping.json` mapping
3. Stay strictly diagnostic — no live path mutation, no auto-application of suggestions
4. Reuse existing strategy implementations from `punk_smart_router.py` to avoid duplicated logic

## Non-goals (explicit)

- Live wire-in to `/punk-smart`, `/regime`, `/signal`, `/validate` or any execution path
- Auto-update of `regime_mapping.json`
- Multi-asset batch mode
- Multi-timeframe consensus HMM
- Pine Script export
- Backtest of arbitrary strategies imported via `/strategy-import` (extension V2)

## Architecture

```
User: /hmm-analyze <SYMBOL> <STRATEGY> [--html] [--suggest-mapping] [--force-refresh] [--seed N]
      alt:  /backtest --hmm-analyze <SYMBOL> <STRATEGY>

                 │
                 ▼
   .claude/scripts/hmm_analyze.py main()
                 │
   ┌─────────────┼──────────────┬──────────────────┬────────────────┐
   ▼             ▼              ▼                  ▼                ▼
fetch_ohlcv  build_features  fit_best_hmm   label_states   backtest_per_regime
 (Binance     (log_return,    (GaussianHMM   (heuristic     (reusa strategies/
  /fapi/v1/    vol_20,         K∈{2..5}      mean_ret ×      A_VWAP, B_TrendPullback,
  klines       momentum_14)    select via    mean_vol)       C_RangeBounce,
  1h × 6m,                     BIC)                          D_MACDMomentum,
  cache 1h)                                                  E_Donchian)
                                  │
   ┌──────────────────────────────┼────────────────────────────────┐
   ▼                              ▼                                ▼
emit_markdown                opt: emit_html              opt: suggest_mapping_patch
  → docs/hmm_analysis/        → docs/hmm_analysis/         → stdout unified diff
    <SYM>_<STRAT>_<DATE>.md     <SYM>_<STRAT>_<DATE>.html    (NEVER writes file)
                                 (plotly)
```

## Components

### File layout

```
.claude/scripts/hmm_analyze.py                  # CLI entry point
.claude/scripts/hmm_lib/                        # reusable module
    __init__.py
    fetcher.py          # OHLCV fetch + cache
    features.py         # feature engineering
    model.py            # HMM fit + K selection
    labeling.py         # state → human label
    backtest.py         # per-regime backtest
    reporting.py        # markdown + HTML emitters
    suggest.py          # dry-run mapping patch
.claude/scripts/strategies/                     # refactor from punk_smart_router
    __init__.py
    base.py             # Strategy ABC
    vwap_reversion.py
    trend_pullback.py
    range_bounce.py
    macd_momentum.py
    donchian.py
shared/wally_core/tests/
    test_hmm_features.py
    test_hmm_model.py
    test_hmm_labeling.py
    test_hmm_backtest.py
    test_hmm_reporting.py
    test_hmm_strategies_refactor.py
    integration/
        test_hmm_analyze_e2e.py
    e2e/
        test_hmm_real_binance.py    # @pytest.mark.network, opt-in
    fixtures/
        hmm_synthetic_bars.json
        _generate_hmm_synthetic.py  # helper to regenerate fixture
docs/hmm_analysis/                              # output dir (created on demand)
.claude/skills/hmm-regime-analysis/SKILL.md     # doc-only skill
.claude/commands/hmm-analyze.md                 # slash command spec
```

### Interfaces

```python
# fetcher.py
def fetch_ohlcv_1h_6m(symbol: str, *, force_refresh: bool = False) -> pd.DataFrame:
    """Pull ~4380 hourly bars from Binance Futures with 1h disk cache.
    Returns DataFrame[open, high, low, close, volume, ts_utc].
    Raises FetchError on HTTP issues, InsufficientDataError on <1000 bars."""

# features.py
def build_features(bars: pd.DataFrame) -> np.ndarray:
    """Return (N, 3) standardized matrix: [log_return, vol_20, momentum_14].
    Drops initial 20 warmup bars. Mean-centered, unit-variance per column."""

# model.py
@dataclass
class HMMFit:
    model: GaussianHMM
    k: int
    bic: float
    log_likelihood: float
    states: np.ndarray              # (N,) integer state per bar
    transition_matrix: np.ndarray   # (K, K) row-stochastic

def fit_best_hmm(features: np.ndarray, *, k_range=(2,3,4,5), random_state=42) -> HMMFit:
    """Fit GaussianHMM for each K, pick lowest BIC. Deterministic via random_state.
    Retries non-convergent K up to 5 seeds, falls back to covariance_type='diag' on singularity."""

# labeling.py
def label_states(fit: HMMFit, features: np.ndarray) -> dict[int, dict]:
    """Returns {state_id: {label: str, mean_return: float, mean_vol: float,
                            pct_bars: float, low_sample: bool}}
    Heuristic: per state compute mean_return & mean_vol, classify into
    {CALM_UP, CALM_DOWN, TREND_UP, TREND_DOWN, STRESS, STRESS_LITE, CHOP}.
    States with <5% bars get low_sample=True flag."""

# backtest.py
@dataclass
class RegimeBacktest:
    regime_label: str
    n_bars: int
    pct_time: float
    trades: int
    wr: float
    pf: float
    net_pnl_pct: float
    max_dd_pct: float
    low_trade_count: bool          # n<10 flag

def backtest_per_regime(
    bars: pd.DataFrame,
    states: np.ndarray,
    labels: dict[int, dict],
    strategy_name: str,
) -> list[RegimeBacktest]:
    """Run strategy across ALL bars, partition trades by entry-bar regime.
    Always emits a 'GLOBAL' row (all regimes pooled) as baseline."""

# reporting.py
def emit_markdown(report: dict, out_path: Path) -> None: ...
def emit_html(report: dict, out_path: Path) -> None: ...  # plotly, optional

# suggest.py
def suggest_mapping_patch(
    backtests: list[RegimeBacktest],
    current_mapping_path: Path,
    symbol: str,
    strategy_name: str,
) -> str:
    """Returns a unified diff string. NEVER writes to file.
    Excludes low_sample regimes and low_trade_count rows from suggestions."""
```

### CLI surface

```bash
# Primary
python3 .claude/scripts/hmm_analyze.py --symbol ETHUSDT --strategy A_VWAP \
    [--html] [--suggest-mapping] [--force-refresh] [--seed 42] [--timestamp]

# Secondary via /backtest
python3 .claude/scripts/backtest_runner.py --hmm-analyze --symbol ETHUSDT --strategy A_VWAP

# Slash commands
/hmm-analyze ETHUSDT A_VWAP
/backtest --hmm-analyze ETHUSDT A_VWAP
```

### Strategies refactor approach

The 5 strategies currently live inline in `punk_smart_router.py`. We extract them to `.claude/scripts/strategies/` behind a `Strategy` ABC with a pure `signal(bars) -> list[Trade]` interface.

- Router keeps its public API (`evaluate_setup`, `run_router_scan`) unchanged
- Router imports strategies from the new module
- **Regression test:** `python3 .claude/scripts/punk_smart_router.py --json` produces identical output before and after the refactor on a fixed fixture

**Fallback if refactor is too risky:** duplicate the 5 functions in `strategies/` with `# TODO: dedupe with router` comments. V1 ships with duplication; V2 (future PR) does the real refactor. Decision made at implementation time after inspecting the router code.

## Data flow (concrete example)

Invocation: `/hmm-analyze ETHUSDT A_VWAP`

1. **Fetch OHLCV:** Binance Futures `/fapi/v1/klines?symbol=ETHUSDT&interval=1h&limit=1500`, paginated 3x to reach ~4380 bars (6 months). Cache in `.claude/cache/ohlcv_ETHUSDT_1h_6m.json` with 1h TTL.

2. **Features:** compute log_return, rolling 20-bar volatility, 14-bar momentum. Drop first 20 bars (warmup). Standardize each column.

3. **Fit HMM:** for K ∈ {2,3,4,5}, fit `GaussianHMM(n_components=K, covariance_type='full', random_state=42)`. Pick K with lowest BIC.

4. **Label states:** for each state, compute `mean_return` and `mean_vol`. Classify via decision tree:

```
                       mean_vol > p66?
                     yes ┃    no
              ┌──────────┴──────────┐
              ▼                     ▼
        STRESS                 mean_return > 0?
                              yes ┃    no
                          ┌───────┴───────┐
                          ▼               ▼
              vol < p33?         vol < p33?
            yes ┃  no          yes ┃  no
          ┌────┴────┐        ┌────┴────┐
          ▼         ▼        ▼         ▼
       CALM_UP  TREND_UP  CALM_DN  TREND_DN
```

If 2 states get the same label, disambiguate the higher-vol one to `STRESS_LITE`.
If `|mean_return| < CHOP_RETURN_THRESHOLD=0.0005`, override to `CHOP`.
Mark `low_sample=True` if pct_bars < 5%.

5. **Backtest A_VWAP per regime:** run strategy on full series, then partition trades by **entry-bar regime**. Also compute `GLOBAL` baseline.

6. **Emit markdown** to `docs/hmm_analysis/ETHUSDT_A_VWAP_2026-05-13.md` with 6 sections:
   - Summary
   - Regime Distribution
   - Transition Matrix
   - Backtest per Regime (with GLOBAL baseline)
   - Recommendations vs current `regime_mapping.json` (only if discrepancy detected)
   - Caveats (low-sample warnings, deterministic seed disclosure, limitations)

7. **Optional `--html`:** generate plotly artifact with price + colored regime bands, transition matrix heatmap, equity curves per regime.

8. **Optional `--suggest-mapping`:** print unified diff to stdout if HMM dominant regime ≠ current mapping AND backtest in dominant regime > current mapping backtest. **Never writes to file.**

## Error handling

### Fetch errors

| Scenario | Behavior |
|---|---|
| Symbol not listed (HTTP 4xx) | `FetchError` → exit 2 |
| Network timeout / 5xx | 3 retries with backoff 1s/2s/4s → exit 3 |
| Cache parse error | Delete cache, re-fetch, warn |
| <1000 bars | `InsufficientDataError` → exit 4 |

### HMM fit errors

| Scenario | Behavior |
|---|---|
| Non-convergence on seed=42 | Retry seeds 43, 44, 45, 46 |
| Singular covariance | Fallback to `covariance_type='diag'` |
| BIC NaN/inf | Discard that K |
| All K fail | Exit 5 |

### Labeling edge cases

| Scenario | Behavior |
|---|---|
| Duplicate labels across states | Disambiguate higher-vol to STRESS_LITE |
| State with <5% bars | Label normal + `low_sample=True` flag, excluded from suggestions |
| All states CHOP-like (lateral market) | Report warning: no differentiation |
| `|mean_return| < CHOP_RETURN_THRESHOLD` | Override to CHOP |

### Backtest edge cases

| Scenario | Behavior |
|---|---|
| 0 trades in regime | Row with `trades=0`, rest `—` |
| <10 trades in regime | `low_trade_count=True` flag, excluded from suggestions |
| Trade crosses regime boundary | Partition by **entry-bar regime** (explicit decision) |
| Strategy raises mid-backtest | Catch + log bar_index + reraise with context |

### Strategy refactor risk

| Scenario | Behavior |
|---|---|
| Side effects in strategy fn | Move to router callsite, ABC enforces pure |
| Strategy reads `regime_mapping.json` | Inject params via constructor `__init__(params=cfg)` |
| Regression test fails post-refactor | STOP refactor, propose bug fix or fallback duplication |
| Refactor too risky | Fallback: duplicate 5 fns with `# TODO: dedupe` comments |

### Exit codes

```
0  - success
1  - CLI usage error
2  - symbol not listed
3  - network failure after retries
4  - insufficient OHLCV data
5  - HMM fit failed all K
6  - strategy backtest crashed
7  - internal unexpected (with stack trace)
```

### Logging

Single append-only log: `.claude/cache/hmm_analyze.log`. Python `logging` stdlib.

## Testing strategy

### Unit tests (20 total)

- `test_hmm_features.py` — 3 tests (log_returns correctness, warmup drop, standardization)
- `test_hmm_model.py` — 4 tests (BIC selection, determinism with seed, retry on convergence, fallback to diag)
- `test_hmm_labeling.py` — 4 tests (high-vol-negative → STRESS, low-vol-positive → CALM_UP, duplicate disambiguation, low-sample flag)
- `test_hmm_backtest.py` — 4 tests (entry-regime partition, GLOBAL = unfiltered, zero-trades row, exception with bar_index)
- `test_hmm_reporting.py` — 2 tests (all 6 sections in markdown, suggest_patch unified diff format)
- `test_hmm_strategies_refactor.py` — 3 tests (signal matches pre-refactor, ABC purity, router still loads)

### Integration tests (3 total)

- Full pipeline on synthetic 2000-bar fixture with 3 injected regimes → HMM detects 3 states with >75% accuracy vs injected labels
- CLI exit codes (unknown symbol → 2, unknown strategy → 1)
- Cache hit skips network on 2nd run within TTL

### E2E smoke (1 test, `@pytest.mark.network` opt-in)

- Real Binance ETHUSDT 1H → ≥4000 bars
- Fit HMM → K ∈ {2,3,4,5}, transition_matrix rows sum to ~1
- Markdown emitted to disk with size >2KB

### Fixtures

`shared/wally_core/tests/fixtures/hmm_synthetic_bars.json` — 2000 bars, 3 injected regimes with fixed seed:
- Bars 0-800: mean_ret +0.1%, vol 0.8% → CALM_UP / TREND_UP
- Bars 800-1500: mean_ret 0%, vol 1.2% → CHOP
- Bars 1500-2000: mean_ret -0.3%, vol 2.5% → STRESS

## Acceptance criteria

### Functional

- [ ] `/hmm-analyze ETHUSDT A_VWAP` produces valid markdown in <30s on cache hit
- [ ] `--html` flag additionally produces HTML if plotly installed (graceful warn if not)
- [ ] `--suggest-mapping` prints diff to stdout, never writes file
- [ ] `/backtest --hmm-analyze ETHUSDT A_VWAP` equivalent to primary form
- [ ] All 5 strategies (A/B/C/D/E) supported

### Tests

- [ ] 20 unit tests green
- [ ] 3 integration tests green
- [ ] 1 E2E test green when run manually with `pytest -m network`
- [ ] Regression: `punk_smart_router.py --json` produces identical output before/after refactor

### Documentation

- [ ] Skill `@hmm-regime-analysis` with interpretation guide + 1 complete example
- [ ] CLAUDE.md gains "HMM Analysis Tool" section (Bundle 4 style)
- [ ] `memory/hmm_analysis.md` entry (when to invoke, no-go cases)
- [ ] Spec in `docs/superpowers/specs/2026-05-13-hmm-diagnostic-tool-design.md` (this file)
- [ ] Plan in `docs/superpowers/plans/2026-05-13-hmm-diagnostic-tool.md`

### No-regression

- [ ] `regime_mapping.json` unchanged
- [ ] Live paths (`/morning`, `/punk-morning`, `/punk-hunt`, `/punk-smart`, `/signal`, `/validate`) unchanged
- [ ] `.claude/cache/` gains `ohlcv_*` and `hmm_analyze.log`, nothing else touched
- [ ] Router still functions with extracted strategies

### Performance

- [ ] Cold cache + fetch ≤45s end-to-end
- [ ] Cache hit ≤15s end-to-end
- [ ] Peak memory <500MB

### Honest-first

- [ ] Markdown report includes explicit Caveats section
- [ ] Suggestion patch always includes "DRY-RUN — review manually" warning
- [ ] Low-sample regimes flagged ⚠️ and excluded from suggestions
- [ ] If all regimes are CHOP-like, report "no differentiation" message

## Dependencies

- New: `hmmlearn>=0.3.0` (~5MB, scientific-maintained, compatible with sklearn family)
- Optional: `plotly>=5.0` (only for `--html` flag, graceful fallback if missing)
- Already installed: `pandas`, `numpy`, `requests`, `pytest`, `scikit-learn`

Install: `.claude/scripts/.venv/bin/pip install 'hmmlearn>=0.3.0'`

## Open questions resolved during brainstorming

1. **Live wire-in?** No. Diagnostic only.
2. **Strategy scope?** The 5 in `punk_smart_router.py`.
3. **Universe?** Single asset per invocation.
4. **Output?** Markdown + optional HTML.
5. **Timeframe / K?** 1H × 6m, auto-detect K ∈ {2,3,4,5} via BIC.
6. **HMM library?** `hmmlearn`. Custom EM rejected (YAGNI).
7. **Strategy refactor?** Yes, but with regression test + fallback path if too risky.

## Open questions for implementation time

1. Does `punk_smart_router.py` structure allow clean extraction of strategies into ABC, or does it require the duplication fallback? Decide after inspecting code.
2. Are there assets in the bitunix watchlist not listed on Binance Futures? If so, document them as unsupported in the skill doc.
3. Should the suggest patch use sorted JSON keys (matching jq output) or preserve original order? Decide based on `regime_mapping.json` current format.

## Out of scope (deferred)

- Live wire-in to `/punk-smart` or auto-rebalance of `regime_mapping.json`
- Multi-asset batch mode
- Multi-timeframe HMM consensus
- Pine Script export
- Strategy import from `/strategy-import` JSON declarative
- HMM applied at portfolio level (systemic regime across all alts)
