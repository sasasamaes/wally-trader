---
name: Morning protocol COMPLETO — rutina 5:30/6:00 AM MX
description: Protocolo de 15 fases que debe ejecutar Claude cuando usuario inicia sesión de trading diario. Incluye auto-check personal, sentiment, correlaciones, técnica, position sizing y journal.
type: project
originSessionId: 870cfb36-0066-4b6c-a1b7-eeaebc9a6ca8
---
**Cuando el usuario diga "análisis matutino", "morning analysis", "empezar sesión" o equivalente en ventana MX 05:00-09:00 AM** → ejecutar TODO este protocolo en orden. No omitir fases.

## FASE 1: Auto-check personal (obligatorio al inicio)
Preguntarle al usuario directamente:
1. ¿Dormiste 6+ horas?
2. ¿Comiste algo?
3. ¿Mentalmente claro (sin resaca emocional de trade anterior)?
4. ¿Tienes hasta 12 MD sin distracciones?
5. ¿Capital sano (>70% del inicial)?

Si alguna respuesta es NO → recomendar skip + razón concreta + ofrecer reschedule.

## FASE 2: Contexto Global (paralelo, un solo message con múltiples WebFetch)
- Fear & Greed 7d: `api.alternative.me/fng/?limit=7`
- Funding rate OKX: `okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP`
- CoinGecko BTC: `api.coingecko.com/api/v3/coins/bitcoin?community_data=true`
- CoinPaprika: `api.coinpaprika.com/v1/tickers/btc-bitcoin`
- Mempool: `mempool.space/api/mempool`
- Hashrate: `bitinfocharts.com/bitcoin/`
- Txs: `api.blockchain.info/charts/n-transactions?timespan=7days&format=json`

## FASE 3: Correlaciones (crítico)
- ETH 24h change (correlación esperada +0.85 con BTC)
- SPX / NASDAQ direction (+0.30 a +0.60)
- DXY direction (-0.50 con BTC)
- Gold (+0.20 en crisis)

Regla: si ETH va contra el sesgo de BTC → reducir convicción/skip. Si DXY rompe al alza → sesgo bearish crypto.

## FASE 4: Noticias y Eventos
- Revisar: FOMC, CPI, NFP, PPI, Powell en próximas 6h
- Eventos crypto: ETF decisions, halving, forks, expiraciones opciones (último viernes del mes)
- Si evento alto impacto en <4h → **NO OPERAR** hasta pasar + 1h

## FASE 5: Detección de Régimen
- Pull 4H summary 50 bars
- Pull 1H summary 24 bars
- Clasificar según criterios:
  - RANGE: oscila <5% en 48h sin romper niveles
  - TRENDING UP/DOWN: higher highs + higher lows (o mirror) diarios
  - VOLATILE: ATR 4H > 2× promedio histórico

## FASE 6: Selección de Estrategia
- RANGE → Mean Reversion 15m (4 filtros strict)
- TRENDING UP → Donchian Breakout solo LONGS
- TRENDING DOWN → Donchian Breakout solo SHORTS
- VOLATILE → **NO OPERAR**, documentar en journal

## FASE 7: Niveles Técnicos Multi-TF
- 4H: EMA 50/200 (contexto macro)
- 1H: Donchian H/L + estructura
- 15m:
  - Donchian(15) H/L de últimas 15 barras CERRADAS
  - BB(20, 2) upper/mid/lower
  - RSI(14) actual
  - ATR(14) actual
  - EMA 50

Niveles adicionales a incluir:
- Previous Day High/Low (PDH/PDL)
- Weekly Open
- VWAP del día (desde UTC 00:00)
- Fibonacci 0.618 último swing 1H

## FASE 8: Money Flow
- Volumen 5m vs promedio 24h
- Spikes > 2× avg: identificar rejection vs acumulación
- Volume Profile POC del día si posible

## FASE 9: Patrones Técnicos
- Últimas 5 velas 15m y 1H: dojis, hammers, engulfing
- 1H: doble techo/piso
- Divergencias RSI vs precio (bullish/bearish)
- Breakouts con retest o fakeouts

## FASE 10: Position Sizing (OBLIGATORIO)
Leer capital actual de trading_log.md. Calcular:
- Riesgo max por trade = 2% del capital actual
- Qty BTC = Riesgo_USD / SL_distance_en_USD
- Tabla: margen a usar, leverage sugerido, qty BTC
- Nunca recomendar > 2% risk per trade

## FASE 11: Dibujar en TradingView
1. LIMPIAR: `ui_mouse_click 12 619 right` → `ui_click data-name=remove-drawing-tools`
2. Dibujar niveles según estrategia:
   - Mean Reversion: Donchian H/L + BB + zonas entry + MID + SL/TP3 ambos lados
   - Breakout: niveles ruptura + buffer + SL/TP3
3. Niveles extra: PDH/PDL (azul), Weekly Open (morado), VWAP (amarillo)
4. Línea vertical cierre 17:00 MX
5. Texto superior con resumen

## FASE 12: Plan de Entrada
- Entry zone exacto (precio)
- SL con 2% risk sizing
- TP1/TP2/TP3 con ATR
- Hora óptima (priorizar MX 06:00-10:00 = London/NY overlap UTC 12-16)
- 4 filtros obligatorios listados
- Invalidación del setup

## FASE 13: Checklist Pre-Entry (entregar al usuario)
Lista de 12+ ítems tachables:
- Personal: dormido, comido, claro, no revenge
- Contexto: régimen, noticias, ETH, hora
- Setup: 4/4 filtros, MTF confluence, volumen
- Ejecución: SL listo, TPs, sizing 2%, orden completa
- Límites: <3 trades, <2 SLs, PnL >-6%

## FASE 14: Reglas Duras de Sesión (recordatorio)
- Max 3 trades/día
- Post-SL: pausa 30 min OBLIGATORIA
- 2 SLs consecutivos → STOP día
- NUNCA mover SL en contra
- Pérdida día >6% → stop + revisión
- Cap < 70% inicial → volver a demo 1 semana

## FASE 15: Veredicto Final
UNA línea clara:
- ENTRAR LONG en X → razón
- ENTRAR SHORT en Y → razón
- ESPERAR SETUP → qué vigilar
- NO OPERAR HOY → razón

## FASE 16 (fin de día): Journal
Al cerrar sesión pedirle al usuario:
- Cada trade: entry/exit/razón
- PnL total, capital antes/después
- ¿Siguió 4 filtros en cada trade? ¿Hora OK?
- ¿Qué salió bien? ¿Qué mejorar?
- Lección del día

Actualizar trading_log.md con toda esta info.

## FASE 17 (domingo): Review Semanal
Si el usuario pide review semanal:
- Leer trading_log últimos 7 días
- Calcular: WR, PF, avg win/loss, max DD
- Identificar patrones (hora, día, setup)
- 1 cambio concreto para semana siguiente
- Objetivo próxima semana

**Why:** El usuario necesita un flujo REPETIBLE que incluye disciplina psicológica (auto-check, reglas duras) tanto como análisis técnico. Sin las fases 1, 13, 14 → el análisis solo lleva a sobreoperar.

**How to apply:** Al detectar que es rutina matutina → ejecutar el protocolo completo en paralelo donde sea posible (WebFetch batch, cálculos concurrentes). Tiempo objetivo: 3-5 min de análisis + 2 min de dibujo + respuesta estructurada.

**Importante:**
- NUNCA omitir Fase 1 (auto-check) — es la protección contra tilt
- NUNCA omitir Fase 10 (sizing) — es la protección contra blowup
- NUNCA omitir Fase 14 (reglas duras) — recuerdo al usuario de sus límites
- Tablas, emojis para urgencia, veredicto obvio al final

**Integración con archivos:**
- Leer trading_log.md para capital actual y patrones históricos
- Actualizar trading_log.md al cerrar sesión
- Referenciar trading_strategy.md para config de estrategia
- Referenciar market_regime.md para decisión de estrategia
