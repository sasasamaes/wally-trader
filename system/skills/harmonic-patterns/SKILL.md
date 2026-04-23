---
name: harmonic-patterns
description: Use para identificar y operar patrones armónicos (Gartley, Bat, Butterfly, Crab, Shark, Cypher, 3-Drive, AB=CD). Basados en ratios Fibonacci precisos. Pattern completion = PRZ (Potential Reversal Zone) donde se ejecuta entry de reversión.
---

# Patrones Armónicos — Trading con Fibonacci

Patrones geométricos basados en ratios Fibonacci precisos. Desarrollados por H.M. Gartley (1935) y expandidos por Scott Carney, Larry Pesavento, etc.

## 🔷 Estructura general XABCD

Todos los armónicos tienen 5 puntos: **X, A, B, C, D**

```
        B
       /\
      /  \
X-----\  /\
       \/  \
       A    \
             D  ← PRZ (Potential Reversal Zone) = entry
             
(en bearish harmonic todo invertido)
```

- **X:** punto de origen
- **A:** primer swing
- **B:** retroceso de XA (ratio específico)
- **C:** retroceso de AB
- **D:** punto de entrada — extensión/retroceso específico de BC y XA

## 📐 Ratios Fibonacci clave

| Ratio | Uso común |
|---|---|
| 0.382 | Retroceso shallow |
| 0.5 | Retroceso medio |
| **0.618** | **Golden ratio** — retroceso standard |
| 0.786 | Retroceso deep |
| 0.886 | Retroceso muy deep |
| 1.272 | Extensión corta |
| **1.618** | **Golden extension** |
| 2.0 | Extensión media |
| 2.24 | Extensión Crab |
| 2.618 | Extensión Deep Crab |
| 3.14 / 3.618 | Extensiones extremas |

## 🎯 Los 6 patrones clásicos

### 1. **Gartley (222)**

El original. Reversal conservador.

| Pierna | Ratio |
|---|---|
| B retrocede XA | **0.618** |
| C retrocede AB | 0.382 – 0.886 |
| BC extensión | 1.13 – 1.618 |
| D = retroceso XA | **0.786** |
| AD retroceso XA | 0.786 |

**PRZ:** ~0.786 del XA
**SL:** más allá de X
**TP1:** 0.382 del AD | **TP2:** 0.618 del AD

---

### 2. **Bat**

Similar al Gartley pero retroceso más profundo. Más común en cripto.

| Pierna | Ratio |
|---|---|
| B retrocede XA | 0.382 – 0.5 |
| C retrocede AB | 0.382 – 0.886 |
| BC extensión | 1.618 – 2.618 |
| D = retroceso XA | **0.886** |

**PRZ:** 0.886 de XA (más profundo que Gartley)
**SL:** más allá de X
**TP1:** 0.382 de AD

---

### 3. **Butterfly**

Pattern de extensión — D va MÁS ALLÁ de X.

| Pierna | Ratio |
|---|---|
| B retrocede XA | **0.786** |
| C retrocede AB | 0.382 – 0.886 |
| BC extensión | 1.618 – 2.24 |
| D = extensión XA | **1.272** (AD > XA) |

**PRZ:** 1.272 de XA
**SL:** beyond 1.414 de XA
**TP:** más agresivo — 0.618 de AD

---

### 4. **Crab**

Pattern más precisa, extensión extrema.

| Pierna | Ratio |
|---|---|
| B retrocede XA | 0.382 – 0.618 |
| C retrocede AB | 0.382 – 0.886 |
| BC extensión | **2.618 – 3.618** |
| D = extensión XA | **1.618** |

**PRZ:** 1.618 de XA (extremo)
**SL:** beyond 1.786 de XA (stop muy cercano al PRZ)
**TP:** 0.618 de AD — scalp rápido

---

### 5. **Shark**

Pattern de Carney, 5 puntos con nomenclatura diferente (0, X, A, B, C).

| Pierna | Ratio |
|---|---|
| B retrocede XA | 1.13 – 1.618 |
| C extensión AB | **1.618 – 2.24** |

**PRZ:** en la zona 88.6% – 113% de 0-X
**SL:** beyond el PRZ (~20 pips)
**TP:** 0.5 del BC

---

### 6. **Cypher**

Menos conocido, pero muy eficaz en timeframes cortos.

| Pierna | Ratio |
|---|---|
| B retrocede XA | 0.382 – 0.618 |
| C extensión XB | 1.272 – 1.414 |
| D retrocede XC | **0.786** |

**PRZ:** 0.786 de XC
**SL:** beyond C (no X)
**TP:** 0.382 – 0.618 de CD

---

## 🎯 Cómo identificar armónicos en BTC 15m

### Paso 1: Identifica 2 swing points claros
Busca pivotes obvios en el chart — 2 máximos o 2 mínimos conectados por un impulso.

### Paso 2: Dibuja los 3 primeros puntos (X, A, B)
- X = primer pivot
- A = swing opuesto
- B = retroceso de XA (debe ser uno de los ratios estándar: 0.382, 0.5, 0.618, 0.786, 0.886)

### Paso 3: Identifica el ratio de B
Si B es 0.618 de XA → puede ser Gartley o Butterfly
Si B es 0.5 de XA → puede ser Bat
Si B es 0.786 de XA → puede ser Butterfly

### Paso 4: Espera el movimiento C
Debe ser retroceso de AB (entre 0.382 y 0.886)

### Paso 5: Proyecta el PRZ donde estará D
Según el pattern, D estará en un ratio específico de XA o BC.

### Paso 6: Espera que precio llegue al PRZ
Ahí es donde se ejecuta el trade.

## 🎨 Tools en TradingView

TV tiene herramientas nativas:
- **XABCD Pattern** (en drawing tools)
- **Harmonic Pattern** (por Shark, Bat, Gartley)
- **Cypher Pattern**
- **5-0 Pattern**

También hay scripts públicos como:
- "Harmonic Pattern Finder" (detecta automáticamente)
- "Auto Harmonic Pattern" (alertas automáticas)

## 📊 Integración con Mean Reversion

**Cuando un harmónico completa en la zona Donchian:**

**Bullish harmonic (Gartley/Bat/Butterfly/Crab bullish) + Mean Reversion LONG:**
- Los 4 filtros Mean Reversion dan GO
- ADEMÁS el PRZ del harmónico coincide con la zona LONG (Donchian Low ±0.1%)
- → Setup con **CONFLUENCIA FUERTE** — size 1.5× normal
- SL más conservador: fuera del X (más profundo que el SL normal)
- TP1 al 0.382 del AD (puede ser más lejano que el TP1 del Mean Reversion)

**Bearish harmonic + Mean Reversion SHORT:**
- Mismo concepto mirror

## 🚨 Reglas de validación

**Un harmónico es VÁLIDO solo si:**
1. Los 3 ratios clave están dentro de tolerancia ±5%
2. Los 5 puntos (X,A,B,C,D) son pivotes claros, no noise
3. Está en timeframe coherente (no mezclar H4 con 5m)
4. Hay confirmación de reversión (divergencia RSI, volumen, etc.)

**Patrón es INVÁLIDO si:**
- Precio rompe X (en Gartley/Bat/Butterfly)
- Precio rompe D significativamente sin reversión
- Los ratios están fuera de tolerancia
- Hay noticia major durante la formación (invalida geometría pura)

## 📐 Fibonacci Ratios cheat sheet

```
Retracements: 0.236, 0.382, 0.5, 0.618, 0.786, 0.886
Extensions:   1.272, 1.414, 1.618, 2.0, 2.24, 2.618, 3.14, 3.618
```

## 🎯 Workflow para BTC scalping 15m

1. **Escanear últimas 50-100 velas** por pivotes claros
2. **Identificar potencial X-A-B** (3 primeros puntos)
3. **Medir ratios** con TV Fibonacci tool
4. **Proyectar PRZ** del pattern más probable
5. **Esperar precio al PRZ**
6. **Confirmar** con:
   - Divergencia RSI
   - Volumen elevado en el toque
   - Bullish/bearish engulfing al llegar
7. **Entry** en el PRZ con SL al otro lado del X (o D para Cypher)

## 🎓 Errores comunes

1. **Forzar el pattern** — si los ratios no cuadran, NO es ese pattern
2. **Ignorar tendencia macro** — un bullish Gartley contra downtrend D1 = skip
3. **Entry antes del PRZ** — no anticipes, espera el toque
4. **SL demasiado apretado** — armónicos a veces "penetran" antes de revertir
5. **TP muy lejano** — los armónicos suelen dar moves moderados, toma profits a tiempo

## ⚡ Tip: auto-detectar con scripts

En TV, agregar indicador "Harmonic Pattern Detection" (varios gratis) que:
- Dibuja automáticamente patterns formándose
- Marca el PRZ
- Alerta cuando precio llega al PRZ

Recomendado: **"Harmonic Patterns"** por HeWhoMustNotBeNamed (muy bueno, gratis)

## Uso en el sistema

Cuando se te pida "armónico", "harmonic", "Gartley/Bat/Butterfly/Crab":
1. Analiza últimas 50 velas 15m (o TF relevante)
2. Identifica potenciales XABCD
3. Mide ratios con precisión (±5% tolerancia)
4. Reporta pattern detectado + PRZ + SL + TP
5. Si se combina con setup Mean Reversion → confluencia fuerte
