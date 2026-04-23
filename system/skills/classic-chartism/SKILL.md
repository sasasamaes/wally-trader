---
name: classic-chartism
description: Use para identificar patrones chartistas clásicos — Head & Shoulders, triangles, flags, pennants, wedges, double/triple tops/bottoms, cup and handle, rectangles. Patterns con décadas de validación estadística.
---

# Chartismo Clásico — Patrones de Precio

Patrones geométricos que se repiten en los mercados desde hace +100 años. Dow Theory → Edwards & Magee → base de técnica moderna.

## 📚 Los 2 grandes grupos

### **REVERSIÓN:** señalan cambio de tendencia
- Head & Shoulders / Inverse H&S
- Double Top / Double Bottom
- Triple Top / Triple Bottom
- Rounding Top / Rounding Bottom (Saucer)

### **CONTINUACIÓN:** señalan pausa y continuación
- Triangles (ascending, descending, symmetrical)
- Flags / Pennants
- Rectangles
- Wedges (rising/falling)
- Cup and Handle

---

## 🔻 PATRONES DE REVERSIÓN

### 1. Head & Shoulders (Cabeza y Hombros) — Top reversal

**Estructura:**
```
          H
    LS  /  \  RS
    /\ /    \/\
   /  V      V  \
  /              \
 /   NECKLINE    \
-------×----------
```

- **LS (Left Shoulder):** primer máximo
- **H (Head):** máximo más alto
- **RS (Right Shoulder):** máximo similar al LS
- **Neckline:** línea que conecta los mínimos entre LS-H y H-RS

**Target (objetivo):**
Target = Neckline - (Head height - Neckline)
Ejemplo: Head = 78,000, Neckline = 75,000 → Target = 72,000

**Entry:** al romper neckline hacia abajo (con volumen)
**SL:** arriba del RS
**Confirmación:** volumen decreciente en RS vs LS, y spike al romper neckline

### 2. Inverse Head & Shoulders — Bottom reversal (mirror)
Mismo concepto pero invertido. Señal alcista. Target calculado igual pero al alza.

### 3. Double Top (M pattern)

```
  P1    P2
  /\   /\
 /  \ /  \
/    V    \
   VALLEY  \
```

- Dos máximos similares
- Valley (valle) entre ambos
- Target = Valley - (Peak - Valley)

**Entry:** al romper valley hacia abajo
**SL:** arriba de P2

### 4. Double Bottom (W pattern) — mirror
Dos mínimos similares. Target al alza.

### 5. Triple Top / Bottom
Tres intentos de romper nivel. Cuando falla 3 veces → reversal muy probable.

### 6. Rounding Bottom (Saucer)
Gradual cambio de bearish a bullish. Meses de formación típicamente. Muy bullish cuando completa.

---

## 🔺 PATRONES DE CONTINUACIÓN

### 7. Ascending Triangle (alcista)

```
       ───────────  ← resistencia horizontal
      /|
     / |
    /  |
   /___|___
  trendline alcista
```

- Resistencia HORIZONTAL
- Soporte ASCENDENTE
- Higher lows presionan contra la resistencia
- Breakout USUAL hacia arriba (70% probabilidad)

**Target:** altura del triángulo proyectada arriba
**Entry:** al romper resistencia con volumen

### 8. Descending Triangle (bajista) — mirror
Resistencia descendente, soporte horizontal. Breakout usual hacia abajo.

### 9. Symmetrical Triangle (neutro)

```
  \         /
   \       /
    \     /
     \   /
      \ /
       V
```

- Ambas líneas convergen
- Indecisión
- Breakout en dirección de tendencia previa (con volumen)

### 10. Flag (Bandera)

Después de movimiento fuerte, consolidación pequeña contra-tendencia.

**Bull flag:**
- Subida fuerte (mástil)
- Consolidación bajando levemente (flag)
- Breakout arriba = continuación

**Target:** altura del mástil proyectado desde el breakout

**Bear flag:** mirror

### 11. Pennant (Gallardete)

Similar al flag pero con convergencia (triangular) en vez de paralela.
- Mástil fuerte + triángulo pequeño
- Breakout en dirección del mástil

### 12. Rectangle (Rango horizontal)

```
 ─────────────────  ← resistencia
 
       range
 
 ─────────────────  ← soporte
```

- Consolidación lateral clara
- Se rompe en dirección de la tendencia mayor

**Target:** altura del rectángulo proyectado en la dirección del breakout

### 13. Rising Wedge (Cuña ascendente) — bajista

```
      /
     /
    /  /
   /  /
  /  /
  ambas líneas suben pero convergen
```

Ambas líneas ascendentes convergiendo. **BAJISTA** (contraintuitivo).

### 14. Falling Wedge (Cuña descendente) — alcista (mirror)

### 15. Cup and Handle

```
    ╭──────╮         ← handle (pullback pequeño)
   /        \
  /          \
 /   cup      \
──            ──
```

- Cup: redondeo en U (forma de taza)
- Handle: pullback pequeño en el borde derecho de la U
- Breakout del handle = señal alcista fuerte

---

## 🎨 Herramientas de detección en TV

TV tiene indicadores para auto-detectar:
- "Auto Chart Patterns" (detecta H&S, triangles, flags)
- "Chart Pattern Recognition" (Gilbert)
- "Simple Chart Pattern Detector"

Scripts gratis de calidad: muchos en TV Community Scripts.

---

## 📊 Integración con estrategia Mean Reversion

**En mercado RANGE (régimen actual):**

Los patrones que funcionan mejor:
- **Rectangle** → trading del rango (compra bottom, vende top)
- **Double top/bottom** → reversal al llegar al extremo del rango
- **Symmetric triangle** → señal de inminente breakout

**Cuando BTC rompe el rango (TRENDING):**
- **Ascending/descending triangle** → continuación probable
- **Flag/Pennant** → pausa breve, continúa el move
- **Cup and handle** → fuerza alcista/bajista confirmada

**Cuando chartismo SE OPONE a Mean Reversion:**
Ejemplo: Mean Reversion dice LONG en Donchian Low, pero hay Head & Shoulders formándose en 1H → **SKIP o reduce size**.

## 🎯 Reglas prácticas de chartismo

### 1. El volumen confirma el patrón
- En triangles/flags: volumen DISMINUYE durante la formación, EXPLOTA en breakout
- En H&S: volumen decreciente en cada hombro, explota al romper neckline
- Sin volumen confirmatorio → el patrón es sospechoso

### 2. Medición de targets
Todos los patrones tienen cálculo geométrico de target:
- **H&S:** altura de la cabeza proyectada desde neckline
- **Triangles:** altura del triángulo proyectada desde breakout
- **Flags:** altura del mástil proyectada desde breakout
- **Rectangles:** altura del rango proyectada desde breakout

### 3. False breakouts son comunes
- **Confirmación:** esperar cierre de 1-3 velas fuera del patrón
- **Retest:** muchos patrones retroceden al nivel roto (retest) antes de continuar
- Entry en el retest tiene mejor R:R que en el breakout inicial

### 4. Timeframe importa
- H&S en Daily tiene mucha más fuerza que en 5m
- Flag en 15m es válido si el mástil es de 1H o más
- No mezcles TFs — identifica y opera en el mismo

### 5. Contexto macro
Un patrón contra la tendencia macro tiene menor probabilidad.
- Ascending triangle en downtrend diario → probable fakeout
- Double bottom en uptrend diario → reversal confirmado

---

## 🎓 Psicología detrás de cada patrón

Cada patrón refleja un comportamiento de mercado:

- **H&S:** buyers se agotaron en la cabeza, smart money distribuyendo
- **Triangle:** equilibrio entre bulls y bears, uno va a romper
- **Flag:** pausa saludable antes de continuación
- **Double bottom:** segundo test de soporte falla, bulls toman control
- **Rising wedge:** ganancias cada vez más pequeñas, momentum bajando

Entender el "por qué" te ayuda a confiar en el patrón.

---

## 📚 Checklist de validación de patrón

Antes de operar un patrón, verifica:

- [ ] Identificable claramente (no forzado)
- [ ] Mínimo 2 touches en cada nivel relevante
- [ ] Volumen coherente con el patrón
- [ ] En timeframe apropiado (H4 o superior para swings; 15m+ para intraday)
- [ ] Confirmación (cierre fuera del patrón, no solo wick)
- [ ] Tendencia macro no contradice
- [ ] Target proyectado tiene sentido (no está a 10% de distancia en 15m)
- [ ] Puedo identificar el SL claramente

Si ✅ todos → ejecutar. Si ❌ cualquiera → esperar.

## Uso en el sistema

Cuando se te pida "chartismo", "patrón clásico", "H&S", "triangle", "flag":
1. Analiza últimas 50-100 velas en TF relevante
2. Identifica cualquier patrón en formación
3. Mide geometría y calcula target
4. Verifica volumen coherente
5. Reporta pattern + confirmación necesaria + entry/SL/TP
6. Integra con Mean Reversion si hay confluencia
