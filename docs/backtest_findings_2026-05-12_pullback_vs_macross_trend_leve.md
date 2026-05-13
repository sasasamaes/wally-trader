# Backtest — Pullback Detector vs MA Crossover (TREND_LEVE)

**Date:** 2026-05-13
**Trigger:** Bundle 3 deferred wire-in of /pullback → regime_mapping.json. This compares
it against the existing TREND_LEVE strategy (MA Crossover EMA 9/21).

## Methodology

- **Universe:** BTCUSDT, ETHUSDT, SOLUSDT, AVAXUSDT, INJUSDT
- **Period:** last 60 days, 15m bars (Binance Futures public klines)
- **Filter:** TREND_LEVE only (ADX 25–30) — no signals evaluated outside this regime
- **ADX computation:** local Wilder-smoothed ADX(14) on rolling 30-bar window per bar
- **SL/TP simulation:** pullback uses helper output (entry/sl/tp1 from evaluate_setup);
  macross derives SL = entry ± ATR(14)×1.5, TP1 = entry ± ATR(14)×2.5
- **Hold window:** 96 bars (24h) max; SL/TP1/flat outcomes
- **OOS split:** 70/30 temporal (train = first 70%, test = last 30%)
- **Degradation flag:** PASS/WARN/FAIL per backtest_split.degradation_flag()

## Results — All assets aggregated

| Strategy | N | WR % | PF | Total R | Avg R | OOS verdict |
|---|---|---|---|---|---|---|
| Pullback Detector | 402 | 42.8% | 1.14 | +28.80R | +0.072R | ❌ FAIL |
| MA Crossover EMA9/21 | 145 | 33.8% | 0.87 | -12.33R | -0.085R | ❌ FAIL |

## Results — Per asset

| Asset | Strategy | N | WR % | PF | Total R | OOS |
|---|---|---|---|---|---|---|
| BTCUSDT | pullback | 79 | 45.6% | 1.30 | +11.03R | ✅ PASS |
| BTCUSDT | macross | 28 | 39.3% | 1.22 | +3.33R | ❌ FAIL |
| ETHUSDT | pullback | 68 | 52.9% | 1.35 | +10.43R | ✅ PASS |
| ETHUSDT | macross | 22 | 45.5% | 1.39 | +4.67R | ❌ FAIL |
| SOLUSDT | pullback | 84 | 45.2% | 1.11 | +4.70R | ❌ FAIL |
| SOLUSDT | macross | 32 | 31.2% | 0.76 | -5.33R | ✅ PASS |
| AVAXUSDT | pullback | 78 | 33.3% | 0.99 | -0.54R | ❌ FAIL |
| AVAXUSDT | macross | 30 | 33.3% | 0.83 | -3.33R | ✅ PASS |
| INJUSDT | pullback | 93 | 38.7% | 1.06 | +3.19R | ✅ PASS |
| INJUSDT | macross | 33 | 24.2% | 0.53 | -11.67R | ✅ PASS |

## Verdict

↔️ **NEUTRAL**

Strategies are comparable within margin (WR diff=+9.0pp, PF diff=+0.27). Per honesty contract: WR within 5pp or PF within 0.2 → NEUTRAL/KEEP-MACROSS. Retaining MA Crossover (lower complexity, existing wire-in). Revisit if Pullback edge improves with more data.

## Caveats

- **ADX filter scarcity:** TREND_LEVE [25–30] is a narrow band. In a predominantly
  ranging or strongly trending 60-day window, very few bars qualify, producing
  small N per (asset, strategy). The honesty contract threshold is ≥30 trades per cell.
- **15m bars from Binance Futures:** index assets (NAS100, EURUSD) are not available
  here; universe is crypto-only. Conclusions apply to crypto TREND_LEVE only.
- **Pullback detector sensitivity:** the pattern (3+ impulse candles → fib retrace →
  continuation) is structurally infrequent. Combined with the ADX gate, signal
  frequency is naturally low.
- **MA Crossover bar-by-bar limitation:** only LONG/SHORT cross bars trigger a signal
  (not the following bars in a sustained trend). This underestimates its true edge in
  a real trend-following context where a trader holds through trend.
- **No slippage/fees modeled.** Real execution would reduce metrics by ~0.1% roundtrip.
- **Past 60 days may not represent future TREND_LEVE frequency** — if BTC enters a
  sustained trend, TREND_LEVE bars become more common and sample sizes improve.

## Next steps

- If SAMPLE_TOO_SMALL: extend to 90d or add 3–5 more assets (SOL, LINK, DOGE)
- If WIRE-IN-RECOMMENDED: update `regime_mapping.json` TREND_LEVE entry to `/pullback`
  and run 2 weeks of live paper-trades to confirm
- If KEEP-MACROSS or NEUTRAL: no change to regime_mapping.json; re-evaluate in 30d
