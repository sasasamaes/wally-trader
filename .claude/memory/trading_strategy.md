---
name: Trading strategy — Mean Reversion en Range
description: Estrategia primaria validada para scalping intraday BTC cuando market está en range (régimen actual)
type: project
originSessionId: 870cfb36-0066-4b6c-a1b7-eeaebc9a6ca8
---
**Estrategia activa: Mean Reversion en Range**

**Validación:** Grid search de 144 configs reveló que Donchian breakout tiene 0% WR en mercado actual (RANGE 73,500-78,300). Mean reversion ganó con:
- **100% WR** (2/2 trades)
- **+15.1% retorno** en 3 días
- **DD 2.9%**

**Parámetros:**
- Timeframe: 15m
- Donchian: **15 velas** (no 20)
- Edge: **±0.1%** del extremo Donchian (precio debe tocar)
- RSI(14): OB **65**, OS **35** (no extremos puros)
- Bollinger Bands(20, 2): confirmación obligatoria (low toca BB inferior / high toca BB superior)
- SL: **1.5 × ATR(14)**
- TP1 (40%): 2.5×SL → mueve SL a BE
- TP2 (40%): 4.0×SL
- TP3 (20%): 6.0×SL
- Leverage: 10x
- Ventana: **MX 06:00 – 23:59** (cripto 24/7, trader no duerme con posición abierta)
- Force exit: **23:59 MX** (06:00 UTC del día siguiente). Cierre anticipado permitido si ya hay ganancia buena del día o pendiente personal.
- Max 5 trades/día, stop en 2 SLs

**4 filtros obligatorios (todos deben cumplirse):**

LONG:
1. Precio toca o cruza **Donchian Low(15)** (dentro de 0.1%)
2. **RSI < 35**
3. **Low de vela toca BB inferior**
4. Vela cierra **verde** (close > open)

SHORT:
1. Precio toca o cruza **Donchian High(15)** (dentro de 0.1%)
2. **RSI > 65**
3. **High de vela toca BB superior**
4. Vela cierra **roja** (close < open)

**Why:** El mercado BTC está en range lateral hace 5+ días (73,500-78,300). En rangos, breakouts son trampas (0% WR comprobado). Mean reversion compra soporte / vende resistencia — funciona hasta que el range se rompe.

**How to apply:**
1. Al iniciar sesión verificar regimen — si close 4H sigue dentro 73,500-78,300 → mean reversion
2. Dibujar niveles Donchian High/Low del 15m + BB bandas
3. Esperar que precio toque UNA de las zonas extremas + RSI confirme
4. Entrar solo si TODOS los 4 filtros alinean simultáneamente
5. Máx 1 posición abierta a la vez

**Regla de cambio de estrategia:**
Si precio cierra **4H fuera** de la caja 73,500-78,300 **con volumen >2x promedio** → cambiar a Donchian Breakout (estrategia previa, documentada en backtest_findings.md)

**Niveles vigentes al 2026-04-20 MX 09:00 aprox:**
- Donchian High(15): **75,729**
- Donchian Low(15): **74,816**
- Mid: **75,272**
- Range width: 1.22%
- ATR(14): ~357 pts (0.48%)
