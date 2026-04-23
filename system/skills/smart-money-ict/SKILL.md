---
name: smart-money-ict
description: Use para análisis de Smart Money Concepts (SMC/ICT) — Order Blocks, Fair Value Gaps, Breaker Blocks, Break of Structure, Change of Character, Liquidity Grabs, Premium/Discount zones. Ideal para identificar niveles donde instituciones dejan huella.
---

# Smart Money Concepts (ICT — Inner Circle Trader)

Metodología de Michael J. Huddleston que identifica el comportamiento de instituciones/market makers en el precio. Se basa en que el mercado no es aleatorio — el "dinero inteligente" deja patrones identificables.

## 🧠 Conceptos core

### 1. **Order Block (OB)** — Bloque de órdenes
Última vela opuesta antes de un movimiento impulsivo.
- **Bullish OB:** última vela BAJISTA antes de impulso alcista
- **Bearish OB:** última vela ALCISTA antes de impulso bajista
- **Uso:** precio tiende a regresar a "mitigar" el OB y rebotar

**Cómo identificar en BTC 15m:**
1. Busca un movimiento impulsivo (>3 velas mismo color, >1% move)
2. Marca la última vela de color opuesto ANTES del impulso
3. El rango high-low de esa vela = Order Block
4. Precio vuelve 60-70% de las veces para "mitigar" el OB

### 2. **Fair Value Gap (FVG)** — Brecha de valor justo
Imbalance de 3 velas donde la vela del medio "salta" por encima del high/low de las adyacentes.
- **Bullish FVG:** low de vela 3 > high de vela 1
- **Bearish FVG:** high de vela 3 < low de vela 1
- **Uso:** precio rellena el FVG 80% de las veces (mean reversion implícita)

**Ejemplo visual:**
```
Vela 1: high 75,400
Vela 2: salta de 75,500 a 76,200 (gap)
Vela 3: low 76,100

FVG = zona 75,400 - 76,100 (sin tocar)
Expectativa: precio vuelve a tocar esa zona
```

### 3. **Break of Structure (BoS)** — Ruptura estructural
Cuando precio rompe un high/low previo significativo, confirmando continuación de tendencia.
- **Bullish BoS:** precio rompe Higher High anterior
- **Bearish BoS:** precio rompe Lower Low anterior
- **Uso:** confirma que la tendencia sigue viva

### 4. **Change of Character (ChoCh)** — Cambio de carácter
Primera ruptura contra la tendencia previa.
- **De bull a bear:** precio rompe el Higher Low anterior (primer LL)
- **De bear a bull:** precio rompe el Lower High anterior (primer HH)
- **Uso:** señal temprana de reversal de tendencia

### 5. **Liquidity** — Liquidez
Zonas donde hay órdenes acumuladas (stop losses, pending orders).
- **Buy-side Liquidity (BSL):** above recent highs (donde shorts tienen SL)
- **Sell-side Liquidity (SSL):** below recent lows (donde longs tienen SL)
- **Uso:** precio va a buscar liquidez ANTES de el movimiento real

**Liquidity grab / Stop hunt:**
Precio hace un wick corto sobre un nivel de liquidez (BSL/SSL) y luego se revierte → clásico "caza de stops" antes del movimiento institucional.

### 6. **Premium / Discount zones**
Divide el rango macro en 3:
- **Premium (top 50%):** zona de VENTA preferida
- **Equilibrium (mid):** neutro
- **Discount (bottom 50%):** zona de COMPRA preferida

**Uso:** compra solo en discount, vende solo en premium (si la tendencia lo permite).

### 7. **Breaker Block**
Un Order Block que fue roto y se convierte en soporte/resistencia invertido.
- **Bullish Breaker:** bearish OB roto al alza → ahora es soporte
- **Bearish Breaker:** bullish OB roto a la baja → ahora es resistencia

### 8. **Mitigation Block**
OB que fue parcialmente mitigado (precio tocó y rebotó). Si vuelve a tocarlo, probablemente rompe.

## 🎯 Setup ICT clásico (aplicable a BTC 15m)

### Entrada bullish con confluencia ICT:

1. **Identificar estructura:** ¿tendencia alcista? (HHs + HLs)
2. **Detectar ChoCh o BoS reciente:** sabe por dónde va el precio
3. **Marcar Order Block bullish** en el último pullback
4. **Buscar FVG abajo del precio** (zona de mitigación)
5. **Liquidity grab:** ¿precio barrió lows cercanos antes de subir?
6. **Entry:** al toque del OB + FVG (confluencia)
7. **SL:** debajo del OB (vela entera + buffer)
8. **TP:** siguiente liquidity pool (BSL above) o nivel de premium

### Entrada bearish (mirror):

1. Tendencia bajista (LHs + LLs)
2. BoS o ChoCh bajista
3. Bearish OB en último rally
4. Bearish FVG arriba
5. Liquidity grab en HH
6. Entry al toque de OB + FVG
7. SL arriba del OB
8. TP: SSL abajo o discount zone

## 📊 Aplicación a la estrategia Mean Reversion actual

**Cómo integrar ICT al sistema:**

Antes de entrar a un setup Mean Reversion 4/4, añade confirmación ICT:

**LONG Mean Reversion + ICT:**
- ✅ 4 filtros Mean Reversion cumplidos
- ✅ **BONUS:** precio tocando un Bullish OB o rellenando un Bullish FVG
- ✅ **BONUS:** hubo liquidity grab reciente (barrido de SSL abajo)
- → Entry con confianza AUMENTADA (size 1.2× normal)

**SHORT Mean Reversion + ICT:**
- ✅ 4 filtros SHORT cumplidos
- ✅ **BONUS:** precio tocando Bearish OB o rellenando Bearish FVG
- ✅ **BONUS:** liquidity grab en BSL arriba
- → Entry con mayor convicción

**Señal de contradicción ICT:**
Si los 4 filtros dan LONG pero ICT muestra:
- Bearish OB arriba (resistencia institucional)
- Falta mitigar un Bearish FVG arriba
- No ha habido liquidity grab en SSL
→ **SKIP el trade** aunque técnica diga GO

## 🔍 Niveles clave BTC actuales (a dibujar en chart)

Cuando se analice BTC, identificar y dibujar:
- **Daily Order Blocks** (recientes)
- **H4 Fair Value Gaps** no rellenados
- **Weekly liquidity pools** (BSL/SSL macro)
- **Asian session range** (suele ser mitigado en NY)

## 🧭 Sesiones ICT (importante para timing)

| Sesión | Hora UTC | Hora MX | Comportamiento típico |
|---|---|---|---|
| **Asian range** | 00:00-07:00 | 18:00-01:00 | Consolida, crea el rango del día |
| **London open** | 07:00-10:00 | 01:00-04:00 | Manipulación + primer move |
| **NY open** | 13:30-16:00 | 07:30-10:00 | **Movimiento real**, el que vale |
| **NY close** | 20:00-22:00 | 14:00-16:00 | Cierre posiciones, reversión común |

**Regla ICT:** la MEJOR entrada del día suele estar en el **London-NY overlap (UTC 13-15 = MX 07-09)**, después de que London hizo el "judas swing" (fake move) y NY lo revierte.

**Coincide con tu ventana óptima MX 06-10.** ✅

## 📚 Reglas mentales ICT

1. **El mercado busca liquidez** — si hay stops arriba/abajo, los va a tomar
2. **OBs no se tocan para siempre** — después de 2-3 mitigaciones, se rompen
3. **FVGs tienden a rellenarse** — pero a veces el "gap" queda abierto si el momentum es muy fuerte
4. **ChoCh > BoS** — el cambio de carácter es más poderoso que la continuación
5. **Premium/Discount define sesgo macro** — no operes contra él

## ⚠️ Limitaciones

- ICT requiere práctica visual para identificar OBs/FVGs correctamente
- En mercados ranging muy apretados, los OBs se mitigan constantemente y pierden validez
- Funciona mejor en H4/D1 para identificación, 15m/5m para ejecución
- No hay indicador perfecto — es análisis visual con reglas

## 🎓 Recursos para profundizar

- ICT Mentorship (gratis en YouTube de Michael Huddleston)
- The Strat by Rob Smith (complementario)
- SMC Concepts por varios creators en YouTube

## Uso en el sistema actual

Cuando se te pida un análisis con "smart money" o "ICT" o "institucional":
1. Identifica últimos 3 Order Blocks significativos (alcistas y bajistas)
2. Detecta FVGs abiertos
3. Marca BSL/SSL obvios
4. Identifica ChoCh/BoS reciente
5. Divide el rango en Premium/Discount
6. Sugiere entry con confluencia ICT + Mean Reversion
