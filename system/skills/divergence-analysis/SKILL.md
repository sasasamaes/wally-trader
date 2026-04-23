---
name: divergence-analysis
description: Use para detectar divergencias entre precio e indicadores (RSI, MACD, Stochastic, OBV). Divergencias clase A, B, C. Bull/bear regular y hidden. Señal temprana de reversión con ROI asimétrico.
---

# Análisis de Divergencias

Una de las herramientas más poderosas del TA. Cuando el precio hace un movimiento pero el indicador NO lo confirma, es señal de momentum agotándose.

## 🎯 Concepto base

**Divergencia = precio e indicador se mueven en direcciones DIFERENTES**

Si el precio dice "voy arriba" pero el indicador dice "el momentum se agota" → probable reversión.

## 📊 Tipos de divergencias

### 1. **Bearish Regular Divergence** (reversal top)

```
Precio:      HH  (higher high)
Indicador:   LH  (lower high)
```

Precio hace un máximo más alto, pero RSI/MACD hace un máximo más bajo → **momentum alcista agotándose, bajada incoming**.

**Setup:** SHORT cuando se confirma la divergencia con vela bearish de reversión.

### 2. **Bullish Regular Divergence** (reversal bottom)

```
Precio:      LL  (lower low)
Indicador:   HL  (higher low)
```

Precio hace un mínimo más bajo, pero RSI/MACD hace mínimo más alto → **momentum bajista agotándose, subida incoming**.

**Setup:** LONG cuando se confirma con vela bullish de reversión.

### 3. **Hidden Bullish Divergence** (continuación alcista)

```
Precio:      HL  (higher low)
Indicador:   LL  (lower low)
```

En un uptrend, precio hace un pullback pero no toca el low anterior (HL), mientras el indicador SÍ hace LL → **trend sigue vivo, continúa subiendo**.

**Setup:** LONG en el final del pullback, dirección del trend mayor.

### 4. **Hidden Bearish Divergence** (continuación bajista)

```
Precio:      LH  (lower high)
Indicador:   HH  (higher high)
```

En downtrend, rally a LH pero indicador a HH → **trend bajista sigue, próximo leg down incoming**.

**Setup:** SHORT en el final del rally.

## 🔬 Clasificación por fuerza

### Clase A (la más fuerte)
- Múltiples divergencias consecutivas en el mismo nivel
- Se presenta en turning points mayores
- Confirma con volumen aumentando

### Clase B (moderada)
- Una divergencia clara
- En niveles de soporte/resistencia conocidos
- Volumen normal

### Clase C (débil)
- Divergencia en mini-swings
- Sin contexto de S/R
- Ignorar en TFs bajos (5m)

## 🎨 Mejores indicadores para divergencias

### 1. **RSI (14)**
El más común y efectivo.
- Busca HH precio vs LH RSI (bearish)
- Busca LL precio vs HL RSI (bullish)

### 2. **MACD**
Usa MACD histogram (no la línea).
- Histogram muestra aceleración/desaceleración
- Divergencias en histogram muy poderosas

### 3. **Stochastic**
Bueno para scalping (más sensible).
- Stochastic RSI detecta divergencias muy tempranas

### 4. **OBV (On-Balance Volume)**
- Mide acumulación/distribución
- Divergencias aquí indican **smart money moving contrario al precio**

### 5. **AO (Awesome Oscillator)** de Bill Williams
- Histograma simple
- Bueno para swing trading

## 🎯 Setup completo de divergencia

### Bearish divergence setup (short):

1. Precio hace HH significativo
2. RSI/MACD hace LH (divergencia)
3. Esperar vela de confirmación (engulfing, shooting star)
4. **Entry** en el cierre de la vela de confirmación
5. **SL** arriba del HH reciente
6. **TP1:** swing low del impulso previo
7. **TP2:** soporte mayor
8. **TP3:** Fibonacci extension 1.618

### Bullish divergence setup (long):

Mirror del anterior.

## 📊 Timeframes y divergencias

**Regla fundamental:** divergencia en TF alto > divergencia en TF bajo.

| TF divergencia | Fuerza | Uso |
|---|---|---|
| **Weekly/Daily** | Máxima | Cambio de tendencia macro |
| **4H** | Fuerte | Reversal swing trade |
| **1H** | Media | Mean reversion 15m-1H |
| **15m** | Débil | Scalping (+1 confirmation) |
| **5m** | Muy débil | Noise, ignorar |

**Combo mortal:** divergencia en 4H + confirmación en 15m = setup ÉPICO.

## 🔥 Divergencia + Confluencia

Las divergencias solas son útiles, pero el poder viene de la **confluencia**:

- Divergencia RSI + nivel Fibonacci = bueno
- Divergencia RSI + Fib + Order Block = mejor
- Divergencia RSI + Fib + OB + Elliott wave completing = ÉPICO

## 🎯 Integración con Mean Reversion

### Cómo las divergencias refuerzan tu estrategia:

**LONG Mean Reversion + Bullish Divergence:**
- 4 filtros básicos ✅
- **+ Bullish divergence en RSI 15m** ✅ (señal temprana de reversión)
- **+ Bullish divergence en RSI 1H** ✅ (super bonus)
→ Setup con **ROI asimétrico** — riesgo chico, recompensa grande

**SHORT Mean Reversion + Bearish Divergence:**
- Similar, con divergencia bajista

### Divergencias detectan TOPS y BOTTOMS:

A veces el mercado no está exactamente en "Donchian Low" (no cumple Mean Reversion estricto) pero hay una **divergencia clara**. En ese caso, el trade puede ser válido **si hay fuerte confluencia de otras señales**.

## 🎨 TradingView tools

### Indicadores automáticos de divergencia:
- **"Divergence Indicator"** (muchas versiones community)
- **"RSI Divergence Scanner"**
- **"MACD Divergence"**
- **"Auto Divergence Finder"** (muy popular)

Estos marcan automáticamente las divergencias en el chart con líneas y etiquetas.

### Manual (más preciso):
1. Añade RSI (14)
2. Identifica 2 swing highs recientes del precio
3. Compara los valores de RSI en esos mismos puntos
4. Si precio HH pero RSI LH → bearish divergence dibujada

## 🧠 Filosofía de las divergencias

Las divergencias son **pre-señales de cambio**. El precio todavía no ha invertido, pero el momentum ya está mostrando debilidad.

Esto te da:
- **Entry más temprana** → mejor R:R
- **SL más cercano** → menor riesgo
- **Timing profesional** → antes de que otros se den cuenta

## ⚠️ Limitaciones honestas

1. **Falsas divergencias son comunes** — 30-40% no resultan en reversión
2. **Puede tardar MUCHAS velas** en materializarse
3. **En trends fuertes**, las divergencias pueden extenderse por semanas
4. **Requiere confirmación** — nunca entres solo por divergencia

## 🎓 Reglas mentales

1. **"Divergencia sin confirmación = observar, no actuar"**
2. **"TF alto > TF bajo"** — siempre
3. **"Clase A es rara pero valiosa"** — cuando la ves, préstale atención
4. **"Hidden divergences en dirección del trend = dinero fácil"**
5. **"Divergencia + S/R = combo ganador"**

## Uso en el sistema

Cuando se te pida "divergencia", "divergence", "RSI divergence", "momentum":
1. Analiza últimas 10-20 velas
2. Busca HH/LL del precio
3. Compara con RSI y MACD
4. Identifica tipo de divergencia (regular/hidden, bull/bear)
5. Clasifica fuerza (A/B/C)
6. Reporta con recomendación de acción
7. Integra con setup Mean Reversion si aplica
