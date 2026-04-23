# 📈 BTC Trading System — Scalping Intraday con Claude

Sistema completo de trading algorítmico-asistido para BTCUSDT.P en BingX, construido sobre TradingView + Claude Code + Pine Script.

**Status actual:** Sistema validado con 3 trades ganadores (+36.3% / $10 → $13.63).
**Objetivo:** Escalar cuenta de $10 → $100 → FTMO $10k fundeado en ~4-6 meses.

---

## 🎯 Qué es este proyecto

Un **sistema operativo de trading** que combina:

- **Estrategia validada por backtest** (Mean Reversion + Donchian Breakout según régimen)
- **Indicador Pine Script** con los 4 filtros de entrada automatizados
- **Protocolo matutino** de 17 fases (análisis + psicología + disciplina)
- **Memoria persistente en Claude** que recuerda tu perfil, reglas y progreso
- **Journal obligatorio** de cada trade + review semanal
- **Integración con TradingView** via MCP (Claude dibuja niveles, detecta señales)
- **Capa ML** (NLP sentiment + XGBoost supervisado) como 5° filtro opcional

No es un bot automatizado. Es una **disciplina acompañada** — Claude hace el análisis pesado, tú ejecutas con reglas.

---

## 📁 Estructura del proyecto

```
trading/
├── CLAUDE.md                      # Guía del proyecto (la que Claude lee al iniciar)
├── MORNING_PROMPT.md              # Protocolo matutino de 17 fases
├── MEAN_REVERSION_INDICATOR.pine  # Indicador Pine Script (4 filtros + alertas)
├── DAILY_TRADING_JOURNAL.md       # Template journal diario
├── BREAKOUT_DASHBOARD_TRACKER.md  # Dashboard de niveles Donchian
├── NEPTUNE_TRADING_SYSTEM.md      # Docs sistema Neptune (legacy, referencia)
├── DOCUMENTATION.md               # Documentación general del sistema
├── QUICK_START_GUIDE.md           # Guía rápida de arranque
├── RISK_CALCULATOR.md             # Fórmulas de position sizing
├── .gitignore                     # Excluye /tmp, screenshots, node_modules
├── README.md                      # Este archivo
└── .claude/
    ├── settings.json              # Config principal (statusline, hooks, permissions)
    ├── settings.local.json        # Overrides locales (gitignored)
    ├── agents/                    # 7 agentes Claude especializados
    │   ├── morning-analyst.md     # Protocolo 17 fases 6 AM
    │   ├── trade-validator.md     # Valida GO/NO-GO antes de entrar
    │   ├── regime-detector.md     # Detecta RANGE/TRENDING/VOLATILE
    │   ├── chart-drafter.md       # Dibuja niveles en TradingView
    │   ├── risk-manager.md        # Calcula position sizing 2% rule
    │   ├── journal-keeper.md      # Actualiza trading_log + review semanal
    │   └── backtest-runner.md     # Corre backtests y grid search
    ├── commands/                  # 11 slash commands
    │   ├── morning.md             # /morning
    │   ├── validate.md            # /validate
    │   ├── regime.md              # /regime
    │   ├── risk.md                # /risk
    │   ├── journal.md             # /journal
    │   ├── chart.md               # /chart
    │   ├── backtest.md            # /backtest
    │   ├── status.md              # /status
    │   ├── review.md              # /review
    │   ├── levels.md              # /levels
    │   └── alert.md               # /alert
    ├── scripts/                   # Shell scripts (hooks + helpers)
    │   ├── statusline.sh          # Status line: cap/PnL/hora/ventana
    │   ├── session_start.sh       # Hook: inyecta contexto al iniciar
    │   ├── stop_hook.sh           # Hook: auto-commit journal al cerrar
    │   ├── preprompt_check.sh     # Hook: detecta auto-sabotaje
    │   ├── notify.sh              # Helper notificaciones macOS
    │   ├── alert_setup.sh         # Monitor setup 4/4 en background
    │   ├── daily_cron.sh          # Cron matutino 5:30 AM
    │   └── README.md              # Docs de los scripts
    └── skills/                    # 3 skills custom del dominio
        ├── btc-regime-analysis/   # Deep dive análisis régimen
        ├── btc-on-chain/          # Métricas on-chain
        └── trade-psychology/      # Framework disciplina mental

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
| Ventana entradas | MX 06:00 – 23:59 |
| Cierre forzado | MX 23:59 (no dormir con posición abierta) |
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

### 1. Preparación nocturna (el día anterior)
- Review del día
- Actualizar `DAILY_TRADING_JOURNAL.md`
- Dormir 7+ horas

### 2. Mañana 5:30 AM MX
Abre Claude Code en este directorio:
```bash
cd ~/Documents/trading
claude
```

### 3. Invoca el agente matutino
Dile a Claude: **"análisis matutino"** o **"morning analysis"**.

Claude detectará automáticamente el agente `morning-analyst` y ejecutará el protocolo completo.

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

### 5. Cierre de sesión MX 17:00
```
"Cierre sesión. Resumen PnL + actualiza trading_log.md"
```

### 6. Review semanal (domingos)
```
"Review semana: métricas, patrones, 1 cambio para la próxima"
```

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

Un día operativo completo usando TODO el stack (técnico + sentiment + ML). Ventana **MX 06:00 – 23:59** (cripto 24/7, pero no dormir con trade abierto).

### 🌅 MX 05:30 — Despertar

```bash
cd ~/Documents/trading
claude
```

El status line muestra: `💰 $13.63 (+$3.63) │ 📊 0/3 │ 🟢 VENT │ 🕐 MX 05:30 │ BTC.P`

### 🌄 MX 05:45-06:00 — Check personal

- [ ] Dormí 6+ horas
- [ ] Desayuné algo
- [ ] Estoy mentalmente claro (no tilt, no FOMO, no revenge)
- [ ] No estoy "recuperando" pérdida de ayer

Si alguno falla → **NO operar hoy**.

### ☀️ MX 06:00 — Análisis matutino (17 fases + ML)

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

### 🎯 MX 06:00 – 23:30 — Monitoreo de setup

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
   - Hora MX exacta
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
- Si necesitas cerrar manual (hora MX 23:30, evento macro imprevisto, pendiente personal) → cerrar a mercado sin mover SL.

### 🌙 MX 23:30 — Alarma de cierre próximo

Si el trade sigue abierto a las 23:30 MX:
- Evalúa si hay chance real de tocar TP antes de 23:59
- Si no → cerrar a mercado

### 🔚 MX 23:59 — Force exit

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

- **TradingView Desktop** (plan Basic mínimo)
- **BingX Futures** con BTCUSDT.P activado
- **Claude Code** (Anthropic CLI)
- **TradingView MCP** instalado y conectado (ver `tradingview-mcp/`)
- **Python 3.9+** (para backtests y sistema ML)
- **Homebrew** (para `libomp` requerido por XGBoost en Mac)

### Instalación

```bash
# 1. Clonar este repo
git clone git@github.com:sasasamaes/trading.git
cd trading

# 2. Instalar y conectar el TradingView MCP (ver prompt abajo)
#    Luego abrir TradingView Desktop con CDP en puerto 9222

# 3. Abrir Claude Code en este directorio
claude

# 4. Instalar indicador Pine en TV (manual):
#    - Abrir Pine Editor en TV
#    - Copiar contenido de MEAN_REVERSION_INDICATOR.pine
#    - Pegar, guardar como "MR Signals"
#    - Añadir al chart

# 5. (Opcional pero recomendado) Setup del sistema ML:
cd scripts/ml_system
./setup.sh                              # instala deps Python
brew install libomp                     # runtime XGBoost en Mac
python3 supervised/train.py --days 365  # entrena modelo (~100MB download, 2-4 min)
```

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

### `.claude/commands/` — 11 Slash commands

Atajos rápidos para acciones frecuentes:

| Comando | Acción |
|---|---|
| `/morning` | Análisis matutino completo (17 fases) |
| `/validate` | Valida entry con 4 filtros (GO/NO-GO) |
| `/regime` | Detecta régimen rápido |
| `/risk` | Position sizing con regla 2% |
| `/journal` | Actualiza log del día |
| `/chart` | Limpia y redibuja niveles en TV |
| `/backtest` | Ejecuta backtest/grid search |
| `/status` | Estado sistema (cap, trades, hora) |
| `/review` | Review semanal con métricas |
| `/levels` | Niveles técnicos actuales |
| `/alert` | Configura alerta custom |
| `/ta` | **Análisis técnico avanzado** (ICT, armónicos, chartismo, Elliott, Fibonacci) |
| `/signal` | **Valida señal externa** de comunidad con tu sistema (GO/NO-GO) |
| `/neptune` | Lee outputs de indicadores **Neptune** (Bangchan10) en el chart |
| `/sentiment` | **NLP Sentiment Aggregator** (F&G + News + Reddit + Funding) → score 0-100 |
| `/ml` | **ML score** del setup actual (XGBoost, probabilidad TP-first LONG/SHORT) |
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

- **statusline.sh** — Status line siempre visible: `💰 $13.63 (+$3.63) │ 📊 0/3 │ 🟢 VENT │ 🕐 MX 06:00 │ BTC.P`
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
💰 $13.63 (+$3.63) │ 📊 0/3 │ 🟢 VENT │ 🕐 MX 06:00 │ BTC.P
```

Muestra: capital actual, delta desde inicial, trades hoy, si estás en ventana, hora MX, símbolo.

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

Este repo es **personal** pero si quieres proponer mejoras:

1. Fork el repo
2. Crea una branch (`git checkout -b feature/mi-mejora`)
3. Commit (`git commit -m 'Propuesta: ...'`)
4. Push (`git push origin feature/mi-mejora`)
5. Abre un Pull Request

Idealmente acompaña con:
- Backtest evidencia (>20 trades mínimo)
- Justificación del cambio
- Comparación vs estrategia actual

---

## 📜 Licencia

Proyecto personal sin licencia pública. Si quieres usar partes del código, cita la fuente.

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

**Última actualización:** 2026-04-22
**Capital actual:** $13.63 (3/3 wins, +36.3% acumulado)
**Próximo objetivo:** $20 (≈ +63%) en las próximas 2 semanas
**Última feature:** Capa ML (Sentiment NLP + XGBoost + LSTM scaffold) — commit `fa06770`
