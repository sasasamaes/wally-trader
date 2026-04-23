---
description: Muestra niveles técnicos actuales (Donchian, BB, RSI, ATR)
allowed-tools: mcp__tradingview__quote_get, mcp__tradingview__chart_set_timeframe, mcp__tradingview__data_get_ohlcv, Bash
---

Dame los niveles técnicos actuales de BTCUSDT.P en formato tabla:

1. Cambia TF a 15m y pull últimas 25 velas (excluir la forming)
2. Calcula:
   - **Donchian(15)** High y Low
   - **Bollinger Bands(20, 2)** upper, mid, lower
   - **RSI(14)** actual
   - **ATR(14)** actual
   - **EMA 50** (si hay 50+ barras disponibles)
3. Identifica:
   - Distancia del precio actual a cada nivel (%)
   - Cuál está más cerca (soporte o resistencia)
   - Si precio está dentro de zona de entrada (±0.1% de Donchian H/L)
4. Entrega:
   - Tabla con todos los niveles
   - Precio actual vs nivel más cercano
   - Recomendación rápida: ¿esperar, vigilar, o ya está en zona?

Formato compacto, máximo 20 líneas de output.
