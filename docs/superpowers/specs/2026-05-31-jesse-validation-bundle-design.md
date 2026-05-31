# Design — Jesse Validation Bundle (RST + Monte Carlo + Jesse lab)

**Fecha:** 2026-05-31
**Fuente:** Video *"Opus 4.8 + Claude Code + MCP = Algo Trading on Autopilot"*
(Algo-trading with Saleh, `youtube.com/watch?v=1SLbe0k6x4I`, framework Jesse).

## Problema

El video destila un flujo de validación de estrategias más riguroso que el del proyecto.
Hoy el `backtest-runner` declara una config "ganadora" con métricas + OOS (split 70/30).
Faltan dos gates que el video martilla:

1. **Rule Significance Test (RST):** una estrategia rentable NO prueba que su entrada tenga
   edge. En un bull year un "always long" gana sin poder predictivo. Hay que probar que la
   regla de ENTRADA bate al azar antes de invertir en sizing/exits/backtest.
2. **Monte Carlo:** un backtest puntual no dice si el resultado es robusto. Reshuffle de
   trades mide el riesgo de drawdown del sizing; candles sintéticos detectan overfit.

El tercer método del video (out-of-sample multi-período) **ya existe**:
`.claude/scripts/backtest_split.py` (`temporal_split` + `report_oos`).

## Decisión

Enfoque de **dos pistas** (el motor de backtest propio está demasiado integrado —
profiles, `regime_mapping.json`, TV MCP — para reemplazarlo por Jesse):

### Pista 1 — Helpers nativos (destilación durable)
Portables, corren sobre el motor existente, benefician a todos los profiles sin depender
de Jesse:
- `rule_significance.py` — RST por **permutación de timing de entrada** (no bootstrap de
  retornos), para igualar el método del video ("bate a 2,000 variantes de entrada
  aleatoria"). API importable + CLI `donchian_ema`.
- `monte_carlo.py` — `monte_carlo_trades` (reshuffle → distribución de max DD) +
  `monte_carlo_candles` (block-bootstrap de factores de vela → distribución de Sharpe,
  `overfit_flag = orig > p95`).
- Slash `/rst`, `/montecarlo`; tests pytest; wire-in al `backtest-runner`.

### Pista 2 — Jesse como laboratorio paralelo
`integrations/jesse/` con Docker compose (Postgres+Redis+Jesse), MCP conectado a Claude
Code, estrategia de ejemplo `DonchianEMATrend` (port del video). **Opcional**, lo levanta
el usuario; es power-tooling para backtests de año completo + Monte Carlo/walk-forward
nativos. No reemplaza el motor Wally ni los gates live.

## Gate combinado (orden del video)

```
RST → backtest/ranking → OOS (70/30) → Monte Carlo (trades+candles) → veredicto honesto
```
Recomendar SOLO si: RST=PASS **Y** OOS≠FAIL **Y** candles≠OVERFIT_SUSPECT. Si no, reportar
con caveat explícito (estilo "honest takeaway" del video).

## Detalles de diseño relevantes

- **RST p-value:** estimador conservador `(n_beaten + 1) / (n_permutations + 1)`
  (Davison & Hinkley), evita p=0 exacto. α=0.05. Determinista vía `np.random.default_rng(seed)`.
- **Pool de entradas nulas:** span `[min(entries), max(entries)]` — random entries en el
  mismo régimen temporal (null más justo).
- **MC trades reshuffle:** retorno final invariante (es el punto — solo el orden cambia);
  WARN si `dd_p95` infla >50% sobre el DD observado. Modo `bootstrap` opcional varía retorno.
- **MC candles:** factores multiplicativos por vela `(o/c_prev, h/o, l/o, c/o)` re-muestreados
  en bloques contiguos → preserva geometría de vela + autocorrelación corta, rompe la
  trayectoria macro exacta (rompe overfit a la serie real).
- Reuso: `fetch_paginated` (Binance Futures), indicadores autocontenidos; `monte_carlo.py`
  importa la estrategia/exit de `rule_significance.py` (single source of truth).

## Caveats honestos

- Los helpers nativos paginan Binance Futures (sin el cap de 300 barras del TV MCP) pero
  igual sobre un universo limitado; un Monte Carlo de 1 año hereda el régimen de ese año.
- Jesse requiere setup de sistema (Docker/Postgres/Redis) que ejecuta/autoriza el usuario.
- RST valida la entrada, NO la rentabilidad. PASS no garantiza profit; FAIL sí descarta edge.

## Plan
`docs/superpowers/plans/2026-05-31-jesse-validation-bundle.md`
