---
name: neptune-community-config
description: Use cuando necesites las configuraciones EXACTAS recomendadas por la comunidad punkchainer's de los 4 indicadores Neptune principales (Oscillator, Signals, ICT/Smart Money Concepts, SMC). Configs validadas por la comunidad para timeframes 15M-4H. Crítico para profile bitunix (copy-validated trading) — replica el setup de las señales que recibes para entender el contexto de cada call.
---

# Neptune Community Config — Setup oficial punkchainer's

> Configuraciones EXACTAS que la comunidad punkchainer's en Discord recomienda. Útil cuando recibes una señal y quieres tener TU TradingView con los mismos indicadores configurados igual para validar el setup en tu propio chart.

## Indicadores Neptune (Bangchan10, requieren invitación)

| Indicador | Boosts | Uso |
|---|---|---|
| Neptune® - Oscillator™ | 70 | Oscilador principal con WaveTrend, divergencias, momentum |
| Neptune® - Signals™ | 49 | Generador de señales con Neptune Pilot + ML classifier |
| Neptune® - Smart Money Concepts™ | 74 | SMC: order blocks, FVG, liquidity, market structure |
| Neptune® - ICT Concepts™ | (en grupo Neptune) | ICT-specific: displacement, structure filter, FVG |
| Neptune® - Money Flow Profile™ | 29 | Volume profile con money flow direction |
| Pivots and Phases™ | 19+17 | Pivots clásicos + fases de mercado |
| SMC Oscillator™ | 27 | SMC en formato oscilador |

## 1. Neptune ICT — Configuración 15M a 4H (la canónica)

```yaml
# OSCILLATOR / TRADING TOGGLES
ICT Concepts Signals: ON
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
| Neptune Signals + Neptune Oscillator | Day-to-day, señales + confluencias en oscilador |
| Neptune SMC + Neptune Oscillator | Análisis SMC con confirmación de momentum |
| Neptune ICT + Neptune Oscillator | Para ICT-specific setups (displacement, FVG) |

Tu setup actual default (`tradingview_setup.md`): Neptune Signals + Neptune Oscillator.

## Referencias

- Manual completo Neptune SMC: `Neptune_Manual_Usuario_Completo.pdf` (35 pages, lectura obligatoria si vas a usar Neptune SMC en serio)
- Placeholders para alertas/webhooks: ver skill `neptune-alert-placeholders`
- Discord punkchainer's: canal `#neptune-indicators`, `#chat-de-bots`, `#material-de-estudio`
