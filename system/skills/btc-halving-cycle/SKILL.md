---
name: btc-halving-cycle
description: Use cuando user pregunte por "halving", "ciclo de bitcoin", "where are we in the cycle", "stock-to-flow", "bull market top", o cuando estés evaluando si un trade va con o contra la macro tendencia del ciclo. Crítico para profile quantfury (BTC-stack mentality) y para validar si HODL pasivo es mejor que trading activo en la fase actual.
---

# BTC Halving Cycle Analysis — la macro tendencia que domina todo

> El ciclo de halving de Bitcoin es la fuerza macro más predictiva en cripto desde 2012. Conocer la fase actual cambia toda decisión de trading vs HODL.

## Las 4 fases del ciclo (~4 años cada uno)

### 1. Pre-halving (6-12 meses antes)
- **Fecha aprox** del halving: cada ~210,000 bloques = ~4 años
- Próximos halvings: 2024-04 (DONE), 2028-04 (estimated), 2032
- Característica: **acumulación silenciosa**, low volatility, sideways
- **Acción**: HODL pasivo + buy dips en demand zones

### 2. Halving event + 6 meses post
- Inflación BTC se reduce 50% (3.125 BTC/block → 1.5625 BTC/block en 2028)
- **Reacción inicial**: poco move (price already in expectations)
- **Acción**: HODL, NO short squeeze yet

### 3. Bull market explosivo (6-18 meses post-halving)
- Histórico: **+200% to +1500%** en 12-18 meses
- Ej: 2017 cycle (+1700%), 2020-2021 cycle (+550%), 2024-2025 cycle (en curso)
- Característica: **parabolic moves**, alts moonshot, FOMO retail
- **Acción**:
  - **Quantfury**: HODL agresivo (no lo arruines con shorts)
  - **Retail/Bitunix**: longs direccionales
  - **NO Mean Reversion** (estrategia inadecuada en parabolic)

### 4. Bear market correction (12-24 meses post-cycle top)
- Crashes de **-70% a -90%** desde top
- Ej: 2018 (-83%), 2022 (-77%)
- Característica: liquidaciones masivas, capitulación retail
- **Acción**:
  - **Cierra HODL parcial** en señales de top (mostradas más abajo)
  - **Quantfury**: pausar acumulación nueva, esperar bottom
  - **Bitunix shorts**: alta probabilidad pero alta vol

## Halving cycle history

| Halving | Fecha | Top alcanzado | Tiempo a top | % Move | Bottom cycle | % Drawdown |
|---|---|---|---|---|---|---|
| 1st | 2012-11-28 | $1,150 (Nov 2013) | ~12 mo | +9,350% | $200 | -83% |
| 2nd | 2016-07-09 | $20,000 (Dec 2017) | ~18 mo | +3,000% | $3,200 | -84% |
| 3rd | 2020-05-11 | $69,000 (Nov 2021) | ~18 mo | +700% | $15,500 | -77% |
| **4th** | **2024-04-19** | TBD (estimated 2025-2026) | TBD | TBD | TBD | TBD |

## Cómo identificar la fase actual

### Indicadores de fase BULL (acumular)

```
✅ Price > Stock-to-Flow model line
✅ MVRV < 2.5 (no overheated)
✅ NUPL > 0 but < 0.75
✅ ATH > 12 meses ago (bull breakout fresh)
✅ Funding rates moderados (no extremos)
```

### Indicadores de TOP (distribuir parcial)

```
🔴 MVRV > 4 (extreme overvaluation)
🔴 NUPL > 0.75 (euphoria)
🔴 Funding rate > 0.10%/8h sostenido (longs apalancados)
🔴 Google trends "Bitcoin" en máximos
🔴 Retail interest extremo (Coinbase #1 app)
🔴 4H/1D divergencias bajistas en RSI/MACD
```

### Indicadores de BOTTOM (acumular agresivo)

```
🟢 MVRV < 1 (deeply discount)
🟢 NUPL < -0.25 (capitulation)
🟢 Funding negativo sostenido (shorts apalancados)
🟢 Retail interest bajo (no en mainstream news)
🟢 Hashrate sigue creciendo (miners no capitulan)
```

## Estrategia óptima por fase

| Fase | Quantfury (BTC-unit) | Retail (USD-unit) | FTMO/FundingPips |
|---|---|---|---|
| Pre-halving (6-12 mo before) | HODL + buy dips | Mean Reversion if range, else HODL | Strategy mapping per asset |
| Halving + 6 mo | HODL, no shorts | Mean Reversion if range | Strategy mapping per asset |
| **Parabolic bull** | **HODL agresivo** (NO trades) | Longs direccionales (NO MR) | Conservar — no hacer héroe |
| **Top zone** | Cerrar 30-50% HODL | Tomar parciales en longs | NO operar BTC, solo forex/idx |
| **Bear market** | Pausar acumulación | Shorts si setup, MR en bouncas | Conservar capital |

## Cómo consultar la fase actual

### APIs (free)

```bash
# Stock-to-Flow + MVRV
curl 'https://api.coinglass.com/api/index/v3/cycle?key=YOUR_KEY'

# CryptoQuant (free tier)
# Glassnode (free tier limit 30/min): MVRV, NUPL, etc.
curl 'https://api.glassnode.com/v1/metrics/market/mvrv?a=BTC&api_key=...'

# CoinMetrics community API (free)
curl 'https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=btc&metrics=PriceUSD,CapMVRVCur'
```

### Sources (manual)

- **LookIntoBitcoin**: https://www.lookintobitcoin.com/charts (MVRV, NUPL, S2F gratis)
- **Glassnode Studio**: https://studio.glassnode.com/ (free tier)
- **Bitcoin Magazine Pro**: https://www.bitcoinmagazinepro.com/

## Aplicación al sistema

Antes de decisiones grandes:

```bash
# /journal o /review pueden incluir:
# "Phase actual: post-halving bull market, ~12 months in"
# "Implicación: HODL > trading activo. Reduce trade frequency."
```

Para **profile quantfury específicamente**: si la métrica `outperformance vs HODL`
está negativa por >2% mensual durante una fase BULL → casi seguro estás haciendo
trading en una fase donde HODL pasivo gana. **Reducir actividad**, no más trades.

## Disclaimer

El ciclo de halving es **patrón histórico no garantía**. Cada ciclo puede romper
expectativas (institutional adoption en 2024 pudo cambiar la dinámica). Usar como
**uno de varios filtros**, no como único guía.

## Referencias

- Bitcoin halving schedule: https://www.bitbo.io/halving/
- Stock-to-Flow model (PlanB): https://stats.buybitcoinworldwide.com/stock-to-flow/
- Halving cycle backtest: https://www.coinglass.com/cycle
