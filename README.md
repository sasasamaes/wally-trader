# 🌭 Wally Trader — Triple-Profile Trading System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-84%20passing-brightgreen.svg)](#)
[![Multi-CLI](https://img.shields.io/badge/CLI-Claude%20Code%20%7C%20OpenCode-blue.svg)](#)

> Nombrado en honor a **Wally**, perro salchicha y CEO mascota del proyecto.

Sistema de trading algorítmico-asistido **triple-profile**: retail BingX BTCUSDT.P, FTMO MT5 multi-asset, y Fotmarkets bonus micro-capital. Construido sobre TradingView + Claude Code + Pine Script + MQL5 EA.

**Autor:** [Francisco Campos Diaz (@sasasamaes)](https://github.com/sasasamaes) · **License:** [MIT](LICENSE) · **Contribuciones:** ver [CONTRIBUTING.md](CONTRIBUTING.md)

**Status actual:** Retail validado con 3 wins (+36.3% / $10 → $13.63). FTMO profile + MT5 bridge implementados, pendientes de paper trading.
**Objetivo:** Escalar retail $10 → $100 y en paralelo pasar challenge FTMO $10k fundeado.

---

## 🎯 Qué es este proyecto

Un **sistema operativo de trading** dual-profile que combina:

- **Dual profile aislado** — retail (BingX $13.63, Mean Reversion 15m) y FTMO ($10k demo, FTMO-Conservative multi-asset)
- **Guardian rules engine** — enforce automático de reglas FTMO (3% daily hard, 10% trailing warn, Best Day info)
- **MT5 Bridge** — manual-asistido o via ClaudeBridge.mq5 EA (file-based JSON bridge para macOS)
- **Estrategias validadas** — Mean Reversion + Donchian Breakout (retail) / FTMO-Conservative multi-asset (FTMO)
- **Indicador Pine Script** con los 4 filtros de entrada automatizados
- **Protocolo matutino** (retail 17 fases / FTMO 14 fases multi-asset)
- **Memoria aislada por profile** — trades FTMO no contaminan log retail y viceversa
- **Journal obligatorio** de cada trade + review semanal
- **Integración con TradingView** via MCP (Claude dibuja niveles, detecta señales)
- **Capa ML** (NLP sentiment + XGBoost supervisado) como 5° filtro opcional
- **Watcher autónomo "set & forget"** — `/order` programa entry virtual, launchd vigila cada 1h, escala a Claude headless cuando precio está cerca, notifica macOS al dispararse trigger
- **Multi-CLI portable** — canonical `system/` con adapters para Claude Code, OpenCode (validado), Codex (untested)

No es un bot automatizado. Es una **disciplina acompañada** — Claude hace el análisis pesado, el guardian aplica reglas, tú ejecutas.

---

## 📁 Estructura del proyecto

```
trading/
├── CLAUDE.md                      # Guía del proyecto (Claude lee al iniciar)
├── MORNING_PROMPT.md              # Protocolo matutino retail (17 fases)
├── MEAN_REVERSION_INDICATOR.pine  # Indicador Pine Script (4 filtros + alertas)
├── DAILY_TRADING_JOURNAL.md       # Template journal diario
├── RISK_CALCULATOR.md             # Fórmulas de position sizing
├── README.md                      # Este archivo
│
├── system/                        # 📌 CANONICAL SOURCE OF TRUTH (multi-CLI)
│   ├── commands/                  # 23 slash commands markdown (formato CC)
│   ├── agents/                    # 12 agentes (incluye morning-analyst-ftmo)
│   ├── skills/                    # 14 skills custom
│   ├── mcp/servers.json           # MCP config neutral
│   ├── hooks/                     # placeholder para hooks compartidos
│   └── README.md                  # Flujo de sync + adapters
│
├── adapters/                      # Per-CLI translators
│   ├── claude-code/install.sh     # Symlinks .claude/ → system/
│   ├── opencode/                  # transform.py + pre-commit hook + watch
│   └── codex/                     # ⚠️ UNTESTED
│
├── .claude/                       # Claude Code harness
│   ├── settings.json              # statusline, hooks, permissions
│   ├── settings.local.json        # overrides locales (gitignored)
│   ├── .env                       # FTMO credentials (gitignored)
│   ├── .env.example               # template credenciales
│   ├── active_profile             # "retail | <iso>" o "ftmo | <iso>"
│   ├── commands/ → ../system/commands/   # symlink
│   ├── agents/   → ../system/agents/     # symlink
│   ├── skills/   → ../system/skills/     # symlink
│   ├── profiles/                  # 🆕 Profile-scoped config + memoria (4 profiles)
│   │   ├── retail/                # Binance main $18.09 (post-migración)
│   │   │   ├── config.md
│   │   │   ├── strategy.md
│   │   │   └── memory/            # + pending_orders.json (watcher v1)
│   │   ├── retail-bingx/          # BingX residual $0.93 (pedagógico)
│   │   │   ├── config.md
│   │   │   └── memory/            # + pending_orders.json
│   │   ├── ftmo/                  # $10k demo multi-asset
│   │   │   ├── config.md
│   │   │   ├── strategy.md
│   │   │   ├── rules.md
│   │   │   ├── memory/            # equity_curve, pending_orders, challenge
│   │   │   └── mt5_ea/            # ClaudeBridge.mq5 (EA bridge)
│   │   └── fotmarkets/            # Bonus $30 MT5 (Mauritius, bonus-only)
│   │       ├── config.md
│   │       ├── strategy.md        # Fotmarkets-Micro (5m reversal)
│   │       ├── rules.md
│   │       └── memory/            # phase_progress + pending_orders + session_notes
│   └── scripts/
│       ├── profile.sh             # Switch profile activo
│       ├── guardian.py            # 🆕 Rules engine FTMO (3%/10%/Best Day)
│       ├── mt5_bridge.py          # 🆕 JSON parser/writer para EA bridge
│       ├── test_guardian.py       # 24 unit tests
│       ├── test_mt5_bridge.py     # 19 unit tests
│       ├── test_integration.sh    # 8 e2e tests
│       ├── backtest_ftmo.py       # Skeleton backtest FTMO-Conservative
│       ├── statusline.sh          # [RETAIL] o [FTMO $10k] + métricas
│       ├── session_start.sh       # Profile-aware context injection
│       ├── stop_hook.sh           # Auto-commit journal
│       ├── preprompt_check.sh     # Detecta auto-sabotaje
│       ├── notify.sh              # Notificaciones macOS
│       ├── daily_cron.sh          # Cron 5:30 AM
│       ├── pending_lib.py         # 🆕 CRUD + invalidation + whitelist matrix
│       ├── price_feeds.py         # 🆕 HTTP prices Binance/OKX/TwelveData
│       ├── notify_hub.py          # 🆕 Multi-channel notify (macOS + stubs TG/email)
│       ├── watcher_tick.py        # 🆕 Launchd target — orchestrator hourly
│       ├── watcher_escalate.sh    # 🆕 Dedupe spawn de `claude -p /watch-deep`
│       ├── order_lib.py           # 🆕 build_order + sizing_for_profile + whitelist
│       ├── binance_real_order.py  # 🆕 Stub v1 para --real flag
│       ├── NOTIFY_SETUP.md        # 🆕 Guía manual (launchd/FDA/Telegram/email)
│       └── tests/                 # 🆕 42 pytest tests (pending_lib + price + notify + tick)
│
├── .claude/watcher/               # 🆕 Watcher system
│   ├── whitelist_matrix.yaml      # Reglas cross-profile (editable)
│   ├── status.json                # Último tick (auto-generado)
│   ├── dashboard.md               # Estado legible (auto-generado cada tick)
│   ├── install_agent.sh           # Portable installer (resuelve paths runtime)
│   ├── uninstall_agent.sh         # Cleanup completo
│   ├── launchd/
│   │   └── com.wallytrader.watcher.plist.template  # Template con __APP_EXECUTABLE__
│   └── WallyWatcher.app/          # Bundle macOS (icono 🌭 + Info.plist)
│       └── Contents/
│           ├── Info.plist         # CFBundleDisplayName "Wally Trader Watcher"
│           ├── MacOS/WallyWatcher # Launcher script (config via ~/.config/wallytrader.conf)
│           └── Resources/wally.icns # Dachshund icon (multi-size)
│
├── .opencode/                     # 🆕 Generated by adapters/opencode (committed)
│   ├── commands/                  # 23 translated (CC → OC format)
│   ├── agents/                    # 12 translated
│   ├── skills/ → ../system/skills/ # symlink (format compatible)
│   └── config.json                # MCP servers.tradingview
│
├── scripts/ml_system/             # Capa ML (NLP + XGBoost + LSTM scaffold)
│   └── ...                        # ver sección ML más abajo
│
├── docs/superpowers/              # 🆕 Specs + plans + implementation logs
│   ├── specs/                     # Design docs aprobados
│   └── plans/                     # Implementation plans + logs
│
└── tradingview-mcp/               # MCP server TradingView (submodule externo)

├── scripts/ml_system/             # Capa ML (NLP + XGBoost + DL scaffold)
│   ├── README.md                  # Doc maestra del sistema ML
│   ├── setup.sh                   # Instalador de dependencias
│   ├── requirements.txt           # Deps Python (requests, vader, xgboost, ...)
│   ├── sentiment/                 # NLP Sentiment Aggregator (ACTIVO)
│   │   ├── aggregator.py          # Entrypoint /sentiment
│   │   └── sources.py             # F&G + Reddit + News RSS + Funding
│   ├── supervised/                # XGBoost LONG/SHORT (ACTIVO)
│   │   ├── data_loader.py         # Binance klines API (sin key)
│   │   ├── features.py            # 12 features técnicas
│   │   ├── train.py               # Entrena + calibra + guarda modelo
│   │   ├── predict.py             # Score 0-100 sobre setup actual
│   │   └── model/                 # Modelo .pkl + metrics.json (gitignored)
│   ├── deep/                      # LSTM scaffold (NO ACTIVO)
│   │   ├── README.md              # Precondiciones de activación
│   │   └── lstm_scaffold.py       # Arquitectura lista para activar
│   └── shared/config.py           # Paths y constantes

# Repos externos (no incluidos en este repo):
├── tradingview-mcp/               # MCP server de TradingView (submódulo externo)
└── claude-tradingview-mcp-trading/  # Bot adicional (submódulo externo)

# Memoria persistente (fuera del repo, en ~/.claude/):
~/.claude/projects/<project-path-encoded>/memory/
├── MEMORY.md                      # Índice de memorias
├── user_profile.md                # Perfil del trader
├── trading_strategy.md            # Config de estrategia activa
├── market_regime.md               # Cómo detectar régimen de mercado
├── trading_log.md                 # Historial de trades
├── morning_protocol.md            # Protocolo de 17 fases (versión memoria)
├── entry_rules.md                 # Filtros de entrada + lecciones
├── backtest_findings.md           # Resultados de backtests
├── tradingview_setup.md           # Setup de TV + workarounds
├── market_context_refs.md         # APIs públicas útiles
├── communication_prefs.md         # Preferencias de comunicación
└── user_goals_reality.md          # Expectativas vs realidad
```

---

## 🏆 Estrategia actual: Mean Reversion en Range

**Validada con 100% WR en primer trade** (2026-04-20, +$1.14 sobre $10 cap).

### Parámetros

| Parámetro | Valor |
|---|---|
| Timeframe | 15m |
| Donchian length | 15 velas |
| Bollinger Bands | (20, 2) |
| RSI | 14 (OB 65 / OS 35) |
| ATR | 14 |
| Stop Loss | 1.5 × ATR |
| TP1 (40%) | 2.5 × SL |
| TP2 (40%) | 4.0 × SL |
| TP3 (20%) | 6.0 × SL |
| Leverage | 10x |
| Position sizing | 2% risk del capital |
| Ventana entradas | CR 06:00 – 23:59 |
| Cierre forzado | CR 23:59 (no dormir con posición abierta) |
| Max trades/día | 3 |
| Stop sesión | 2 SLs → para |

### 4 filtros obligatorios (todos deben cumplirse)

**LONG:**
1. Precio toca o cruza Donchian Low (dentro 0.1%)
2. RSI(14) < 35
3. Low de vela toca Bollinger Band inferior
4. Vela cierra verde (close > open)

**SHORT:** mirror (Donchian High, RSI > 65, BB superior, vela roja)

### Estrategia secundaria (si regime cambia)

**Donchian Breakout** cuando close 4H rompe el rango macro (ahora 73,500-78,300) con volumen >2x promedio. Config documentada en `CLAUDE.md`.

---

## 🌅 Uso diario

El sistema opera en **dos profiles aislados**. Al iniciar el día eliges cuál operar — no ambos el mismo día.

### Profile switching (inicio de día)

```bash
cd ~/Documents/trading
claude

# Dentro de Claude Code:
/profile              # ver profile activo + timestamp
/profile retail       # switch a retail (BingX $13.63)
/profile ftmo         # switch a FTMO ($10k demo)
/profile status       # resumen de ambos profiles
```

Statusline refleja el profile activo:
- `[RETAIL] 💰 $13.63 (+$3.63) │ 📊 0/3 │ 🟢 VENT │ 🕐 CR 06:00 │ BTC.P`
- `[FTMO $10k] Equity: $10,000 • Daily: $+0 (0.0%) • EA ✓ 3s • Pos: 0`

---

### 🏠 Workflow RETAIL (BingX $13.63 — el sistema original)

### 1. Preparación nocturna (el día anterior)
- Review del día
- Actualizar `DAILY_TRADING_JOURNAL.md`
- Dormir 7+ horas

### 2. Mañana 5:30 AM CR
Abre Claude Code en este directorio:
```bash
cd ~/Documents/trading
claude

# Si el profile activo es ftmo, switch primero:
/profile retail
```

### 3. Invoca el agente matutino
Dile a Claude: **"análisis matutino"** o **"morning analysis"**, o usa `/morning`.

Con profile=retail, Claude despacha automáticamente el agente `morning-analyst` (retail-only, 17 fases BTC-BingX).

Alternativamente, copia el bloque `PROMPT PRINCIPAL` de `MORNING_PROMPT.md`.

Claude ejecuta 17 fases en ~5-8 minutos:
- Auto-check personal
- Sentiment global (F&G, funding, on-chain)
- Correlaciones (ETH, SPX, DXY)
- Noticias/eventos próximas 6h
- Detección de régimen (range/trend/volatile)
- Selección de estrategia
- Niveles técnicos multi-TF
- Money flow + patrones
- Position sizing con tu capital
- Dibujo en TradingView
- Plan de entrada exacto
- Checklist pre-entry
- Reglas duras
- **VEREDICTO:** ENTRAR LONG / ENTRAR SHORT / ESPERAR / NO OPERAR

### 4. Ejecución disciplinada
- Imprime el checklist pre-entry (sección en `MORNING_PROMPT.md`)
- Tacha cada ítem antes de apretar COMPRAR/VENDER
- Si no puedes tachar los 15 → **no entres**

### 5. Cierre de sesión CR 17:00
```
"Cierre sesión. Resumen PnL + actualiza trading_log.md"
```

### 6. Review semanal (domingos)
```
"Review semana: métricas, patrones, 1 cambio para la próxima"
```

---

### 🏦 Workflow FTMO ($10k demo — multi-asset)

> **Prerequisitos:** `.claude/.env` llenado con credenciales FTMO + `ClaudeBridge.mq5` EA instalado en MT5 (ver [Setup inicial](#-setup-inicial)).

### 1. Inicio de día FTMO

```bash
cd ~/Documents/trading
claude

/profile ftmo
/equity 10247        # actualizar equity si cambió desde ayer (lee tu MT5)
/challenge           # dashboard de progreso (profit acumulado, rules, DD)
```

### 2. Análisis matutino multi-asset

```
/morning
```

Claude despacha `morning-analyst-ftmo` (14 fases). Analiza 6 assets del universo (BTC, ETH, EURUSD, GBPUSD, NAS100, SPX500), detecta régimen por asset, invoca guardian pre-check, selecciona 1 setup A-grade del día.

### 3. Esperar zona + validar

```
/validate            # 7 filtros (vs 4 del retail) + guardian verdict
```

Si todos 7 ✓ y guardian OK, Claude ofrece auto-`/order`:

```
¿Ejecutar orden ahora? Responde YES para encolar al EA, AJUSTAR <param> <val>, o NO.
```

### 4. Encolar orden (YES typed obligatorio)

Claude escribe la orden a `pending_orders.json` + envía a `mt5_commands.json`. Si el EA está vivo (heartbeat < 60s), ejecuta en MT5 automático. Si EA offline → modo manual, tú copias los params a MT5.

### 5. Monitoreo durante el día

```
/trades              # dashboard: posiciones abiertas, pendientes, cerradas hoy, PnL diario
/sync                # fuerza refresh del state desde MT5
```

Guardian bloquea entradas nuevas si:
- Daily PnL llegará a ≤ -3% con SL → **BLOCK_HARD** o **BLOCK_SIZE** con reducción
- 2 SLs consecutivos hoy → **BLOCK_HARD**
- 2 trades ya ejecutados → **BLOCK_HARD** (cap diario)

### 6. Force exit 16:00 CR

FTMO no permite overnight (y el sistema lo refuerza). A las 16:00 CR cierra todo.

### 7. Cierre de día

```
/journal
```

Auto-ingesta `closed_today` del EA, actualiza `trading_log.md` de FTMO, llama a `guardian --action equity-update` con el nuevo equity, marca pending expired, resume métricas del día.

### 8. Validación antes de challenge pago

**Paper trading obligatorio** en FTMO Free Trial 14 días. Criterios para pagar challenge $93.43:
- WR ≥ 55% sobre 10+ trades paper
- 0 daily breaches simulados
- 0 overrides del guardian
- Max DD ≤ 5%

Detalles en `docs/superpowers/plans/2026-04-22-ftmo-profile-IMPLEMENTATION-LOG.md`.

---

## 🔔 Watcher & Set-and-Forget Orders (v1)

Sistema autónomo para programar entries matutinos y que el sistema los vigile mientras trabajas en otras cosas. Funciona en los 4 profiles (`retail`, `retail-bingx`, `ftmo`, `fotmarkets`) — virtual-only en v1 (notifica cuando disparar, tú ejecutas manual).

### Workflow típico

**CR 06:00 — morning:**
```bash
/morning
# Claude propone: BTC LONG @ 77521, SL 77101, TP 78571, invalid 76900
/order BTCUSDT.P LONG 77521 sl=77101 tp=78571 ttl=6h invalid=76900
# → YES para confirmar → persiste en pending_orders.json
```

**Te vas a trabajar** (codear, meeting, gym).

**Durante el día (autónomo):**

| Tiempo | Comportamiento del watcher |
|---|---|
| Cada 1h (launchd) | `watcher_tick.py` lee pending, pulls precio Binance, evalúa invalidaciones |
| Precio >0.3% del entry | Heartbeat silencioso + actualiza `next_recheck_mx` en el JSON |
| Precio ≤0.3% del entry | Spawn `claude -p /watch-deep <id>` headless con MCP TV completo |
| `/watch-deep` | Valida 4 filtros (RSI, BB, Donchian, cierre vela). Si 4/4 → status `triggered_go` |
| Trigger GO | **🚨 macOS notif CRITICAL** + dibujo entry/SL/TPs en TV |
| TTL / precio rompe invalid / 2 SLs / force_exit | Auto-cancel + macOS notif WARN |

**Llega notif CRITICAL → ejecutas manualmente en Binance/MT5:**
```bash
/filled ord_20260424_104800_retail_btcusdtp_long
# Status → filled, append to trading_log, notify INFO
```

### Comandos clave

| Comando | Descripción |
|---|---|
| `/order <asset> <side> <entry> sl=X tp=Y ttl=Nh invalid=Z` | Encola orden virtual en el profile activo |
| `/pending` | Lista pendings del profile actual (`all` para cross-profile) |
| `/pending show <id>` | Detalle + status history |
| `/pending cancel <id>` | Marca `canceled_manual` (terminal) |
| `/pending modify <id> tp1=X` | Edit `tp1/tp2/tp3/ttl_hours/invalidation_price` |
| `/watch` | Fuerza un tick manual (no espera al launchd) |
| `/filled <id> [price=X]` | Confirma fill tras ejecutar manual en exchange/MT5 |
| `/status` | Incluye sección watcher con último tick + pending counts |

### Invalidaciones automáticas

El watcher auto-cancela cuando:
1. **TTL expired** — pasó `expires_at` sin tocar entry
2. **Precio rompe `invalidation_price`** — tesis muerta (ej: LONG 77521 con invalid 76900 → si close 4H <76900, cancela)
3. **2 SLs hoy en el profile** — regla STOP día hit, todas las pending del día mueren
4. **Force exit CR 23:59 (retail) / 16:00 (ftmo) / 10:55 (fotmarkets)** — no dormir con trade abierto

### Matriz whitelist cross-profile

Evita doble exposición direccional al mismo underlying entre profiles. Ejemplos:

| Escenario | Resultado |
|---|---|
| `retail BTCUSDT.P LONG` + `fotmarkets BTCUSD LONG` | ❌ La 2ª queda `suspended_policy` (mismo BTC, misma dirección) |
| `retail BTCUSDT.P LONG` + `fotmarkets EURUSD SHORT` | ✅ Ambas activas (assets distintos) |
| `retail BTCUSDT.P LONG` + `ftmo BTCUSD SHORT` | ⚠️ Hedge permitido con warning |
| `ftmo NAS100 LONG` + `fotmarkets NAS100 LONG` | ❌ 2 brokers MT5 = doble real-ish |

Reglas en `.claude/watcher/whitelist_matrix.yaml` (editable).

### Arquitectura técnica

```
USER: /order → pending_orders.json (profile-scoped)
                  │
                  ▼
          launchd (cada 1h)
                  │
                  ▼
         watcher_tick.py
            (stateless)
         ├─ load_all_pendings()
         ├─ apply_whitelist_matrix()
         ├─ price_for()        # HTTP Binance/OKX/TwelveData
         ├─ evaluate_invalidation()  # TTL/price/stopday/force_exit
         └─ distance check:
            ├─ >0.3% → heartbeat + next_recheck
            └─ ≤0.3% → spawn claude -p /watch-deep
                         │
                         ▼
                Claude headless (120s timeout)
                ├─ chart_set_symbol + MCP read
                ├─ Evalúa 4 filtros
                └─ notify_hub.notify()
                         │
                         ▼
              ┌──────────┴──────────┐
              ▼                     ▼
          macOS notif            dashboard.md + log
          (Glass/Submarine)      (auditoría)
```

### Instalación launchd (opcional — sistema funciona sin él vía `/watch` manual)

**Requisito:** brew python 3.12+ (evita el shim de Xcode en `/usr/bin/python3`).

```bash
# Si no tienes brew python:
brew install python@3.13

# Instalador portable — resuelve paths a runtime, funciona en cualquier Mac/usuario
bash .claude/watcher/install_agent.sh
```

El instalador:
1. Detecta repo desde su propia ubicación (puedes clonar en `~/code/`, `/opt/`, donde sea)
2. Busca Python 3.12+ disponible (prefiere 3.13)
3. Instala deps Python si faltan
4. Copia `.claude/watcher/WallyWatcher.app` a `~/.local/Applications/`
5. Escribe config runtime a `~/.config/wallytrader.conf` (REPO_ROOT + PYTHON)
6. Renderiza plist launchd con paths absolutos a `~/Library/LaunchAgents/`
7. Registra `.app` con LaunchServices (icono dachshund en Background Items)
8. `launchctl load`

```bash
# Verificar
launchctl list | grep wallytrader
launchctl start com.wallytrader.watcher
cat /tmp/wally_watcher.out
cat .claude/watcher/dashboard.md

# Desinstalar
bash .claude/watcher/uninstall_agent.sh
```

**macOS Full Disk Access:** `~/Documents` está protegido por TCC. Concede FDA al binario usado por launchd (`/opt/homebrew/bin/python3.13` o el que detectó el installer) en **System Settings → Privacy & Security → Full Disk Access**.

**Background Items:** tras instalar, *System Settings → General → Ítems de inicio y extensiones* muestra **"Wally Trader Watcher"** con icono 🌭 dachshund en vez de "bash".

### Rollback

```bash
bash .claude/watcher/uninstall_agent.sh
# Remueve plist + bundle + config. Sistema sigue funcional vía /watch manual.
```

### Stubs en v1 (activables después)

- `--real` flag en `/order` (para retail → Binance API real order): stub, imprime "not implemented"
- Telegram bot notifications: no-op silencioso si no hay `TELEGRAM_BOT_TOKEN` en `.claude/.env`
- Email via Resend: no-op silencioso si no hay `RESEND_API_KEY`

Docs completos para activar cada uno en `.claude/scripts/NOTIFY_SETUP.md`.

**Spec + plan:**
- `docs/superpowers/specs/2026-04-24-watcher-pending-orders-design.md`
- `docs/superpowers/plans/2026-04-24-watcher-pending-orders.md`

---

## 🤖 Capa ML (Sentiment + XGBoost + LSTM scaffold)

Sistema complementario en `scripts/ml_system/` que NO reemplaza las reglas mecánicas. Se usa como **5° filtro** cuando los 4 filtros técnicos ya están alineados.

### Componentes

| Componente | Estado | Qué hace |
|---|---|---|
| **NLP Sentiment** | ✅ Activo | F&G 35% + News VADER 30% + Reddit VADER 20% + Funding contrarian 15% → score 0-100 |
| **XGBoost Supervisado** | ✅ Activo | Predice probabilidad TP-first (LONG y SHORT) usando 12 features técnicas, calibrado con Platt |
| **LSTM Deep Learning** | ⏸️ Scaffold | No activo hasta cumplir precondiciones (capital ≥$500, n≥100 trades, etc.) |

### Setup inicial (primera vez)

```bash
cd scripts/ml_system
./setup.sh                              # instala requests, vader, xgboost, pandas, sklearn
brew install libomp                     # runtime para xgboost en Mac
python3 supervised/train.py --days 365  # entrena modelo (descarga ~100MB de Binance)
```

### Uso diario

```bash
# Sentiment (al iniciar sesión matutina)
python3 scripts/ml_system/sentiment/aggregator.py
# o slash command
/sentiment

# ML score sobre estado actual (cuando 4 filtros técnicos estén alineados)
python3 scripts/ml_system/supervised/predict.py --auto
# o slash command
/ml

# Re-entrenar (cada 2-4 semanas o si regime shift)
/ml-train
```

### Cómo interpretar scores

**Sentiment:**
| Score | Label | Acción |
|---|---|---|
| 0-19 | 🔴 EXTREME FEAR | Contrarian bullish — setups LONG tienen edge |
| 20-34 | 🟠 FEAR | Ligero bullish — cuidado con shorts |
| 35-69 | 🟡 NEUTRAL | Operar técnico puro, sin sesgo |
| 70-84 | 🟢 GREED | Ligero bearish — cuidado con longs tardíos |
| 85-100 | 🔴 EXTREME GREED | Contrarian bearish — setups SHORT tienen edge |

**ML Score (probabilidad TP-first):**
| Score | Acción |
|---|---|
| <35 | 🔴 BAJO — pasar o size 50% aunque técnico sea GO |
| 35-55 | 🟡 NEUTRAL — decisión por técnico puro |
| 55-70 | 🟢 FAVORABLE — modelo confirma el setup |
| >70 | 🟢 ALTO — edge histórico alto |

### Reality check honest-first

- AUC típico en crypto 15m: **0.52-0.62**. Más es sospechoso de overfitting.
- El modelo NO encuentra setups — solo confirma/cuestiona los que tu sistema técnico ya detectó.
- `/ml-train` corre automáticamente un reality check y warna si AUC >0.65 (posible leakage).
- Con n<20 trades reales, la varianza supera la señal. Trata el score ML como un voto más.

---

## 📋 Paso a paso diario (workflow óptimo)

Un día operativo completo usando TODO el stack (técnico + sentiment + ML). Ventana **CR 06:00 – 23:59** (cripto 24/7, pero no dormir con trade abierto).

### 🌅 CR 05:30 — Despertar

```bash
cd ~/Documents/trading
claude
```

El status line muestra: `💰 $13.63 (+$3.63) │ 📊 0/3 │ 🟢 VENT │ 🕐 CR 05:30 │ BTC.P`

### 🌄 CR 05:45-06:00 — Check personal

- [ ] Dormí 6+ horas
- [ ] Desayuné algo
- [ ] Estoy mentalmente claro (no tilt, no FOMO, no revenge)
- [ ] No estoy "recuperando" pérdida de ayer

Si alguno falla → **NO operar hoy**.

### ☀️ CR 06:00 — Análisis matutino (17 fases + ML)

```
/morning
```

El agente `morning-analyst` ejecuta el protocolo completo en 5-8 min. Al finalizar, complementa con:

```
/sentiment          # score NLP agregado para calibrar sesgo del día
/regime             # confirmación rápida de régimen (RANGE vs TRENDING vs VOLATILE)
/chart              # dibuja niveles actualizados en TradingView
```

**Veredicto posible:** `ENTRAR LONG` / `ENTRAR SHORT` / `ESPERAR` / `NO OPERAR`.

### 🎯 CR 06:00 – 23:30 — Monitoreo de setup

Durante la ventana, espera a que BTC toque una zona operativa (Donchian High/Low ±0.1%). Puedes dejar alerta activa:

```
/alert 4 filtros
```

**Cuando el setup 4/4 aparezca:**

```
/validate           # confirma los 4 filtros técnicos (GO/NO-GO)
/ml                 # 5° filtro: probabilidad TP-first según modelo
/risk               # position sizing según regla 2%
```

**Decisión matriz:**

| Técnico 4/4 | ML Score | Sentiment | Acción |
|---|---|---|---|
| ✅ GO | >55 | Alineado | **ENTRAR** con size normal |
| ✅ GO | 40-55 | Alineado o neutral | **ENTRAR** con size 75% |
| ✅ GO | <40 | — | **REDUCIR size a 50%** o esperar siguiente setup |
| ✅ GO | — | Contrario extremo (setup LONG + sentiment 90) | **PASAR** — no pelees el sentiment extremo |
| ❌ 3/4 o menos | — | — | **NO ENTRAR** — nunca forzar |

### 💥 Al entrar — Disciplina mecánica

1. Loggear **ANTES** de pulsar "Abrir" en BingX:
   - Hora CR exacta
   - Precio de entry
   - Los 4 filtros con checkmark uno por uno
   - SL planeado ($)
   - TP1/TP2/TP3 planeados ($)
   - Size calculado (en USDT)
   - Score ML y Sentiment del momento

2. Abrir posición:
   - SL colocado inmediatamente (nunca "después")
   - TPs escalonados: 40% TP1, 40% TP2, 20% TP3
   - TP1 hit → SL a breakeven automático

3. **NO TOCAR** una vez abierto. La posición ejecuta sola.

### ⏳ Durante el trade — Paciencia activa

- **NUNCA mover SL en contra.** Es la regla más violada y más cara.
- Si el precio se aleja del SL sin llegar a TP1 → puede pasar. Respira.
- Si necesitas cerrar manual (hora CR 23:30, evento macro imprevisto, pendiente personal) → cerrar a mercado sin mover SL.

### 🌙 CR 23:30 — Alarma de cierre próximo

Si el trade sigue abierto a las 23:30 CR:
- Evalúa si hay chance real de tocar TP antes de 23:59
- Si no → cerrar a mercado

### 🔚 CR 23:59 — Force exit

**Cerrar toda posición abierta. Sin excepción.** Cripto es 24/7; tu sueño no. Un wick de madrugada con leverage 10x puede liquidar la cuenta mientras duermes.

### 📝 Al cerrar la sesión (o al cerrar trade)

```
/journal
```

El agente `journal-keeper` actualiza:
- `trading_log.md` (memoria persistente)
- `DAILY_TRADING_JOURNAL.md` (repo)
- Métricas acumuladas (WR, PnL, capital)
- Disciplina (reglas cumplidas/violadas)
- 1 cosa a cambiar mañana

### 🛏️ Antes de dormir

- [ ] Trade del día cerrado
- [ ] Journal actualizado
- [ ] Git push hecho
- [ ] SL/alarmas activas canceladas
- [ ] Capital actual anotado mentalmente (sin obsesionarse)

### 📅 Domingo — Review semanal

```
/review semanal
```

Métricas: WR, PF, DD, avg win/loss. Compara vs target (WR≥60%, PF≥1.8, DD≤15%). Identifica el patrón de la semana. Decide 1 ajuste para la próxima.

### 🗓️ Cada 2-4 semanas — Re-entrenar ML

```
/ml-train --days 365
```

Recalibra el modelo con data reciente para adaptarse al régimen. Verifica AUC en `supervised/model/metrics.json`.

---

## 🔧 Setup inicial

### Requisitos

**Core (ambos profiles):**
- **Claude Code** (Anthropic CLI) — primario, mejor soporte
- **TradingView Desktop** (plan Basic mínimo) + MCP conectado
- **Python 3.9+** con PyYAML (`pip3 install pyyaml`)
- **Homebrew** (macOS) para `libomp` (XGBoost) y `fswatch` (opcional)

**Retail profile (BingX):**
- **BingX Futures** con BTCUSDT.P activado
- Capital real (actual $13.63)

**FTMO profile (opcional, para challenge):**
- **Cuenta FTMO Demo** (gratis 14 días Free Trial) o challenge $93.43
- **MT5 Desktop for Mac** instalado y loggeado al menos una vez
- Credenciales FTMO (login, password, server FTMO-Demo)

**Multi-CLI (opcional, hedge):**
- **OpenCode** — `curl -fsSL https://opencode.ai/install | bash` (free)
- **Codex** — OpenAI API key + `npm install -g @openai/codex` (adapter UNTESTED)

### Instalación

```bash
# 1. Clonar este repo
git clone git@github.com:sasasamaes/trading.git
cd trading

# 2. Instalar TradingView MCP (ver "prompt listo para Claude Code" abajo)
#    Luego abrir TradingView Desktop con --remote-debugging-port=9222

# 3. Abrir Claude Code
claude

# 4. Instalar indicador Pine en TV (manual):
#    Pine Editor → copiar MEAN_REVERSION_INDICATOR.pine → guardar "MR Signals" → añadir al chart

# 5. Instalar adapter Claude Code (sincroniza symlinks .claude/ → system/)
bash adapters/claude-code/install.sh

# 6. Verificar profile default (debe ser "retail")
bash .claude/scripts/profile.sh show
# → retail | <iso>

# 7. (Opcional) Setup ML
cd scripts/ml_system
./setup.sh
brew install libomp
python3 supervised/train.py --days 365
cd ../..
```

### Setup FTMO profile (opcional)

Si quieres operar el challenge FTMO además del retail:

```bash
# 1. Llenar credenciales FTMO en .env (gitignored)
cp .claude/.env.example .claude/.env
# Editar .claude/.env con tu editor:
#   FTMO_LOGIN=<tu login>
#   FTMO_PASSWORD=<tu password>
#   FTMO_READONLY_PASSWORD=<tu ro password>
#   FTMO_SERVER=FTMO-Demo

# 2. Abrir MT5 al menos una vez (login con cuenta FTMO-Demo)
open -a "MetaTrader 5"
# Login → cerrar

# 3. Instalar el EA ClaudeBridge.mq5 en MT5
bash .claude/profiles/ftmo/mt5_ea/install.sh
# Auto-detecta bottle path de Mac, copia EA, crea symlinks a memory/

# 4. En MT5: habilitar algo-trading + drag ClaudeBridge al chart BTCUSD
#    Tools → Options → Expert Advisors → ✅ Allow algorithmic trading
#    Navigator (Ctrl+N) → Expert Advisors → F5 → drag ClaudeBridge a chart
#    Diálogo → ✅ Allow Automated Trading → OK
#    Experts tab (Ctrl+T) debe mostrar: "ClaudeBridge EA v1.00 starting magic=77777"

# 5. Verificar heartbeat
cat .claude/profiles/ftmo/memory/mt5_state.json
# Debe tener last_update reciente
bash .claude/scripts/profile.sh set ftmo
bash .claude/scripts/statusline.sh
# [FTMO $10k] ... EA ✓ Xs

# 6. Primer test con 0.01 lots
/profile ftmo
/order BTCUSD BUY 77500 sl=77400 tp=77600 lots=0.01
# Confirmar YES → EA ejecuta → /trades muestra
```

Guía completa paso a paso: `.claude/profiles/ftmo/mt5_ea/README.md`.

### Setup OpenCode (opcional, hedge)

```bash
# 1. Instalar OpenCode
curl -fsSL https://opencode.ai/install | bash

# 2. Generar .opencode/ desde system/ + instalar git pre-commit hook
bash adapters/opencode/install.sh

# 3. (Opcional) Real-time sync durante edición activa
brew install fswatch
bash adapters/opencode/watch.sh   # en terminal aparte

# 4. Probar
cd ~/Documents/trading
opencode
# → dentro de OpenCode: /status
```

Detalles en `adapters/opencode/README.md`.

### Instalar TradingView MCP (prompt listo para Claude Code)

Copia este prompt tal cual a Claude Code (o a Claude Desktop) en una sesión nueva. Claude ejecuta paso por paso y te reporta cada etapa:

```text
Quiero conectar mi app de TradingView a Claude Code usando el MCP de @Tradesdontlie.
Repo oficial: https://github.com/tradesdontlie/tradingview-mcp

Por favor haz TODO esto paso por paso, reportándome cada etapa. No avances al
siguiente paso si uno falla — explícame el error y cómo resolverlo.

1. VERIFICAR PRERREQUISITOS:
   - Corre "node --version" — tengo que tener Node.js 18 o mayor. Si me falta o es
     muy viejo, dime exactamente cómo instalarlo para mi sistema operativo.
   - Corre "git --version" — si no tengo Git, dime cómo instalarlo.
   - Pregúntame si ya tengo TradingView Desktop instalado. Si no, mándame el link
     oficial: https://www.tradingview.com/desktop/

2. CLONAR EL REPO:
   Clona el repositorio en mi carpeta home:
   git clone https://github.com/tradesdontlie/tradingview-mcp.git ~/tradingview-mcp

3. INSTALAR DEPENDENCIAS:
   Entra a la carpeta y corre la instalación:
   cd ~/tradingview-mcp && npm install

4. LEER EL README:
   Lee el README.md del repo para identificar:
   - El comando exacto para iniciar el servidor MCP (puede ser "node src/server.js"
     o algo distinto según la versión).
   - El flag de debug para lanzar TradingView (suele ser --remote-debugging-port=9222).
   - Si hay scripts de lanzamiento en la carpeta "scripts/" que yo deba usar directo.

5. CONFIGURAR EL MCP EN CLAUDE CODE:
   Edita mi archivo de configuración de MCPs. Ubicación según mi OS:
   - macOS / Linux: ~/.claude/.mcp.json
   - Windows: %USERPROFILE%\.claude\.mcp.json

   Si el archivo no existe, créalo. Si ya existe con otros MCPs, NO los sobrescribas
   — solo agrega el de tradingview dentro de "mcpServers". El bloque a insertar
   (ajusta la ruta absoluta con mi carpeta real):

   {
     "mcpServers": {
       "tradingview": {
         "command": "node",
         "args": ["/ruta/absoluta/a/tradingview-mcp/src/server.js"]
       }
     }
   }

6. LANZAR TRADINGVIEW CON DEBUG PORT:
   Explícame cómo cerrar completamente TradingView y volverlo a abrir con el flag
   de debug. Dame el comando exacto para mi sistema operativo. Si el repo incluye
   un script en scripts/ (por ejemplo launch_tv_debug_mac.sh), úsalo y dime cómo
   correrlo.

7. DECIRME QUÉ HAGO AHORA:
   Resume en 3 pasos finales lo que me toca hacer:
     (a) reiniciar Claude Code
     (b) abrir una conversación nueva
     (c) correr el primer prompt de verificación
   Dame el prompt exacto para el paso (c).

Objetivo final: que cuando abra Claude Code y escriba "Corre tv_health_check",
me responda cdp_connected: true. Ahí sabemos que jaló.
```

**Qué hace el prompt:** verifica Node/Git, clona el MCP al home, instala deps, lee el README del upstream, edita `~/.claude/.mcp.json` sin borrar otros servers, lanza TV con `--remote-debugging-port=9222`, y termina con un health check. Objetivo: `tv_health_check` devuelve `cdp_connected: true`.

**Alternativa manual** (si prefieres no usar el prompt): seguir `tradingview-mcp/README.md` del submodule y agregar el server con `claude mcp add tradingview node /absolute/path/to/tradingview-mcp/src/server.js`.

### Instalar Notion MCP — dual-write de journal a Notion (prompt listo para Claude Code)

Opcional pero recomendado si quieres que cada trade se loggee **tanto en `.md` local como en Notion**. El sistema detecta la config automáticamente — si no configurás Notion, sigue funcionando con solo `.md`.

Copia este prompt tal cual a Claude Code en una sesión nueva. Claude ejecuta paso por paso, crea las DBs via MCP, y te reporta cada etapa:

```text
Quiero conectar Notion MCP al sistema de trading para dual-write de journal
(retail + FTMO). Repo: este mismo (~/Documents/trading). Docs de referencia:
docs/NOTION_SETUP.md del repo.

Por favor haz TODO esto paso por paso, reportándome cada etapa. No avances al
siguiente paso si uno falla — explícame el error y cómo resolverlo.

1. VERIFICAR PRERREQUISITOS:
   - Verifica que estamos en la raíz del repo: `pwd` debe ser ~/Documents/trading
     (o donde clonaste). Si no, `cd` ahí primero.
   - Verifica que tengo cuenta de Notion activa. Preguntame si no lo sabes.
   - Verifica Node.js 18+: `node --version`. Si falta, dime cómo instalarlo.

2. INSTALAR EL NOTION MCP OFICIAL (OAuth):
   Corre: `claude mcp add notion https://mcp.notion.com/mcp`
   Esto va a abrir OAuth flow en el browser:
     - Te voy a pedir login a Notion
     - Autorizar acceso al workspace que usaré para las DBs
   Espera a que complete. Luego verifica con:
   `claude mcp list | grep notion`
   Debe mostrar: "notion: https://mcp.notion.com/mcp - ✓ Connected"
   Si no conecta, retry una vez. Si sigue fallando, diagnostica el error.

3. CREAR LAS 2 NOTION DBs VIA MCP:
   Ahora que el MCP está conectado, usá las tools mcp__notion__* para crear
   2 databases en mi workspace. Primero preguntame en qué página quiero que
   vivan (raíz del workspace o una página específica). Luego:

   DB 1: "Trades Retail" con schema (exacto):
     - Name (Title)
     - Date (Date)
     - Time CR (Text)
     - Asset (Select: BTCUSDT.P)
     - Direction (Select: LONG, SHORT)
     - Entry (Number)
     - SL (Number)
     - TP1 (Number)
     - TP2 (Number)
     - TP3 (Number)
     - Size (BTC) (Number)
     - Leverage (Number)
     - Result (Select: TP1, TP2, TP3, SL, BE, partial, open)
     - PnL $ (Number)
     - PnL % (Number)
     - R multiple (Number)
     - Filters passed (Text)
     - ML score (Number)
     - Sentiment (Number)
     - Notes (Text)

   DB 2: "Trades FTMO" con schema (exacto):
     - Name (Title)
     - Date (Date)
     - Time CR (Text)
     - Asset (Select: BTCUSD, ETHUSD, EURUSD, GBPUSD, NAS100, SPX500)
     - Direction (Select: LONG, SHORT)
     - Entry (Number)
     - SL (Number)
     - TP1 (Number)
     - TP2 (Number)
     - Lots (Number)
     - Magic (Number)
     - Ticket MT5 (Number)
     - Status (Select: queued, sent_to_ea, filled, expired, canceled, manual_pending, closed)
     - Result (Select: TP1, TP2, SL, BE, partial, open, N/A)
     - PnL $ (Number)
     - PnL % (Number)
     - R multiple (Number)
     - Filters passed (Text)
     - Guardian verdict (Select: OK, OK_WITH_WARN, BLOCK_SIZE, BLOCK_HARD, override)
     - Equity pre (Number)
     - Equity post (Number)
     - Notes (Text)

   Reporta los 2 database_id generados (hex 32 chars cada uno).

4. LLENAR .env CON LOS DB IDs:
   - Si no existe .claude/.env, crealo copiando de .env.example:
     `cp .claude/.env.example .claude/.env`
   - Edita .claude/.env y agrega/actualiza estas dos líneas con los IDs del paso 3:
     NOTION_RETAIL_DB_ID=<id_db_retail>
     NOTION_FTMO_DB_ID=<id_db_ftmo>
   - Verificá que .env NO está en git: `git status --short` — .env no debe aparecer.

5. VERIFICAR DETECCIÓN:
   Corre: `bash .claude/scripts/statusline.sh`
   El output debe terminar con "• 📝 Notion ✓". Si no, revisá paso 4 y relee.

6. TEST DE DUAL-WRITE:
   - Cambia a profile retail: `bash .claude/scripts/profile.sh set retail`
   - Simula un trade cerrado: invoca /journal y dime qué parámetros te pido
     para crear una entrada de prueba (trade #TEST con capital unchanged).
   - Al ejecutar /journal, deberías:
     (a) Append al .md local
     (b) Crear una row nueva en Notion DB Trades Retail
     Verificá visualmente ambos. Si falla Notion, reporta el error exacto
     y dejá el .md local intacto.
   - Al terminar exitoso, borra el row de prueba de Notion (fue solo test)
     y revierte el append del .md.

7. DECIRME QUÉ HAGO AHORA:
   Resume en 3 pasos:
     (a) recarga/reinicia Claude Code si el statusline no mostraba el tag
     (b) uso normal: cada /journal, /order, /sync, /trades, /challenge ahora
         hace dual-write transparente (sin pedirme nada extra)
     (c) si quiero desactivar Notion temporalmente: comentar las líneas en
         .env o borrarlas

Objetivo final: que cuando corra /journal en modo retail con un trade real,
aparezca un row nuevo en la DB "Trades Retail" en mi Notion, y el .md local
también tenga el append. Ahí sabemos que funciona.
```

**Qué hace el prompt:** conecta Notion MCP via OAuth, crea las 2 DBs (retail + ftmo) directamente desde Claude con el schema correcto (sin copiar/pegar manual), actualiza `.env` con los IDs, verifica detección via statusline, y prueba end-to-end con un trade dummy. Todo lo que no requiere UI del browser, lo automatiza.

**Alternativa manual** (si prefieres hacer las DBs a mano): seguir `docs/NOTION_SETUP.md` paso a paso — incluye schemas con checkboxes y troubleshooting.

### Memoria persistente

Claude mantendrá memoria de tu perfil en `~/.claude/projects/.../memory/`.
**Importante:** esa carpeta NO está en este repo (excluida por `.gitignore`).
Si cambias de máquina, deberás regenerar la memoria o copiarla manualmente.

---

## 📊 Progreso y objetivos

### Ruta planificada

| Meta | Capital | Días estimados | Estado |
|---|---|---|---|
| Primer trade ganador | $10 → $11.14 | 1 | ✅ **Completado** (2026-04-20) |
| Segundo trade ganador | $11.14 → $12.23 | 1 | ✅ **Completado** (2026-04-21) |
| Tercer trade ganador | $11.82 → $13.63 | 1 | ✅ **Completado** (2026-04-22, +15.32%) |
| Acumular 25 trades estadísticos | → $15-20 | ~15-20 | 🔄 En progreso (3/25) |
| WR validado ≥ 60% sobre 25+ trades | — | ~20 | ⏳ Pendiente |
| $20 por trade | $161 cap | ~26 | ⏳ Pendiente |
| $50/día promedio | $325 cap | ~70 | ⏳ Pendiente |
| **$100/día promedio** | **$650 cap** | **~85** | ⏳ Pendiente |
| FTMO $10k fundeado | — | ~60 post-validación | ⏳ Pendiente |

### Métricas objetivo mínimo (después de 25 trades)

- Win Rate ≥ 60%
- Profit Factor ≥ 1.8
- Max Drawdown ≤ 15%
- Days operated ≥ 15

---

## 🧠 Principios del sistema

### 1. Régimen dicta estrategia
Una estrategia no es universal. **Mean Reversion** funciona en RANGE. **Donchian Breakout** funciona en TRENDING. Cada día detectar el régimen antes de elegir.

### 2. 4 filtros obligatorios
Nunca entrar con 3/4 filtros. La disciplina es el edge.

### 3. Position sizing 2% fijo
Nunca arriesgar más del 2% del capital por trade. Matemáticamente imposible quebrar con 60%+ WR.

### 4. Stop de sesión duro
2 SLs consecutivos → para el día. No hay "recuperación".

### 5. Journal obligatorio
Cada trade se documenta. Sin journal no hay mejora.

### 6. Disciplina > Estrategia
El 90% de retail pierde por emocional, no por análisis. Tu mayor enemigo eres tú.

---

## 📚 Archivos clave y para qué sirven

### `CLAUDE.md`
Guía principal que Claude lee al iniciar sesión. Contiene perfil del trader, estrategia activa, reglas, niveles técnicos vigentes, APIs útiles.

### `MORNING_PROMPT.md` ⭐
**El archivo más importante.** Contiene:
- Prompt completo de 17 fases para copy-paste cada mañana
- Checklist físico imprimible
- Templates de journal diario y review semanal
- Quick commands
- Mantras del día

### `MEAN_REVERSION_INDICATOR.pine`
Código Pine Script del indicador con los 4 filtros automatizados. Se pega en TradingView → Pine Editor.

Incluye:
- Donchian(15) channel
- Bollinger Bands(20, 2)
- RSI(14) OB/OS
- ATR(14) para SL/TP dinámicos
- Flechas LONG/SHORT cuando 4/4 filtros alinean
- Tabla top-right con status de filtros en tiempo real
- Alertas configurables

### `DAILY_TRADING_JOURNAL.md`
Template para registrar cada trade con todos sus datos. Obligatorio.

### `RISK_CALCULATOR.md`
Fórmulas de position sizing, cálculo de SL/TP basado en capital.

### `.claude/agents/` — 7 Agentes especializados

Claude detectará automáticamente cuál invocar según tu pregunta:

| Agente | Se activa cuando preguntas... |
|---|---|
| **morning-analyst** | "análisis matutino", "morning analysis", "empezar sesión" |
| **trade-validator** | "¿entro?", "valida entry", "4 filtros alineados?" |
| **regime-detector** | "¿qué régimen?", "¿range o trend?", "qué estrategia uso" |
| **chart-drafter** | "dibuja niveles", "actualiza chart", "limpia y redibuja" |
| **risk-manager** | "cuánto abro", "size del trade", "position sizing" |
| **journal-keeper** | "cierro día", "journal", "log trade", "review semana" |
| **backtest-runner** | "backtest X", "probar esta config", "grid search" |
| **technical-analyst** | "TA profundo", "smart money", "armónico", "elliot", "fibonacci" |
| **signal-validator** | "valida señal", "[comunidad] dice...", "/signal Short XLM" |

### `system/commands/` — 23 Slash commands (profile-aware)

Atajos rápidos. La mayoría se adaptan al profile activo automáticamente.

**Dual-profile (nuevos):**

| Comando | Acción |
|---|---|
| `/profile` | Ver/cambiar profile activo (retail/ftmo) |
| `/status` | Estado profile-aware (retail: cap/régimen; ftmo: equity/DD/EA) |

**FTMO-only:**

| Comando | Acción |
|---|---|
| `/equity <valor>` | Actualizar equity FTMO desde MT5 |
| `/challenge` | Dashboard progreso challenge (profit, rules, best day ratio) |
| `/order` | Encolar orden al EA (con YES typed obligatorio) |
| `/trades` | Dashboard MT5 (posiciones, pendientes, closed today) |
| `/sync` | Reconciliar pending_orders.json ↔ mt5_state.json |

**Trading core (profile-aware):**

| Comando | Acción |
|---|---|
| `/morning` | Despacha morning-analyst (retail 17 fases) o morning-analyst-ftmo (14 fases multi-asset) |
| `/validate` | Retail: 4 filtros + ML opcional. FTMO: 7 filtros + guardian check_entry |
| `/regime` | Detecta régimen rápido (RANGE/TRENDING/VOLATILE) |
| `/risk` | Position sizing — 2% retail, 0.5% FTMO (via guardian) |
| `/journal` | Retail: tradicional. FTMO: auto-ingest closed_today del EA |
| `/chart` | Limpia y redibuja niveles en TV |
| `/backtest` | Ejecuta backtest/grid search |
| `/review` | Review semanal con métricas |
| `/levels` | Niveles técnicos actuales |
| `/alert` | Configura alerta custom |

**Análisis técnico avanzado:**

| Comando | Acción |
|---|---|
| `/ta` | Análisis técnico avanzado (ICT, armónicos, chartismo, Elliott, Fibonacci) |
| `/signal` | Valida señal externa de comunidad (GO/NO-GO) |
| `/neptune` | Lee outputs de indicadores Neptune (Bangchan10) |

**Capa ML:**

| Comando | Acción |
|---|---|
| `/sentiment` | NLP Sentiment Aggregator (F&G + News + Reddit + Funding) → score 0-100 |
| `/ml` | ML score del setup actual (XGBoost, probabilidad TP-first) |
| `/ml-train` | Re-entrena el modelo XGBoost con histórico Binance |

### `.claude/skills/` — 8 Skills custom

**Análisis técnico avanzado (metodologías):**
- **smart-money-ict** — Order Blocks, Fair Value Gaps, Liquidity, BoS/ChoCh, Premium/Discount
- **harmonic-patterns** — Gartley, Bat, Butterfly, Crab, Shark, Cypher con Fibonacci
- **classic-chartism** — H&S, triangles, flags, wedges, double/triple tops
- **elliott-waves** — 5-impulsivo + 3-correctivo con Fibonacci targets
- **fibonacci-tools** — Retracements, extensions, time zones, confluencia MTF

**Indicadores técnicos:**
- **stochastic-oscillator** — Full/Slow/Stoch RSI, crossovers, divergencias
- **bollinger-bands-advanced** — Squeeze, walking band, %B, bandwidth, TTM
- **adx-trend-strength** — ADX, +DI/-DI para fuerza y dirección de tendencia
- **divergence-analysis** — Regular/hidden, bull/bear, clase A/B/C con RSI/MACD/OBV
- **trendlines-sr** — Soportes, resistencias, trendlines, canales, breakouts vs fakeouts

**Indicadores de comunidad:**
- **neptune-indicators** — Neptune® Signals/Oscillator/SMC/Money Flow/Pivots (Bangchan10) — usa la salida de estos indicadores privados de la comunidad punkchainer's para validar cruzadamente

**Análisis contextual:**
- **btc-regime-analysis** — Deep dive de régimen con MTF + divergencias + cycle analysis
- **btc-on-chain** — Análisis on-chain (hashrate, flows, whales, MVRV)
- **trade-psychology** — Framework para manejar tilt, FOMO, revenge trading, overconfidence

### `.claude/scripts/` — Automatización

- **statusline.sh** — Status line siempre visible: `💰 $13.63 (+$3.63) │ 📊 0/3 │ 🟢 VENT │ 🕐 CR 06:00 │ BTC.P`
- **session_start.sh** — Carga contexto al iniciar Claude (capital, reglas, comandos)
- **stop_hook.sh** — Auto-commit del journal al cerrar sesión
- **preprompt_check.sh** — Detecta "arriesgar todo", "mover SL", "aumentar leverage" y alerta
- **notify.sh** — Notificaciones nativas macOS
- **alert_setup.sh** — Monitor de setup 4/4 en background
- **daily_cron.sh** — Recordatorio matutino 5:30 AM (vía cron/launchd)

### Hooks configurados en `settings.json`

| Hook | Acción |
|---|---|
| **SessionStart** | Inyecta contexto trading automáticamente |
| **Stop** | Auto-commit del journal si hay cambios |
| **UserPromptSubmit** | Detecta palabras de auto-sabotaje y advierte |

### Status line persistente

Siempre visible en tu terminal:

```
💰 $13.63 (+$3.63) │ 📊 0/3 │ 🟢 VENT │ 🕐 CR 06:00 │ BTC.P
```

Muestra: capital actual, delta desde inicial, trades hoy, si estás en ventana, hora CR, símbolo.

---

## 🔄 Workflow con Git

### Commit diario del journal
```bash
git add DAILY_TRADING_JOURNAL.md
git commit -m "journal: 2026-04-21 +$1.20 (+12.4%)"
git push
```

### Commit de cambios de estrategia
```bash
git add CLAUDE.md MORNING_PROMPT.md
git commit -m "strategy: ajustar filtro RSI tras review semanal"
git push
```

### Commit de nuevos backtest findings
```bash
# Los backtests corren en /tmp/ y NO se commitean.
# Solo los hallazgos se documentan en memoria de Claude
# o en markdowns específicos si son relevantes.
```

---

## ⚠️ Disclaimers importantes

1. **Esto NO es consejo financiero.** Todo lo aquí descrito es para fines educativos y de investigación personal.

2. **Futuros con leverage pueden liquidar capital en minutos.** Usa solo capital que puedas perder sin afectar tu vida.

3. **Win Rate histórico ≠ Win Rate futuro.** Los backtests tienen data limitada (3-50 días según TF). Validación real requiere 25+ trades live.

4. **El sistema depende de disciplina.** Saltarte filtros o mover SLs convierte un sistema ganador en perdedor.

5. **El mercado cambia.** Si regime shift no detectado → recalibrar estrategia. Revisa régimen semanalmente.

---

## 🛠️ Troubleshooting

### Claude no recuerda mi capital/progreso
- Verifica que exista `~/.claude/projects/<project-path-encoded>/memory/`
- Lee `MEMORY.md` — debe listar todas las memorias activas
- Si falta, pide a Claude: "lee mi memoria y cárgala"

### El indicador Pine no aparece en TradingView
- TV Basic limita a 2 indicadores por chart
- Quita uno (Neptune Signals o Oscillator) primero
- Luego añade MR Signals

### draw_clear falla con "getChartApi is not defined"
- Workaround: click derecho en trash icon del left sidebar
- Menú contextual → "Eliminar dibujos"
- Documentado en `~/.claude/.../tradingview_setup.md`

### Pine Editor hang/loading infinito
- Cierra el panel y reabre
- Si persiste, guarda el código localmente (ya está en `MEAN_REVERSION_INDICATOR.pine`) y pega manual

---

## 🤝 Colaboración

PRs bienvenidos. Lee **[CONTRIBUTING.md](CONTRIBUTING.md)** antes de empezar — incluye tipos de contribución aceptadas, reglas de seguridad (nunca commitear credenciales), convenciones de commit, y el scope del proyecto.

**Issues y feature requests:** usa los [templates](.github/ISSUE_TEMPLATE/) del repo para bug reports y feature requests.

---

## 📜 Licencia

Este proyecto está licenciado bajo **[MIT License](LICENSE)**.

En resumen: puedes usar, modificar, distribuir y vender este código libremente con o sin atribución, siempre que (a) incluyas el copyright + licencia, y (b) entiendas que se provee "as is" sin garantías.

**Nota adicional:** el código se comparte con fines educativos e investigación. Nada aquí constituye consejo financiero. Ver disclaimer completo en [LICENSE](LICENSE).

---

## 🙏 Créditos

- **Estrategia Mean Reversion / Donchian Breakout:** construida iterativamente vía backtests
- **Indicadores Pine Script:** escritos en Pine v6
- **TradingView MCP:** [tradingview-mcp](https://github.com/anthropics/claude-code/tree/main/examples/tradingview) (o equivalente)
- **Claude Code:** [Anthropic](https://claude.com/claude-code)

---

## 💎 Mantra del sistema

> **"El mejor trade del año es el que NO hiciste por falta de setup."**
>
> **"Un SL pequeño respetado es una victoria. Un SL movido es el principio del fin."**
>
> **"Tu cuenta crece por lo que NO haces, tanto como por lo que haces."**

---

**Última actualización:** 2026-04-23 (sesión arquitectura — 3 features nuevos, 66 commits)
**Capital actual (retail):** $13.63 (3/3 wins, +36.3% acumulado)
**Estado FTMO:** profile + MT5 bridge implementados, pendiente paper trading en Free Trial
**Próximo objetivo retail:** $20 (≈ +63%) en las próximas 2 semanas
**Próximo objetivo FTMO:** correr backtest → paper trading 10+ trades → decidir challenge $93

**Features recientes:**
- Dual-profile system (retail + FTMO) — commit `086e754`
- MT5 Bridge con EA MQL5 — commit `c27ccf6`
- Multi-CLI portability (system/ + adapters OC/Codex) — commit `c3eda3a`
- Capa ML (Sentiment NLP + XGBoost + LSTM scaffold) — commit `fa06770`

**Tests totales:** 54 unit (24 guardian + 19 mt5_bridge + 11 transform) + 8 integration e2e.
