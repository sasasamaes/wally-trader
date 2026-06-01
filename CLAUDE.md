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

## Profile System (7 profiles)

El sistema soporta **7 profiles aislados**. Se switchean con `/profile` o con env var `WALLY_PROFILE` (multi-terminal).

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

### Profile `fundingpips` (Zero $10k — direct funded MT5)
- **Capital $10,000 USD** real-money funded (NO demo, NO challenge)
- **Costo cuenta:** $99 USD ($79 con HELLO -20%)
- **Provider:** [FundingPips](https://fundingpips.com), modelo "Zero" (sin evaluación)
- **MT5** server `FundingPips-Live` (reusa EA bridge del profile FTMO)
- **Multi-asset universe** (20+): forex majors/crosses, indices (NAS/SPX/US30/DAX/FTSE/JPN), crypto (BTC/ETH), commodities (XAU/XAG/oil)
- Estrategia **FundingPips-Conservative** (más estricta que FTMO-Conservative)
  - Risk per trade: **0.3%** ($30) — NO 0.5% como FTMO
  - Target diario: 0.5-0.7% (consistency-friendly)
  - Max trades/día: **2**
  - TP fijo (NO trailing — incompatible con regla 15% consistency)
- **Reglas duras:**
  - 3% daily loss → BLOCK sistema en -2%
  - **5% max DD vs balance fijo** $10k → BLOCK sistema en -3% (más estricto que FTMO 10% trailing)
  - **15% consistency:** biggest day NO puede exceder 15% del profit total → BLOCK en 12%
  - 7 días min trading antes de retirar
  - Leverage 1:50 (vs FTMO 1:100)
- **Payout:** Bi-weekly 95% al trader
- Ventana **CR 06:00–16:00** (forex/indices) o **06:00–20:00** (crypto)
- Guardian: `.claude/scripts/fundingpips_guard.sh` antes de cada entry
- Ver `.claude/profiles/fundingpips/config.md`, `strategy.md`, `rules.md`

**⚠️ Filosofía FundingPips:** dinero real desde día 1, $99 perdido si rompes 5% DD. **El edge no es ganar — es no perder.** Estrategia ultra-conservadora.

**Plan declarado:** usar payouts FundingPips para fondear retail (Binance) y eventualmente comprar otra cuenta FTMO $100k.

### Profile `bitunix` (copy trading punkchainer's community)
- **Capital $200 USD** (recalibrado 2026-05-04 — capital real para operativa diaria)
- **Provider:** [Bitunix](https://bitunix.com), código referido `punkchainer`
- **Filosofía:** NO es análisis propio — es validar señales externas con `/signal` antes de copiar
- **Universo:** dinámico (lo que la comunidad punkchainer's señale en Discord — BTC, ETH, MSTRUSDT, altcoins)
- **Watchlist exhaustivo (32 assets, prefix `Bitunix:.P` capitalizado):** 24 tradeables en Bitunix (BTC, ETH, SOL, MSTR, AVAX, INJ, DOGE, WIF, FARTCOIN, XLM, TON, ADA, LINK, SUI, TRX, RUNE, ENJ, CHZ, AXS, SEI, POL, HBAR, TIA, ROSE) + 8 sólo contexto vía fallback OKX/Binance/Bybit (PEPE, PIPPIN, BCH, MON, XAUT, STRK, XMR, BANANAS31) — pre-scaneado por `/punk-morning` y `/punk-hunt`. Scan completo ~3-5 min; usar `/punk-hunt quick` para top-5 líquidos.
- **Validación:** 4 filtros + multifactor>±50 + ML>55 + chainlink delta <1%. Score >=60% → APPROVE
- **Leverage cap:** sigue al leverage de la señal hasta **20x** (bitunix excepción del cap global 10x). Si señal pide >20x → WARN y consciencia operador, no override automático.
- **Risk per signal:** 2% capital ($4 sobre $200). **Max 7 signals/día**, **max 2 concurrentes**. Auto-blacklist asset con 2 SLs
- **Daily loss BLOCK:** -6% ($12 sobre $200, ~3 SLs)
- **Objetivo PnL diario:** $20-100 (5+ wins / 7 attempts con WR comunidad ~70% y R:R 2:1 → 5:1)
- **Ventana:** 24/7 cripto, prefiere London/NY overlap (CR 06:00-15:00)
- **Pre-sesión:** `/punk-morning` prepara macro gate + scan 10+ assets + Neptune setup en TV (Signals + Oscillator default) + slot counter (X/2)
- **Caza autónoma:** `/punk-hunt` (modo híbrido) escanea las 10 cripto cada ~1h, scoring 0-100, requiere score≥70 (más estricto que /signal), auto-loggea propuesta self-generated. Loop opcional: `/loop 60m /punk-hunt`
- **Tracking:** `signals_received.md` documenta TODAS las señales (Discord vía /signal + self-generated vía /punk-hunt) con outcome — comparable hit rate por origen
- Ver `.claude/profiles/bitunix/config.md`, `strategy.md`, `rules.md`

**⚠️ Filosofía Bitunix:** "el edge no es seguir gurús — es entender por qué su señal funciona (o no) y filtrar las malas con tu propia lógica."

### Profile `quantfury` (BTC-denominated trading)
- **Capital 0.01 BTC** inicial (≈$750 a $75k/BTC — ajustable)
- **Provider:** [Quantfury](https://quantfury.com) — broker app crypto-native con custodia
- **Unit of account:** **BTC (no USD)** — todo PnL/Sharpe/métricas en BTC absoluto
- **Asset único:** BTCUSD long/short (estrategia Mean Reversion 15m igual que retail, pero medida en BTC)
- **Métrica clave:** **outperformance vs HODL** — si BTC sube 10% USD y tú haces +5% USD, perdiste BTC stack
- **Risk per trade:** 2% del BTC capital (0.0002 BTC en 0.01)
- **Leverage cap:** 5x effective
- **Régimen-aware:**
  - TRENDING UP: prefer HODL > longs (replica spot)
  - TRENDING DOWN: SHORTS direccionales (fase oro para stack BTC)
  - RANGE: Mean Reversion ambos lados
  - VOLATILE: NO operar
- **Reglas duras:** -2% daily BLOCK, -10% total DD BLOCK, outperformance <-2% → PAUSAR profile 30d
- **Helper único:** `bash .claude/scripts/btc_outperform.py --period 30d` calcula vs HODL benchmark
- Ver `.claude/profiles/quantfury/config.md`, `strategy.md`, `rules.md`, `memory/hodl_benchmark.md`

**⚠️ Filosofía Quantfury:** "Bitcoin is the unit. USD is the noise. Si HODL hubiera dado más BTC stack, tu trading no tiene edge."

### Reglas de operación multi-profile
1. **No operar el mismo setup BTC simultáneamente en múltiples profiles.** retail + retail-bingx + ftmo + fundingpips + bitunix + quantfury todos pueden tradear BTC. **Doble/triple/quadruple exposición direccional = riesgo correlacionado.** Uno por día.
2. **No mezclar profiles distintos el mismo día** (general). Switch al inicio de sesión.
3. **Nunca cruzar memorias** — cada profile tiene su trading_log y memorias aisladas.
4. **Guardian** (`.claude/scripts/guardian.py`) obligatorio en FTMO antes de cada entry.
5. **Lite Guardian** (`.claude/scripts/fotmarkets_guard.sh`) obligatorio en fotmarkets antes de cada entry.
6. **FundingPips Guardian** (`.claude/scripts/fundingpips_guard.sh`) obligatorio en fundingpips antes de cada entry.
7. **Bitunix copy validation:** cada señal externa debe pasar `/signal` con score ≥60% antes de ejecutar. Leverage cap profile-específico: **20x** (no aplica el 10x global). >20x = WARN, no auto-override.
8. **Quantfury BTC-aware:** medir todo en BTC, no USD. Si outperformance vs HODL <-2% mensual → PAUSAR profile 30 días.
9. **Cross-asset BTC exclusion (CRÍTICO):** NO BTC simultáneo en retail + ftmo + fundingpips + bitunix + quantfury. Default: usar 1 profile por día.
10. **Statusline** muestra `[PROFILE]` en todo momento para prevenir confusión.

### Comandos específicos multi-profile
- `/profile` — ver/cambiar profile activo
- `/equity <valor>` — actualizar equity FTMO manualmente
- `/challenge` — dashboard progreso FTMO (solo ftmo)
- `/status` — estado adaptado al profile activo
- `/punk-morning` — preparación pre-sesión bitunix con scan exhaustivo 10+ assets + Neptune setup en TV [solo bitunix]
- `/punk-hunt` — caza autónoma cada ~1h: escanea 10 cripto, elige el mejor setup, score≥70, auto-loggea recomendación [solo bitunix]
- `/punk-smart` v2 — regime-aware router 5-stage [solo bitunix]. Ver bloque dedicado más abajo.
- `/signal SYMBOL SIDE entry sl=X tp=Y leverage=N` — valida señal externa Discord (auto-log si profile=bitunix)
- `/log-outcome SYMBOL TP1|TP2|TP3|SL EXIT [--id N] [--pnl USD]` — cierra outcome de señal bitunix (cualquier origen)
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

### `/punk-smart` v2 (2026-05-05) — bitunix-only

Regime-aware router con pipeline de 5 stages: kill-switch → per-asset mapping →
strategy → 6-veto layer → dynamic sizing → trail-SL annotation. Backtest 60-day,
schema v2 mapping con per-asset overrides (n≥10) + global fallback.

- **Kill-switch:** 2 SLs en 4h activa PAUSE hasta el siguiente CR 00:00.
- **Vetos (6):** macro events / blacklist asset / correlation bucket / sentiment
  contrarian / funding contrarian / time-of-day weak window.
- **Sizing:** `pnl_per_trade / 2.0` clipped a `[0.3, 1.5]` × $4 margin base.
- **Trail SL:** TP1 hit → SL se mueve a BE + 0.2×ATR (anotado en setup).

Rollback flags en `regime_mapping.json`:
- `version: 1` → router cae a comportamiento v1 (sin per-asset, sin vetos, sin trail).
- `vetos_enabled: []` → todos los setups pasan la veto layer.
- `dynamic_sizing: false` → tamaño fijo $4 margin, sin multiplier.
- `trail_sl_offset_atr: 0.0` → trail equivale a BE plano.

Daily state reset launchd: `com.wally.bitunix-daily-reset` corre a CR 00:00 y
trunca `asset_sl_streaks.json` + `sl_window.json` (los re-crea con esquema vacío).

Ver: `docs/superpowers/specs/2026-05-05-punk-smart-v2-design.md`,
`docs/backtest_findings_2026-05-05_punk_smart_v2.md` (gates fail strictly,
mergeado con override explícito 2026-05-06; live-data > pre-launch tuning).

### `/fot-scout` (2026-05-31) — fotmarkets-only

Análogo de `/punk-smart` para el universo MT5 de fotmarkets. Cada corrida escanea los 8 activos
(EURUSD/GBPUSD/USDJPY/XAUUSD/NAS100/SPX500/BTCUSD/ETHUSD), detecta régimen por activo y aplica la
estrategia ganadora, valida y propone el mejor setup (entry/SL/TP + sizing) para **MT5 manual**.
Pensado para correrse varias veces/sesión o con `/loop 30m /fot-scout` para crecer $50 → $500.

- **Mapping honesto** (`fot_strategy_mapping.json`, ASIMÉTRICO): solo Mean Reversion (RANGE_CHOP)
  es edge `VALIDATED` → puede llegar a GO. Breakout/MA-Cross (TREND) son `WEAK` → máximo TENTATIVE
  con `⚠️ edge no validado`, NUNCA GO (backtest 2026-05-31: PF ~0.9-1.07, mueren al spread CFD bonus).
  VOLATILE/TREND_EXTREMO → stand aside. Oro fue el mejor activo (~0.89 setups/día, +0.46R, WARN OOS).
- **Split:** command (`system/commands/fot-scout.md`, profile guard + `fotmarkets_guard.py check` +
  router) → `fot_scout_router.py` (motor determinista, `--json`, reusa wally_core + per_asset_backtest +
  macross) → agente `fot-scout-analyst` (refina quote TV live anti-delay yfinance + cadena
  macro_gate/session_quality/volume_divergence/min_rr_gate + GO/NO-GO MT5 + log).
- **Override consciente:** `phase_1.allowed_assets` ampliado a `[EURUSD, XAUUSD, BTCUSD, ETHUSD]`
  (config.md + `PHASE_ALLOWED` en el router espejan). A $50/1% risk muchos activos dan
  `UNTRADEABLE_SIZE` (min lot 0.01 excede 1%) — el scout lo marca; honest-first sobre el capital chico.
- **Disciplina:** WAIT honesto cuando no hay edge; sizing phase-aware; propuestas a
  `memory/scout_proposals.md` (no a `trading_log.md`, no contamina el day-count del guardian).
- CLI: `.claude/scripts/.venv/bin/python .claude/scripts/fot_scout_router.py --json`.
  Tests: `shared/wally_core/tests/test_fot_scout.py` (17). Spec/plan:
  `docs/superpowers/{specs/2026-05-31-fot-scout-design.md,plans/2026-05-31-fot-scout.md}`.
- **Noticias FF (2026-06-01):** el router adjunta un bloque `news` (eventos high-impact FF
  próximas 48h, filtrados a las divisas de los activos desbloqueados) al `--json`; se muestra
  en cada tick (incluido WAIT). Informativo, no gatea. Helper:
  `wally_core.macro.upcoming_relevant()`.

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

### Hallazgos legacy
- **$10 → $100 en un solo trade es matemáticamente imposible a 20x** (requiere +45% move sin liquidación)
- **20x con SL 1% en 4H = -48% en 50 días** (winrate 10%). NO usar esa config.
- **10x ST(2,7) en 4H** ganó +87% en 50 días pero con DD 51% (casi liquidación)
- **Pasado NO equivale a futuro** — data disponible en TV MCP está capada a 300 barras por timeframe (3-50 días según TF)
- Ruta realista $10→$100: **6-12 meses compoundeando** al 2-5% neto diario

### 🆕 Hallazgos backtest 2026-04-30 (autoritativo)

📄 **Reporte completo:** `docs/backtest_findings_2026-04-30.md` (lectura obligatoria)

**3 fixes aplicados al sistema:**

1. **Regime gate ADX<20 hard precondition** (retail/retail-bingx/quantfury)
   - MR sin gate en período TRENDING dio -34.83% Ret / WR 22.7% / 66 trades
   - Con gate ADX<20: -4.01% (4 trades) — **prevención de pérdidas 88%**
   - **Antes de evaluar 4 filtros MR**, `/regime` debe arrojar RANGE_CHOP

2. **Fotmarkets risk recalibrado fase 1: 10% → 1%**
   - Risk 10% legacy generó DD 70.20% (viola regla 12% DD)
   - Risk 1% en EURUSD: DD 10.53% ✅ Ret +39.8% / WR 49.67% / PF 1.5
   - **GBPUSD removido** del whitelist (sin edge a ningún risk)

3. **Quantfury HODL pre-flight obligatorio**
   - Backtest demostró outperformance vs HODL fue **-49.81pp** en período
   - Strategy -34.83% vs HODL pasivo +14.98%
   - Pre-flight check antes de cada entry; regla "<-2% mensual → PAUSAR 30d"

**Strategy mapping per-asset (FTMO/FundingPips):**

| Asset | Strategy ganadora | TF | WR | PF |
|---|---|---|---|---|
| **XAUUSD** ⭐ | Donchian Breakout | 4H | 66.67 | 2.175 |
| USDJPY | MA Crossover (9/21) | 1H | 55.17 | 1.861 |
| EURUSD | Donchian Breakout | 1H | 55.17 | 1.357 |
| BTCUSDT/ETH | Mean Reversion | 1H | 31.25 | 1.048 |
| GBPUSD ❌ | (sin edge) | — | — | — |

**Hallazgos no implementados (futuro):**
- **Bitunix backtest real**: requiere dataset histórico de señales reales de la comunidad. Iniciar log en `signals_received.md` desde 2026-04-30 (template + CSV listos).
- **NAS100/SPX500**: data backtest insuficiente (8/3 trades) — más data needed.
- **Donchian Breakout en BTC**: probar como alternativa para períodos TRENDING.

### 🆕 Backtest findings 2026-05-12 (post-Bundle 3)

📄 **Reportes:** `docs/backtest_findings_2026-05-12_pullback_vs_macross_trend_leve.md` y `docs/backtest_findings_2026-05-12_asian_range_eurusd.md`

**1. Pullback Detector vs MA Crossover (TREND_LEVE) — verdict NEUTRAL / KEEP-MACROSS**
- Universe: BTCUSDT/ETHUSDT/SOLUSDT/AVAXUSDT/INJUSDT 60d 15m
- Pullback: 402 trades, WR 42.8%, PF 1.14, +28.80R
- MACross: 145 trades, WR 33.8%, PF 0.87, -12.33R
- Pullback es **más robusto** (2.8× más setups, PF >1, OOS PASS) pero ambos están abajo del umbral wire-in (≥10pp WR AND ≥0.4 PF).
- **Acción:** mantener MA Crossover en `regime_mapping.json` TREND_LEVE slot. `/pullback` queda standalone. Re-evaluar en 30d con más data.

**2. Asian Range strategy en fotmarkets EURUSD 5m — verdict DISCARD ⛔**
- 25 trades en 60d. WR 32%, PF 0.83, ret -2.62%, **0% TP hits**.
- **Causa raíz estructural:** ventana fotmarkets (CR 07:00-10:55 = UTC 13:00-16:55) es NY open, NO London open. Los grabs reales ocurren UTC 08:00-11:00 (CR 02:00-05:00) — fuera del horario operativo del trader.
- **Acción:** DISCARD para fotmarkets. `strategy_asian_range.md` actualizado con el verdict. `/asian-range` slash queda como herramienta sin profile target. Considerar futuro profile dedicado madrugador si interesa la estrategia.

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

## Discipline & Observability tooling (Bundle 1, 2026-05-04)

Three new automated systems added in branch `feat/discipline-observability`:

### Macro events gate (#7)
- Cache: `.claude/cache/macro_events.json`, refrescado diario CR 04:00 vía launchd `com.wally.macro-calendar`
- CLI: `python3 .claude/scripts/macro_gate.py --check-now | --check-day YYYY-MM-DD | --next-events --days N`
- Wire-in: agentes `trade-validator`, `signal-validator` chequean **antes** de los 4 filtros (NO-GO inmediato si dentro de ±30 min de evento high-impact). `morning-analyst` y `morning-analyst-ftmo` chequean al inicio (warning, no block).
- Manual refresh: `.claude/scripts/.venv/bin/python .claude/scripts/macro_calendar.py`
- Whitelist: USA tier-1 (FOMC/CPI/NFP/PCE/PPI/GDP/Powell/Retail Sales) + ECB/BoE/BoJ rate decisions + employment change/unemployment rate/AHE (FF naming variants)
- DST-aware: usa `zoneinfo.ZoneInfo("America/New_York")` para conversión EST/EDT → CR correcta año redondo
- Activar launchd: `cp .claude/launchd/com.wally.macro-calendar.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.wally.macro-calendar.plist`

### Session quality gate (FASE 0.5) — VWAP-flat detector (2026-05-09)
- CLI: `python3 .claude/scripts/session_quality.py --symbol <SYM> --quick`
- Detecta micro-estructura plana ANTES de los 4 filtros: VWAP std-dev < 0.10% AND últimas 8 velas con range < 0.50% → BLOCK ("dead session")
- Solo flat XOR compressed → WARN (reducir size 50%)
- Wire-in: `trade-validator` (FASE 0.5 después de macro_gate) y `signal-validator` (mismo, con excepción bitunix override visual)
- Ratio: lección directa del video YouTube "How to Connect Claude to TradingView" — "Asia some nights completely flat. I lost two trades. I know better than to trade that."
- Tests: `shared/wally_core/tests/test_session_quality.py` (12/12 green)
- Exit codes: 0=OK 1=BLOCK 2=WARN otros=ERROR (no block)

### `/pine-gen` — Pine v6 generator desde NL (2026-05-09)
- Slash command: `/pine-gen <descripción>` genera indicador Pine Script v6 desde lenguaje natural
- Workflow: NL description → Claude genera código Pine v6 → guarda en `system/pine_library/<slug>.pine` → compila vía MCP (`pine_set_source` + `pine_smart_compile`) → reporta clean/errors corregidos (max 3 retry cycles)
- Reglas estrictas: `//@version=6`, `indicator()` declaration, inputs visibles, no funciones deprecated v4/v5, alertas con `alert()`/`alertcondition()`
- Disclaimer: tratar output como **draft** que necesita 1 revisión visual + 1 backtest antes de confiar
- Para strategies con backtester usa `strategy()` en vez de `indicator()` (preguntar al user si ambiguo)

### `/liq-heatmap` — Liquidation cluster estimator (2026-05-09)
- Slash command: `/liq-heatmap <SYMBOL>` estima clusters de liquidación sin APIs pagadas
- CLI: `python3 .claude/scripts/liq_heatmap.py --symbol BTCUSDT --quick`
- Combina: Binance Futures public data (OI, L/S retail+smart) + 24h price swings + leverage tier distribution (5x/10x/20x/50x/100x con weights típicos)
- Output: top N clusters por side (LONG_LIQ price-down / SHORT_LIQ price-up) con heat score 0-100 + magnet (cluster más cercano con heat≥50)
- Wire-in TV: dibuja líneas horizontales en TradingView para clusters heat≥70 (rojas LONG-side / verdes SHORT-side / sólida thicker para magnet)
- Use cases: pre-trade (verificar SL no en honeypot), mid-trade (ajustar TP hacia magnet), squeeze setups (asymmetric long en short clusters densos)
- Tests: 10/10 green en `test_liq_heatmap.py`
- Limitaciones: aproximación, no es Coinglass real; solo Binance OI; falla en alts con OI <$5M

### `/strategy-import` — Strategy distiller desde fuentes externas (2026-05-09)
- Slash command: `/strategy-import youtube <URL>` | `file <PATH>` | `url <URL>` | `text "..."`
- CLI: `python3 .claude/scripts/strategy_distill.py --youtube|--file|--url|--text ...`
- Workflow Fase 1 — extracción: yt-dlp para YouTube auto-subs, pdftotext/PyPDF2 para PDFs, urllib + HTML strip para web URLs
- Workflow Fase 2 — distilación (Claude): lee texto crudo en `.claude/strategy_imports/raw/<slug>.txt` y produce JSON declarativo en `.claude/strategy_imports/rules/<slug>.json` con schema (entry_rules, exit_rules, filters, asset_universe, timeframe, risk_per_trade_pct, etc.)
- Filtros honest-first: rechaza promesas garantizadas ("100% WR"), esquemas pump-dump, content sin lógica clara (output `NOT_A_STRATEGY`)
- Tests: 10/10 green en `test_strategy_distill.py`
- Limitaciones: YT auto-subs imperfectos; PDFs scaneados (imágenes) requieren OCR previo; Twitter API no integrada (copiar texto manual)
- Próximo: `/strategy-scan <slug>` (futuro) escaneará universe definido buscando setups que matcheen rules

### `/track-dragno` — External bot performance tracker (2026-05-10)
- Slash command: `/track-dragno` — append trades from screenshots OR show stats dashboard
- CLI: `python3 .claude/scripts/dragno_track.py --append-from-stdin | --stats | --regenerate-md`
- Manual ingestion: user pastes Bitunix screenshots → Claude parses → JSON piped to script → CSV append + dedup
- Counterfactual integrated: every dashboard shows what PnL would have been with SL -8% hard cap
- Storage: `memory/external_traders/dragno_ai.csv` (append-only) + `dragno_ai.md` (regenerated)
- Validates the 2026-05-10 hypothesis: Dragno AI's edge is real (WR 57%, PF 1.69) but SL -8% would have improved net PnL by +80% by clipping 2 outlier losses (VIRTUAL -15%, SUSDT -20%)
- Tests: 13 in `test_dragno_track.py` (derive_margin, parse_input_rows, dedup, compute_stats, counterfactual baseline pin)
- YAGNI scope: no scraping, no API, single-bot (one CSV per bot if more added later)
- Spec: `docs/superpowers/specs/2026-05-10-track-dragno-design.md`

### Bitunix signal log capture (#3)
- Auto-log: cada `/signal` ejecutado con `WALLY_PROFILE=bitunix` appendea su reporte a `signals_received.md` y `.csv`
- Cierre manual: `/log-outcome SYMBOL TP1|TP2|TP3|SL|manual EXIT_PRICE [--id N] [--pnl USD]`
- Ej: `/log-outcome BTCUSDT TP1 68000 --pnl 1.50`
- Multi-entry: si hay 2 señales abiertas mismo símbolo, lista los `--id` y pide elegir
- Schema validado: si CSV existente tiene esquema distinto, escribe a `bitunix_log_errors.log` y aborta (previene corrupción silenciosa)
- Goal: acumular 30+ señales con outcome para enable backtest real (ver `docs/backtest_findings_2026-04-30.md` Group E)

### Weekly cross-profile digest (#8)
- Auto-run: domingo 18:00 CR vía launchd `com.wally.weekly-digest`
- Manual: `.claude/scripts/.venv/bin/python .claude/scripts/weekly_digest.py --week current` (o `--week 2026-W17` para regenerar pasada)
- Output: `memory/weekly_digests/YYYY-Wnn.md` + macOS notification
- Contiene: tabla cross-profile (capital, PnL semana/mes, WR, status), próxima semana macro events (lee del cache de #7), highlights de disciplina, sugerencias
- Profile parser registry: retail/retail-bingx/ftmo/fundingpips/fotmarkets/bitunix tienen parsers; quantfury intencionalmente "parser pending"
- Activar launchd: `cp .claude/launchd/com.wally.weekly-digest.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.wally.weekly-digest.plist`

### Spec & plan
- Design: `docs/superpowers/specs/2026-05-04-discipline-observability-bundle-design.md`
- Implementation plan: `docs/superpowers/plans/2026-05-04-discipline-observability-bundle.md`

## Live Insights Bundle (Bundle 2, 2026-05-10)

Five features inspired by Dragno community master live (YouTube `Be8IYJLgdYA`, 25 min):

### Feature A — USDT.D dominance tracker
- CLI: `python3 .claude/scripts/usdtd_tracker.py [--json|--quick]`
- Source: CoinGecko `/global` (free, no auth). Cache 10 min en `.claude/cache/usdtd.json`.
- Returns: USDT.D, BTC.D, trend (UP/DOWN/FLAT), btc_inverse_bias (BEARISH/BULLISH/NEUTRAL).
- Inverse-correlation thesis: USDT.D ↑ = capital rotando a stables = bearish BTC.
- Wired into: `regime-detector` (USDT.D context), `signal-validator` (FASE 0.8).

### Feature B — Macro multi-tier blackout
- CLI: `python3 .claude/scripts/macro_gate.py --check-tier [--soft-hours N]`
- Tiers:
  - `HARD` (±30 min de high-impact event) → NO-GO
  - `WARN` (±4 horas) → reduce size 50%
  - `SOFT` (próximas 48h con default, configurable) → INFO + sugiere tier-0 MUGRES
  - `OK` → continue normalmente
- Wired into: `trade-validator` FASE 0.6, `signal-validator` FASE 0.6.

### Feature C — Volume/OBV divergence pre-entry
- CLI: `python3 .claude/scripts/volume_divergence.py --symbol BTCUSDT --direction LONG --quick`
- Detecta: precio sube pero OBV/volumen bajan → divergencia bearish → WARN contra LONG.
- Implementa el veto del master: "subiendo sin fuerza, no es creíble".
- Wired into: `trade-validator` FASE 0.7, `signal-validator` FASE 0.7.

### Feature D — Auto-MUGRE switch on macro WARN/SOFT
- `/punk-hunt` ejecuta `macro_gate --check-tier` antes del scan:
  - `HARD` → aborta scan
  - `WARN`/`SOFT` → auto-fuerza `--tier-0` (MUGRES, decoupled de BTC)
  - `OK` → scan estándar
- Override con `--no-auto-tier` para forzar scan normal.

### Feature E — Fib extension exhaustion
- CLI: `python3 .claude/scripts/fib_extension.py --symbol BTCUSDT --tf 1w --quick`
- Auto-detecta swing high/low del rango visible y clasifica el precio actual:
  - `OK` (< 150% extension)
  - `EXHAUSTION_MILD` (≥ 150%)
  - `EXHAUSTION_HIGH` (≥ 200%)
  - `EXHAUSTION_EXTREME` (≥ 261.8%)
- Wired into: `morning-analyst` (BTC), `morning-analyst-ftmo` (multi-asset). Informativo only.

**Tests:** 36 nuevos green (usdtd 6 + macro_gate +5 = 17 total + vol_div 5 + fib_ext 8).

**Spec:** `docs/superpowers/specs/2026-05-10-live-insights-bundle-design.md`
**Plan:** `docs/superpowers/plans/2026-05-10-live-insights-bundle.md`

## YouTube Improvements Bundle (Bundle 3, 2026-05-12)

Six improvements distilled from four Alex Ruiz videos (es):

### Feature B — Dynamic Min-R:R Gate
- CLI: `.claude/scripts/.venv/bin/python .claude/scripts/min_rr_gate.py --profile <name> --setup-rr <ratio>`
- Formula: `min_rr = ((1-wr)/wr) * 1.2` with WR clamped [0.20, 0.80], fallback 1.5 when <10 trades.
- Wired into `trade-validator` FASE 0.9 and `signal-validator` (LOW_RR score penalty).

### Feature C — Fib Retracement Zones (extension of fib_extension.py)
- CLI: `.claude/scripts/.venv/bin/python .claude/scripts/fib_extension.py --mode retracement --symbol BTCUSDT --tf 1h`
- Output: 0.382 / 0.500 / 0.618 entry zones + SL at 0.75 + TP at swing extreme.
- Used internally by pullback_detector.py.

### Feature F — Three-Months-Positive Challenge Gate
- CLI: `.claude/scripts/.venv/bin/python .claude/scripts/challenge_readiness.py --profile <name>`
- Returns READY / BORDERLINE / NOT_READY based on last 3 months of PnL parsed from the profile log.
- Wired into `/challenge` as a soft advisory banner before any "buy next challenge" decision.

### Feature G — retail-bingx Cost Reality (documentation only)
- `.claude/profiles/retail-bingx/config.md` updated to mark the profile as observation-only ($0.93 capital + tick size makes real execution non-viable despite tiny fees).

### Feature A — Pullback Detector (standalone, no router wire-in yet)
- CLI: `.claude/scripts/.venv/bin/python .claude/scripts/pullback_detector.py --symbol BTCUSDT --tf 15m`
- Slash: `/pullback [SYMBOL] [TF]`
- Pipeline: ADX≥25 gate → impulse (3+ same-color, ATR>μ) → fib 0.382-0.618 retrace → continuation candle.
- Output: entry / SL (fib 0.75) / 3 TPs (Fibonacci extensions) / confidence 0-100.
- **Standalone-first** by design — backtest vs MA Crossover required before wiring into `regime_mapping.json`.

### Feature E — Asian Range Secondary Strategy (fotmarkets)
- CLI: `.claude/scripts/.venv/bin/python .claude/scripts/asian_range.py --file <bars5m.json> --check-grab`
- Slash: `/asian-range [SYMBOL] --file <path>`
- Pipeline: compute Asian session H/L (UTC 23:00-08:00) → detect break-and-reverse within 4 bars of London open.
- **Secondary only** — Fotmarkets-Micro 5m remains primary. See `.claude/profiles/fotmarkets/strategy_asian_range.md`.

### Out of scope (intentional)
- HMM regime detector — Alex's own V2 conclusion walked back HMM-for-param-tuning; existing `regime_mapping.json` + ADX cover the use case.
- 3h IA course (V4) — chapters 1:21, 1:36, 1:53, 2:06, 2:30 identified as worth manual viewing, but no programmatic distillation.

### Tests
- 22+ new tests across `test_min_rr_gate.py`, `test_fib_extension.py` (new tests), `test_challenge_readiness.py`, `test_pullback_detector.py`, `test_asian_range.py`. All synthetic fixtures, no live-data dependence.

### Spec & plan
- Design: `docs/superpowers/specs/2026-05-12-youtube-improvements-bundle-design.md`
- Plan: `docs/superpowers/plans/2026-05-12-youtube-improvements-bundle.md`

## HMM Diagnostic Tool (Bundle 4, 2026-05-13)

`/hmm-analyze SYMBOL STRATEGY` — diagnostic tool that fits a Hidden Markov Model to 1H × 6m OHLCV from Binance Futures, labels regimes (CALM_UP/TREND_UP/CHOP/TREND_DOWN/CALM_DOWN/STRESS/STRESS_LITE), backtests one of the 5 router strategies (A_VWAP, B_TrendPullback, C_BBSqueeze, D_MACDMomentum, E_RangeBounce) per regime, and emits a markdown report.

**Strictly diagnostic.** No live wire-in. Never modifies `regime_mapping.json`.

- CLI: `.claude/scripts/.venv/bin/python .claude/scripts/hmm_analyze.py --symbol ETHUSDT --strategy A_VWAP [--html] [--suggest-mapping]`
- Slash: `/hmm-analyze ETHUSDT A_VWAP` or `/backtest --hmm-analyze ETHUSDT A_VWAP`
- Output: `docs/hmm_analysis/<SYM>_<STRAT>_<YYYY-MM-DD>.md`
- Skill: `@hmm-regime-analysis` documents how to interpret outputs.
- Dependency: `hmmlearn>=0.3.0` installed in `.claude/scripts/.venv` (and `plotly` for `--html`, optional).

Reference: video `Cdhqu6rIvb0` by Alex Ruiz. Spec/plan in `docs/superpowers/{specs,plans}/2026-05-13-hmm-diagnostic-tool*.md`.

Bundle 3 (2026-05-12) rejected HMM-for-live-tuning; this tool implements only the **portfolio-management framing** Alex describes in the conclusion (~25 min mark): parameters fixed, strategy selection per regime informed by analysis.

## Strategy Validation Bundle — RST + Monte Carlo + Jesse lab (Bundle 5, 2026-05-31)

Destilado del video **"Opus 4.8 + Claude Code + MCP = Algo Trading on Autopilot"**
(Algo-trading with Saleh, framework Jesse, `youtube.com/watch?v=1SLbe0k6x4I`). Añade dos
gates de validación que faltaban + adopta Jesse como laboratorio paralelo. El gate completo
del flujo de backtest pasa a ser: **RST → backtest → OOS → Monte Carlo → veredicto honesto**.

### `/rst` — Rule Significance Test (entrada: ¿edge o ruido?)
- CLI: `.claude/scripts/.venv/bin/python .claude/scripts/rule_significance.py --symbol BTCUSDT --tf 30m --days 365 --strategy donchian_ema --side long --n 2000 --json`
- Permuta el timing de las entradas ~2,000 veces (mismas reglas de salida) → p-value.
  PASS si p<0.05 (la entrada bate al azar → tiene edge). Estimador conservador
  `(n_beaten+1)/(n+1)`, determinista por `seed`.
- API importable: `from rule_significance import significance_test, make_donchian_atr_exit`.
- Lección del video: una estrategia rentable NO prueba edge de entrada (un "always long"
  gana en bull year sin poder predictivo). Separa edge-de-entrada de rentabilidad.
- Exit 0=PASS / 2=FAIL|INSUFFICIENT / 3=error.

### `/montecarlo` — robustez del sizing + detector de overfit
- CLI: `.claude/scripts/.venv/bin/python .claude/scripts/monte_carlo.py --mode trades|candles ...`
- **trades (reshuffle):** reordena la secuencia de trades → distribución de max DD (retorno
  final invariante). WARN si `dd_p95` infla >50% sobre el observado → dimensiona el sizing
  al p95. Modo `bootstrap` opcional varía retorno + prob. de retorno negativo.
- **candles (block-bootstrap):** OHLCV sintético (factores de vela `o/c_prev,h/o,l/o,c/o`
  re-muestreados en bloques) → distribución de Sharpe. `overfit_flag = orig > p95` (zona
  OVERFIT_SUSPECT). Zonas: ROBUST / FRAGILE / WEAK / OVERFIT_SUSPECT.
- API: `from monte_carlo import monte_carlo_trades, monte_carlo_candles, default_strategy_sharpe`.

### Wire-in `backtest-runner`
- Pasos 5.6 (RST), 5.7 (Monte Carlo), 5.8 (veredicto combinado). Recomendar SOLO si
  RST=PASS **Y** OOS≠FAIL **Y** candles≠OVERFIT_SUSPECT; si no, caveat explícito.
- OOS multi-período NO se reimplementa: ya existe (`backtest_split.py`) y se integra al veredicto.

### Jesse lab (`integrations/jesse/`) — opcional, lo levanta el usuario
- Docker (Postgres+Redis+Jesse), su MCP a Claude Code (`claude mcp add --transport http jesse <url>/mcp`),
  estrategia de ejemplo `DonchianEMATrend` (port del video). Para backtests de año completo +
  Monte Carlo/walk-forward nativos. **NO reemplaza** el motor Wally ni los gates live.
- Caveat: setup toca servicios de sistema; el comando/puerto exacto del MCP es el que imprime
  `jesse run` (termina en `/mcp`).

### Tests
- 20 nuevos green: `test_rule_significance.py` (8) + `test_monte_carlo.py` (12). Fixtures
  sintéticas + edge plantado, sin dependencia de live-data.

### Spec & plan
- Design: `docs/superpowers/specs/2026-05-31-jesse-validation-bundle-design.md`
- Plan: `docs/superpowers/plans/2026-05-31-jesse-validation-bundle.md`

**Caveat honesto:** RST valida la entrada, no la rentabilidad (PASS no garantiza profit;
FAIL sí descarta edge). Un Monte Carlo de 1 año hereda el régimen de ese año — robustez ≠
garantía. Jesse acelera la iteración honesta, no fabrica edge.

## AI Strategy Optimization Bundle (Bundle 6, 2026-05-31)

Destilado del video **"I Let Claude AI Opus 4.8 Trade For Me"** (Trading with DaviddTech,
`youtube.com/watch?v=tkAq6g2Gjz4`). El video deja a Claude "loopear cada 5 min por 1 hora"
optimizando hasta hallar backtests rentables — pero presume ganadores con 27% max DD y curvas
sideways **sin validación OOS/Monte Carlo**. Este bundle toma el loop y lo hace honesto.

### `/optimize` — loop de optimización con gates anti-overfit
- CLI: `.claude/scripts/.venv/bin/python .claude/scripts/optimize_strategy.py --symbol BTCUSDT --tf 4h --side long --iterations 40 --validate-top 3 --export-pine --json`
- Random search seeded sobre la familia donchian_ema → rankea por score → valida el **top-K**
  con los gates del Bundle 5 (RST + OOS + Monte Carlo) → recomienda SOLO la que sobrevive los 3.
- **Verdict honesto:** RECOMMEND (exit 0) si una config pasa todo; **NONE_SURVIVED** (exit 2)
  si ninguna — no maquilla un sideways como ganador (verificado: BTC 4h long 365d → ninguna pasa).
- Presupuesto: `--iterations N` o `--minutes M` (estilo loop del video). API: `from optimize_strategy import optimize`.

### Export Pine `strategy()`
- `--export-pine` escribe `system/pine_library/opt_donchian_ema_<symbol>_<tf>_<side>.pine` —
  un `strategy()` v6 importable a TradingView para verificar el backtest visualmente.
- **Draft:** compilar + revisar visual + re-backtestear antes de confiar (el backtester de TV
  difiere levemente del motor Wally — salida ATR/Donchian sin pyramiding). API: `to_pine_strategy()`, `write_pine()`.

### Trader Dev MCP (`integrations/trader-dev/`) — opcional, ready-to-connect
- Scaffold del MCP de DaviddTech/StrategyFactory.ai. **No hay endpoint público** (gated tras
  signup/comment); no se inventa URL. Template `claude mcp add` con placeholder.
- Solapa casi 100% con el stack nativo (`/pine-gen`, `/backtest`, `/optimize`, `/rst`,
  `/montecarlo`) → opcional. Si lo conectas, mantené la frontera proposes-you-approve.

### Excluido a propósito
- **Auto-ejecución live en exchange** (el Bybit del video): choca con la filosofía
  manual/human-approve y las reglas de riesgo del proyecto.

### Tests
- 13 nuevos en `test_optimize_strategy.py` + 2 sanity checks en el harness horario. Fixtures
  sintéticas, determinismo por seed.

### Spec & plan
- Design: `docs/superpowers/specs/2026-05-31-ai-strategy-optimization-bundle-design.md`
- Plan: `docs/superpowers/plans/2026-05-31-ai-strategy-optimization-bundle.md`

## Disclaimer

Nada en este proyecto es consejo financiero. Futuros con leverage pueden liquidar capital en minutos con un wick. Usa capital que puedas perder sin afectar tu vida.
