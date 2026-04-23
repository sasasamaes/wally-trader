---
name: btc-regime-analysis
description: Use para análisis profundo del régimen de mercado BTC — más allá del detector rápido. Incluye historical context (50 días 4H), estructura macro/micro, divergencias MTF, cycle analysis. Útil cuando el régimen es ambiguo o hay transición.
---

# BTC Regime Analysis — Deep Dive

## Cuándo usar este skill

Cuando la clasificación simple RANGE/TRENDING/VOLATILE no es suficiente porque:
- El mercado está en transición (rompiendo un rango previo)
- Hay divergencia entre timeframes (4H bullish pero 1D bearish)
- ATR comportamiento anómalo (explota y contrae sin dirección)
- Necesitas contexto macro para decisión importante (ej: aumentar size)

## Protocolo extendido

### 1. Context macro (1D)
Pull 1D OHLCV 100 bars:
- Estructura: ¿higher highs + higher lows? ¿lower highs + lower lows? ¿sideways?
- Last swing high / swing low importantes
- EMA 50 vs EMA 200 cross (golden/death cross)
- Volumen en reversiones clave
- Distance to next major resistance/support

### 2. Medio plazo (4H)
Pull 4H 50 bars:
- Range of last 30 days (macro box)
- Key levels tocados 3+ veces (strong S/R)
- Fibonacci retracements del último swing 1D
- VWAP anchored from last swing low/high
- Bull/bear divergencias RSI vs precio

### 3. Corto plazo (1H + 15m)
- Micro-estructura
- Patrones de continuación vs reversión
- Volume imbalances

### 4. Análisis de divergencias MTF

Tabla de régimen por TF:
| TF | Trend | Fuerza |
|---|---|---|
| 1D | ??? | weak/medium/strong |
| 4H | ??? | weak/medium/strong |
| 1H | ??? | weak/medium/strong |
| 15m | ??? | weak/medium/strong |

**Reglas:**
- Todos alineados → régimen CONFIRMADO
- Higher TFs disagree with lower → riesgo alto, reduce size
- 1D vs 4H disagree → esperar clarificación

### 5. Catalyst scan
- ¿Precio cerca de nivel psicológico (80k, 100k)?
- ¿Evento próximo macro?
- ¿Halving effect activo?
- ¿BTC dominance subiendo/bajando?

### 6. Ciclo de mercado

En qué fase estamos (approx):
- Accumulation (post-bear market)
- Mark-up (bull trend early)
- Distribution (topping)
- Mark-down (bear)
- Re-accumulation / re-distribution

### 7. Output

```
🔍 REGIME DEEP DIVE

Contexto Macro (1D):
- Estructura: [descripción]
- EMA status: [crossover history]
- Volumen: [tendencia]

Medio plazo (4H):
- Range macro: XX,XXX - XX,XXX (activo desde YYYY-MM-DD)
- Strong S/R: [niveles con 3+ toques]
- Divergencias: [si hay]

MTF Alignment:
[tabla 1D/4H/1H/15m]

Régimen consolidado: [RANGE/TRENDING/VOLATILE + subtipo]
  (ej: "RANGE shifting up" — range se está moviendo al alza)

Estrategia recomendada:
- Primary: [Mean Reversion / Breakout]
- Size modifier: [100% / 75% / 50% / skip]
- Invalidación: [condición que cambia el diagnóstico]

Catalyst upcoming:
- [eventos próximos relevantes]
```

## Señales de transición crítica

**RANGE → TRENDING UP** confirmado cuando:
1. Cierre 4H > techo del range con vol >2× promedio
2. Retest del nivel roto sostiene (no vuelve adentro)
3. EMA 50 1H cruza arriba de EMA 200 1H
4. RSI semanal > 60

**TRENDING UP → TRENDING DOWN** (reversión) cuando:
1. Lower high en 1D confirmado
2. Break de EMA 50 1D con vol
3. Bear divergencia RSI en 1D

**Cualquier → VOLATILE** cuando:
1. ATR 4H > 2.5× promedio 20d
2. Mechas > 2× rango típico
3. Movimientos bidireccionales > 2% en horas

## Comandos útiles

```
/regime               # quick check (uses regime-detector agent)
# Para deep dive: invoca este skill con "regime deep dive"
```

## Fuentes de contexto adicional

- Fear & Greed diario y semanal
- BTC dominance en TradingView (CRYPTOCAP:BTC.D)
- Funding rate histórico (no solo actual)
- ETF flows (si farside accesible)
