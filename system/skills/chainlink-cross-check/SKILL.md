---
name: chainlink-cross-check
description: Use cuando necesites validar el precio actual mostrado en TradingView contra una fuente independiente (Chainlink Data Feeds — oráculos on-chain agregados). Útil para detectar wicks fakeados, datos stale del MCP, o divergencias cross-exchange antes de ejecutar un trade.
---

# Chainlink Cross-Check — validación de precio cross-source

## Cuándo usarla

**Pre-entry validation (CRÍTICO):**
- Antes de ejecutar trade con leverage 10x, validar que el precio en TV coincide con el agregado global.
- Si TV muestra $75,500 pero Chainlink dice $74,200 → algo está mal (feed stale, exchange-specific premium, o manipulación).

**Post-SL forensics:**
- Si tu SL pegó en wick sospechoso, compara Chainlink vs TV en el mismo timestamp.
- Si Chainlink no movió pero TV sí → wick fake/stop hunt local del exchange.

**Multi-exchange divergence detection:**
- Binance Futures vs spot global puede divergir 0.3-2% en momentos de alta volatilidad.
- Chainlink agrega múltiples exchanges con tolerancia → es "precio justo" más cercano.

**FTMO/Fotmarkets multi-asset:**
- Validar EURUSD, GBPUSD, XAUUSD contra Chainlink antes de trade.
- Brokers MT5 suelen tener spreads/markups que Chainlink no tiene.

## Pares soportados

Solo los que tienen feed en Ethereum mainnet:

| Par | Feed Address | Decimals |
|---|---|---|
| BTC/USD | `0xF4030086...` | 8 |
| ETH/USD | `0x5f4eC3Df...` | 8 |
| LINK/USD | `0x2c1d072e...` | 8 |
| EUR/USD | `0xb49f6779...` | 8 |
| GBP/USD | `0x5c0Ab2d9...` | 8 |
| XAU/USD | `0x214eD9Da...` | 8 |

**No soportados** (no hay feed): `NAS100`, `SPX500`, `USDJPY` (existe pero invertido). `BTCUSDT.P` se mapea a `BTC/USD` (Chainlink no distingue futures vs spot).

## Cómo invocarla

```bash
# Helper directo
bash .claude/scripts/chainlink_price.sh BTC                    # precio Chainlink solo
bash .claude/scripts/chainlink_price.sh BTC --compare 75500    # compare vs TV
bash .claude/scripts/chainlink_price.sh ETH --json             # JSON output
```

```
# Slash command (CC/OpenCode/Hermes)
/chainlink BTC
/chainlink ETH
```

## Interpretación de delta

| Delta % | Verdict | Acción |
|---|---|---|
| < 0.3% | OK | Procede con análisis. Precio TV confiable. |
| 0.3 - 1.0% | WARN | Posible lag de feed o exchange-specific. NO bloquea pero registra en journal si tomas trade. |
| > 1.0% | ALERT | BLOCK trade. Verifica TV symbol/exchange. Probable feed stale o evento de manipulación. |

## Pitfalls conocidos

1. **Latencia Chainlink:** feeds tienen heartbeat 3-30 min según el par. NO es tick-by-tick. Si BTC se mueve $500 en 30s, Chainlink puede aún reportar el precio anterior. **No usar en scalping de 1m**, solo para confirmaciones de entry en 15m+.

2. **Cache 30s:** el helper cachea para no hammear RPCs públicos. Si quieres precio fresh dentro del cache window, espera o borra `/tmp/wally_chainlink_<PAIR>.cache`.

3. **RPC público fallback:** si todos los 4 RPCs (1rpc.io, llamarpc, blastapi, publicnode) fallan, el helper devuelve cache stale con warning a stderr. Si nunca tuvo cache → exit 1.

4. **BTCUSDT.P en BingX puede divergir 0.5%+ vs spot global** durante eventos de alto volumen. Chainlink reporta el "global agg", no el preciso del exchange. WARN no necesariamente significa problema — es info.

## Verificación rápida

```bash
# Sanity check: si Chainlink retorna $0.00 o el script devuelve exit != 0, algo falla
bash .claude/scripts/chainlink_price.sh BTC && echo OK || echo FAIL
```

## Integración con /morning

La FASE 1.5 del morning protocol invoca este skill automáticamente para profile retail (BTC) y FTMO (los assets que aplican: BTC, ETH, EUR, GBP, XAU). Si el verdict es ALERT, el morning report bloquea recomendaciones de entry.
