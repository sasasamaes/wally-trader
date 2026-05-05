---
name: neptune-community-config
description: Use cuando necesites las configuraciones EXACTAS recomendadas por la comunidad punkchainer's de los 4 indicadores Neptune principales (Oscillator, Signals, ICT/Smart Money Concepts, SMC). Configs validadas por la comunidad para timeframes 15M-4H. Crítico para profile bitunix (copy-validated trading) — replica el setup de las señales que recibes para entender el contexto de cada call.
---

# Neptune Community Config — Setup oficial punkchainer's

> Configuraciones EXACTAS que la comunidad punkchainer's en Discord recomienda. Útil cuando recibes una señal y quieres tener TU TradingView con los mismos indicadores configurados igual para validar el setup en tu propio chart.

## Indicadores Neptune (Bangchan10, requieren invitación)

**Lista verificada 2026-05-04 (screenshot del usuario):** 7 indicadores disponibles, todos by Bangchan10. Nombres EXACTOS para usar con `chart_manage_indicator action=add indicator="<nombre exacto>"`:

| Indicador (nombre EXACTO en TV) | Boosts | Uso |
|---|---|---|
| `Neptune® - Money Flow Profile™` | 29 | Volume profile con money flow direction |
| `Neptune® - Oscillator™` | 72 | Oscilador principal con WaveTrend, divergencias, momentum |
| `Neptune® - Signals™` | 50 | Generador de señales (versión 2.0 — integra oscilador interno) |
| `Neptune® - Smart Money Concepts™` | 74 | **SMC + ICT en uno** — Áreas de Interés, OB, FVG, liquidity, displacement, market structure |
| `Pivots and Phases™` | 19 | Pivots clásicos + fases de mercado (1ra versión) |
| `Pivots and Phases™` | 17 | Pivots y fases (2da versión, alternativa) |
| `SMC Oscillator™` | 27 | SMC en formato oscilador |

**⚠️ Importante — SMC = ICT (mismo indicador):** Lo que en algunas docs aparece como "Neptune® - ICT Concepts™" **es el mismo `Neptune® - Smart Money Concepts™`**. Bangchan10 unificó ambos en un solo script porque comparten 90% de conceptos (OB, FVG, liquidity, CHoCH/BOS). Usar siempre el nombre EXACTO `Neptune® - Smart Money Concepts™` para `chart_manage_indicator`. Las features ICT-specific (displacement, structure filter, etc) están dentro del panel del SMC.

## 1. Neptune Smart Money Concepts (ex-ICT) — Configuración 15M a 4H (la canónica)

> **Nota terminológica:** los toggles internos del indicador siguen llamándose "ICT Concepts" porque Bangchan10 mantiene la nomenclatura legacy en el panel. El indicador en sí se llama `Neptune® - Smart Money Concepts™` (nombre EXACTO para `chart_manage_indicator`). Tanto las funciones ICT como SMC están dentro de este único indicador.

```yaml
# OSCILLATOR / TRADING TOGGLES
ICT Concepts Signals: ON   # toggle interno conserva nombre "ICT" pero está en SMC
Show Swings Areas: ON (color claro)
Trading Overlay: OFF
Trading Dashboard: OFF (Top Right si lo activas)

# ICT CONCEPTS COLORS
ICT Signals: green/red
Dashboard: transparent / white
ICT Overlay: gray / green / red

# ORDER BLOCKS
Order Blocks: ON
Visualization: Chart
Mitigation Method: Close
Hide Overlap: ON
Max OBs: 5
Length: 22
Extend: OFF
Text Size: Small
Volume: ON
Percentage: ON
Mid Line: OFF
Line Style: Solid
MTF OB: OFF (4 hours si lo necesitas)

# MARKET STRUCTURE
Market Structure: ON (External)
Equal Highs & Lows: ON (0.5)
Swing Points: OFF (25, Small)

# DISPLACEMENT
Show Displacement Candles: ON (pink/blue)
Type: Candle
Strength: 2
Structure Filter: ON

# FAIR VALUE GAPS
Fair Value Gaps (FVG): ON
Timeframe: Chart
Opacity %: 12
Max Width: 2
Filter FVG: ON
Mitigation: Close
Fill: ON
Shade: OFF
Max FVG: 3
Length: 20
Extend: OFF
Mid Line: ON
Style: Solid
Line Width: 1
Extend (Current): OFF

# LIQUIDITY LINE
Liquidity Line: ON (yellow)
Line Style: Solid
Width: 2
Line Length: 20
Text Size: Small
Show Text: ON

# TRENDLINES
Trendlines: OFF (si lo activas: Solid, Width 1, Lookback 25)
Show Broken: OFF
Show Signals: OFF
Max Broken: 1
Mitigation: Close
Style (Broken): Dashed

# KEY LEVELS
Monday: OFF
Style: Dotted
Shorten: ON
Text Size: Small
```

## 2. Neptune Signals — Sensibilidad MANUAL crítica

⚠️ **REGLA #1:** NO usar sensibilidad "Automatic". La comunidad confirma que **"no es la misma efectividad"** con auto.

```yaml
# ADVANCED SETTINGS (importantes)
ML Oscillator Classifier: 13
Neptune Pilot Sensitivity: Manual  # ⚠️ NUNCA Automatic
Smart Dashboard: OFF (default 2)
Sessions: Auto
Optimal Sensitivity: ON

# TAKE PROFIT / STOP LOSSES
TP/SL Levels: Neptune
Distance: 2.5
TP1: blue
TP2: blue
SL1: red
SL2: red

# Neptune Line: OFF (1, blue) — solo si quieres la línea visible

# DASHBOARD AND INDICATOR AI FUNCTIONS
Smart Dashboard: OFF
Sessions: Auto
Optimal Sensitivity: ON
```

## 3. Neptune Oscillator — Setup unificado todas las temporalidades

> "Configuracion ideal en todas las temporalidades. Configuracion para trading de todos los días."
> "Configuración SIN señales si estás usando Neptune Signals (Recomendado)"

```yaml
# OSCILLATOR SIGNALS
Neptune Bounce: ON  # ⭐ siempre
Neptune Signals: OFF  # OFF si usas Neptune Signals separado (recomendado)
Exit Signals: OFF
Momentum Signal: ON
Confluences Lines: ON  # ⭐ siempre
(Square): ON  # confluencias en cuadros

# CHART SIGNALS (para chart visible)
Chart Signals: ON
Bearish Label Color: red
Bullish Label Color: green
Visible Signals (1, 2, 3): 3

# OSCILLATOR FEATURES
Hyper Wave Pressure: ON  # ⭐
Fibonacci Lines: ON  # ⭐
SMA Line: OFF
RVOL Bars: ON
Neptune Pivots: ON
Oscillator Divergences: ON
Divergences (Chart): 4  # ON con valor 4
Volume Analysis: ON  # ⭐ con alta volatilidad da señal de momentum extremo
Ticker ID: OFF
Neptune Line (Chart): OFF

# OSCILLATOR SETTINGS
Hyper Wave: 6 (yellow / white)
EOT 1 (Main Oscillator) Trigger Length: 4
Fast Oscillator Kernel Settings: 0.8 / 0.3 (default)

# SMART MONEY MODE (cuando quieras lectura SMC en el oscilador)
Top/Bottom: ON
WT Cross: ON  # avisos de cruces en zonas importantes
Momentum Signal: ON

# SMART MONEY FLOW
Money Flow: Smart Money  # NO Neptune (cambio crítico vs default)
Length: default

# NEPTUNE TARGETS (chart signals)
Signals: ON (3 visible) — green/red
Targets: ON (2.5) — blue/red

# WT BULL / WT BEAR
WT Bull: green
WT Bear: red

# ALERTS SCRIPTING (modo BOT)
Enable Dynamic Bot Alerts (alert() function): ON  # ⭐ activa para webhooks
Bullish Alert Message: usar JSON con placeholders (ver skill neptune-alert-placeholders)
Bearish Alert Message: usar JSON con placeholders
```

### 3.1. Anomalies Signals (toggle especial Oscillator)

> "Los puntos celestes pequeños del oscilador detectan divergencias entre precio y volumen/momentum vía presión del volumen (LSMA cruzando línea 0). Excelentes avisos de toma de liquidez o CHoCH inminente formándose."

**Qué son:** Anomalies Signals es un toggle dentro del Neptune Oscillator que dispara puntos celestes pequeños cuando el LSMA (Least Squares Moving Average) cruza la línea 0 del oscilador. Esto identifica momentos donde el flujo de volumen y la regresión lineal **NO coinciden** con el movimiento típico del precio → divergencia oculta.

**Por qué importa:**
- Detecta acumulación/distribución silenciosa antes del move
- Suele anticipar **CHoCH inminente** o **toma de liquidez** formándose
- En setups SMC: confluencia con OB/FVG + Anomaly Signal = entry de alta convicción

**Cómo activar:**
```yaml
# En Neptune Oscillator settings
Anomalies Signals: ON  # default OFF — activar para divergencias volumétricas
Color: cyan/celeste (default)
Size: small
```

**Cómo leerlas en flow operativo:**
1. Punto celeste aparece en oscilador → el volumen NO valida el movimiento del precio
2. Si en el chart 15m hay barrida de liquidez reciente en la misma dirección → **probable reversión**
3. Esperar confirmación (CHoCH en SMC) antes de entrar — el punto solo es "alerta", no señal de entrada

**Combinación recomendada:** Anomalies Signals + 4-pilar checklist Neptune SMC (ver skill `punkchainer-playbook`) = confluencia máxima.

## 4. Neptune SMC — Smart Money Concepts

```yaml
# MARKET STRUCTURE (config inicial canónica)
Window: ON (500)
Swing: ON (Tiny, 25, green/red)
HH/LL: ON (25, Medium, green/red)  # ⚠️ NOTA: en setup ZigZag se desactiva
ZigZag: ON (2 width, 23 length)  # cuando quieras ZigZag, desactiva HH/LL
Algorithmic Logic: Adjustable (5)
Build Sweep: ON (selector "x")
Strong/Weak HL: OFF
Bubbles: OFF
Color Candles: OFF
Modern UI: ON  # ⭐ nuevo diseño 2026

# VOLUMETRIC ORDER BLOCKS
Show Last: 5
Show Buy/Sell Activity: ON (green/red)
Show Breakers: OFF (3, transparent)

# OPENING LEVELS
1W Opening price: OFF (blue/blue)
1Y Opening price: OFF (red/red)

# FAIR VALUE GAP
Mode: Breakers (NO solo FVG — usar mode Breakers)
Mitigation: Close
Threshold: 0
FVG Ext.: 12
Hide Overlap: ON
Show Mid-Line: ON
Extend FVG: OFF
Display Raids: OFF

# LIQUIDITY CONCEPTS
Trend Lines: ON (10)  # ⭐ activado
Equal H&L: OFF (Short-Term, green/red)  # se activa según dinámica del día
Liquidity Prints: ON (red/blue)
Buyside & Sellside: ON (Area)  # ⭐ áreas de liquidez
Sweep Area: OFF (10, transparent)

# HIGHS & LOWS MTF
Day: OFF (blue, ─)
Week: OFF
Month: OFF
Quarterly: OFF

# PREMIUM / DISCOUNT
Premium / Equilibrium / Discount: según necesidad de la sesión
```

### Variantes Neptune SMC según situación:

**Setup canónico día normal:** HH/LL ON, ZigZag OFF
**Setup ZigZag para ver swings claramente:** HH/LL OFF, ZigZag ON (2/23)
**Activar Volumetric Order Blocks Breakers cuando:** quieres ver dónde un OB roto puede actuar como reacción inversa

## Reglas críticas de uso

1. **Neptune Signals: SIEMPRE Sensitivity Manual.** Auto degrada efectividad.
2. **Si tienes Neptune Signals activo** → en Neptune Oscillator desactiva "Neptune Signals" toggle (evita duplicación).
3. **Confluences Lines + Square ON** en Oscillator es el setup de la comunidad para detectar confluencias visuales.
4. **Modern UI ON** en SMC para el diseño 2026.
5. **Money Flow: Smart Money** (NO "Neptune") en oscillator es el cambio clave para lectura institucional.
6. **Volume Analysis ON** en Oscillator detecta señales de momentum extremo en alta volatilidad.

## Cómo replicar el setup completo

```
Paso 1: TradingView → cargar BTCUSDT.P (o el asset de la señal)
Paso 2: Indicators → Requiere invitación → buscar "Neptune"
        ⚠️ Necesitas estar en la comunidad punkchainer's o tener invitación de Bangchan10
Paso 3: Cargar (en orden):
        - Neptune ICT (timeframe activo del trade)
        - Neptune Signals
        - Neptune Oscillator
        - Neptune SMC
Paso 4: Para cada uno: Settings → seguir las configs arriba
Paso 5: Save layout para reutilizar
```

## Limitación: TradingView Plan Basic (2 indicadores max)

Tu plan Basic permite máximo 2 indicadores por chart. Con la comunidad usando 4 Neptune simultáneos, **solo puedes activar 2 a la vez**. Recomendación:

| Combo | Cuándo usar |
|---|---|
| **Neptune Signals + Neptune SMC** ⭐ DEFAULT 2026 (FIJO TV Basic) | Day-to-day. Signals 2.0 ya integra oscilador. SMC aporta Áreas de Interés + FVG + OB |
| Neptune Signals + Neptune Oscillator | Setup viejo (válido si querés ver el oscilador en pane separado vs integrado en Signals) |
| Neptune SMC + Neptune Oscillator | Análisis SMC con confirmación de momentum independiente |
| Neptune SMC + SMC Oscillator | Para análisis SMC profundo con su oscilador específico |
| Neptune Money Flow + Neptune Signals | Para validar direccion institucional del flow vs señales |

Tu setup actual default (`tradingview_setup.md`): **Neptune Signals + Neptune SMC** (post-rediseño 2026-05-04).

### ✅ TV Premium activado — combo de 5 indicadores

**Confirmado por user 2026-05-04:** Premium pagado, 5 slots disponibles. Combo recomendado:

| Slot | Indicador (nombre EXACTO) | Función |
|---|---|---|
| 1 | `Neptune® - Signals™` | Signal triggers, Range Filter, Reversal Bands, Smooth Trail, Trade Builder, Trendlines auto |
| 2 | `Neptune® - Smart Money Concepts™` | Áreas de Interés, FVG, OB, CHoCH/BOS, Liquidity, ICT (mismo indicador) |
| 3 | `Neptune® - Oscillator™` | Hyper Wave numérico, Money Flow direction, divergencias, Anomalies Top, Directional Pressure |
| 4 | `Pivots and Phases™` | Fases del mercado (alcista/bajista/correctiva), pivots azules de cambio de fase con liquidez |
| 5 | `Neptune® - Money Flow Profile™` | POC, VAH, VAL — volume profile institucional para validar zonas de absorción |

**⚠️ NO disponible (no cargar):** `SMC Oscillator™` — redundante con Neptune Oscillator. Sólo cargar si futuro test demuestra valor adicional.

**Setup pasos para el user (1 vez):**
1. Abrir TradingView → ícono `fx` → "Indicadores, métricas y estrategias"
2. Click "**Requiere invitación**" (panel izquierdo)
3. Cargar uno por uno los 5 indicadores listados arriba
4. **Save Layout** (icono guardar arriba a la derecha) con nombre "Bitunix Punk Setup"
5. Verificar configuración de cada uno según secciones específicas de este SKILL

**Validación con MCP:**
```bash
python3 -c "
# Verifica que TV tiene los 5 cargados
import subprocess, json
# Llamar mcp__tradingview__chart_get_state vía claude
"
```

O simplemente: ejecutar `mcp__tradingview__chart_get_state` y confirmar que `studies` contiene los 5 nombres exactos arriba (+ Volume built-in opcional).

### Limitación pasada (TV Basic, ya superada)

> **Histórico:** entre el momento de creación del profile bitunix y el 2026-05-04 ~22:00 CR, el user usó TV Basic con solo 2 indicadores cargables (combo Signals + SMC). El componente Oscilador del scoring `/punk-hunt` operaba con proxies (Shapes + Neptune Line distance + Trade Builder labels). Tras upgrade Premium 2026-05-04, scoring Oscilador restaurado a lógica completa con Hyper Wave numérico.

## Referencias

- Manual completo Neptune SMC: `Neptune_Manual_Usuario_Completo.pdf` (35 pages, lectura obligatoria si vas a usar Neptune SMC en serio)
- Placeholders para alertas/webhooks: ver skill `neptune-alert-placeholders`
- Discord punkchainer's: canal `#neptune-indicators`, `#chat-de-bots`, `#material-de-estudio`

### Videos oficiales de referencia (Elite Crypto Academy / Ponk — mismo ecosistema punkchainer's)

Estos 4 videos son la fuente autoritativa de la metodología actual. Cualquier ambigüedad en las skills/agentes se resuelve consultándolos:

| Video | URL | Duración | Tema |
|---|---|---|---|
| **1. SMC + Fibonacci + Fases del MIT** | https://www.youtube.com/watch?v=b8XChVarsto | ~40 min | Análisis top-down 1W→1D→4H→15m. Fibo 38.2/50/61.8 como núcleo. Targets matemáticos del MIT (100/161.8/200/300% extensions) |
| **2. Estrategia $3K/mes con $300 (15m)** | https://www.youtube.com/watch?v=lO9GqGxtGpY | ~25 min | Scalping con 4 confluencias en orden: Oscilador → Zona extrema → Reversal Band → IA. SL 0.30% + target próxima banda. |
| **3. Áreas de Interés + Gestión de Riesgo** | https://www.youtube.com/watch?v=C2Z0Eyatk-M | ~153 min | Áreas de Interés (auto-FVG+S/R+liquidez), regla de FVG (cierre vela en contra), regla anti-interés-compuesto, división del capital, bot Ramón (5%/mes flotante) |
| **4. Neptune Signals 2.0 tutorial** | https://www.youtube.com/watch?v=xOmStJE3iRw | ~25 min | Tutorial oficial del nuevo Signals 2.0: Range Filter, 2 tipos señales (triángulos/+/-), X de TP, Smooth Trail + Reversal Bands combo, Trade Builder, Trendlines auto |

**Comando para extraer transcripts** (para agentes que necesiten consultarlos en el futuro):
```bash
.claude/scripts/.venv/bin/pip install youtube-transcript-api
python3 -c "
from youtube_transcript_api import YouTubeTranscriptApi
api = YouTubeTranscriptApi()
for vid in ['b8XChVarsto', 'lO9GqGxtGpY', 'C2Z0Eyatk-M', 'xOmStJE3iRw']:
    t = api.fetch(vid, languages=['es','es-419','en'])
    # imprime transcript con timestamps
"
```

**Reglas que vienen explícitamente de los videos** (no inventarlas, citarlas):

1. **"El oscilador es lo más importante"** (video 2) → razón del peso 40pts en `/punk-hunt`
2. **"El precio SIEMPRE busca la banda"** (video 2) → razón del peso 25pts a Reversal Band
3. **"NO interés compuesto en trading"** (video 3) → razón de la regla "ganancias se retiran a bolsillo"
4. **"FVG válido hasta cierre de vela en contra (no mecha)"** (video 3) → criterio para validar FVG
5. **"Range Filter NUNCA deshabilitar"** (video 4) → siempre activo en Signals 2.0
6. **"Smooth Trail + Reversal Bands combo es brutal"** (video 4) → estrategia favorita Ponk
7. **Top-down 1W → 1D → 4H → 15m** (video 1) → orden obligatorio de análisis
8. **Targets de Fibonacci 100/161.8/200/300%** (video 1) → cálculo de TPs largos
9. **"50% capital libre, 50% trading dividido en 2-3 trades"** (video 3) → gestión de riesgo
10. **Bot Ramón hace ~5% mensual del flotante** (video 3) → benchmark realista (no prometer más)

---

## 🆕 Neptune Signals 2.0 (versión nueva — videos Ponk 2026)

> **Updated 2026-05-04** desde tutorial oficial de Ponk (Elite Crypto / mismo ecosistema). Esta versión sustituye al antiguo Signals + Oscillator separados — todo integrado en un solo indicador.

### Filosofía del rediseño

- Las señales ahora están **basadas 100% en el oscilador** (mismo algoritmo que las del oscilador antiguo, ahora dentro de Signals)
- Por eso podés usar **solo 2 indicadores en TV Basic**: Signals 2.0 + Smart Money Concepts 2.0
- Se elimina la necesidad de cargar el Neptune Oscillator en su propio slot

### Configuración Neptune Signals 2.0

```yaml
# SIGNALS — el algoritmo nuevo
Signals: ON  # ⭐ señales triángulos (movimientos largos)
Range Filter: ON  # ⭐⭐ NUNCA deshabilitar — detecta lateral y muestra "RANGING" en pantalla

# 2 TIPOS DE SEÑALES
Triangle signals (long/short normal): ON  # movimientos largos
+/- signals (long+/short+): ON  # movimientos cortos (scalping)

# X SIGNALS (reversal / take profit)
X Signals: ON  # ⭐ X de TP + reversal — cerrar trade o entrar contrario
Bullish/Bearish color: green/red

# CANDLE COLORS
Color Candles: ON  # verde positivo, rojo negativo, morado = precio bajo señal long

# OVERLAYS
Smooth Trail: ON  # ⭐ S/R dinámica — combo poderoso con Reversal Bands
Cumo (Ichimoku-like): OPTIONAL  # útil para tendencia macro
Premium/Equilibrium/Discount Zones: OPTIONAL  # útil para spot
Reversal Bands: ON  # ⭐⭐⭐ HERRAMIENTA FAVORITA — el precio SIEMPRE busca la banda
  - Banda externa: 1.8 default (recomendado)
  - Para scalping cerrar a 1.0
TP Levels: ON  # SL1, TP1, TP2, TP3 niveles intradía
Trade Builder: ON  # dibuja TP/SL automáticamente al 2%
Trendlines: ON  # ⭐ líneas de tendencia automáticas — break = signal
Neptune Line (ex MA Line): ON  # ⭐ la clásica línea de Neptune
Liquidity (Swing Failure Pattern): ON  # SFP automático
Zigzag (fases del mercado): ON  # phase tracking del MIT strategy
Fibonacci Levels: ON  # 38.2 / 50 / 61.8
Fibonacci Projections: ON  # 100% / 161.8% / 200% / 300% (extensions)
```

### Setup recomendado por Ponk (combo de su Smooth Trail + Reversal Bands)

> **Mi técnica favorita:** "cuando vengo con una señal de long y rompe el Smooth Trail, es entry confirmado. Hasta que no toque la Reversal Band, no cierro el trade." — Ponk

**Workflow:**
1. Aparece señal LONG (triángulo verde) en parte baja del oscilador
2. Esperar a que rompa el **Smooth Trail** (S/R dinámica) hacia arriba
3. Entry confirmado en breakout del Smooth Trail
4. Stop loss debajo del Smooth Trail (1-2% precio)
5. Target: **Reversal Band superior** (lo que sea que esté en 1.8 default)
6. NO cerrar prematuramente — el precio "siempre busca la banda"
7. Si aparece **X de TP** antes de la banda → cerrar parcial (40% según Trade Builder)

### Configuración Smart Money Concepts 2.0 (combo recomendado con Signals 2.0)

```yaml
# AREAS DE INTERES (NUEVA — feature destacada)
Áreas de Interés: ON  # ⭐⭐ auto-calculated zonas combinando 9+ factores
  - LONG: meter en áreas BAJAS
  - SHORT: meter en áreas ALTAS
  - Se mueven cuando el precio rompe (refresh automático)

# FVG (Fair Value Gaps)
FVG: ON  # ⭐ regla crítica
  - Bullish FVG: válido hasta que vela CIERRE por debajo (no cuenta mecha)
  - Bearish FVG: válido hasta que vela CIERRE por encima

# ORDER BLOCKS (subset)
Order Blocks: ON
Max OBs visibles: 3 alcistas + 3 bajistas (más es ruido)
Mostrar % liquidez: ON  # útil para validar fuerza del OB

# LIQUIDITY
Liquidity Prints: ON  # importante para SSL/BSL

# UI
Modern UI: ON
```

### Alertas disponibles en Neptune Signals 2.0

Toda la versión 2.0 tiene **alertas exhaustivas** (premium TV recomendado para más slots):

- `Long Signal` / `Short Signal` (triángulos largos)
- `Long+ Signal` / `Short+ Signal` (señales cortas)
- `Exit Bullish` / `Exit Bearish` (X de TP)
- `Reversal Band Upper Touch` / `Lower Touch`
- `Premium Zone Entry` / `Equilibrium` / `Discount`
- `Smooth Trail Cross Bullish/Bearish`
- `Cumo Cross Bullish/Bearish` + `Cumo Retest`
- `Trendline Break Bullish/Bearish`
- `Neptune Line Cross Bullish/Bearish`
- `Bullish/Bearish SFP`

Ver skill `neptune-alert-placeholders` para JSON templates de webhooks.

### Range Filter — gate crítico para `/punk-hunt`

**Comportamiento:** cuando el indicador detecta mercado lateral, muestra **"RANGING"** en pantalla. Esto es importante porque:
- Las señales sí aparecen en rango pero los movimientos serán cortos
- R:R limitado — no esperar TPs lejanos
- En `/punk-hunt`: si Range Filter activo → score multiplicado × 0.7 (penalización 30%)

### Cambios vs versión vieja

| Concepto | Versión vieja (1.x) | Versión 2.0 |
|---|---|---|
| Indicadores en TV Basic (2 slots) | Signals + Oscillator | Signals 2.0 + SMC 2.0 |
| Algoritmo señales | Neptune Pilot + ML | 100% basado en oscilador |
| Range filter | NO existía | ⭐⭐ NUEVA — crítico |
| 2 tipos señales | NO existía | Triángulos largos + +/- cortos |
| Reversal Bands | Solo en oscilador | Como overlay en chart principal |
| Trade Builder | Manual con herramienta TV | Auto al 2% |
| Trendlines | Manual | Automáticas con break alerts |
| IA detrás | Parcial | Construida 100% sobre IA |
