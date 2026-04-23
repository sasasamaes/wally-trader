---
name: neptune-indicators
description: Use para leer y usar los indicadores privados Neptune (by Bangchan10) — Oscillator, Signals, SMC, Money Flow Profile, SMC Oscillator, Pivots and Phases. La comunidad punkchainer's los usa para generar señales. Mi sistema puede leer su output via MCP y validar cruzadamente con mis propios indicadores.
---

# Neptune Indicators (by Bangchan10)

Set de indicadores privados usados por la comunidad **punkchainer's** para generar señales. Son invitation-only en TradingView pero al estar cargados en tu chart, mi sistema puede leer sus outputs.

## 📋 Los 6 indicadores Neptune

### 1. **Neptune® — Signals™**
**Función:** Genera señales de entrada/salida con línea de tendencia adaptativa.

**Outputs legibles via MCP:**
- `Neptune Line` — línea dinámica de soporte/resistencia (proxy de tendencia)
- `Shapes` — marcadores de entrada (0 si no hay, valor si hay)
- `Exit Bearish` / `Bearish Exit` — salida de short
- `Exit Bullish` / `Bullish Exit` — salida de long

**Lectura:**
- Precio > Neptune Line → sesgo **BULLISH**
- Precio < Neptune Line → sesgo **BEARISH**
- Shape aparece (valor != 0) → señal de entrada
- Exit value aparece → cierre de posición actual

**Timeframes comunes:** 15m-4h

### 2. **Neptune® — Oscillator™**
**Función:** Oscilador combinado de momentum + volumen + volatilidad.

**Outputs legibles via MCP:**
- `Hyper Wave (Main)` — oscilador principal (0-100)
- `Hyper Wave MA (Main)` — promedio móvil del Hyper Wave
- `Hyper Wave Signal` — línea de señal
- `Oscillator Trackprice` — tracking del precio en el oscilador
- `Directional Pressure Volume Bars` — presión direccional del volumen
- `Anomalies Top` — detector de anomalías extremas

**Lectura:**
- Hyper Wave > 84 → **sobrecomprado extremo**
- Hyper Wave > 64 → sobrecompra moderada
- Hyper Wave 36-64 → **zona neutral**
- Hyper Wave < 36 → sobreventa moderada
- Hyper Wave < 18 → **sobreventa extrema**
- Hyper Wave cruza arriba Hyper Wave MA → momentum bullish
- Hyper Wave cruza abajo Hyper Wave MA → momentum bearish
- Directional Pressure > 5 → flujo direccional positivo
- Directional Pressure < -5 → flujo direccional negativo

**Niveles clave dibujados:** 84, 64, 50, 36, 18

### 3. **Neptune® — Smart Money Concepts™ (SMC)**
**Función:** Identifica Order Blocks, Fair Value Gaps, Break of Structure, liquidity zones.

**Outputs legibles via MCP:**
- Via `data_get_pine_boxes` → Order Blocks como {high, low}
- Via `data_get_pine_lines` → niveles de liquidity y FVG
- Via `data_get_pine_labels` → "OB", "FVG", "BOS", "CHOCH" con precios

**Lectura:**
- Box verde abajo = Bullish OB
- Box rojo arriba = Bearish OB
- Líneas horizontales = liquidity pools (BSL/SSL)
- Labels con texto = eventos estructurales

### 4. **Neptune® — Money Flow Profile™**
**Función:** Profile de volumen + money flow por niveles de precio.

**Outputs legibles via MCP:**
- Via `data_get_pine_tables` → tabla de niveles con volumen
- Via `data_get_pine_lines` → niveles de alta actividad (POC, VAH, VAL)

**Lectura:**
- POC (Point of Control) = precio con más volumen = imán de precio
- VAH / VAL (Value Area High/Low) = zona donde ocurrió 70% del volumen

### 5. **SMC Oscillator™**
**Función:** Oscilador específico para SMC (fuerza del smart money).

**Outputs:** Similar estructura al Neptune Oscillator pero filtrado por actividad institucional.

### 6. **Pivots and Phases™**
**Función:** Detecta pivotes de mercado + ciclo actual del precio.

**Outputs legibles:**
- Labels con tipo de pivote ("Pivot High", "Pivot Low")
- Fases del ciclo (accumulation, markup, distribution, markdown)

## 🔬 Cómo leer Neptune desde tu sistema

### Verificar si están cargados

```
chart_get_state
```

Busca en `studies`:
- "Neptune® - Signals™"
- "Neptune® - Oscillator™"
- "Neptune® - Smart Money Concepts™"
- "Neptune® - Money Flow Profile™"
- "SMC Oscillator™"
- "Pivots and Phases™"

### Leer valores actuales

```
data_get_study_values
```

Retorna tabla con todos los valores calculados de cada indicador visible.

### Leer elementos dibujados

```
data_get_pine_lines     # líneas horizontales
data_get_pine_labels    # etiquetas con texto
data_get_pine_boxes     # zonas/order blocks
data_get_pine_tables    # tablas de analytics
```

**Parameter crítico:** `study_filter="Neptune"` para filtrar solo outputs Neptune.

## 📊 Ejemplo real

**Chart con Neptune Oscillator + Signals activos:**

```
data_get_study_values retorna:
{
  "Neptune® - Signals™": {
    "Neptune Line": "75,938.4",
    "Shapes": "0,0",
    "Exit Bearish": "0,0",
    "Exit Bullish": "0,0"
  },
  "Neptune® - Oscillator™": {
    "Hyper Wave (Main)": "59.8",
    "Hyper Wave MA (Main)": "25.7",
    "Hyper Wave Signal": "68.9",
    "Directional Pressure Volume Bars": "4.6"
  }
}
```

**Interpretación:**
- Precio actual 75,375 vs Neptune Line 75,938 → **BEARISH sesgo** (precio debajo)
- Hyper Wave 59.8 > MA 25.7 → **momentum bullish reciente** (cruce arriba)
- Hyper Wave 59.8 < 64 → no overbought todavía
- Directional Pressure 4.6 → presión alcista moderada

**Conclusión:** bullish bounce dentro de un context bajista. Cuidado.

## 🎯 Integración con tu sistema

### Confluencia Neptune + Mean Reversion

**LONG setup con TODAS las confluencias:**

1. ✅ Mean Reversion 4/4 filtros (Donchian + BB + RSI + vela verde)
2. ✅ **Precio > Neptune Line** (sesgo bullish)
3. ✅ **Hyper Wave < 36** (oversold)
4. ✅ **Hyper Wave cruza arriba MA** (momentum giro bullish)
5. ✅ **Directional Pressure > 0** (flujo comprador)
6. ✅ **Neptune SMC muestra Bullish OB o FVG no rellenado**
7. ✅ **Neptune Signals "Shape" != 0** (señal de entrada activa)

→ Setup **ÉPICO** — 7/7 confluencias

**SHORT setup inverso**

### Usar Neptune para validar señales de la comunidad

Cuando alguien del grupo comparte una señal (ej: Sabueso dice "Short XLM 0.1822"):

1. Cambia chart a XLMUSDT.P
2. Verifica que Neptune indicators estén cargados
3. Lee outputs:
   - Hyper Wave: ¿overbought?
   - Neptune Line: precio arriba o abajo?
   - SMC: ¿Bearish OB cerca?
   - Signals: ¿Shape activo?
4. Si 4+ outputs Neptune alinean con la señal → **validar con mayor confianza**
5. Si Neptune contradice → **skip o reduce size**

## 📝 Cómo activar Neptune en un chart nuevo

**Problema:** TV Basic limita a 2 indicadores. Si quieres usar Neptune + otros, necesitas plan Premium.

**Workaround si estás en Basic:**
1. Prioriza Neptune Signals + Neptune Oscillator (los 2 más útiles)
2. Para otros análisis, quita temporalmente y añade

**Con plan Premium (25 indicadores max):**
- Carga todos los 6 Neptune + tus propios indicadores
- Sistema tiene visibilidad completa

**Comando para añadir:**
```
chart_manage_indicator action=add indicator="Neptune® - Signals™"
```

⚠️ Nota: los indicadores privados requieren que estés **suscrito/invitado** al script. Si no tienes acceso, `chart_manage_indicator` falla.

## 🔄 Flujo recomendado para validar señal Sabueso

```
Tú: "Sabueso dice short XLM 0.1822, ¿qué dice Neptune?"

Agente signal-validator:
1. chart_set_symbol → XLMUSDT.P
2. chart_get_state → verifica Neptune cargados
3. data_get_study_values → lee todo Neptune
4. data_get_pine_boxes study_filter="Neptune - SMC" → Order Blocks
5. data_get_pine_labels study_filter="Neptune" → eventos estructurales

Reporta:
- "Neptune Line XLM: 0.1805 (precio 0.1822 arriba → bullish sesgo)"
- "Hyper Wave: 71 (overbought zone, favor short)"
- "Neptune SMC: Bearish OB en 0.1825-0.1835 ✅ favor short"
- "Directional Pressure: -3.2 → presión vendedora activa ✅"

Score Neptune: 3/4 favor short
+ Score del sistema propio
= Score final
```

## 🧠 Filosofía

Los Neptune son **excelentes** pero no infalibles. Úsalos como **confirmación**, no como única señal.

**Regla de oro:** si Neptune + tu sistema + señal del Sabueso dicen LO MISMO, probabilidad alta. Si hay disagreement, duda.

**Red flag:** si la comunidad está emocionada con una señal pero Neptune + tu sistema dicen NO-GO → **skip**, sin importar el FOMO.

## 📚 Para la comunidad punkchainer's

Cuando opera con ellos:
1. **Siempre valida con tu sistema** primero
2. **Documenta cada señal** en `external_signals_tracker.md`
3. **Después de 20+ señales**, revisa WR del Sabueso, Maestro Oso, etc.
4. **Decide** a quién seguir basado en DATA, no en hype

## Uso en el sistema

Cuando se te pida "Neptune", "sabueso dice X", "la comunidad dice Y":
1. Lee outputs de Neptune actuales (`data_get_study_values` + pine reads)
2. Integra con Mean Reversion + ICT + otros
3. Scoring cruzado: ¿Neptune apoya o contradice?
4. Reporta con transparencia qué dice cada componente
5. Decisión final basada en mayoría

## ⚠️ Limitaciones honestas

1. **Si el usuario no tiene acceso a Neptune** → skip este skill, usar solo tu sistema propio
2. **Neptune es privado** → no puedo replicar su lógica, solo leer output
3. **El output puede cambiar** si Bangchan actualiza el indicator
4. **No reemplaza** tu análisis técnico propio
