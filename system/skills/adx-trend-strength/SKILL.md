---
name: adx-trend-strength
description: Use para medir FUERZA de tendencia con ADX (Average Directional Index). Determina si hay trend real para operar (ADX>25) o chop lateral (ADX<20). Incluye +DI/-DI para dirección. Crítico para elegir estrategia correcta.
---

# ADX — Average Directional Index

J. Welles Wilder Jr. (1978). Mide la FUERZA de la tendencia, independiente de la dirección.

## 📐 Componentes

### 1. +DI (Positive Directional Indicator)
Mide fuerza del movimiento alcista.

### 2. -DI (Negative Directional Indicator)
Mide fuerza del movimiento bajista.

### 3. ADX (Average Directional Index)
Promedio móvil del DX (derivado de +DI y -DI).
- **SOLO mide fuerza**, NO dirección
- Range: 0 a 100

## 🎯 Interpretación de ADX

| ADX | Lectura | Acción |
|---|---|---|
| **0-20** | Sin tendencia / ranging | **MEAN REVERSION** funciona |
| **20-25** | Tendencia débil | Indeciso — cuidado |
| **25-50** | Tendencia MEDIA a FUERTE | **TREND FOLLOWING** funciona |
| **50-75** | Tendencia muy fuerte | Cabalga el trend |
| **75-100** | Trend extremo | Probable reversal pronto |

## 🔄 Señales combinadas

### ADX rising + +DI > -DI → Trend alcista fuerte
- Momentum bullish aumentando
- **Compra en pullbacks**, no shortees

### ADX rising + -DI > +DI → Trend bajista fuerte
- Momentum bearish aumentando
- **Vende en rallys**, no longees

### ADX falling → Tendencia debilitándose
- Trend previo se agota
- Possible reversal o range
- Reduce size

### +DI cruza arriba -DI → Cambio bullish
- **Señal LONG** (especialmente si ADX > 20)

### +DI cruza abajo -DI → Cambio bearish
- **Señal SHORT** (especialmente si ADX > 20)

## 🎨 Setup clásico con ADX

### Setup trending (ADX > 25):

**Long:**
1. ADX > 25 (trend confirmado)
2. +DI > -DI (dirección bullish)
3. Precio en soporte / pullback
4. Entry en rebote
5. SL debajo del swing low
6. TP = próxima resistencia

**Short:** mirror

### Setup de ruptura (ADX subiendo desde 15-20):

1. ADX estaba bajo 20 (range) y empieza a subir
2. Precio rompe rango con volumen
3. +DI/-DI confirman dirección
4. Entry en el breakout
5. Este setup anticipa el "inicio" de un trend

## 📊 Integración con tu sistema

### Cómo ADX mejora tu elección de estrategia:

**Tu sistema actual:** RANGE → Mean Reversion, TRENDING → Breakout

**Con ADX:**
- ADX < 20 → **Usar Mean Reversion** (la estrategia actual)
- ADX > 25 → **Cambiar a Breakout** (Donchian breakout)
- ADX 20-25 → **NO OPERAR** (zona de transición, alta incertidumbre)

### Protocolo:

Antes de cualquier setup, chequea ADX de TU timeframe operativo:

```
Si ADX 15m > 25 + +DI > -DI: solo LONGs (trend alcista)
Si ADX 15m > 25 + -DI > +DI: solo SHORTs (trend bajista)
Si ADX 15m < 20: mean reversion OK (range)
Si ADX 15m 20-25: skip trade (transición)
```

## 🎯 ADX en diferentes timeframes

### ADX Daily
- Contexto macro
- > 25 = estamos en trend semanal → prioriza breakouts
- < 20 = BTC en consolidación lateral → mean reversion macro

### ADX 4H
- Régimen medio plazo
- Usa para elegir estrategia del día

### ADX 1H
- Estructura inmediata
- Confirma o niega ADX 4H

### ADX 15m (tu TF operativo)
- Para ejecución
- Confirma con ADX superiores

**Regla:** si ADX 4H dice "trend fuerte" pero ADX 15m dice "ranging" → probable pullback dentro del trend mayor. Compra en pullback.

## 🔥 ADX Squeeze / Explosion

Similar al Bollinger squeeze:

**ADX en mínimos históricos** (<15 por muchas velas) → **explosión incoming**.
- Precio consolidado
- Volatilidad comprimida
- Breakout masivo probable

## 📐 Parámetros recomendados para BTC

| TF | ADX length | Smoothing |
|---|---|---|
| 5m scalping | 7 | 7 |
| 15m (tu TF) | 14 | 14 |
| 1H | 14 | 14 |
| 4H | 21 | 21 |

## 🎨 Indicadores TradingView

- **Average Directional Index** (ADX, default 14)
- **Directional Movement Index** (DMI — incluye +DI y -DI)
- **ADX and DI** (combinación)

## 🎓 Errores comunes

1. **Operar sin chequear ADX** — entras a mean reversion durante trend y te barren
2. **Shortear trend fuerte** — +DI > -DI con ADX > 30 = nunca shortees
3. **ADX alto = reversal pronto** — NO, ADX 50+ puede seguir subiendo
4. **Ignorar +DI/-DI** — ADX solo no dice dirección

## 🧠 Reglas mentales

1. **"ADX first, entry second"** — siempre chequea ADX antes de buscar setup
2. **"Trend is your friend hasta que deja de serlo"** — ADX rising = sigue con trend
3. **"No trend, mean reversion; trend, breakout"** — binario
4. **"ADX cruzando 20 = momento de atención"** — cambio de régimen en marcha

## Uso en el sistema

Cuando se te pida "ADX", "fuerza de tendencia", "trending":
1. Lee ADX actual en el TF operativo
2. Lee +DI y -DI
3. Confirma en TF superior (4H)
4. Determina: RANGING / TRENDING UP / TRENDING DOWN
5. Recomienda estrategia apropiada
6. Integra con detección de régimen actual del sistema
