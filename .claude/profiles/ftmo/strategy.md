# Estrategia: FTMO-Conservative (multi-asset)

Diseñada para pasar el challenge FTMO 1-Step en 10-30 días con bajo riesgo.

> 🆕 **Backtest 2026-04-30 — strategy mapping per-asset (NUEVO):**
>
> Mean Reversion 1H universal tenía WR 22-67% disparity (no universal).
> Backtest probó alternativas — winners por asset:
>
> | Asset | Estrategia ganadora | TF | WR | PF |
> |---|---|---|---|---|
> | XAUUSD ⭐ | Donchian Breakout | 4H | 66.67 | 2.175 |
> | USDJPY | MA Crossover (9/21) | 1H | 55.17 | 1.861 |
> | EURUSD | Donchian Breakout | 1H | 55.17 | 1.357 |
> | BTCUSDT | Mean Reversion | 1H | 31.25 | 1.048 |
> | GBPUSD ❌ | (sin edge en ninguna) | — | — | — |
>
> Ver `docs/backtest_findings_2026-04-30.md` Group F. **GBPUSD removido del universo.**

## 🎯 Strategy mapping per-asset (override universal MR)

ANTES del análisis multi-asset diario, aplicar este mapping según asset elegido:

| Asset | Strategy aplicable | TF |
|---|---|---|
| BTCUSD/ETHUSD | Mean Reversion | 1H |
| EURUSD | **Donchian Breakout** | 1H |
| USDJPY | **MA Crossover (9/21)** | 1H |
| XAUUSD | **Donchian Breakout** | 4H |
| NAS100/SPX500 | TBD (data insuficiente backtest) | — |
| GBPUSD | ❌ NO TRADEAR | — |

## Principios

1. Target diario **1.0-1.5%** (no persigues más aunque tengas setup)
2. SL **0.4% fijo** por trade (no ATR-based)
3. Size **0.5% risk** = $50 inicial por trade
4. **Multi-asset selection**: 1 setup A-grade por día
5. Asset rotation por EV diario
6. Best Day compliance natural: cierras terminal si ya +1.5% del día

## Universo

| Asset | MT5 Symbol (validar) | Sesión óptima CR | Régimen ideal |
|---|---|---|---|
| BTCUSD | `BTCUSD` | 06:00-10:00 | RANGE |
| ETHUSD | `ETHUSD` | 06:00-10:00 | RANGE/TREND leve |
| EURUSD | `EURUSD` | 07:00-10:00, 14:00-16:00 | RANGE |
| GBPUSD | `GBPUSD` | 07:00-11:00 | TREND leve |
| NAS100 | `US100.cash` o `NAS100` | 08:30-15:00 | TREND (ADX>25) |
| SPX500 | `US500.cash` o `SPX500` | 08:30-15:00 | TREND/RANGE |

**Ventana operativa:** CR 06:00–16:00. Post-16:00 = no operar (cierre sesión US).

## Filtros de selección diaria

Score A/B/C/D por asset (morning-analyst-ftmo lo calcula):
- **A**: régimen RANGE + RSI en zona + BB extremo + volumen OK
- **B**: RANGE pero solo 2/3 condiciones técnicas
- **C**: régimen ambiguo
- **D**: VOLATILE o NO DATA → skip

**Selección:**
- 1 A-grade → ese es el trade del día
- 2+ A-grades → prioriza menor spread + sesión activa
- Todos B o peor → no operar hoy

## Entradas — 7 filtros simultáneos

**LONG:**
1. Precio toca Donchian Low(20)
2. RSI(14) < 30
3. BB(20,2) Lower toca
4. Vela 15m cierra verde con cuerpo ≥ 60% del rango
5. Spread ≤ 1.5× spread promedio del asset
6. Hora dentro de sesión óptima del asset
7. Guardian OK o OK_WITH_WARN

**SHORT:** espejo (Donchian High, RSI > 70, BB Upper, cuerpo rojo 60%+).

## Gestión de trade

| Componente | Valor |
|---|---|
| Entry | Mercado o limit dentro 0.1% de zona |
| SL | 0.4% del entry (fijo) |
| TP1 (50%) | 0.6% (1.5R) → mueve SL a BE |
| TP2 (50%) | 1.2% (3.0R) |
| Trailing post-TP1 | Stop a mid entre entry y TP2 (default) **o** EMA(20) 15m si ADX>25 |
| Force exit | 16:00 CR |
| Overnight | PROHIBIDO |

**Trailing EMA(20) 15m** (alternativa al stop discreto): tras TP1, en lugar de saltar SL a
mid entry-TP2, dejar trailing dinámico con EMA(20) de bars 15m. Salir cuando close 15m
cruce la EMA en contra. Helper: `python3 .claude/scripts/trailing_stop.py`. Aplica cuando
régimen del asset es TREND_LEVE/FUERTE (ADX>25 — verifica con `python3 .claude/scripts/adx_calc.py`).

**R:R efectivo:** +0.9% notional por trade exitoso = **+0.45% equity** con size 0.5%.

Matemática: 3-4 trades exitosos/semana × 0.45% = ~1.8%/sem ≈ 10% en 6-8 semanas.

## Position sizing

```python
def calc_lots(asset, entry, sl, equity, risk_pct=0.5):
    risk_usd = equity * (risk_pct / 100)        # $50
    sl_pips = abs(entry - sl)
    pip_value = get_pip_value(asset)            # desde mt5_symbols.md
    lots = risk_usd / (sl_pips * pip_value)
    return round(lots, 2)
```

Tabla de pip values se valida el primer día del challenge con screenshots de la pantalla Specification de MT5 para cada símbolo.

## Validación obligatoria antes de challenge pago

1. Sistema completo implementado (fases 1-5 del spec)
2. Backtest python (`backtest_ftmo.py`) sobre 3 meses BTC + ETH + EURUSD: WR>55%, DD<5%, 0 daily breaches simulados
3. Paper trading en FTMO Free Trial 14 días, 10+ trades reales: WR>55%, 0 overrides, 0 breaches
4. Si cumple → comprar challenge $93.43
5. Si no cumple → refinar estrategia, repetir backtest + paper
