---
name: Market context APIs
description: Endpoints públicos para sentiment, funding, on-chain y volumen BTC
type: reference
originSessionId: 870cfb36-0066-4b6c-a1b7-eeaebc9a6ca8
---
**APIs verificadas que funcionan (sin auth):**

| Dato | Endpoint | Notas |
|---|---|---|
| Fear & Greed Index | `https://api.alternative.me/fng/?limit=7` | JSON, trend 7 días útil |
| Funding rate | `https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP` | OKX sí responde desde el MCP |
| BTC community sentiment | `https://api.coingecko.com/api/v3/coins/bitcoin?community_data=true` | sentiment_votes_up/down_percentage |
| BTC precio/vol 24h | `https://api.coinpaprika.com/v1/tickers/btc-bitcoin` | 24h/7d/30d change |
| Mempool/on-chain | `https://mempool.space/api/mempool` | Congestion real-time |
| Difficulty/Hashrate | `https://mempool.space/api/v1/difficulty-adjustment` | Miner health |
| Tx count históricas | `https://api.blockchain.info/charts/n-transactions?timespan=7days&format=json` | Actividad red |
| Hashrate detallado | `https://bitinfocharts.com/bitcoin/` | Incluye whale concentration |

**APIs BLOQUEADAS desde el MCP (NO usar, siempre fallan):**

| Endpoint | Error |
|---|---|
| `fapi.binance.com/*` | 451 Unavailable For Legal Reasons |
| `cryptopanic.com/news/*` | 403 Forbidden |
| `theblock.co/*` | 403 |
| `farside.co.uk/btc/` | 403 |
| `coinglass.com/*` sin JS | Retorna HTML sin datos (JS-rendered) |
| `whale-alert.io/` | HTML sin datos (requiere suscripción) |

**Interpretación rápida de datos clave:**

- **Fear & Greed < 25:** Extreme Fear → contrarian bullish
- **F&G > 75:** Extreme Greed → contrarian bearish
- **Funding rate negativo sostenido (-0.001% o peor):** shorts pagan longs, setup short squeeze si rompe arriba
- **Funding positivo alto (+0.01%):** longs muy cargados, setup long liquidation si rompe abajo
- **Retail sentiment 80%+ bullish (CoinGecko):** sesgo contrarian bearish (retail suele estar en el lado equivocado antes de correcciones)
- **Hashrate subiendo:** miners confiados, estructura sana
- **Mempool congestionado:** demanda real de blockspace = actividad legítima
