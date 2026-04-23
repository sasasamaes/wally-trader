# Wally Trader — Claude Instructions

> Sistema de trading personal con capital real + challenge FTMO + bonus Fotmarkets.
> Bautizado en honor a Wally 🌭, perro salchicha y CEO mascota del proyecto.

Guía operativa para sesiones de trading con Claude. Lee esto al inicio de cada sesión.

## Perfil del trader

- **Exchange:** BingX (BTCUSDT.P perpetual)
- **Zona horaria:** México (UTC-6)
- **Capital activo:** $10 (objetivo inicial: escalar a $100)
- **TradingView:** Plan Basic (máx 2 indicadores — Neptune Signals + Neptune Oscillator ocupan ambos slots)
- **Ventana operativa:** MX 06:00 – 23:59 (análisis desde 06:00, force exit 23:59 MX "antes de dormir")
  - Cripto opera 24/7, pero el trader NO duerme con posición abierta
  - Cierre anticipado permitido si: ya acumuló ganancia buena del día **O** tiene un pendiente personal
- **Estilo:** scalping intraday, no day-trading de múltiples días

## Profile System (Triple)

El sistema soporta **3 profiles aislados**. Se switchean al inicio del día con `/profile`.

### Profile `retail` (default)
- Capital $13.63 real en BingX BTCUSDT.P
- Estrategia Mean Reversion 15m (este documento)
- Ventana MX 06:00–23:59
- Ver `.claude/profiles/retail/config.md`

### Profile `ftmo`
- Capital $10,000 virtual (FTMO 1-Step challenge demo)
- Multi-asset: BTC + ETH + EURUSD + GBPUSD + NAS100 + SPX500
- Estrategia FTMO-Conservative (SL 0.4%, risk 0.5%, target 1.5%/día)
- Reglas FTMO duras: 3% daily (BLOCK), 10% trailing (WARN), Best Day 50% (INFO)
- Ventana MX 06:00–16:00 (no overnight)
- Ver `.claude/profiles/ftmo/config.md` y `rules.md`

### Profile `fotmarkets` (bonus $30)
- **Capital $30 USD** — bonus no-deposit de Fotmarkets (Mauritius, sin regulación tier-1)
- **MT5 Standard 1:500** (forzado por bonus T&C)
- Multi-asset (8 assets, desbloqueados por fase): EURUSD/GBPUSD → USDJPY/XAUUSD/NAS100 → SPX500/BTCUSD/ETHUSD
- Estrategia **Fotmarkets-Micro** (scalping reversal post-pullback 5m)
- Escalation risk: **10% → 5% → 2%** según fase ($30→$100→$300+)
- Ventana **MX 07:00–11:00** (London/NY overlap)
- Ejecución **manual en MT5** (sin EA bridge)
- Ver `.claude/profiles/fotmarkets/config.md`, `strategy.md`, `rules.md`

**⚠️ Filosofía Fotmarkets:** capital es bonus ("casa de juego"), NO depositar dinero propio,
no reemplaza el profile FTMO/retail real.

### Reglas de operación multi-profile
1. **No operar múltiples profiles el mismo día.** Switch al inicio de sesión.
2. **Nunca cruzar memorias** — trade FTMO no se escribe al log retail/fotmarkets y viceversa.
3. **Guardian** (`.claude/scripts/guardian.py`) obligatorio en FTMO antes de cada entry.
4. **Lite Guardian** (`.claude/scripts/fotmarkets_guard.sh`) obligatorio en fotmarkets antes de cada entry.
5. **Statusline** muestra `[PROFILE]` en todo momento para prevenir confusión.

### Comandos específicos multi-profile
- `/profile` — ver/cambiar profile activo
- `/equity <valor>` — actualizar equity FTMO manualmente
- `/challenge` — dashboard progreso FTMO (solo ftmo)
- `/status` — estado adaptado al profile activo
- Los demás (`/morning`, `/validate`, `/risk`, `/journal`) son profile-aware
- `/profile fotmarkets` — switch al 3er profile
- `/risk` en fotmarkets → calcula sizing phase-aware (10%/5%/2%)

## Estrategia oficial — DEPENDE DEL RÉGIMEN DE MERCADO

**Principio crítico:** NO hay estrategia universal. Cada día al iniciar sesión (MX 05:30), detectar el régimen ANTES de elegir estrategia.

### Detección de régimen (primer paso obligatorio)

| Régimen | Señales | Estrategia |
|---|---|---|
| **RANGE** | BTC dentro de caja <5% por 3+ días, rebota en niveles | Mean Reversion |
| **TRENDING** | Higher highs + higher lows diarios, rompe rangos con vol 2x | Donchian Breakout |
| **VOLATILE** | ATR 2x promedio, mechas grandes en ambas direcciones | NO operar |

### Estrategia PRIMARIA: Mean Reversion (régimen actual — range 73.5k-78.3k)

Validada con **100% WR** y **+15.1%** en backtest 3 días frente a 144 configs.

| Parámetro | Valor |
|---|---|
| Timeframe | **15m** |
| Donchian | **15 velas** |
| Edge de entrada | **±0.1%** del extremo Donchian |
| RSI(14) | OB **65**, OS **35** |
| Bollinger Bands | **(20, 2)** confirmación obligatoria |
| ATR length | **14** |
| SL | **1.5 × ATR** (adaptativo) |
| TP1 (40%) | **2.5 × SL** → SL a BE |
| TP2 (40%) | **4.0 × SL** |
| TP3 (20%) | **6.0 × SL** |
| Leverage | **10x** |
| Ventana | **MX 06:00 – 23:59** |
| Force exit | **23:59 MX** (regla "no dormir con trade abierto"); cierre anticipado permitido si ya hay ganancia del día o pendiente personal |
| Max 5 trades/día | 2 SLs → stop |

**Entradas (4 filtros obligatorios, todos simultáneos):**

LONG:
1. Precio toca o cruza **Donchian Low(15)** (dentro 0.1%)
2. **RSI < 35**
3. **Low de vela toca BB inferior**
4. Vela cierra **verde**

SHORT:
1. Precio toca o cruza **Donchian High(15)** (dentro 0.1%)
2. **RSI > 65**
3. **High de vela toca BB superior**
4. Vela cierra **roja**

### Estrategia SECUNDARIA: Donchian Breakout (si BTC rompe el range)

Usar cuando close 4H cae fuera de 73,500-78,300 con volumen >2x promedio.

Config: Donchian(20), buffer 30 pts, vol >300 BTC, SL 0.5%, TP 0.75/1.25/2.0%. Ver backtest_findings.md para detalles históricos.

### Reglas de invalidación comunes

- 2 SLs consecutivos → **parar ese día**
- En días con noticias macro (CPI, Fed, etc.) → **no operar**
- ATR explotado a 2x promedio → **no operar** (régimen volatile)

## Contexto de mercado (usar al inicio de sesión)

Antes de operar, verificar:

1. **Fear & Greed Index** (api.alternative.me/fng) — extremos dan pistas contrarian
2. **Funding rate** (OKX api `public/funding-rate?instId=BTC-USDT-SWAP`) — negativo sostenido = setup de short squeeze
3. **Retail sentiment** (CoinGecko community votes) — cuando retail está 80%+ bullish, sesgo contrarian bearish
4. **Liquidaciones / OI / L-S ratio** (Binance Futures Data API, sin key) — ver `liquidations_data.md`
   - OI hourly: `https://fapi.binance.com/futures/data/openInterestHist?symbol=BTCUSDT&period=1h&limit=24`
   - L/S retail: `https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=1h&limit=24`
   - L/S smart money: `https://fapi.binance.com/futures/data/topLongShortAccountRatio?symbol=BTCUSDT&period=1h&limit=24`
   - Buscar drops OI >$100M en 1h (liq event), L/S <0.8 (short squeeze setup) o >1.5 (long squeeze)
5. **Volumen 5m/15m vs promedio** — spike sin seguimiento = rejection (trampa). TV chart tiene Volume cargado.
6. **Sesión horaria óptima:** MX 06:00–10:00 (London/NY overlap, mayor volatilidad 0.85%)

## Hallazgos clave del backtesting

- **$10 → $100 en un solo trade es matemáticamente imposible a 20x** (requiere +45% move sin liquidación)
- **20x con SL 1% en 4H = -48% en 50 días** (winrate 10%). NO usar esa config.
- **10x ST(2,7) en 4H** ganó +87% en 50 días pero con DD 51% (casi liquidación)
- **Pasado NO equivale a futuro** — data disponible en TV MCP está capada a 300 barras por timeframe (3-50 días según TF)
- Ruta realista $10→$100: **6-12 meses compoundeando** al 2-5% neto diario

## Niveles técnicos vigentes (al 2026-04-20)

- **Neptune Line 1D:** 67,836 (soporte fuerte de trend diario)
- **Neptune Line 4H:** 73,380 (soporte trend 4H)
- **Estructura 1D:** uptrend con Hyper Wave en sobrecompra extrema (93)
- **Máximo reciente:** 78,285 (techo a vigilar)

## Archivos de trabajo

En `/tmp/` durante sesiones activas:
- `bars.json` / `bars1h.json` / `bars15m.json` — datasets OHLCV
- `backtest*.py` — scripts de simulación
- `scalp_best.py` — grid search de estrategias scalping

Estos son efímeros y se regeneran por sesión.

## Subsistema ML (`scripts/ml_system/`)

Capa de inteligencia que complementa (NO reemplaza) las reglas mecánicas:

| Componente | Estado | Comando | Agente |
|---|---|---|---|
| **Sentiment NLP** (F&G + Reddit VADER + News RSS + Funding) | Activo | `/sentiment` | `sentiment-analyst` |
| **ML Supervisado** (XGBoost, score TP-first LONG/SHORT) | Activo | `/ml`, `/ml-train` | `ml-analyst` |
| **Deep Learning** (LSTM bidirectional) | Scaffold NO ACTIVO | — | — |

Setup (primera vez): `scripts/ml_system/setup.sh`

Datos históricos Binance se cachean en `scripts/ml_system/data/`. Modelos entrenados en `scripts/ml_system/supervised/model/`.

**Reglas de uso:**
- Ningún score ML convierte un NO-GO técnico en GO
- ML score se usa como **5° filtro** cuando los 4 filtros técnicos ya están alineados
- Si ML score <40 con setup técnico 4/4 → reducir size 50% o esperar siguiente setup
- Sentiment extremo (<20 o >80) = sesgo contrarian para calibrar convicción
- Deep Learning NO se activa hasta cumplir precondiciones en `scripts/ml_system/deep/README.md`

## Convenciones de interacción

- **Idioma:** Español (mixto con términos técnicos de trading en inglés: SL, TP, long, short, leverage, etc.)
- **Directness:** El usuario prefiere respuestas concretas y numeradas, sin rodeos
- **Honesty first:** Cuando algo no funciona en backtest o data es insuficiente, decirlo explícitamente
- **Disclaimers:** Siempre incluir advertencia de riesgo en decisiones con leverage real
- **Dibujos TV:** Cuando haga setups, limpiar dibujos previos antes con menú contextual del trash icon (draw_clear del MCP frecuentemente falla con "getChartApi is not defined")

## Referencias externas útiles

- **TradingView MCP guía:** `tradingview-mcp/CLAUDE.md` (78 tools para leer/controlar TV)
- **Fear & Greed:** https://api.alternative.me/fng/
- **OKX funding:** https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP
- **CoinGecko BTC:** https://api.coingecko.com/api/v3/coins/bitcoin
- **Mempool stats:** https://mempool.space/api/

## Disclaimer

Nada en este proyecto es consejo financiero. Futuros con leverage pueden liquidar capital en minutos con un wick. Usa capital que puedas perder sin afectar tu vida.
