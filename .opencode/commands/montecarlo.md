---
description: Monte Carlo robustness — reshuffle de trades (drawdown) + candles sintéticos
  (overfit)
---

Corre **Monte Carlo** para estresar un resultado de backtest, igual que el dashboard de
Jesse en el video "Opus 4.8 + Claude Code + MCP = Algo Trading on Autopilot". Dos pruebas:

1. **trades (reshuffle)** — reordena la secuencia de los trades (mismos trades, distinto
   orden). El retorno final es invariante; el max drawdown NO. Responde "¿qué pasa con mi
   sizing si las pérdidas se agrupan al inicio?". Output: distribución de max DD.
2. **candles (block-bootstrap)** — genera OHLCV sintético desde la data real (preserva
   geometría de vela + autocorrelación) y corre la estrategia en cada path. Stress test de
   overfit: si el Sharpe original supera el p95 sintético → sospecha de overfit.

## Uso

```
/montecarlo trades              # usa los retornos del último backtest
/montecarlo candles BTCUSDT 30m # estrategia donchian_ema del video
```

## Pasos

### Modo trades (reshuffle)
1. Junta los pnl% por trade del último backtest en un JSON (lista de floats):
   ```bash
   echo '[0.05,-0.02,0.03,-0.08,0.06,...]' > /tmp/trades.json
   ```
2. Corre:
   ```bash
   .claude/scripts/.venv/bin/python .claude/scripts/monte_carlo.py \
       --mode trades --trades-file /tmp/trades.json --json
   ```
3. Interpretar:
   - **OK** (exit 0) → DD estable bajo reordenamiento; el sizing tolera el peor caso.
   - **WARN** (exit 2) → el DD p95 supera al original >50%. Dimensiona el sizing para el
     **p95**, no para el DD observado.
   - `--mc-method bootstrap` → resample con reemplazo (también varía el retorno + prob. de retorno negativo).

### Modo candles (overfit)
1. Corre:
   ```bash
   .claude/scripts/.venv/bin/python .claude/scripts/monte_carlo.py \
       --mode candles --symbol BTCUSDT --tf 30m --days 365 --n 100 --json
   ```
2. Interpretar la **zona** del Sharpe original vs la distribución sintética:
   - `ROBUST` (entre mediana y p95) → robustez razonable. ✅
   - `OVERFIT_SUSPECT` (> p95, exit 2) → el real bate a casi toda la data sintética; la
     estrategia memorizó la trayectoria, no una estructura. ⚠️
   - `FRAGILE` (bajo la mediana) / `WEAK` (bajo p5) → poco o ningún margen.

## Flags útiles

- `--n N` — # simulaciones (default 1000 trades / 100 candles)
- `--block N` — tamaño de bloque del bootstrap de candles (default 10)
- `--side long|short`, `--days N`, `--tf`
- `--bars-file PATH` — OHLCV propio en modo candles

## Notas honestas

- El Monte Carlo es el **último gate** del flujo: RST → backtest → OOS → Monte Carlo.
- "OK"/"ROBUST" reduce el riesgo de overfit pero NO lo elimina — la data sintética hereda
  los sesgos de la real (un solo régimen de 1 año sigue siendo 1 régimen).
- Para deep-validation con walk-forward + VaR ver `integrations/jesse/` (MCP de Jesse).

$ARGUMENTS
