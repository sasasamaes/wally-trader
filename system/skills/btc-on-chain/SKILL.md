---
name: btc-on-chain
description: Use para análisis on-chain profundo de BTC — métricas de blockchain que predicen movimientos antes que el precio. Incluye hashrate, difficulty, MVRV, SOPR, exchange flows, whale activity. Complementa análisis técnico con datos fundamentales.
---

# BTC On-Chain Analysis

## Cuándo usar

- Análisis matutino cuando el contexto técnico es ambiguo
- Antes de tomar posición más grande (>5% cap)
- Para identificar divergencias entre precio y fundamentos
- Cuando hay volatility macro (catalyst eventos)

## Métricas clave y endpoints

### 1. Hashrate y Difficulty
```
https://bitinfocharts.com/bitcoin/
https://mempool.space/api/v1/difficulty-adjustment
```

**Lectura:**
- Hashrate subiendo → miners confiados, bullish estructural
- Hashrate bajando → capitulación miners, posible bottom en formación
- Difficulty adjustment +% → BTC network robustez
- Difficulty adjustment -% → stress en miners

### 2. Mempool y transactions
```
https://mempool.space/api/mempool
https://api.blockchain.info/charts/n-transactions?timespan=7days&format=json
https://api.blockchain.info/charts/estimated-transaction-volume-usd?timespan=7days&format=json
```

**Lectura:**
- Mempool congestionado → demanda real de blockspace
- Tx count subiendo → uso de red creciendo
- Avg tx value alto → transacciones institucionales/whales

### 3. Exchange flows (requiere fuente Pro)
```
Glassnode / CryptoQuant (requieren suscripción)
Alternativa gratuita: intotheblock.com (limited)
```

**Lectura:**
- Netflow exchanges NEGATIVO (outflow) → bullish (HODL wave)
- Netflow exchanges POSITIVO (inflow) → bearish (prep to sell)
- Large deposits USDT/USDC → buying pressure incoming
- Large withdrawals BTC → accumulation

### 4. Whale activity
```
https://whale-alert.io/ (limited free)
https://bitinfocharts.com/top-100-richest-bitcoin-addresses.html
```

**Lectura:**
- Top 100 concentration creciendo → accumulation
- Top 100 concentration bajando → distribution
- Transacciones > 1,000 BTC entre wallets desconocidas → movimiento institucional

### 5. MVRV Z-Score (overvaluation indicator)
**Aproximación gratuita:** precio actual vs media histórica móvil

**Bandas:**
- Z > 7: EXTREME overvalued (top histórico)
- 3 < Z < 7: Overvalued (zona de distribution)
- 0 < Z < 3: Fair value
- -1 < Z < 0: Undervalued
- Z < -1: EXTREME undervalued (bottom histórico)

### 6. SOPR (Spent Output Profit Ratio)
Requiere Glassnode o cálculo propio.
- SOPR > 1: en promedio se vende en profit (bull market)
- SOPR = 1: break-even (soporte/resistencia psicológica)
- SOPR < 1: se vende en pérdida (bear market)

## Protocolo de análisis on-chain

### 1. Pull data básico (paralelo)
- Hashrate + difficulty
- Mempool stats
- Transactions 7d trend
- Fear & Greed
- Active addresses

### 2. Interpretar señales

Tabla resumen:
| Métrica | Valor | Señal (B/N/S) |
|---|---|---|
| Hashrate 7d change | XX% | B/N/S |
| Difficulty next adj | XX% | B/N/S |
| Tx count trend | ↑/↓ | B/N/S |
| Mempool | congestionado/normal | B/N |
| Avg tx value | $XX,XXX | B/N/S |
| Whale concentration | stable/changing | B/N/S |
| F&G | XX | contrarian |

**B = Bullish, N = Neutral, S = Bearish**

### 3. Consenso on-chain

- 5+ B → sesgo bullish estructural
- 5+ S → sesgo bearish estructural
- Mixed → no usar on-chain como decisión, ir por técnica

### 4. Divergencias precio vs on-chain

**Bearish divergence:**
- Precio sube pero hashrate cae
- Precio sube pero activity baja
- Precio en top pero whales distribuyendo

**Bullish divergence:**
- Precio cae pero hashrate sube
- Precio cae pero accumulation aumenta
- Precio en bottom pero whales acumulan

## Output format

```
⛓️ ON-CHAIN ANALYSIS

Métricas principales:
| Métrica | Valor | Señal |
|---|---|---|
[tabla]

Lectura estructural: [BULLISH / NEUTRAL / BEARISH]
Confianza: [1-10]

Divergencias detectadas:
- [si hay]

Implicación táctica:
- Si operas en dirección del consenso on-chain → confianza aumenta
- Si operas contra → reduce size, stops más conservadores

Próximos eventos catalyst:
- Difficulty adjustment: [fecha, impacto]
- Halving: [tiempo restante]
- ETF updates: [si aplica]
```

## Limitaciones

1. **Data gratuita limitada** — las métricas premium (MVRV, SOPR, exchange flows precisos) requieren Glassnode/CryptoQuant pagos
2. **Latencia** — on-chain data puede tener 1-4h de delay
3. **Correlación ≠ Causación** — hashrate y precio correlacionan pero con lag variable
4. **No reemplaza análisis técnico** — es complemento, no sustituto

## Uso en decisiones de trading

**Para entrada:**
- Si setup técnico dice GO + on-chain bullish → confidence 100%, size normal
- Si setup técnico GO + on-chain bearish → confidence 60%, size reducido 50%
- Si setup técnico GO + on-chain MIXED → ignorar on-chain, ir con técnico

**Para size modifier:**
- On-chain extreme bullish + técnico bullish → size 1.5× normal (sin exceder 2% risk total)
- On-chain extreme bearish + técnico bullish → size 0.5× normal

**Para exit timing:**
- On-chain distribution detectada → TP más apretado (tomar profit antes)
- On-chain accumulation → TP3 runner más holgado (dejar correr)
