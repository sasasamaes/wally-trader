# Design — AI Strategy Optimization Bundle (Bundle 6)

**Fecha:** 2026-05-31
**Fuente:** Video *"I Let Claude AI Opus 4.8 Trade For Me"* (Trading with DaviddTech,
`youtube.com/watch?v=tkAq6g2Gjz4`).

## Problema / oportunidad

El video deja a Claude "loopear cada 5 min por 1 hora" optimizando una estrategia hasta
hallar backtests rentables (BTC 4h 112% PnL, **27% max DD**, curva sideways; ETH/SOL 4h).
Demuestra el flujo build → backtest → optimize → export Pine → (live Bybit). **Pero presenta
los "ganadores" sin validación out-of-sample ni Monte Carlo** — el clásico optimizar-hacia-
overfit. También usa un MCP externo (Trader Dev) y auto-ejecuta trades reales en Bybit.

El proyecto ya tiene `/backtest` (one-shot vía agente), `/loop` (genérico) y, desde el
Bundle 5, gates de validación rigurosos (RST + OOS + Monte Carlo). Falta empaquetar el **loop
autónomo de optimización** — y hacerlo honesto (con esos gates).

## Decisión (alcance elegido por el usuario)

Implementar 3 de los elementos del video; excluir explícitamente la auto-ejecución live:

1. **`/optimize` — loop con gates anti-overfit.** Random search sobre la familia
   donchian_ema → rankea por score barato → valida el top-K con RST + OOS + Monte Carlo →
   recomienda SOLO la que sobrevive los 3. Si ninguna pasa, lo dice (honest verdict que el
   video no da).
2. **Export Pine `strategy()`** del ganador → `system/pine_library/<slug>.pine`, importable a
   TradingView para verificación visual del backtest.
3. **Trader Dev MCP — scaffold ready-to-connect.** El usuario lo pidió; pero NO hay endpoint
   público (gated tras signup/comment). Se documenta qué es, su solapamiento total con el
   stack nativo, y un template `claude mcp add` con placeholder de URL. No se inventa endpoint.

**Excluido a propósito:** auto-ejecución en exchange (Bybit del video). Choca con la filosofía
manual/human-approve y las reglas de riesgo del proyecto.

## Arquitectura

`.claude/scripts/optimize_strategy.py`:
- Reusa: `rule_significance` (`donchian_ema_entries`, `make_donchian_atr_exit`,
  `significance_test`, `fetch_paginated`), `monte_carlo` (`monte_carlo_trades/candles`,
  `max_drawdown`, `sharpe`), `backtest_split` (`temporal_split`, `degradation_flag`).
- `backtest_config(bars, params, side)` → entries + returns + métricas {n,wr,pf,ret,dd,sharpe}.
- `optimize(...)`: random search seeded (`--iterations` o presupuesto `--minutes` estilo loop
  del video) → `base_score` rankea → valida top-K (gates caros solo en los mejores, igual que
  el video backtestea muchos y valida pocos) → `winner` = primera que sobrevive RST+OOS+MC.
- `to_pine_strategy(params, ...)` / `write_pine(...)`: emite Pine v6 `strategy()` correcto
  (statements top-level sin indentar, `ta.*`, `input.*`, comisión 0.05%, pyramiding 0).

Gate de recomendación: `RST=PASS AND OOS≠FAIL AND MC_candles≠OVERFIT_SUSPECT`.

## Por qué este diseño

- **Anti-overfit por construcción:** el video optimiza una métrica y muestra el mejor backtest;
  nosotros optimizamos pero filtramos con los gates → el output típico real es NONE_SURVIVED
  (verificado: BTC 4h long últimos 365d → ninguna config pasa, todas fallan RST+OOS). Honesto.
- **Validar solo el top-K** mantiene el costo manejable (RST 1000 perms + MC 60 sims son caros).
- **Determinismo por `seed`** → reproducible y testeable.

## Caveats honestos

- El optimizador NO inventa edge: cubre la familia donchian_ema (trend-following). Si no hay
  edge en ese símbolo/TF/régimen → NONE_SURVIVED. Otras familias = extender `SEARCH_SPACE`.
- El Pine exportado es **draft**: compilar + revisar visual + re-backtestear (el backtester de
  TV difiere levemente del motor Wally — salida ATR/Donchian sin pyramiding). No se compiló
  live aquí porque TV Desktop estaba apagado.
- Trader Dev MCP: sin endpoint público; scaffold queda ready-to-fill.

## Plan
`docs/superpowers/plans/2026-05-31-ai-strategy-optimization-bundle.md`
