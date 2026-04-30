# Estrategia: Mean Reversion 15m (RETAIL)

Validada con **100% WR** y **+15.1%** en backtest 3 días frente a 144 configs.

> ⚠️ **Backtest 60d 2026-04-30**: en período TRENDING UP (BTC +15%) sin regime gate, MR
> dio -34.83% Ret / WR 22.7% / 66 trades. Con regime gate ADX<20 las pérdidas bajaron
> a -4.01% (4 trades) — el gate es **prevención de pérdidas**, no generador de edge.
> **Consecuencia**: regime gate ADX<20 ahora es **HARD PRECONDITION** (ver abajo).
> Detalles: `docs/backtest_findings_2026-04-30.md`.

## 🚨 Regime gate (precondition obligatoria, agregada 2026-04-30)

**ANTES de evaluar los 4 filtros**, verificar régimen 1H:

```bash
/regime
# → debe arrojar RANGE_CHOP (ADX < 20) para permitir Mean Reversion
```

| ADX(14) 1H | Régimen | Acción |
|---|---|---|
| < 20 | RANGE_CHOP | ✅ MR habilitada — evalúa los 4 filtros |
| 20-25 | TRANSITION | ⚠️ NO MR — esperar confirmación |
| 25-30 | TREND_LEVE | 🔄 Switch a MA Crossover (`/macross`) |
| 30-40 | TREND_FUERTE | 🔄 Switch a Donchian Breakout |
| > 40 | TREND_EXTREMO | 🚫 NO operar (volatilidad extrema) |

Si ADX ≥ 20 → **abortar entry MR**, anotar en log "skipped: regime no chop".
Esto **es bloqueo hard** — los 4 filtros pueden alinear pero si ADX ≥ 20 la entrada
se descarta. Backtest valida que esto reduce losses 88% en períodos de tendencia.

## Parámetros

| Parámetro | Valor |
|---|---|
| Timeframe | 15m |
| Donchian | 15 velas |
| Edge de entrada | ±0.1% del extremo Donchian |
| RSI(14) | OB 65, OS 35 |
| Bollinger Bands | (20, 2) confirmación obligatoria |
| ATR length | 14 |
| SL | 1.5 × ATR (adaptativo) |
| TP1 (40%) | 2.5 × SL → SL a BE |
| TP2 (40%) | 4.0 × SL |
| TP3 (20%) | 6.0 × SL **o** trailing EMA(20) 15m (ver §Trailing) |
| Leverage | 10x |
| Ventana | CR 06:00 – 23:59 |

## Entradas — 4 filtros obligatorios

**LONG:**
1. Precio toca o cruza Donchian Low(15) (dentro 0.1%)
2. RSI < 35
3. Low de vela toca BB inferior
4. Vela cierra verde

**SHORT:**
1. Precio toca o cruza Donchian High(15) (dentro 0.1%)
2. RSI > 65
3. High de vela toca BB superior
4. Vela cierra roja

## Estrategia 3 — MA Crossover (EMA 9/21) para TRENDING

Activa cuando régimen detectado es TREND_LEVE o TREND_FUERTE (ADX > 25).

| Parámetro | Valor |
|---|---|
| Timeframe | 15m (entry) — 1H (confirmación) |
| EMA fast | 9 |
| EMA slow | 21 |
| Filtro trend | close 15m por encima/debajo de EMA(21) |
| SL | 1.5 × ATR(14) |
| TP1 (40%) | 1.5R → SL a BE |
| TP2 (40%) | 3.0R |
| TP3 (20%) | Trailing EMA(21) 15m vía `/trail long X 21` |
| Confirmación | Volumen vela cross ≥ promedio 20 velas |

Helper: `python3 .claude/scripts/macross.py --file /tmp/bars15m.json --quick`
Comando: `/macross`

**Cuándo elegirla sobre Breakout:**
- Si ADX > 25 pero no hay nivel claro de Donchian a romper → MA Crossover
- Si Donchian extremo ya fue tocado y rebotó (false breakout) → MA Crossover en próximo cross
- Mean Reversion solo si ADX < 25

## Trailing Stop con EMA(20) — modo de salida alternativo (TP3 runner)

El runner (20% del size restante tras TP1+TP2) puede usar **uno** de dos modos:

**Modo A — Target fijo (default):** TP3 a 6.0 × SL.

**Modo B — Trailing EMA(20) en 15m:** preferible cuando el mercado está en TRENDING (ADX>25)
porque captura más del rally sin dejar gain on table:
- Tras TP2 cierra, dejas el runner abierto sin target fijo
- Cada cierre de vela 15m calcula EMA(20)
- Si próximo cierre 15m **toca** EMA(20) (precio cruza la EMA por debajo en LONG / arriba en SHORT) → exit market
- Mientras EMA(20) suba (LONG) o baje (SHORT), el trail se ajusta solo

Helper: `python3 .claude/scripts/trailing_stop.py --file /tmp/bars15m.json --side long --entry X --current Y`
o usa el comando `/trail`.

**Cuándo elegir B sobre A:**
- ADX(14, 1H) > 25 al cerrar TP2 → modo B
- Régimen detectado TRENDING UP/DOWN → modo B
- Si RANGE/CHOP → modo A (target fijo evita whipsaw en EMA)

## Invalidación

- 2 SLs consecutivos → parar ese día
- Días con noticias macro (CPI, Fed) → no operar
- ATR 2x promedio → no operar (régimen volatile)

## Estrategia secundaria

Donchian Breakout si BTC rompe el range (cierre 4H fuera de 73.5k–78.3k con volumen >2x promedio). Config: Donchian(20), buffer 30 pts, vol >300 BTC, SL 0.5%, TP 0.75/1.25/2.0%.
