---
name: stochastic-oscillator
description: Use para análisis con Estocásticos — Full Stochastic, Slow Stochastic, Stochastic RSI. Identifica zonas overbought/oversold, crossovers %K/%D, divergencias con precio. Complementa RSI para timing de entries en scalping.
---

# Estocástico — Momentum Oscillator

George C. Lane (1950s). Mide dónde está el precio actual en relación al rango high-low de N periodos.

## 📐 Fórmula

```
%K = 100 × (Close - LowestLow) / (HighestHigh - LowestLow)
%D = SMA(%K, 3)   # signal line
```

**Lectura:**
- %K > 80 → overbought (cerca del máximo del rango)
- %K < 20 → oversold (cerca del mínimo del rango)
- %K cruza %D de abajo hacia arriba → **señal LONG**
- %K cruza %D de arriba hacia abajo → **señal SHORT**

## 🎨 Tipos de Estocástico

### 1. Fast Stochastic
- %K raw (muy sensible)
- %D = SMA(%K, 3)
- **Problema:** muy ruidoso en scalping

### 2. Slow Stochastic (más usado)
- %K = SMA(Fast %K, 3)  # smoothed
- %D = SMA(Slow %K, 3)
- **Ventaja:** menos false signals

### 3. Full Stochastic (configurable)
- %K length (ej: 14)
- %K smooth (ej: 3)
- %D length (ej: 3)
- **Ventaja:** tú ajustas sensibilidad

### 4. Stochastic RSI (Stoch RSI)
Aplica fórmula de Stochastic AL RSI (no al precio).
- **Hiper-sensible** — detecta cambios antes que RSI solo
- Muy usado en scalping 5m/15m

## 🎯 Parámetros recomendados para BTC 15m

| Tipo | Parámetros | Uso |
|---|---|---|
| **Slow Stoch** | 14, 3, 3 | General |
| **Fast Stoch** | 5, 3, 3 | Scalping 1m/5m |
| **Stoch RSI** | 14, 14, 3, 3 | Scalping 15m confirmation |

## 🔄 Las 5 señales del Stochastic

### 1. Crossover %K/%D
- **Bullish:** %K cruza arriba %D en zona oversold (<20)
- **Bearish:** %K cruza abajo %D en zona overbought (>80)

### 2. Cruce de 50
- **Bullish:** %K cruza arriba de 50 → momentum alcista
- **Bearish:** %K cruza abajo de 50 → momentum bajista

### 3. Estocástico extremo (>80 o <20)
- Precio está en "extremo" del rango reciente
- **Pero ojo:** en trends fuertes, Stoch puede quedarse en overbought/oversold MUCHAS velas
- No vender solo porque >80

### 4. Divergencia Stoch vs Precio
**Bearish divergence:**
- Precio hace HH
- Stoch hace LH
- → Probable reversal bajista

**Bullish divergence:**
- Precio hace LL
- Stoch hace HL
- → Probable reversal alcista

### 5. Failure swing
- Stoch llega a >80 pero no puede hacer HH → señal bearish temprana
- Stoch llega a <20 pero no puede hacer LL → señal bullish temprana

## 📊 Integración con Mean Reversion

**El Stochastic mejora tu confluencia:**

**LONG setup con Stoch:**
- Mean Reversion 4/4 filtros ✅
- **+ Stoch %K < 20** (oversold) ✅
- **+ Cruce %K sobre %D en <20** ✅ (BONUS)
- **+ Divergencia bullish si hay** ✅ (SUPER BONUS)
→ Setup de alta probabilidad

**SHORT setup con Stoch:**
- Mean Reversion SHORT 4/4 ✅
- **+ Stoch %K > 80** (overbought) ✅
- **+ Cruce %K bajo %D en >80** ✅
- **+ Divergencia bearish** ✅
→ Setup de alta probabilidad

## ⚠️ Cuándo NO confiar en Stochastic

1. **Strong trend:** En un rally fuerte, Stoch se queda en >80 por horas. Si vendes cada cruce bajista, pierdes el trend.
2. **Baja volatilidad:** Stoch en rangos de 40-60 = mercado lateral sin dirección clara.
3. **Durante noticias:** spikes momentáneos distorsionan la lectura.

## 🎨 Aplicación en TradingView

En TV buscar:
- "Stochastic" (default, Slow Stoch 14,3,3)
- "Stochastic RSI" (default 14,14,3,3)

Configurable:
- Length
- Smoothing %K
- Smoothing %D
- Upper band (default 80)
- Lower band (default 20)

## 🎓 Reglas prácticas

1. **Usa Stoch EN CONFLUENCIA con otros:**
   - Stoch oversold + precio en soporte + RSI oversold = señal fuerte
   - Stoch oversold solo = débil

2. **TF superior debe confirmar:**
   - Si Stoch 15m es oversold pero Stoch 4H es neutral → OK
   - Si Stoch 15m es oversold pero Stoch 4H es overbought → skip

3. **Ajusta parámetros al TF:**
   - 5m scalping: Stoch 5,3,3 (más rápido)
   - 15m swing: Stoch 14,3,3 (estándar)
   - 1H+ swing: Stoch 21,5,5 (más lento)

## Uso en el sistema

Cuando se te pida "stochastic", "estocástico", "stoch":
1. Lee Stoch del indicador si está visible en chart
2. Analiza si está OB/OS
3. Busca crossovers %K/%D recientes
4. Identifica divergencias
5. Reporta como **confluencia** con Mean Reversion
