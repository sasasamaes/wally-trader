---
name: bollinger-bands-advanced
description: Use para análisis avanzado con Bollinger Bands — squeeze, walking the band, bandwidth, %B, divergencias. Más allá del simple "rebota en banda" hay múltiples setups profesionales.
---

# Bollinger Bands — Análisis Avanzado

John Bollinger (1980s). Medida de volatilidad relativa — el precio "rebota" dentro de bandas basadas en desviación estándar.

## 📐 Fórmula básica

```
Mid = SMA(close, 20)
Upper = Mid + 2 × StdDev(close, 20)
Lower = Mid - 2 × StdDev(close, 20)
```

Típicamente (20, 2) pero ajustable:
- Scalping 5m: BB(10, 2)
- Scalping 15m: BB(20, 2) — estándar
- Swing 1H+: BB(20, 2) o BB(50, 2.5)

## 🎯 Los 4 conceptos clave (más allá del básico)

### 1. **Squeeze** — Contracción de volatilidad

Cuando las bandas se ACERCAN entre sí — volatilidad histórica baja.

**Indicador:** Bollinger Bandwidth
```
BW = (Upper - Lower) / Mid × 100
```

**Interpretación:**
- BW < promedio 6 meses → squeeze (volatilidad comprimida)
- **Regla Bollinger:** volatilidad baja siempre precede alta volatilidad
- **Implica:** breakout inminente, dirección desconocida

**Setup:**
1. Identifica squeeze (BW al mínimo 6 meses)
2. Espera breakout de una banda con volumen
3. Entra en dirección del breakout
4. SL en la banda opuesta
5. TP = 1.5× BW proyectado en dirección

### 2. **Walking the Band** — Surfing la banda

En trends FUERTES, precio "camina" tocando repetidamente una banda.

**Bullish walk:**
- Precio toca banda superior varias veces sin tocar mid
- Cada pullback es a la banda media (SMA 20)
- Continúa mientras la banda suba

**Bearish walk:**
- Precio toca banda inferior repetidamente
- Pullbacks hasta banda media
- Continúa mientras la banda baje

**IMPORTANTE:** En walking the band, NO intentes shortear el top ni longear el bottom.
En vez de eso, **compra/vende en pullbacks a la mid**.

### 3. **%B indicator** — Posición dentro del rango

```
%B = (Close - Lower) / (Upper - Lower)
```

**Lectura:**
- %B > 1.0 → precio arriba de la banda superior (breakout posible)
- %B = 1.0 → tocando banda superior
- %B = 0.5 → en la mid
- %B = 0.0 → tocando banda inferior
- %B < 0.0 → precio abajo de banda inferior

**Uso:**
- %B > 1 sostenido = trend fuerte (not overbought)
- %B < 0 sostenido = trend bajista fuerte
- %B oscila entre 0.2-0.8 = mean reversion funciona

### 4. **Divergencias con BB**

**Bearish divergence con bandas:**
- Precio hace HH tocando banda superior
- Siguiente HH NO toca banda superior
- → Momentum bajista incoming

**Bullish divergence:**
- Precio hace LL tocando banda inferior
- Siguiente LL NO toca banda inferior
- → Momentum alcista incoming

## 🔥 Setups clásicos con Bollinger

### Setup #1: Mean Reversion (el que ya usas)

- Precio toca banda exterior
- RSI extremo
- Vela de rechazo
- Entry al retorno hacia la mid
- Ya implementado en tu estrategia ✅

### Setup #2: Bollinger Squeeze Breakout

1. Identifica squeeze (bandwidth al mínimo de 20 barras)
2. Espera breakout con volumen > 2× promedio
3. Entry en la vela de breakout
4. SL en la banda opuesta al breakout
5. TP1 = altura del squeeze proyectada
6. TP2 = 1.5× altura del squeeze
7. Stop trailing cuando precio llega a banda media

### Setup #3: Walking the Band (trend following)

En trend fuerte:
1. Identifica walk en banda superior/inferior
2. Espera pullback a la banda media (SMA 20)
3. Entry en el rebote de la mid
4. SL debajo del swing low anterior (para long)
5. TP = banda exterior más reciente

### Setup #4: Bollinger + %B convergence

1. Precio se acerca a banda extrema
2. %B llega a extremo (> 1 o < 0)
3. Siguiente vela %B reverso (< 0.95 o > 0.05)
4. Entry en la reversión
5. Target = mid line
6. Extended target = banda opuesta

### Setup #5: Reversal extremos

Cuando precio cierra FUERA de las bandas (raro):
- **Bearish:** close > upper band + bearish candle → probable reversión
- **Bullish:** close < lower band + bullish candle → probable reversión
- Entry en la reversión, SL más allá del extremo

## 📊 Integración con Mean Reversion (tu estrategia)

Tu estrategia Mean Reversion ya usa BB. **Refuerza con estos filtros adicionales:**

**LONG Mean Reversion + BB avanzado:**
- Precio toca Donchian Low ✅
- RSI < 35 ✅
- Low toca BB inferior ✅
- Vela verde ✅
- **+ BONUS: %B < 0 luego > 0 en la misma vela** (true penetration + recovery)
- **+ BONUS: Bandwidth > promedio** (volatilidad normal, no squeeze)
→ Setup robusto

**Durante SQUEEZE:**
- Mean Reversion puede dar señales pero con BAJA conviction
- Mejor esperar el breakout del squeeze ANTES de operar
- En squeeze, regla es "wait and watch"

## 🎨 Indicadores TradingView

- **Bollinger Bands** (default, 20, 2)
- **Bollinger Bands %B**
- **Bollinger Bandwidth**
- **Bollinger Band Width Percentile** (histograma de BW vs histórico)
- **Squeeze Momentum Indicator (LazyBear)** — combina BB + Keltner + momentum

## 🔬 Bollinger Bands + Keltner Channels = TTM Squeeze

**John Carter's TTM Squeeze** combina BB y Keltner:

- **Squeeze ON:** BB dentro de Keltner (volatilidad baja)
- **Squeeze OFF:** BB fuera de Keltner (volatilidad expandiéndose)

Cuando squeeze pasa de ON a OFF → breakout inminente, dirección indicada por momentum.

Indicador gratis en TV: "Squeeze Momentum Indicator" by LazyBear

## 🎓 Errores comunes

1. **Pensar que rebota SIEMPRE en la banda** — en trends walking, no rebota
2. **Shortear solo porque toca banda superior** — necesitas confirmación
3. **No considerar el trend mayor** — BB en contra de trend 4H = riesgo
4. **Ignorar el squeeze** — perder breakouts porque no identifiste contracción

## Uso en el sistema

Cuando se te pida "bollinger", "BB", "squeeze", "bandwidth":
1. Analiza BB actuales (upper, mid, lower, bandwidth)
2. Identifica si estamos en squeeze, walking, o normal
3. Calcula %B actual
4. Busca divergencias
5. Reporta setup apropiado según contexto
6. Integra con Mean Reversion existente
