---
name: funding-rate-arbitrage
description: Use cuando funding rate de perpetuals está extremo (>0.05% per 8h o negativo sostenido) para evaluar oportunidades de arbitrage delta-neutral entre perp y spot. También activar cuando user pregunte por "funding rate", "carry trade", "delta neutral cripto", "long spot short perp". Aplica a profiles retail/quantfury/bitunix donde se tradean perpetuals.
---

# Funding Rate Arbitrage — Carry trades en perpetuals

> Funding rate es el "interés" que paga la posición mayoritaria en un perpetual. Cuando es extremo (>0.05% per 8h = >55% APY), hay oportunidad de arbitraje delta-neutral.

## Concepto base

**Perpetual futures** no tienen expiración. Para mantener su precio anclado al spot, se cobra/paga un **funding rate** cada 8h:
- Funding **positivo** → longs pagan a shorts (mercado bullish, longs sobre-apalancados)
- Funding **negativo** → shorts pagan a longs (mercado bearish extremo)

## Strategy: delta-neutral carry

### Cuando funding > +0.05% / 8h (3x al día = +0.15%/día = ~55% APY)

```
1. SHORT perpetual (capturas el funding pago)
2. LONG spot equivalente (hedge direccional)
3. Net exposure = ~0 (delta-neutral)
4. Yield = funding rate received (sin riesgo direccional sustancial)
```

### Cuando funding < -0.05% / 8h (perp más barato que spot, mercado bearish)

```
1. LONG perpetual (recibes el funding)
2. SHORT spot (vende lo que tienes en spot, idealmente)  
3. Yield = funding rate negativo capturado
```

## Cuándo activar (umbrales)

| Funding rate per 8h | APY equivalente | Acción |
|---|---|---|
| >0.10% | >110% | 🔥 **Setup excelente** — abrir delta-neutral |
| 0.05% – 0.10% | 55-110% | ✅ Setup bueno — considerar |
| 0.01% – 0.05% | 11-55% | 🔍 Marginal — evaluar fees |
| <0.01% / >-0.01% | Neutral | 🚫 No vale la pena (fees > yield) |
| -0.05% — -0.01% | -55%-11% | ⚠️ Funding bajista leve — informativo |
| <-0.05% | <-55% | 🔥 **Bear extremo** — long perp + short spot |

## Riesgos críticos

1. **Liquidación del perp short** si BTC bombea +20% sin que cierres a tiempo
   - Mitigation: leverage bajo (3-5x max) + stop on perp side
2. **Spread spot/perp se expande** durante volatilidad → hedge imperfecto
3. **Fees acumulados**: maker/taker fees + spread + funding swing si te pillan en mal momento
4. **Borrow rate del spot** si shortear vía margin (puede comer el yield del perp)

## Cómo ejecutarlo en el sistema

### 1. Check funding rate actual
```bash
# OKX BTC perpetual
curl -s 'https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP'

# Binance Futures
curl -s 'https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT'
```

### 2. Evaluar oportunidad
- Funding > +0.05%/8h **sostenido por 24h+** → setup confiable
- Funding extremo de un solo period es noise

### 3. Sizing
```
Capital total: $10,000
Spot long:      $5,000 BTC (sin leverage)
Perp short:     $5,000 short equivalente, leverage 1x effective
Net delta:      ~0 (perfecta cobertura)
Yield/día:      $5,000 × 0.15% = $7.50/día = $225/mes
```

⚠️ Sin embargo: **NO funciona en profiles** que limitan exposición direccional (FTMO/FundingPips).
Solo aplica a **retail/quantfury/bitunix** donde puedes tener spot + perp simultáneamente.

## Backtest histórico (referencia)

Funding extremo (>0.10% per 8h) ocurre típicamente:
- **Bull market top**: leverage longs sobre-apalancados (e.g. early 2021, late 2024)
- **Capitulation events**: panic shorts (e.g. March 2020, June 2022)

Yield histórico del carry: 30-60% APY en períodos extremos, 5-15% en mercados normales.

## Referencias externas

- **Coinglass funding rate dashboard**: https://www.coinglass.com/FundingRate
- **OKX funding API** (sin key): `/api/v5/public/funding-rate?instId=BTC-USDT-SWAP`
- **Binance funding API**: `/fapi/v1/premiumIndex?symbol=BTCUSDT`

## Disclaimer

Este NO es free money. Los riesgos de liquidación + spread expansion + borrow costs pueden anular el yield. Test paper trading 1 mes antes de capital real.
