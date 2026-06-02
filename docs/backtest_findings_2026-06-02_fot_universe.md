# fot-scout Universe Backtest — Mean Reversion edge (2026-06-02)

> Disparado por "hacer backtesting de todos los activos nuevos" del universo curado de 23
> instrumentos (expansión 2026-06-01). Objetivo: poblar honestamente `per_asset_edge` en
> `fot_strategy_mapping.json` para los 19 activos con `edge_backtested:false` y refrescar los 4 ya backtesteados.

## Metodología

- **Estrategia:** Mean Reversion 4-filtros (Donchian15 ±0.1% / RSI 35-65 / toque BB(20,2) / color de cierre).
- **Gate de régimen (CRÍTICO):** entradas SOLO cuando la última 1h cerrada fue **RANGE_CHOP**
  (ADX 1h < 25, ventana rolling de 80 barras — réplica de `detect_regime` del router). MR fuera de
  RANGE_CHOP es el desastre -34% que CLAUDE.md advierte; sin este gate los números son ruido.
- **Exit = el que CONSTRUYE el router** (no el cascade 2.5/4/6 de CLAUDE.md): **SL = max(ATR×1.2,
  floor_pips)**, **TP único a 2R**. Outcome binario (+2R / -1R). SL primero si ambos en la misma vela.
- **Data:** 5m, ~60 días. yfinance (FX/índices/metales/energía) + Binance paginado (cripto).
- **Costo:** dos lecturas — `gross` (sin costo, edge puro = 3×WR−1) y `net` (FEE notional 0.05%
  round-trip del engine).
- **OOS:** split temporal 70/30 + `degradation_flag`.
- Runner: `.claude/scripts/fot_backtest_universe.py` (aislado; no muta el engine compartido).

## Resultados (23 activos, ordenados por expR_gross)

| Asset | n | WR% | PF | expR_gross | expR_net | setups/d | range% | OOS |
|---|---|---|---|---|---|---|---|---|
| EURGBP | 61 | 42.6 | 0.69 | +0.279 | -0.263 | 0.88 | 58.6 | PASS |
| GBPJPY | 122 | 40.2 | 0.43 | +0.205 | -0.654 | 1.77 | 53.3 | FAIL |
| SPX500 | 35 | 40.0 | 0.74 | +0.200 | -0.215 | 0.58 | 34.8 | PASS |
| NAS100 | 31 | 38.7 | 0.81 | +0.161 | -0.150 | 0.52 | 28.0 | PASS |
| BRENT | 93 | 37.6 | 0.92 | +0.108 | -0.049 | 1.6 | 48.4 | PASS |
| XAUUSD | 138 | 37.0 | 0.75 | +0.097 | -0.235 | 2.34 | 55.5 | FAIL |
| GER40 | 56 | 37.5 | 0.74 | +0.097 | -0.199 | 0.93 | 50.0 | WARN |
| USDJPY | 122 | 35.2 | 0.37 | +0.057 | -0.715 | 1.77 | 53.6 | PASS |
| AUDUSD | 118 | 33.1 | 0.54 | -0.004 | -0.444 | 1.71 | 47.5 | FAIL |
| EURUSD | 107 | 32.7 | 0.37 | -0.019 | -0.743 | 1.55 | 49.0 | WARN |
| GBPUSD | 126 | 32.5 | 0.39 | -0.023 | -0.690 | 1.83 | 46.3 | PASS |
| US30 | 43 | 32.6 | 0.53 | -0.023 | -0.444 | 0.72 | 53.5 | PASS |
| BTCUSD | 134 | 32.1 | 0.58 | -0.037 | -0.391 | 2.2 | 43.3 | PASS |
| UK100 | 52 | 32.7 | 0.64 | -0.037 | -0.291 | 0.87 | 51.4 | PASS |
| WTI | 98 | 31.6 | 0.7 | -0.051 | -0.201 | 1.69 | 42.9 | PASS |
| NZDUSD | 106 | 31.1 | 0.53 | -0.081 | -0.443 | 1.54 | 46.0 | PASS |
| XAGUSD | 112 | 30.4 | 0.72 | -0.089 | -0.210 | 1.9 | 53.2 | PASS |
| EURJPY | 128 | 29.7 | 0.26 | -0.102 | -0.978 | 1.86 | 58.2 | PASS |
| SOLUSD | 132 | 28.8 | 0.64 | -0.136 | -0.275 | 2.16 | 56.6 | PASS |
| XRPUSD | 82 | 28.0 | 0.68 | -0.159 | -0.228 | 1.34 | 53.7 | PASS |
| ETHUSD | 126 | 27.8 | 0.55 | -0.167 | -0.393 | 2.07 | 48.3 | PASS |
| USDCHF | 108 | 27.8 | 0.43 | -0.167 | -0.559 | 1.57 | 56.6 | WARN |
| USDCAD | 80 | 27.5 | 0.33 | -0.175 | -0.841 | 1.16 | 52.4 | WARN |

_expR_gross = edge puro (3×WR−1, sin costo); expR_net = con FEE notional 0.05% round-trip del engine. Solo RANGE_CHOP (gate ADX 1h<25). SL=max(ATR×1.2, floor), TP 2R._

## Hallazgos

1. **NET expectancy negativa en los 23 activos.** Bajo el modelo de costo del engine (fee % del
   notional), ningún instrumento sobrevive. El fee castiga desproporcionadamente SL ajustado +
   precio alto (XAUUSD: drag de **0.33R** por trade solo de fee).
2. **GROSS: solo 8 superan el break-even del TP-2R (WR>33.3%):** EURGBP (+0.28), GBPJPY (+0.21),
   SPX500 (+0.20), NAS100 (+0.16), BRENT (+0.11), XAUUSD (+0.10), GER40 (+0.10), USDJPY (+0.06).
   Los mejores edges brutos son **activos NUEVOS** (EURGBP, GBPJPY, índices), no los 4 originales.
3. **Los 4 edges "VALIDATED" originales del mapping NO se reproducen:**
   | Asset | mapping (2026-05-31) | real gross (hoy) | real net | OOS hoy |
   |---|---|---|---|---|
   | XAUUSD | +0.46 / WARN | +0.10 | -0.235 | **FAIL** |
   | BTCUSD | +0.29 / WARN | -0.04 | -0.391 | PASS |
   | SPX500 | +0.24 / FAIL | +0.20 | -0.215 | PASS |
   | EURUSD | +0.16 / FAIL | -0.02 | -0.743 | WARN |
   Eran **optimistas**. Ninguno llega al +0.30 que dispara el +10 de score en el router.
4. **Caveat del modelo de costo:** el fee notional 0.05% sobre-castiga. Para un CFD el costo real
   ≈ spread (distancia de precio fija), que en majors líquidos da un drag mucho menor (~0.05-0.10R)
   → el net real probablemente cae **entre gross y net-engine**, más cerca de gross en FX majors.
   En exóticos/índices del bonus el spread es ancho → más cerca del net-engine.

## Veredicto honesto

El edge de Mean Reversion sobre fotmarkets es **marginal en el mejor de los casos**. No hay ningún
activo con expectancy net claramente positiva. Los mejores candidatos brutos (EURGBP, SPX500,
NAS100, BRENT, XAUUSD) tienen edge frágil que vive o muere según el spread real del broker. Esto
**refuerza** la filosofía del profile: "sobre $50 esto rinde centavos/día — semilla, no ingreso" y el
WAIT honesto del scout. No justifica subir el riesgo ni perseguir tendencia.

## Acción sobre el mapping (pendiente decisión del usuario)

Ver propuesta en la conversación. La decisión clave: qué expectancy registrar (net realista vs gross
puro) y si corregir los 4 valores optimistas existentes.
