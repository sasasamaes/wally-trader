---
name: optimize
description: Loop de optimización de estrategia con gates anti-overfit (RST + OOS
  + Monte Carlo) + export Pine
version: 1.0.0
metadata:
  hermes:
    tags:
    - wally-trader
    - command
    - slash
    category: trading-command
    requires_toolsets:
    - terminal
    - subagents
---
<!-- generated from system/commands/optimize.md by adapters/hermes/transform.py -->
<!-- Hermes invokes via /optimize -->


Auto-busca configs de estrategia y se queda **solo con la mejor que sobrevive los gates
anti-overfit**. Opcionalmente exporta el ganador como Pine `strategy()` importable a TradingView.

Destilado del video **"I Let Claude AI Opus 4.8 Trade For Me"** (Trading with DaviddTech),
donde Claude "loopea cada 5 min por 1 hora" optimizando hasta hallar backtests rentables.
El problema del video: presume un 112% PnL con **27% max DD** y curva sideways SIN validación
out-of-sample/Monte Carlo — el clásico **optimizar hacia overfit**. Este comando toma la idea
del loop pero la hace honesta: cada candidato pasa por RST + OOS + Monte Carlo (Bundle 5), y
si ninguno sobrevive, lo dice (no maquilla un sideways como ganador).

## Uso

```
/optimize [SYMBOL] [TF] [side]
/optimize BTCUSDT 4h long
/optimize ETHUSDT 1h short --export-pine
```

## Pasos

1. **Correr el loop:**
   ```bash
   .claude/scripts/.venv/bin/python .claude/scripts/optimize_strategy.py \
       --symbol BTCUSDT --tf 4h --days 365 --side long \
       --iterations 40 --validate-top 3 --export-pine --json
   ```
   - Pagina hasta `--days` de historia Binance Futures.
   - Random search de `--iterations` configs (don_len / ema_len / atr_len / sl_mult / max_hold)
     sobre la estrategia donchian_ema (Donchian breakout + filtro EMA).
   - Rankea por score barato; valida el **top `--validate-top`** con los 3 gates.
   - Estilo "loop del video": `--minutes M` busca configs hasta agotar M minutos (override de `--iterations`).

2. **Leer el veredicto:**
   - **RECOMMEND** (exit 0) → una config pasó RST=PASS **Y** OOS≠FAIL **Y** candles≠OVERFIT_SUSPECT.
   - **NONE_SURVIVED** (exit 2) → ninguna pasó. El "mejor" backtest del leaderboard es probable
     overfit/suerte de régimen. **No operar** (verdict honesto que el video no da).

3. **Export Pine (`--export-pine`):** si hay ganador, escribe
   `system/pine_library/opt_donchian_ema_<symbol>_<tf>_<side>.pine` — un `strategy()` v6
   importable a TradingView para verificar el backtest visualmente. **Trátalo como draft**:
   compila + revisa visual + re-backtestea antes de confiar (el backtester de TV puede diferir
   levemente del motor Wally — salida ATR/Donchian sin pyramiding).

## Flags útiles

- `--iterations N` (default 40) | `--minutes M` (presupuesto de tiempo, estilo loop del video)
- `--validate-top K` (default 3) — cuántos top candidatos pasan por los gates caros
- `--min-trades N` (default 15), `--rst-perms N` (default 1000), `--mc-sims N` (default 60)
- `--side long|short`, `--days N`, `--seed N` (determinismo)
- `--bars-file PATH` — OHLCV propio en vez de fetch

## Notas honestas

- El optimizador NO inventa edge: si la estrategia donchian_ema no funciona en ese símbolo/TF/
  régimen, devuelve NONE_SURVIVED. Eso es feature.
- Para validar manualmente un candidato puntual: `/rst` + `/montecarlo`.
- El espacio de búsqueda cubre la familia donchian_ema (trend-following). Otras familias se
  añaden extendiendo `SEARCH_SPACE` + `backtest_config` en el script.
- Relación con `/backtest`: `/backtest` es one-shot (una config o grid manual vía agente);
  `/optimize` es el loop autónomo que rankea + valida + exporta.

$ARGUMENTS
