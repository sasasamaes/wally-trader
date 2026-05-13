---
name: hmm-regime-analysis
description: Use when you want to analyze how a given strategy behaves across HMM-detected regimes for an asset, BEFORE deciding whether to update regime_mapping.json. Strictly diagnostic — never wires into live trading. Read this skill to understand how to interpret transition matrices and when HMM disagrees with ADX detection.
---

# HMM Regime Analysis Skill

## When to invoke

- You suspect a strategy is performing poorly because the ADX-based regime detection is wrong for an asset.
- You want to see how a strategy fares under STRESS vs CHOP vs TREND_UP regimes detected by HMM.
- You're considering updating `regime_mapping.json` for an asset and want backtest-grounded data.

## When NOT to invoke

- You want to execute a trade. (Use `/signal`, `/validate`, or `/punk-smart` — those are live paths. HMM is diagnostic.)
- You want to backtest a strategy in general. (Use `/backtest`.)
- All regimes in the asset are CHOP-like (lateral market) — HMM provides no differentiation.

## How to interpret outputs

### Regime Distribution table

- A state with `pct_bars < 5%` is flagged ⚠️ low_sample. Treat its label and backtest with skepticism — too few observations.
- If all states are labeled CHOP* the asset has been lateral for ~6 months and HMM cannot separate regimes. Try a longer lookback or different asset.

### Transition Matrix

- Diagonal values (state stays the same) typically 0.7–0.95 for daily-scale regimes. A diagonal value < 0.5 suggests an unstable / noisy regime.
- Off-diagonal values show transition probabilities. `P(STRESS → CALM_UP) = 0.05` means STRESS rarely flips directly to a bullish regime — usually transitions through CHOP first.
- Use it to estimate how long the *current* regime is likely to persist.

### Backtest per Regime

- `GLOBAL` row is the baseline (strategy run unconditionally). Per-regime rows partition the GLOBAL trades by HMM state at entry.
- A regime row with `low_trade_count=⚠️` (n<10) has noisy WR/PF — do not rely on it.
- The valuable signal is when the strategy has clear differential performance: e.g., PF=1.74 in CHOP vs PF=0.62 in STRESS means "deploy in CHOP, sit out in STRESS".

### Recommendations / Dry-run patch

- The patch is generated ONLY when:
  - At least one regime has PF > 1.0
  - That regime has ≥10 trades (not low_trade_count)
  - Excluding GLOBAL
- The patch is **never applied to `regime_mapping.json`**. Review it manually before any edit.

## Reproducing the analysis Alex Ruiz demonstrates

In the video `Cdhqu6rIvb0`, Alex generates an HMM dashboard for a strategy on EUR/USD daily. Our tool replicates this for crypto on Binance Futures 1H. The conceptual mapping:

| Alex's video | Our tool |
|---|---|
| EUR/USD daily | Binance Futures `SYMBOL` 1H |
| Auto-detect 2–5 regimes | `K ∈ {2,3,4,5}` selected via BIC |
| Volatility + cumulative returns + momentum | log_return + vol_20 + momentum_14 |
| "Global" vs "Combined" rentabilidad | `GLOBAL` row vs per-regime rows |
| Top-3 parameters per regime | Out-of-scope V1 |

## Honest-first caveats

- HMM regimes are probabilistic — a bar labeled STRESS has *P(STRESS)* high but not 1.0.
- The 5% low_sample threshold is a heuristic — adjust `LOW_SAMPLE_THRESHOLD` in `labeling.py` if you have reasons to.
- Strategy backtest uses TP1/SL resolution over max 6h hold — not the same as router's live exit logic which uses DUREX + scaled exits.
- This tool's findings are NEVER auto-applied. The decision to edit `regime_mapping.json` is yours.
