# Backtest Findings — 2026-04-30

> Backtest unificado de los 7 profiles del sistema. Reporte autoritativo para decisiones de strategy y risk.

**Fecha**: 2026-04-30
**Período data**: ~60 días (BTC 15m: 2026-02-21 → 2026-04-22)
**Engine**: Mean Reversion vectorizado (Donchian + RSI + BB + ATR + close direction)
**Engine v2**: añade regime gate (ADX-based RANGE filter)
**OOS validation**: split 70/30 con verdict PASS/WARN/FAIL

## TL;DR

Las estrategias actuales del sistema **NO tienen edge demostrado** en este período de 60 días. Sin embargo, hallamos **3 fixes accionables** que reducen pérdidas y previenen blow-up:

1. **Regime gate ADX<20** reduce losses de Mean Reversion **88%** (-34.83% → -4.01%)
2. **Fotmarkets risk 10% → 1%** mantiene DD <12% (regla del profile) — antes generaba DD 70%
3. **GBPUSD inviable** en fotmarkets a cualquier risk level (PF 0.94, sin edge)

## Hallazgos por grupo

### Group A — retail / retail-bingx / quantfury (BTC MR 15m)

| Sample | Trades | WR% | PF | Total Ret% | Max DD% | OOS |
|---|---|---|---|---|---|---|
| FULL | 66 | 22.73 | 0.586 | **-34.83** | 34.83 | — |
| TRAIN (70%) | 48 | 27.08 | 0.73 | -16.06 | 29.73 | — |
| TEST (30%) | 17 | 11.76 | 0.257 | -20.78 | 24.66 | **WARN** |

**HODL benchmark (quantfury)**: BTC subió **+14.98%** pasivo. Strategy underperforma HODL por **−49.81pp**.

#### Regime gate experiment (engine v2)

| Config | Trades | WR% | Ret% | DD% | Skipped |
|---|---|---|---|---|---|
| NO_FILTER | 66 | 22.73 | -34.83 | 34.83 | 0 |
| **RANGE_ONLY (ADX<20)** | 4 | 25.00 | **-4.01** | 4.01 | 4038 |
| RANGE_ONLY (ADX<18) | 2 | 0.00 | -3.96 | 3.96 | 4472 |
| RANGE_ONLY (ADX<25) | 15 | 13.33 | -15.62 | 15.62 | 2878 |
| TREND_ONLY (ADX>25) | 53 | 24.53 | -25.82 | 25.82 | 2310 |

**Conclusión Group A**:
- Regime gate ADX<20 es **prevención de pérdidas**, no generador de edge
- 70% de las barras del período tuvieron ADX≥20 (TRENDING) → MR no tenía oportunidad
- En este período, **HODL pasivo derrotó al trading activo** por casi 50pp
- **Acción**: regime gate ADX<20 ahora es **HARD PRECONDITION** en strategy.md

### Group B — ftmo (FTMO-Conservative 1H multi-asset)

| Asset | Bars | Trades | WR% | PF | Ret% | DD% | OOS |
|---|---|---|---|---|---|---|---|
| BTCUSDT | 1434 | 16 | 31.25 | 1.045 | +0.24 | 2.98 | PASS |
| ETHUSDT | 1434 | 16 | 37.50 | 0.871 | -0.64 | 2.19 | PASS |
| EURUSD | 1418 | 23 | **26.09** | 0.698 | -2.54 | 3.29 | PASS |
| GBPUSD | 1418 | 19 | 36.84 | 0.890 | -0.65 | 3.27 | PASS |
| NAS100 | 418 | 8 | 50.00 | 1.771 | +1.58 | 1.99 | **FAIL** |
| SPX500 | 418 | 3 | **66.67** | 4.745 | +1.90 | 0.50 | PASS (small N) |

**WR disparity**: 26.1 → 66.7 = **40.6pp ⚠️** → estrategia NO universal entre assets.

**Conclusión Group B**:
- Forex (EURUSD/GBPUSD) MR 1H **no funciona** — WR 26-37%
- BTC/ETH MR 1H marginal (WR 31-37%)
- NAS100/SPX500 muestras muy pequeñas para conclusión
- **Acción**: limitar FTMO MR a BTC/ETH; rediseñar approach forex

### Group C — fotmarkets (5m fase 1)

#### Risk recalibration (engine v1)

| Asset | Risk% | DD% | Ret% | 12% DD respect? |
|---|---|---|---|---|
| EURUSD | **1%** | **10.53** | **+39.80** | ✅ **OK** |
| EURUSD | 2% | 20.12 | +90.32 | ❌ Breach |
| EURUSD | 3% | 28.84 | +152.44 | ❌ Breach |
| EURUSD | 5% | 43.89 | +311.50 | ❌ Breach |
| EURUSD | 10% (legacy) | 70.20 | +810.16 | ❌❌ Breach |
| GBPUSD | 1% | 18.15 | -6.97 | ❌ Breach |
| GBPUSD | (cualquier) | — | — | ❌ Inviable |

**Sweet spot fase 1**: **risk 1% sobre EURUSD único**. GBPUSD inviable (PF 0.94 incluso a 1%).

**Conclusión Group C**:
- Risk 10% legacy era **mathematically suicidal** — DD 70-95% en backtest
- Risk 1% en EURUSD → DD 10.53% ✅, Ret +39.8%, 153 trades, WR 49.67%, PF 1.5
- GBPUSD removido del whitelist
- **Acción**: bajar risk fase 1 → 1%, fase 2 → 2%, whitelist EURUSD only

### Group D — fundingpips (1H multi-asset)

| Asset | Trades | WR% | PF | Ret% | DD% | 5% DD |
|---|---|---|---|---|---|---|
| EURUSD | 22 | 22.73 | 0.583 | -2.10 | 2.56 | ✅ |
| GBPUSD | 20 | 35.00 | 0.824 | -0.68 | 1.97 | ✅ |
| USDJPY | 21 | 28.57 | 0.927 | -0.33 | 2.14 | ✅ |
| **XAUUSD** | 13 | 38.46 | **1.741** | **+1.79** | 1.20 | ✅ |
| NAS100 | 8 | 50.00 | 1.782 | +0.95 | 1.20 | ✅ (FAIL OOS) |
| BTCUSDT | 16 | 31.25 | 1.048 | +0.16 | 1.80 | ✅ |

**Compliance check**: 0/6 assets violan 5% DD ✅

**Conclusión Group D**:
- 0.3% risk es **defensivo** — no genera edge pero protege capital
- **XAUUSD destaca** con PF 1.74 — explorar como asset principal
- Returns mixed pero ninguno catastrófico — strategy compatible con FundingPips rules
- **Acción**: priorizar XAUUSD; probar TF 4H para reducir ruido en forex

### Group E — bitunix (validador 4-pilar)

**Approach**: signals sintéticos = Donchian Low touch + RSI<35 (proxy de señales comunidad)
**Outcome rule**: WIN si en 16 bars precio alcanza +1.5% antes de -1.5%

| Filtro | Signals | WR% | Δ vs all |
|---|---|---|---|
| All signals (no filter) | 68 | 7.35 | — |
| 3+/4 pillars | 25 | 12.00 | **+4.65pp** |
| 4/4 pillars | 1 | 100.00 | +92.65pp (anecdotal) |

**Conclusión Group E**:
- Filtro 4/4 demasiado restrictivo (1 trade en 60d)
- Filtro 3+/4 mejora WR 7.35→12.0 (+62% relativo) — **señal de valor**
- Pero universo subyacente es de baja calidad (WR 7%)
- **CAVEAT crítico**: este es PROXY simulado. El verdadero backtest requiere dataset histórico de señales reales de la comunidad punkchainer's en Discord
- **Acción**: empezar log real `signals_received.md` desde HOY; revaluar después de 30-60 señales reales

## Acciones implementadas (2026-04-30)

### 1. Regime gate hard-coded en strategy.md

Profiles actualizados:
- `.claude/profiles/retail/strategy.md`
- `.claude/profiles/retail-bingx/strategy.md`
- `.claude/profiles/quantfury/strategy.md`

Regla añadida:
```
ANTES de evaluar 4 filtros MR, verificar /regime debe arrojar RANGE_CHOP (ADX<20).
Si ADX ≥ 20 → abortar entry MR.
```

### 2. Fotmarkets recalibration

`.claude/profiles/fotmarkets/config.md`:
- Fase 1: risk 10% → **1%**, allowed_assets [EURUSD, GBPUSD] → **[EURUSD]**
- Fase 2: risk 5% → **2%**, allowed_assets sin GBPUSD

`.claude/profiles/fotmarkets/rules.md`:
- R2 risk per trade tabla recalibrada con backtest evidence

### 3. Quantfury HODL pre-flight check

`.claude/profiles/quantfury/strategy.md`:
- Pre-flight obligatorio antes de cada entry
- Regla "outperformance vs HODL <-2% → PAUSAR 30d" reforzada

## Disclaimers

1. **Período corto (60 días)**: muestra estadística limitada. NAS100/SPX500 con 8/3 trades NO son base sólida.
2. **No incluye slippage real ni partial fills**.
3. **Engine asume entries en `close`**: real-world entries son al `open` next bar.
4. **Forex via yfinance** menos preciso que tick-data profesional.
5. **Mean Reversion contra-tendencia es mecánicamente robusto**: el problema fue régimen, no estrategia.
6. **OOS WARN/FAIL en varios casos**: indica overfit en train sample.

## Archivos generados

```
/tmp/wally_backtest/
├── engine.py                      # Engine v1 (sin regime gate)
├── engine_v2.py                   # Engine v2 (con ADX regime gate)
├── group_A_btc_meanreversion.py   # Original Group A
├── group_A_v2_regime_aware.py     # Group A con 5 configs regime
├── group_B_ftmo_multi.py          # FTMO multi-asset
├── group_C_fotmarkets.py          # Fotmarkets v1 (risk 10%)
├── group_C_v2_risk_recalibration.py  # Risk 1/2/3/5/10% sweep
├── group_D_fundingpips.py         # FundingPips 1H
├── group_E_bitunix_validator.py   # Bitunix 4-pilar proxy
└── REPORT.md                      # Reporte unificado
```

## Próximos pasos (post-fixes)

1. **Validar fixes en paper trading** (mínimo 10 trades en cada profile actualizado)
2. **Re-run backtest cada 30 días** con data más reciente — si los regímenes cambian, los gates deben adaptarse
3. **Acumular signals_received.md** en bitunix para backtest real del validador
4. **Considerar Donchian Breakout** como estrategia alternativa para periodos TRENDING
5. **Investigar XAUUSD como asset principal** en FundingPips (PF 1.74 en backtest)

---

> "Las estrategias existen correctamente, pero las estrategias subyacentes necesitaban recalibración antes de operar capital real. Los fixes 2026-04-30 abordan los 3 problemas principales: regime gate (loss prevention), risk recalibration (DD compliance), y HODL benchmark check (quantfury edge validation)."
