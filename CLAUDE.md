# Wally Trader — Claude Instructions

> Sistema de trading personal con capital real + challenge FTMO + bonus Fotmarkets.
> Bautizado en honor a Wally 🌭, perro salchicha y CEO mascota del proyecto.

Guía operativa para sesiones de trading con Claude. Lee esto al inicio de cada sesión.

## Perfil del trader

- **Ubicación:** Costa Rica (CR, UTC-6 sin DST). Sistema etiqueta horarios como `CR HH:MM`.
- **USD↔CRC:** statusline muestra capital en USD + equivalente en colones (`$18.09 ≈₡8,241`). Tipo de cambio vía `bash .claude/scripts/fx_rate.sh` (cache 1h, API open.er-api.com).
- **Exchanges activos:** Binance Futures (main) + BingX (micro account residual)
- **Zona horaria:** Costa Rica (UTC-6)
- **Capital retail main (Binance):** $18.09 (post-migración 2026-04-23)
- **Capital retail-bingx:** $0.93 (residual, uso pedagógico)
- **TradingView:** Plan Basic (máx 2 indicadores — Neptune Signals + Neptune Oscillator)
- **Ventana operativa retail:** CR 06:00 – 23:59 (análisis desde 06:00, force exit 23:59 CR)
  - Cripto opera 24/7, pero el trader NO duerme con posición abierta
  - Cierre anticipado permitido si: ya acumuló ganancia buena del día **O** tiene un pendiente personal
- **Estilo:** scalping intraday, no day-trading de múltiples días

## Profile System (4 profiles)

El sistema soporta **4 profiles aislados**. Se switchean con `/profile` o con env var `WALLY_PROFILE` (multi-terminal).

### Profile `retail` — Binance main (default)
- Capital **$18.09** real en Binance Futures `BTCUSDT.P`
- Símbolo TV: `BINANCE:BTCUSDT.P`
- Estrategia Mean Reversion 15m
- Ventana CR 06:00–23:59
- Log arranca limpio (Binance fresh start 2026-04-23)
- Ver `.claude/profiles/retail/config.md`

### Profile `retail-bingx` — BingX micro account
- Capital **$0.93** residual en BingX `BTCUSDT.P`
- Símbolo TV: `BINGX:BTCUSDT.P`
- Estrategia Mean Reversion 15m (idéntica a retail/Binance)
- Histórico preservado: 3 wins BingX ($10 → $13.63) en `./memory/trading_log.md`
- Uso pedagógico — position sizing cosmético al 2%
- Ver `.claude/profiles/retail-bingx/config.md`

### Profile `ftmo`
- Capital $10,000 virtual (FTMO 1-Step challenge demo)
- Multi-asset: BTC + ETH + EURUSD + GBPUSD + NAS100 + SPX500
- Estrategia FTMO-Conservative (SL 0.4%, risk 0.5%, target 1.5%/día)
- Reglas FTMO duras: 3% daily (BLOCK), 10% trailing (WARN), Best Day 50% (INFO)
- Ventana CR 06:00–16:00 (no overnight)
- Ver `.claude/profiles/ftmo/config.md` y `rules.md`

### Profile `fotmarkets` (bonus $30)
- **Capital $30 USD** — bonus no-deposit de Fotmarkets (Mauritius, sin regulación tier-1)
- **MT5 Standard 1:500** (forzado por bonus T&C)
- Multi-asset (8 assets, desbloqueados por fase): EURUSD/GBPUSD → USDJPY/XAUUSD/NAS100 → SPX500/BTCUSD/ETHUSD
- Estrategia **Fotmarkets-Micro** (scalping reversal post-pullback 5m)
- Escalation risk: **10% → 5% → 2%** según fase ($30→$100→$300+)
- Ventana **CR 07:00–11:00** (London/NY overlap)
- Ejecución **manual en MT5** (sin EA bridge)
- Ver `.claude/profiles/fotmarkets/config.md`, `strategy.md`, `rules.md`

**⚠️ Filosofía Fotmarkets:** capital es bonus ("casa de juego"), NO depositar dinero propio,
no reemplaza el profile FTMO/retail real.

### Reglas de operación multi-profile
1. **No operar el mismo setup en `retail` y `retail-bingx` simultáneamente** (doble exposición direccional al mismo BTC). Uno u otro por sesión/día.
2. **No mezclar profiles distintos (retail / ftmo / fotmarkets) el mismo día.** Switch al inicio de sesión.
3. **Nunca cruzar memorias** — trade FTMO no se escribe al log retail/fotmarkets y viceversa. Tampoco cruzar entre `retail` y `retail-bingx`.
4. **Guardian** (`.claude/scripts/guardian.py`) obligatorio en FTMO antes de cada entry.
5. **Lite Guardian** (`.claude/scripts/fotmarkets_guard.sh`) obligatorio en fotmarkets antes de cada entry.
6. **Statusline** muestra `[PROFILE]` en todo momento para prevenir confusión.

### Comandos específicos multi-profile
- `/profile` — ver/cambiar profile activo
- `/equity <valor>` — actualizar equity FTMO manualmente
- `/challenge` — dashboard progreso FTMO (solo ftmo)
- `/status` — estado adaptado al profile activo
- Los demás (`/morning`, `/validate`, `/risk`, `/journal`) son profile-aware
- `/profile fotmarkets` — switch al 3er profile
- `/risk` en fotmarkets → calcula sizing phase-aware (10%/5%/2%)

## Estrategia oficial — DEPENDE DEL RÉGIMEN DE MERCADO

**Principio crítico:** NO hay estrategia universal. Cada día al iniciar sesión (CR 05:30), detectar el régimen ANTES de elegir estrategia.

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
| Ventana | **CR 06:00 – 23:59** |
| Force exit | **23:59 CR** (regla "no dormir con trade abierto"); cierre anticipado permitido si ya hay ganancia del día o pendiente personal |
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

### Trailing Stop con EMA(20) — modo runner alternativo

Para el TP3 (20% runner), modo de salida #4 según el "Manual del Buen Trader Algorítmico":
en lugar de target fijo 6×SL, dejar trail con EMA(20) en bars 15m. Salida cuando close 15m
cruza la EMA en contra. Captura más rally cuando ADX>25.

- Helper: `python3 .claude/scripts/trailing_stop.py --side long --entry X --current Y --file /tmp/bars15m.json`
- Comando: `/trail <side> <entry>` (auto-pull de bars vía MCP)
- Default `ema=20`, threshold de toque 0.1%

### ADX(14) en regime-detector

`/regime` ahora reporta ADX(14) explícito (1H bars):
- ADX < 20 → RANGE_CHOP (Mean Reversion o stand-aside)
- ADX 25–30 → TREND_LEVE (pullback en dirección)
- ADX 30–40 → TREND_FUERTE (Breakout/Momentum)
- ADX > 40 → TREND_EXTREMO (no scalping reversal)
- Direction = +DI vs -DI

Helper: `python3 .claude/scripts/adx_calc.py --file /tmp/bars1h.json --quick`

### Out-of-sample backtest (anti-overfit)

`/backtest` y backtest-runner SIEMPRE hacen split temporal 70/30 ahora. La config "ganadora"
del ranking se valida con `report_oos(train_metrics, test_metrics)`:
- **PASS** → recomendación con confianza moderada
- **WARN** → reportar con advertencia
- **FAIL** → declarado como overfit, NO recomendar

Helper: `python3 .claude/scripts/backtest_split.py --train '{...}' --test '{...}'`

### MA Crossover (EMA 9/21) — 3ª estrategia para TRENDING

Cuando régimen es TREND_LEVE/FUERTE (ADX 25-40) y no hay nivel claro Donchian:
- **LONG**: EMA(9) cruza arriba de EMA(21) AND close > EMA(21)
- **SHORT**: espejo
- TP3 (20%) usa trailing EMA(21) vía `/trail long X 21`

Comando: `/macross` (auto-pull bars 15m vía MCP)
Helper: `python3 .claude/scripts/macross.py --file /tmp/bars15m.json --quick`

### Validación per-asset (multi-symbol disparity check)

Para profiles con múltiples assets (FTMO, fotmarkets), valida si Mean Reversion necesita
thresholds distintos por símbolo. Detecta el principio del PDF: "no hay estrategia
universal — RED FLAG si te dicen que funciona en cualquier activo".

Comando:
```bash
# Crypto via Binance (sin key):
python3 .claude/scripts/per_asset_backtest.py --crypto BTCUSDT,ETHUSDT --tf 1h --bars 300

# Profile completo:
python3 .claude/scripts/per_asset_backtest.py --profile fotmarkets

# Forex/indices: pasa --json-dir con un .json por asset
```

Output: tabla markdown con WR/PF/Ret/DD por asset + flag automático si disparidad WR > 30pp.

### Helpers Python introducidos por el PDF (todos en `.claude/scripts/`)

| Helper | Función | Comando |
|---|---|---|
| `adx_calc.py` | ADX(14) + DI + label_regime | `/regime` |
| `trailing_stop.py` | Eval EMA(20) trail | `/trail` |
| `backtest_split.py` | Split 70/30 + OOS report | usado por backtest-runner |
| `macross.py` | EMA(9/21) cross detector | `/macross` |
| `per_asset_backtest.py` | Backtest multi-asset comparativo | (script directo) |
| `test_pdf_helpers.py` | 19 sanity tests, corre en `preprompt_check.sh` cada 1h | (auto) |

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
6. **Sesión horaria óptima:** CR 06:00–10:00 (London/NY overlap, mayor volatilidad 0.85%)

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
- **Bookmap (orderflow + heatmap liquidez):** https://web.bookmap.com/ — confirmación visual de entries (walls bids/asks, absorción, spoofing, stop hunts). Solo Binance Futures, uso manual no automatizable. Ver `memory/bookmap.md`.

## Disclaimer

Nada en este proyecto es consejo financiero. Futuros con leverage pueden liquidar capital en minutos con un wick. Usa capital que puedas perder sin afectar tu vida.
