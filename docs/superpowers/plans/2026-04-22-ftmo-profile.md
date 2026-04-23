# FTMO Profile System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Claude trading system to support dual profiles (retail BingX $13.63 and FTMO MT5 $10k challenge) with isolated config/memory/strategy, a centralized rules guardian, and a validation pipeline (backtest → paper trading → challenge).

**Architecture:** Profile-based config system. Flag file `.claude/active_profile` drives all commands/agents to read from `.claude/profiles/{retail,ftmo}/`. A Python guardian enforces FTMO rules (3% daily hard, 10% trailing warn, Best Day info). Existing 17 commands and 11 agents become profile-aware; one new agent (`morning-analyst-ftmo`) handles multi-asset FTMO analysis.

**Tech Stack:** Bash scripts, Python 3 (stdlib + pytest), Markdown (commands/agents are prompt files read by Claude Code).

**Spec:** See `docs/superpowers/specs/2026-04-22-ftmo-profile-design.md`

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `.claude/active_profile` | Single-line flag: `{profile} \| {iso_timestamp}` |
| `.claude/profiles/retail/config.md` | Retail capital, exchange, assets |
| `.claude/profiles/retail/strategy.md` | Mean Reversion 15m strategy spec |
| `.claude/profiles/retail/memory/*.md` | Migrated retail-specific memories |
| `.claude/profiles/ftmo/config.md` | FTMO challenge constants (YAML) |
| `.claude/profiles/ftmo/strategy.md` | FTMO-Conservative strategy spec |
| `.claude/profiles/ftmo/rules.md` | Formal spec of 3%/10%/Best Day rules |
| `.claude/profiles/ftmo/memory/equity_curve.csv` | Timeline of equity snapshots |
| `.claude/profiles/ftmo/memory/trading_log.md` | FTMO trades journal |
| `.claude/profiles/ftmo/memory/challenge_progress.md` | % progress dashboard |
| `.claude/profiles/ftmo/memory/mt5_symbols.md` | Pip values per asset |
| `.claude/profiles/ftmo/memory/paper_trading_log.md` | Paper trades pre-challenge |
| `.claude/profiles/ftmo/memory/overrides.log` | Guardian override events |
| `.claude/profiles/ftmo/memory/session_notes.md` | Daily session notes |
| `.claude/scripts/guardian.py` | Rules engine (calculations + CLI) |
| `.claude/scripts/profile.sh` | Profile switch/show/validate |
| `.claude/scripts/test_guardian.py` | Guardian unit tests (pytest) |
| `.claude/scripts/backtest_ftmo.py` | Historical backtest of FTMO strategy |
| `.claude/commands/profile.md` | /profile command |
| `.claude/commands/equity.md` | /equity command |
| `.claude/commands/challenge.md` | /challenge command |
| `.claude/agents/morning-analyst-ftmo.md` | Multi-asset FTMO morning agent |

### Modified files

| Path | Change |
|---|---|
| `.claude/memory/MEMORY.md` | Restructured with GLOBAL / RETAIL / FTMO sections |
| `.claude/scripts/session_start.sh` | Stale detection + profile prompt |
| `.claude/scripts/statusline.sh` | Show `[profile]` + profile-specific metrics |
| `.claude/commands/morning.md` | Profile-aware dispatch |
| `.claude/commands/validate.md` | Invoke guardian after 4 technical filters |
| `.claude/commands/risk.md` | Invoke guardian for size calc |
| `.claude/commands/status.md` | Profile-aware output |
| `.claude/commands/journal.md` | Profile-aware journal write |
| `.claude/agents/*.md` (7 agents) | Add "read active_profile" header |
| `CLAUDE.md` | Document dual-profile system |

### Migrated files

All via `git mv` to preserve history:

| From | To |
|---|---|
| `.claude/memory/trading_log.md` | `.claude/profiles/retail/memory/trading_log.md` |
| `.claude/memory/trading_strategy.md` | `.claude/profiles/retail/memory/trading_strategy.md` |
| `.claude/memory/entry_rules.md` | `.claude/profiles/retail/memory/entry_rules.md` |
| `.claude/memory/backtest_findings.md` | `.claude/profiles/retail/memory/backtest_findings.md` |
| `.claude/memory/market_regime.md` | `.claude/profiles/retail/memory/market_regime.md` |
| `.claude/memory/tradingview_setup.md` | `.claude/profiles/retail/memory/tradingview_setup.md` |
| `.claude/memory/liquidations_data.md` | `.claude/profiles/retail/memory/liquidations_data.md` |

---

## Testing Strategy

**Pure Python (guardian.py):** TDD with pytest. 15+ unit tests covering every rule + edge case.

**Bash scripts (profile.sh, session_start.sh):** Verification steps in each task (execute command + check expected output).

**Markdown files (commands, agents, configs):** No automated tests — these are prompts/config read by Claude at runtime. Verification = execute `/command` in a Claude session and confirm behavior.

**End-to-end:** Task 26 runs a manual integration check covering full flow (sessionStart → morning → validate → equity → journal → switch → status).

---

## Task 0: Branch and baseline verification

**Files:** None (git operations only)

- [ ] **Step 1: Create feature branch**

```bash
cd ~/Documents/trading
git checkout -b feature/ftmo-profile
```

- [ ] **Step 2: Verify clean baseline — current system works**

```bash
# Read current statusline output
bash .claude/scripts/statusline.sh
```

Expected: output mentions "Capital $13.63" and current MX time.

```bash
# Verify memory structure
ls .claude/memory/ | sort
```

Expected: 16 files including `trading_log.md`, `MEMORY.md`, `user_profile.md`.

- [ ] **Step 3: Snapshot commit (empty marker)**

```bash
git commit --allow-empty -m "chore: baseline snapshot before FTMO profile migration"
```

---

## Task 1: Directory scaffolding

**Files:**
- Create: `.claude/profiles/retail/memory/.gitkeep`
- Create: `.claude/profiles/ftmo/memory/.gitkeep`

- [ ] **Step 1: Create profile directory tree**

```bash
mkdir -p .claude/profiles/retail/memory
mkdir -p .claude/profiles/ftmo/memory
touch .claude/profiles/retail/memory/.gitkeep
touch .claude/profiles/ftmo/memory/.gitkeep
```

- [ ] **Step 2: Verify structure**

```bash
find .claude/profiles -type d | sort
```

Expected output:
```
.claude/profiles
.claude/profiles/ftmo
.claude/profiles/ftmo/memory
.claude/profiles/retail
.claude/profiles/retail/memory
```

- [ ] **Step 3: Commit**

```bash
git add .claude/profiles/
git commit -m "feat: scaffold profile directory tree (retail + ftmo)"
```

---

## Task 2: Migrate retail memories with git mv

**Files:**
- Migrate: 7 files from `.claude/memory/` to `.claude/profiles/retail/memory/`

- [ ] **Step 1: Move retail-specific memories**

```bash
git mv .claude/memory/trading_log.md      .claude/profiles/retail/memory/trading_log.md
git mv .claude/memory/trading_strategy.md .claude/profiles/retail/memory/trading_strategy.md
git mv .claude/memory/entry_rules.md      .claude/profiles/retail/memory/entry_rules.md
git mv .claude/memory/backtest_findings.md .claude/profiles/retail/memory/backtest_findings.md
git mv .claude/memory/market_regime.md    .claude/profiles/retail/memory/market_regime.md
git mv .claude/memory/tradingview_setup.md .claude/profiles/retail/memory/tradingview_setup.md
git mv .claude/memory/liquidations_data.md .claude/profiles/retail/memory/liquidations_data.md
```

- [ ] **Step 2: Verify global memories remain untouched**

```bash
ls .claude/memory/ | sort
```

Expected (no retail-specific files):
```
MEMORY.md
communication_prefs.md
external_signals_tracker.md
ml_system.md
morning_protocol.md
operating_window.md
market_context_refs.md
README.md
user_goals_reality.md
user_profile.md
```

- [ ] **Step 3: Verify retail memories migrated**

```bash
ls .claude/profiles/retail/memory/ | sort
```

Expected:
```
.gitkeep
backtest_findings.md
entry_rules.md
liquidations_data.md
market_regime.md
trading_log.md
trading_strategy.md
tradingview_setup.md
```

- [ ] **Step 4: Commit**

```bash
git commit -m "refactor: migrate retail-specific memories to profiles/retail/memory/"
```

---

## Task 3: Write retail config and strategy files

**Files:**
- Create: `.claude/profiles/retail/config.md`
- Create: `.claude/profiles/retail/strategy.md`

- [ ] **Step 1: Write `retail/config.md`**

```markdown
# Profile: RETAIL (BingX Real)

**Capital actual:** $13.63 (iniciado en $10, +36% tras 3 wins)
**Exchange:** BingX (BTCUSDT.P perpetual)
**Leverage máximo:** 10x
**Plataforma análisis:** TradingView (plan Basic, 2 indicadores: Neptune Signals + Neptune Oscillator)

## Assets operables

- Único: `BTCUSDT.P` (BingX)

## Estrategia activa

Ver `strategy.md` en este directorio — **Mean Reversion 15m** (según régimen actual RANGE 73.5k–78.3k).

## Ventana operativa

- Inicio: MX 06:00
- Force exit: MX 23:59 (regla "no dormir con posición abierta")
- Cripto 24/7 pero el trader no duerme con trade abierto

## Reglas duras

1. Max 2% riesgo por trade (del capital actual, no del inicial)
2. Max 3 trades/día
3. 2 SLs consecutivos → STOP día
4. Nunca mover SL en contra (solo a BE tras TP1)
5. Nunca leverage >10x
6. 4/4 filtros obligatorios simultáneos

## Memorias específicas retail

Ver archivos en `./memory/`:
- `trading_log.md` — journal histórico
- `trading_strategy.md` — detalle Mean Reversion
- `entry_rules.md` — 4 filtros
- `market_regime.md` — niveles actuales BTC BingX
- `tradingview_setup.md` — config TV
- `liquidations_data.md` — fuentes datos BingX/Binance
- `backtest_findings.md` — aprendizajes de 144 configs
```

- [ ] **Step 2: Write `retail/strategy.md`**

```markdown
# Estrategia: Mean Reversion 15m (RETAIL)

Validada con **100% WR** y **+15.1%** en backtest 3 días frente a 144 configs.

## Parámetros

| Parámetro | Valor |
|---|---|
| Timeframe | 15m |
| Donchian | 15 velas |
| Edge de entrada | ±0.1% del extremo Donchian |
| RSI(14) | OB 65, OS 35 |
| Bollinger Bands | (20, 2) confirmación obligatoria |
| ATR length | 14 |
| SL | 1.5 × ATR (adaptativo) |
| TP1 (40%) | 2.5 × SL → SL a BE |
| TP2 (40%) | 4.0 × SL |
| TP3 (20%) | 6.0 × SL |
| Leverage | 10x |
| Ventana | MX 06:00 – 23:59 |

## Entradas — 4 filtros obligatorios

**LONG:**
1. Precio toca o cruza Donchian Low(15) (dentro 0.1%)
2. RSI < 35
3. Low de vela toca BB inferior
4. Vela cierra verde

**SHORT:**
1. Precio toca o cruza Donchian High(15) (dentro 0.1%)
2. RSI > 65
3. High de vela toca BB superior
4. Vela cierra roja

## Invalidación

- 2 SLs consecutivos → parar ese día
- Días con noticias macro (CPI, Fed) → no operar
- ATR 2x promedio → no operar (régimen volatile)

## Estrategia secundaria

Donchian Breakout si BTC rompe el range (cierre 4H fuera de 73.5k–78.3k con volumen >2x promedio). Config: Donchian(20), buffer 30 pts, vol >300 BTC, SL 0.5%, TP 0.75/1.25/2.0%.
```

- [ ] **Step 3: Verify files created**

```bash
ls -la .claude/profiles/retail/
```

Expected: `config.md` and `strategy.md` exist, non-empty.

- [ ] **Step 4: Commit**

```bash
git add .claude/profiles/retail/config.md .claude/profiles/retail/strategy.md
git commit -m "feat: retail profile config and strategy"
```

---

## Task 4: Write FTMO config, strategy, and rules files

**Files:**
- Create: `.claude/profiles/ftmo/config.md`
- Create: `.claude/profiles/ftmo/rules.md`
- Create: `.claude/profiles/ftmo/strategy.md`

- [ ] **Step 1: Write `ftmo/config.md`**

```markdown
# Profile: FTMO (Challenge Demo $10k)

**Challenge type:** 1-Step $10,000 USD
**Coste challenge:** $93.43 (único pago)
**Plataforma:** MetaTrader 5 (MT5)
**Leverage:** 1:100

## Constantes (YAML, consumidas por guardian.py)

```yaml
challenge_type: 1-step
initial_capital: 10000
profit_target_pct: 10           # $1000
max_daily_loss_pct: 3           # $300 diario
max_total_trailing_pct: 10      # $1000 desde peak equity
best_day_cap_pct: 50            # cap 50% del profit total
leverage: 100
risk_per_trade_pct: 0.5         # $50 por trade inicial
max_trades_per_day: 2           # hard cap
max_sl_consecutive: 2           # 2 SL seguidos → STOP día
```

## Assets operables (multi-asset)

Ver `memory/mt5_symbols.md` para símbolos exactos en MT5 y pip values.

| Asset | Sesión óptima MX | Régimen ideal |
|---|---|---|
| BTCUSD | 06:00-10:00 | RANGE |
| ETHUSD | 06:00-10:00 | RANGE/TREND leve |
| EURUSD | 07:00-10:00, 14:00-16:00 | RANGE |
| GBPUSD | 07:00-11:00 | TREND leve |
| NAS100 | 08:30-15:00 | TREND (ADX>25) |
| SPX500 | 08:30-15:00 | TREND/RANGE |

## Ventana operativa

- Inicio: MX 06:00
- Force exit: MX 16:00 (cierre sesión US)
- NO overnight — obligatorio cerrar trades antes de 16:00

## Reglas duras (ver `rules.md` para detalle formal)

1. Daily 3% loss → BLOQUEO DURO del guardian
2. Trailing 10% DD → WARNING fuerte del guardian
3. Best Day 50% → INFO del guardian
4. Max 2 trades/día
5. 2 SLs consecutivos → STOP día
6. Size fijo 0.5% risk per trade

## Estrategia activa

Ver `strategy.md` — **FTMO-Conservative** (diseñada para pasar challenge en 10-30 días).
```

- [ ] **Step 2: Write `ftmo/rules.md`**

```markdown
# FTMO 1-Step Rules — Formal Spec

Este documento es la fuente única de verdad sobre reglas FTMO que el guardian implementa.

## Regla 1 — Max Daily Loss 3%

**Definición:** En cualquier día calendario (reset 00:00 UTC), la pérdida neta no puede exceder 3% del equity del inicio del día.

**Cálculo:**
```
daily_pnl = equity_actual - equity_inicio_dia
daily_pct = daily_pnl / equity_inicio_dia * 100
if daily_pct <= -3.0 → BREACH
```

**Enforcement:** BLOCKING (guardian impide entrada que llevaría a breach).

**Nota:** FTMO usa hora de servidor (típicamente UTC+2). Guardian usa timestamp del equity_curve; la consistencia es responsabilidad del usuario.

## Regla 2 — Max Total Trailing Drawdown 10%

**Definición:** La pérdida total desde el peak de equity histórico no puede exceder 10% del capital inicial ($1,000 en $10k).

**Cálculo:**
```
peak = max(equity_curve.equity)
dd_actual = peak - equity_actual
dd_pct = dd_actual / 10000 * 100
if dd_pct >= 10.0 → BREACH
```

**Enforcement:** WARNING (guardian advierte pero no bloquea; el usuario tiene margen de días).

**Threshold de warning:** guardian alerta si dd_pct >= 8.0 (80% del límite).

## Regla 3 — Best Day Rule 50%

**Definición:** Ningún día puede representar más del 50% del profit total del challenge.

**Cálculo:**
```
days_positive = [(date, profit) for date, profit in day_profits if profit > 0]
total_profit = sum(p for _, p in days_positive)
best_day = max(p for _, p in days_positive)
ratio = best_day / total_profit
if ratio > 0.50 → INFO (no bloquea, se soluciona con más días)
```

**Enforcement:** INFO (visible en `/challenge` y al cierre de día). No bloquea entradas.

**Threshold de aviso:** guardian muestra info si ratio >= 0.45.

## Regla 4 — Max 2 Trades/Day (del config, no FTMO)

**Definición:** Límite autoimpuesto para evitar sobretrading.

**Cálculo:**
```
trades_today = count(trades where date == today)
if trades_today >= 2 → BLOCK
```

**Enforcement:** BLOCKING.

## Regla 5 — 2 SLs Consecutivos → STOP día (autoimpuesta)

**Definición:** Después de 2 SLs seguidos (sin TP ni BE entre medio) en el mismo día, STOP.

**Cálculo:**
```
last_two = last 2 trades of today, ordered by close_time
if both are SL → BLOCK
```

**Enforcement:** BLOCKING.

## Override escape hatch

Usuario puede escribir literalmente `OVERRIDE GUARDIAN` en respuesta a un BLOCK. El guardian:
1. Registra evento en `memory/overrides.log` con timestamp, rule, equity, trade propuesto
2. Permite proceder

Usar solo en casos extremos; cada override es material de post-mortem.
```

- [ ] **Step 3: Write `ftmo/strategy.md`**

```markdown
# Estrategia: FTMO-Conservative (multi-asset)

Diseñada para pasar el challenge FTMO 1-Step en 10-30 días con bajo riesgo.

## Principios

1. Target diario **1.0-1.5%** (no persigues más aunque tengas setup)
2. SL **0.4% fijo** por trade (no ATR-based)
3. Size **0.5% risk** = $50 inicial por trade
4. **Multi-asset selection**: 1 setup A-grade por día
5. Asset rotation por EV diario
6. Best Day compliance natural: cierras terminal si ya +1.5% del día

## Universo

| Asset | MT5 Symbol (validar) | Sesión óptima MX | Régimen ideal |
|---|---|---|---|
| BTCUSD | `BTCUSD` | 06:00-10:00 | RANGE |
| ETHUSD | `ETHUSD` | 06:00-10:00 | RANGE/TREND leve |
| EURUSD | `EURUSD` | 07:00-10:00, 14:00-16:00 | RANGE |
| GBPUSD | `GBPUSD` | 07:00-11:00 | TREND leve |
| NAS100 | `US100.cash` o `NAS100` | 08:30-15:00 | TREND (ADX>25) |
| SPX500 | `US500.cash` o `SPX500` | 08:30-15:00 | TREND/RANGE |

**Ventana operativa:** MX 06:00–16:00. Post-16:00 = no operar (cierre sesión US).

## Filtros de selección diaria

Score A/B/C/D por asset (morning-analyst-ftmo lo calcula):
- **A**: régimen RANGE + RSI en zona + BB extremo + volumen OK
- **B**: RANGE pero solo 2/3 condiciones técnicas
- **C**: régimen ambiguo
- **D**: VOLATILE o NO DATA → skip

**Selección:**
- 1 A-grade → ese es el trade del día
- 2+ A-grades → prioriza menor spread + sesión activa
- Todos B o peor → no operar hoy

## Entradas — 7 filtros simultáneos

**LONG:**
1. Precio toca Donchian Low(20)
2. RSI(14) < 30
3. BB(20,2) Lower toca
4. Vela 15m cierra verde con cuerpo ≥ 60% del rango
5. Spread ≤ 1.5× spread promedio del asset
6. Hora dentro de sesión óptima del asset
7. Guardian OK o OK_WITH_WARN

**SHORT:** espejo (Donchian High, RSI > 70, BB Upper, cuerpo rojo 60%+).

## Gestión de trade

| Componente | Valor |
|---|---|
| Entry | Mercado o limit dentro 0.1% de zona |
| SL | 0.4% del entry (fijo) |
| TP1 (50%) | 0.6% (1.5R) → mueve SL a BE |
| TP2 (50%) | 1.2% (3.0R) |
| Trailing post-TP1 | Stop a mid entre entry y TP2 |
| Force exit | 16:00 MX |
| Overnight | PROHIBIDO |

**R:R efectivo:** +0.9% notional por trade exitoso = **+0.45% equity** con size 0.5%.

Matemática: 3-4 trades exitosos/semana × 0.45% = ~1.8%/sem ≈ 10% en 6-8 semanas.

## Position sizing

```python
def calc_lots(asset, entry, sl, equity, risk_pct=0.5):
    risk_usd = equity * (risk_pct / 100)        # $50
    sl_pips = abs(entry - sl)
    pip_value = get_pip_value(asset)            # desde mt5_symbols.md
    lots = risk_usd / (sl_pips * pip_value)
    return round(lots, 2)
```

Tabla de pip values se valida el primer día del challenge con screenshots de la pantalla Specification de MT5 para cada símbolo.

## Validación obligatoria antes de challenge pago

1. Sistema completo implementado (fases 1-5 del spec)
2. Backtest python (`backtest_ftmo.py`) sobre 3 meses BTC + ETH + EURUSD: WR>55%, DD<5%, 0 daily breaches simulados
3. Paper trading en FTMO Free Trial 14 días, 10+ trades reales: WR>55%, 0 overrides, 0 breaches
4. Si cumple → comprar challenge $93.43
5. Si no cumple → refinar estrategia, repetir backtest + paper
```

- [ ] **Step 4: Verify files**

```bash
ls -la .claude/profiles/ftmo/
wc -l .claude/profiles/ftmo/*.md
```

Expected: three files, each >20 lines.

- [ ] **Step 5: Commit**

```bash
git add .claude/profiles/ftmo/config.md .claude/profiles/ftmo/rules.md .claude/profiles/ftmo/strategy.md
git commit -m "feat: FTMO profile config, rules spec, and strategy"
```

---

## Task 5: Seed FTMO memory files (empty/scaffold)

**Files:**
- Create: `.claude/profiles/ftmo/memory/equity_curve.csv`
- Create: `.claude/profiles/ftmo/memory/trading_log.md`
- Create: `.claude/profiles/ftmo/memory/challenge_progress.md`
- Create: `.claude/profiles/ftmo/memory/mt5_symbols.md`
- Create: `.claude/profiles/ftmo/memory/paper_trading_log.md`
- Create: `.claude/profiles/ftmo/memory/overrides.log`
- Create: `.claude/profiles/ftmo/memory/session_notes.md`

- [ ] **Step 1: Create `equity_curve.csv` with header only**

```csv
timestamp,equity,source,note
```

- [ ] **Step 2: Create `trading_log.md` scaffold**

```markdown
# FTMO Trading Log

Registro de cada trade en FTMO demo/real. `journal-keeper` agent lo actualiza al `/journal`.

## Esquema por trade

- **Fecha / Hora MX:** apertura y cierre
- **Asset:** BTCUSD / ETHUSD / EURUSD / etc.
- **Dirección:** LONG / SHORT
- **Entry / SL / TP1 / TP2:** precios exactos
- **Size (lots):** decimal
- **Resultado:** TP1 / TP2 / SL / BE / partial
- **Equity pre / post:** valores
- **PnL $:** neto
- **R múltiplo:** pnl / risk
- **Filtros cumplidos:** 7/7 u otros
- **Guardian veredicto:** OK / WARN / BLOCK_SIZE (con reason)
- **Aprendizaje:** qué aprendí del trade

---

(No hay trades aún. Primer trade se registra al completar Fase 7 paper trading.)
```

- [ ] **Step 3: Create `challenge_progress.md` scaffold**

```markdown
# FTMO Challenge Progress

**Tipo:** 1-Step $10,000
**Inicio:** _pendiente_
**Status:** PREPARING (fases 1-6 del plan)

## Objetivo

- Profit target: **$1,000 (10%)**
- Días mínimos: **ilimitado** (sin deadline)
- Reglas a cumplir: 3% daily, 10% trailing, Best Day 50%

## Progreso actual

- Profit acumulado: $0 / $1,000
- Días activos: 0
- Best day profit: $0
- Best day / total: N/A
- Daily loss max alcanzado: $0
- Trailing DD max alcanzado: $0
- Overrides del guardian: 0

## Métricas rolling (última semana)

Se actualizan automáticamente al `/journal`.

- Win rate: N/A
- Avg R por trade: N/A
- Trades/día promedio: N/A
- Profit factor: N/A

## Próximos pasos

Ver Fases 6-8 del plan de implementación:
- Fase 6: correr backtest histórico
- Fase 7: paper trading FTMO Free Trial
- Fase 8: decisión compra challenge $93.43
```

- [ ] **Step 4: Create `mt5_symbols.md` scaffold**

```markdown
# MT5 Symbols — Pip Values Validados

Se llenan el primer día del challenge con screenshots de la pantalla "Specification" de MT5 para cada símbolo.

## Formato

```
asset: <nombre>
mt5_symbol: <código exacto en MT5>
contract_size: <valor>
tick_size: <decimales>
pip_value_per_lot: <USD por pip por 1.0 lot>
min_lot: <mínimo>
lot_step: <incremento>
spread_avg_pips: <promedio observado>
commission_per_lot: <si aplica>
```

## Símbolos pendientes de validación

### BTCUSD
```
mt5_symbol: BTCUSD
contract_size: PENDING
tick_size: PENDING
pip_value_per_lot: PENDING
min_lot: PENDING
lot_step: PENDING
spread_avg_pips: PENDING
commission_per_lot: PENDING
```

### ETHUSD
```
mt5_symbol: ETHUSD
(valores PENDING)
```

### EURUSD
```
mt5_symbol: EURUSD
(valores PENDING)
```

### GBPUSD
```
mt5_symbol: GBPUSD
(valores PENDING)
```

### NAS100
```
mt5_symbol: US100.cash | NAS100 (confirmar con FTMO MT5)
(valores PENDING)
```

### SPX500
```
mt5_symbol: US500.cash | SPX500 (confirmar con FTMO MT5)
(valores PENDING)
```
```

- [ ] **Step 5: Create `paper_trading_log.md`, `overrides.log`, `session_notes.md` as empty stubs**

```markdown
# Paper Trading Log (FTMO Free Trial)

Registro de trades simulados en FTMO demo antes de comprar el challenge real.

Objetivo: 10+ trades reales con WR≥55%, 0 breaches simulados, 0 overrides.

(Sin trades aún.)
```

```
# Guardian Override Events
# Formato: timestamp|profile|rule_violated|equity|trade|reason
```

```markdown
# Session Notes

Notas cualitativas por día de challenge (psicología, contexto, decisiones no capturadas por el log numérico).

(Sin sesiones aún.)
```

- [ ] **Step 6: Verify and commit**

```bash
ls -la .claude/profiles/ftmo/memory/
```

Expected: 7 files (equity_curve.csv, trading_log.md, challenge_progress.md, mt5_symbols.md, paper_trading_log.md, overrides.log, session_notes.md) plus `.gitkeep`.

```bash
git add .claude/profiles/ftmo/memory/
git commit -m "feat: FTMO memory files scaffold"
```

---

## Task 6: Active profile flag + profile.sh script

**Files:**
- Create: `.claude/active_profile`
- Create: `.claude/scripts/profile.sh`

- [ ] **Step 1: Initialize flag file with `retail`**

```bash
echo "retail | $(date -u +%Y-%m-%dT%H:%M:%S)" > .claude/active_profile
cat .claude/active_profile
```

Expected output: `retail | 2026-04-22T...`

- [ ] **Step 2: Write `profile.sh`**

```bash
#!/usr/bin/env bash
# .claude/scripts/profile.sh
# Usage:
#   profile.sh show        — prints current profile
#   profile.sh get         — prints just the profile name (no timestamp)
#   profile.sh set <name>  — switches to <name> (retail|ftmo)
#   profile.sh stale       — exits 0 if stale >12h, exits 1 otherwise
#   profile.sh validate    — checks profile exists in profiles/ dir

set -euo pipefail

FLAG_FILE="$(dirname "$0")/../active_profile"
PROFILES_DIR="$(dirname "$0")/../profiles"

cmd="${1:-show}"

case "$cmd" in
  show)
    if [[ -f "$FLAG_FILE" ]]; then
      cat "$FLAG_FILE"
    else
      echo "no profile set"
      exit 1
    fi
    ;;
  get)
    if [[ -f "$FLAG_FILE" ]]; then
      cut -d'|' -f1 "$FLAG_FILE" | tr -d ' '
    else
      echo ""
      exit 1
    fi
    ;;
  set)
    name="${2:-}"
    if [[ -z "$name" ]]; then
      echo "ERROR: profile name required" >&2
      exit 2
    fi
    if [[ ! -d "$PROFILES_DIR/$name" ]]; then
      echo "ERROR: profile '$name' not found in $PROFILES_DIR" >&2
      exit 3
    fi
    ts="$(date -u +%Y-%m-%dT%H:%M:%S)"
    echo "$name | $ts" > "$FLAG_FILE"
    echo "switched to: $name | $ts"
    ;;
  stale)
    if [[ ! -f "$FLAG_FILE" ]]; then
      exit 0  # stale = prompt needed
    fi
    ts="$(cut -d'|' -f2 "$FLAG_FILE" | tr -d ' ')"
    # Convert ISO to epoch, compare to now
    now="$(date +%s)"
    if flag_epoch="$(date -j -f "%Y-%m-%dT%H:%M:%S" "$ts" +%s 2>/dev/null)"; then
      age=$((now - flag_epoch))
      if [[ $age -gt 43200 ]]; then  # 12 hours
        exit 0  # stale
      fi
    else
      exit 0  # parse fail = stale
    fi
    exit 1  # fresh
    ;;
  validate)
    name="$(bash "$0" get)"
    if [[ -z "$name" || ! -d "$PROFILES_DIR/$name" ]]; then
      echo "INVALID: profile '$name' not in $PROFILES_DIR" >&2
      exit 1
    fi
    echo "OK: $name"
    ;;
  *)
    echo "Usage: profile.sh {show|get|set <name>|stale|validate}" >&2
    exit 2
    ;;
esac
```

- [ ] **Step 3: Make executable and verify**

```bash
chmod +x .claude/scripts/profile.sh
bash .claude/scripts/profile.sh show
```

Expected: `retail | 2026-04-22T...`

```bash
bash .claude/scripts/profile.sh get
```

Expected: `retail`

```bash
bash .claude/scripts/profile.sh validate
```

Expected: `OK: retail`

- [ ] **Step 4: Test set command with valid profile**

```bash
bash .claude/scripts/profile.sh set ftmo
bash .claude/scripts/profile.sh get
```

Expected second output: `ftmo`

```bash
# Reset to retail for following tasks
bash .claude/scripts/profile.sh set retail
```

- [ ] **Step 5: Test set with invalid profile fails cleanly**

```bash
bash .claude/scripts/profile.sh set nonexistent && echo "UNEXPECTED PASS" || echo "OK: failed as expected"
```

Expected: `OK: failed as expected`

- [ ] **Step 6: Commit**

```bash
git add .claude/active_profile .claude/scripts/profile.sh
git commit -m "feat: active_profile flag file and profile.sh switcher"
```

---

## Task 7: /profile command

**Files:**
- Create: `.claude/commands/profile.md`

- [ ] **Step 1: Write command definition**

```markdown
Muestra o cambia el profile activo del sistema.

Uso:
- `/profile` — muestra profile activo y timestamp
- `/profile ftmo` — switch a FTMO
- `/profile retail` — switch a retail
- `/profile status` — resumen rápido de ambos profiles

Pasos que ejecuta Claude:

1. Si el argumento es vacío:
   - Corre `bash .claude/scripts/profile.sh show`
   - Devuelve el profile actual + timestamp

2. Si el argumento es `status`:
   - Lee `.claude/profiles/retail/config.md` y resume (capital, strategy)
   - Lee `.claude/profiles/ftmo/config.md` y resume (challenge progress)
   - Si FTMO tiene `equity_curve.csv` no vacío, muestra equity actual + daily PnL
   - Marca con ▶ el profile activo

3. Si el argumento es `ftmo` o `retail`:
   - **Validación previa**: pregunta al usuario "¿tienes trade abierto en el profile actual?" — si sí, BLOCK switch con mensaje "cierra primero"
   - Corre `bash .claude/scripts/profile.sh set <arg>`
   - Confirma con el nuevo statusline

4. Si el argumento no es reconocido:
   - Devuelve error: "uso: /profile [ftmo|retail|status]"

Reglas:
- NUNCA cambiar profile si hay trade abierto (evita cross-contamination)
- Después de switch, recordar al usuario que las memorias del otro profile quedan intactas
- Si el profile destino es FTMO, prompteear al usuario: "¿actualizar equity FTMO ahora? (último: $X @ <timestamp>)"
```

- [ ] **Step 2: Verify file**

```bash
wc -l .claude/commands/profile.md
```

Expected: >30 lines.

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/profile.md
git commit -m "feat: /profile command"
```

---

## Task 8: Modify session_start.sh for stale profile detection

**Files:**
- Modify: `.claude/scripts/session_start.sh`

- [ ] **Step 1: Read current session_start.sh to understand baseline**

```bash
cat .claude/scripts/session_start.sh
```

Note the current output format (capital, hora MX, session context). We'll preserve it and prepend profile awareness.

- [ ] **Step 2: Add profile detection header**

Edit the top of `session_start.sh` (after shebang and initial vars), adding:

```bash
# ─────── Profile detection ───────
PROFILE_SCRIPT="$(dirname "$0")/profile.sh"
if [[ -x "$PROFILE_SCRIPT" ]]; then
  PROFILE="$(bash "$PROFILE_SCRIPT" get 2>/dev/null || echo "")"
  if bash "$PROFILE_SCRIPT" stale >/dev/null 2>&1; then
    echo ""
    echo "⚠️  PROFILE STALE o no seteado. Último valor: ${PROFILE:-<ninguno>}"
    echo "   Ejecuta /profile ftmo  o  /profile retail  para confirmar hoy."
    echo ""
  fi
  echo "## CONTEXTO TRADING SESSION — Profile: [$PROFILE]"
else
  echo "## CONTEXTO TRADING SESSION"
fi
# ─────────────────────────────────
```

This replaces the current header line (`## CONTEXTO TRADING SESSION`) with a profile-aware version.

- [ ] **Step 3: Load profile-specific capital**

Find the current line that hardcodes `Capital actual: $13.63` and replace with:

```bash
if [[ "$PROFILE" == "ftmo" ]]; then
  CURVE="$(dirname "$0")/../profiles/ftmo/memory/equity_curve.csv"
  if [[ -f "$CURVE" && $(wc -l < "$CURVE") -gt 1 ]]; then
    LAST_EQ="$(tail -n1 "$CURVE" | cut -d',' -f2)"
    echo "**Capital actual (FTMO):** \$$LAST_EQ"
  else
    echo "**Capital actual (FTMO):** \$10,000 (inicial — corre /equity <valor> para actualizar)"
  fi
elif [[ "$PROFILE" == "retail" ]]; then
  # Preservar comportamiento actual retail
  CONFIG="$(dirname "$0")/../profiles/retail/config.md"
  CAPITAL="$(grep -oE 'Capital actual:[^$]*\$[0-9.]+' "$CONFIG" | head -1 | grep -oE '\$[0-9.]+')"
  echo "**Capital actual (RETAIL):** ${CAPITAL:-\$13.63}"
fi
```

- [ ] **Step 4: Run and verify**

```bash
bash .claude/scripts/profile.sh set retail
bash .claude/scripts/session_start.sh
```

Expected: output shows `Profile: [retail]` and `Capital actual (RETAIL): $13.63`.

```bash
bash .claude/scripts/profile.sh set ftmo
bash .claude/scripts/session_start.sh
```

Expected: output shows `Profile: [ftmo]` and `Capital actual (FTMO): $10,000 (inicial ...)`.

```bash
# Reset to retail for following tasks
bash .claude/scripts/profile.sh set retail
```

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/session_start.sh
git commit -m "feat: session_start.sh profile-aware header and capital"
```

---

## Task 9: Modify statusline.sh to show active profile

**Files:**
- Modify: `.claude/scripts/statusline.sh`

- [ ] **Step 1: Read current statusline.sh**

```bash
cat .claude/scripts/statusline.sh
```

Note current format (typically shows capital + time).

- [ ] **Step 2: Add profile-aware logic at the top**

Modify `statusline.sh` to start with:

```bash
#!/usr/bin/env bash
PROFILE_SCRIPT="$(dirname "$0")/profile.sh"
PROFILE="retail"
if [[ -x "$PROFILE_SCRIPT" ]]; then
  PROFILE="$(bash "$PROFILE_SCRIPT" get 2>/dev/null || echo "retail")"
fi
```

Then branch the output:

```bash
if [[ "$PROFILE" == "ftmo" ]]; then
  CURVE="$(dirname "$0")/../profiles/ftmo/memory/equity_curve.csv"
  if [[ -f "$CURVE" && $(wc -l < "$CURVE") -gt 1 ]]; then
    LAST_EQ="$(tail -n1 "$CURVE" | cut -d',' -f2)"
    # Calcular diario rápido (python one-liner)
    DAILY="$(python3 "$(dirname "$0")/guardian.py" --profile ftmo --action status --brief 2>/dev/null || echo "N/A")"
    echo "[FTMO \$10k] Equity: \$$LAST_EQ  •  $DAILY"
  else
    echo "[FTMO \$10k] Equity: \$10,000 (initial — run /equity)"
  fi
else
  # Preservar retail (lee capital del config)
  CAP="$(grep -oE 'Capital actual:[^$]*\$[0-9.]+' "$(dirname "$0")/../profiles/retail/config.md" 2>/dev/null | head -1 | grep -oE '\$[0-9.]+')"
  echo "[RETAIL ${CAP:-\$13.63}] Setup: Mean Reversion 15m  •  $(date +'%H:%M MX')"
fi
```

Note: the guardian.py invocation is a forward reference — it will be a no-op fallback until Task 14 creates guardian.py. The `|| echo "N/A"` handles the absence gracefully.

- [ ] **Step 3: Test under both profiles**

```bash
bash .claude/scripts/profile.sh set retail
bash .claude/scripts/statusline.sh
```

Expected: `[RETAIL $13.63] Setup: Mean Reversion 15m  •  HH:MM MX`

```bash
bash .claude/scripts/profile.sh set ftmo
bash .claude/scripts/statusline.sh
```

Expected: `[FTMO $10k] Equity: $10,000 (initial — run /equity)`

```bash
bash .claude/scripts/profile.sh set retail
```

- [ ] **Step 4: Commit**

```bash
git add .claude/scripts/statusline.sh
git commit -m "feat: statusline.sh profile-aware output"
```

---

## Task 10: Guardian.py — initial scaffold with tests

**Files:**
- Create: `.claude/scripts/guardian.py`
- Create: `.claude/scripts/test_guardian.py`

- [ ] **Step 1: Write the failing test for load_equity_curve**

Create `.claude/scripts/test_guardian.py`:

```python
# Unit tests for guardian.py — run with: pytest .claude/scripts/test_guardian.py -v
import sys
import tempfile
import pathlib
from datetime import datetime, date

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import guardian


def _write_curve(rows):
    """Helper: write rows to a temp CSV, return path."""
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
    tmp.write("timestamp,equity,source,note\n")
    for r in rows:
        tmp.write(",".join(str(x) for x in r) + "\n")
    tmp.close()
    return tmp.name


def test_load_empty_curve():
    path = _write_curve([])
    curve = guardian.load_equity_curve(path)
    assert curve == []


def test_load_single_row():
    path = _write_curve([
        ("2026-04-23T06:00:00", 10000.0, "manual", "initial"),
    ])
    curve = guardian.load_equity_curve(path)
    assert len(curve) == 1
    assert curve[0]["equity"] == 10000.0
    assert curve[0]["source"] == "manual"
    assert isinstance(curve[0]["timestamp"], datetime)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd ~/Documents/trading
python3 -m pytest .claude/scripts/test_guardian.py::test_load_empty_curve -v 2>&1 | head -20
```

Expected: ImportError or ModuleNotFoundError for `guardian`.

- [ ] **Step 3: Write minimal guardian.py to make tests pass**

Create `.claude/scripts/guardian.py`:

```python
"""
guardian.py — FTMO rules engine for Claude trading system.

Usage:
    python guardian.py --profile ftmo --action status
    python guardian.py --profile ftmo --action check-entry --asset BTCUSD \
                       --entry 77538 --sl 77238 --size 0.1
    python guardian.py --profile ftmo --action equity-update --value 10247
"""
import argparse
import csv
import json
import sys
from datetime import datetime, date
from pathlib import Path


def load_equity_curve(csv_path):
    """Load equity_curve.csv into list of dicts with parsed timestamps."""
    p = Path(csv_path)
    if not p.exists():
        return []
    rows = []
    with open(p, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "timestamp": datetime.fromisoformat(r["timestamp"]),
                "equity": float(r["equity"]),
                "source": r["source"],
                "note": r.get("note", ""),
            })
    rows.sort(key=lambda x: x["timestamp"])
    return rows


def main():
    # Stub — expanded in later tasks
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--action", required=True)
    args, _ = parser.parse_known_args()
    print(json.dumps({"profile": args.profile, "action": args.action, "stub": True}))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest .claude/scripts/test_guardian.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/guardian.py .claude/scripts/test_guardian.py
git commit -m "feat: guardian.py scaffold with load_equity_curve + tests"
```

---

## Task 11: Guardian — peak_equity, daily_pnl, trailing_dd

**Files:**
- Modify: `.claude/scripts/guardian.py`
- Modify: `.claude/scripts/test_guardian.py`

- [ ] **Step 1: Write failing tests for the three functions**

Append to `test_guardian.py`:

```python
def test_peak_equity_empty():
    assert guardian.peak_equity([]) == 0.0


def test_peak_equity_single():
    curve = [{"timestamp": datetime(2026,4,23,6,0), "equity": 10000.0, "source": "m", "note": ""}]
    assert guardian.peak_equity(curve) == 10000.0


def test_peak_equity_multiple():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0), "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,23,9,0), "equity": 10200.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,23,12,0), "equity": 10150.0, "source": "m", "note": ""},
    ]
    assert guardian.peak_equity(curve) == 10200.0


def test_daily_pnl_no_data():
    assert guardian.daily_pnl([], date(2026,4,23)) == 0.0


def test_daily_pnl_single_point_no_baseline():
    curve = [{"timestamp": datetime(2026,4,23,9,0), "equity": 10180.0, "source": "m", "note": ""}]
    # Only one point today — can't compute intraday P&L
    assert guardian.daily_pnl(curve, date(2026,4,23)) == 0.0


def test_daily_pnl_positive():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0), "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,23,9,0), "equity": 10180.0, "source": "m", "note": ""},
    ]
    assert guardian.daily_pnl(curve, date(2026,4,23)) == 180.0


def test_daily_pnl_negative():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0), "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,23,14,0), "equity": 9780.0, "source": "m", "note": ""},
    ]
    assert guardian.daily_pnl(curve, date(2026,4,23)) == -220.0


def test_trailing_dd_no_peak():
    curve = [{"timestamp": datetime(2026,4,23,6,0), "equity": 10000.0, "source": "m", "note": ""}]
    assert guardian.trailing_dd(curve) == 0.0


def test_trailing_dd_in_drawdown():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0), "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,24,10,0), "equity": 10400.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,25,9,0), "equity": 10250.0, "source": "m", "note": ""},
    ]
    # Peak 10400, current 10250, dd = 150
    assert guardian.trailing_dd(curve) == 150.0


def test_trailing_dd_at_new_peak():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0), "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,24,10,0), "equity": 10400.0, "source": "m", "note": ""},
    ]
    assert guardian.trailing_dd(curve) == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest .claude/scripts/test_guardian.py -v 2>&1 | tail -30
```

Expected: `AttributeError: module 'guardian' has no attribute 'peak_equity'` (or similar).

- [ ] **Step 3: Implement the three functions in `guardian.py`**

Add after `load_equity_curve`:

```python
def peak_equity(curve):
    """Highest equity value in the curve. 0.0 if empty."""
    if not curve:
        return 0.0
    return max(r["equity"] for r in curve)


def daily_pnl(curve, target_date):
    """Equity delta for a specific calendar date.
    Returns 0.0 if no data or only one point on the date.
    """
    today_rows = [r for r in curve if r["timestamp"].date() == target_date]
    if len(today_rows) < 2:
        return 0.0
    # Sorted chronologically by load_equity_curve
    return today_rows[-1]["equity"] - today_rows[0]["equity"]


def trailing_dd(curve):
    """Drawdown from the peak equity. Positive value = in drawdown.
    0.0 if empty or at new peak.
    """
    if not curve:
        return 0.0
    peak = peak_equity(curve)
    last = curve[-1]["equity"]
    dd = peak - last
    return max(0.0, dd)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest .claude/scripts/test_guardian.py -v
```

Expected: all 11 tests pass (2 from Task 10 + 9 new).

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/guardian.py .claude/scripts/test_guardian.py
git commit -m "feat: guardian peak_equity, daily_pnl, trailing_dd with tests"
```

---

## Task 12: Guardian — best_day_ratio and count helpers

**Files:**
- Modify: `.claude/scripts/guardian.py`
- Modify: `.claude/scripts/test_guardian.py`

- [ ] **Step 1: Write failing tests**

Append to `test_guardian.py`:

```python
def test_best_day_ratio_no_profit():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0), "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,23,16,0), "equity": 10000.0, "source": "m", "note": ""},
    ]
    best, total = guardian.best_day_ratio(curve)
    assert best == 0.0
    assert total == 0.0


def test_best_day_ratio_single_day():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0), "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,23,16,0), "equity": 10180.0, "source": "m", "note": ""},
    ]
    best, total = guardian.best_day_ratio(curve)
    assert best == 180.0
    assert total == 180.0


def test_best_day_ratio_multiple_days_balanced():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0),  "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,23,16,0), "equity": 10150.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,24,6,0),  "equity": 10150.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,24,16,0), "equity": 10300.0, "source": "m", "note": ""},
    ]
    # Day 1 profit 150, day 2 profit 150, total 300, best 150, ratio 0.5
    best, total = guardian.best_day_ratio(curve)
    assert best == 150.0
    assert total == 300.0


def test_best_day_ratio_one_big_day():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0),  "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,23,16,0), "equity": 10600.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,24,6,0),  "equity": 10600.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,24,16,0), "equity": 10700.0, "source": "m", "note": ""},
    ]
    # Best 600, total 700, ratio 0.857 — violates Best Day Rule
    best, total = guardian.best_day_ratio(curve)
    assert best == 600.0
    assert total == 700.0


def test_best_day_ratio_ignores_losing_days():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0),  "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,23,16,0), "equity": 10200.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,24,6,0),  "equity": 10200.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,24,16,0), "equity": 10100.0, "source": "m", "note": ""},  # losing day
    ]
    best, total = guardian.best_day_ratio(curve)
    assert best == 200.0
    assert total == 200.0  # Only positive days counted
```

- [ ] **Step 2: Run tests, verify fail**

```bash
python3 -m pytest .claude/scripts/test_guardian.py -v 2>&1 | tail -10
```

- [ ] **Step 3: Implement `best_day_ratio` and helpers**

Append to `guardian.py`:

```python
def day_profits(curve):
    """Dict mapping date -> profit for that date (equity end - equity start).
    Only includes dates with 2+ entries.
    """
    by_date = {}
    for row in curve:
        d = row["timestamp"].date()
        by_date.setdefault(d, []).append(row)
    result = {}
    for d, rows in by_date.items():
        if len(rows) < 2:
            continue
        rows.sort(key=lambda x: x["timestamp"])
        result[d] = rows[-1]["equity"] - rows[0]["equity"]
    return result


def best_day_ratio(curve):
    """Returns (best_day_profit, total_positive_profit).
    Only positive days are counted toward total.
    """
    profits = day_profits(curve)
    positive = [p for p in profits.values() if p > 0]
    if not positive:
        return (0.0, 0.0)
    return (max(positive), sum(positive))
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest .claude/scripts/test_guardian.py -v
```

Expected: 16 total tests pass.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/guardian.py .claude/scripts/test_guardian.py
git commit -m "feat: guardian best_day_ratio + day_profits with tests"
```

---

## Task 13: Guardian — config loader and check_entry

**Files:**
- Modify: `.claude/scripts/guardian.py`
- Modify: `.claude/scripts/test_guardian.py`

- [ ] **Step 1: Write failing tests for config loader**

Append to `test_guardian.py`:

```python
def test_load_ftmo_config(tmp_path):
    cfg = tmp_path / "config.md"
    cfg.write_text("""# FTMO

Some prose.

```yaml
challenge_type: 1-step
initial_capital: 10000
max_daily_loss_pct: 3
max_total_trailing_pct: 10
best_day_cap_pct: 50
risk_per_trade_pct: 0.5
max_trades_per_day: 2
max_sl_consecutive: 2
```
""")
    c = guardian.load_profile_config(str(cfg))
    assert c["initial_capital"] == 10000
    assert c["max_daily_loss_pct"] == 3
    assert c["max_trades_per_day"] == 2
```

- [ ] **Step 2: Write failing tests for check_entry**

Append to `test_guardian.py`:

```python
CFG_DEFAULT = {
    "initial_capital": 10000,
    "max_daily_loss_pct": 3,
    "max_total_trailing_pct": 10,
    "best_day_cap_pct": 50,
    "risk_per_trade_pct": 0.5,
    "max_trades_per_day": 2,
    "max_sl_consecutive": 2,
}


def test_check_entry_ok_fresh_day():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0), "equity": 10000.0, "source": "m", "note": ""},
    ]
    trade = {"asset": "BTCUSD", "entry": 77538, "sl": 77238, "loss_if_sl": 30}
    result = guardian.check_entry(CFG_DEFAULT, curve, trade, now=datetime(2026,4,23,9,0))
    assert result["verdict"] == "OK"
    assert result["blocking"] is False


def test_check_entry_block_daily_breach():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0),  "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,23,10,0), "equity":  9780.0, "source": "m", "note": ""},  # already -220
    ]
    trade = {"asset": "BTCUSD", "entry": 77538, "sl": 77238, "loss_if_sl": 100}
    # If SL hits: -220 - 100 = -320 = -3.2% → BREACH daily limit 3% ($300)
    result = guardian.check_entry(CFG_DEFAULT, curve, trade, now=datetime(2026,4,23,11,0))
    assert result["verdict"] in ("BLOCK_SIZE", "BLOCK_HARD")
    assert result["blocking"] is True


def test_check_entry_block_hard_daily_already_breached():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0),  "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,23,10,0), "equity":  9690.0, "source": "m", "note": ""},  # -310, past 3%
    ]
    trade = {"asset": "BTCUSD", "entry": 77538, "sl": 77238, "loss_if_sl": 50}
    result = guardian.check_entry(CFG_DEFAULT, curve, trade, now=datetime(2026,4,23,11,0))
    assert result["verdict"] == "BLOCK_HARD"
    assert "daily" in result["reason"].lower()


def test_check_entry_warn_trailing_close_to_limit():
    curve = [
        {"timestamp": datetime(2026,4,23,6,0),  "equity": 10000.0, "source": "m", "note": ""},
        {"timestamp": datetime(2026,4,24,9,0),  "equity": 10500.0, "source": "m", "note": ""},  # peak
        {"timestamp": datetime(2026,4,25,10,0), "equity":  9700.0, "source": "m", "note": ""},  # dd $800 = 8%
    ]
    trade = {"asset": "BTCUSD", "entry": 77538, "sl": 77238, "loss_if_sl": 50}
    result = guardian.check_entry(CFG_DEFAULT, curve, trade, now=datetime(2026,4,25,11,0))
    # Should warn but not block (trailing is WARN not BLOCK)
    assert result["verdict"] in ("OK_WITH_WARN", "BLOCK_SIZE")
    assert any("trailing" in w.lower() for w in result.get("warnings", []))


def test_check_entry_block_max_trades():
    # Simulate 2 trades already today via markers in notes
    curve = [
        {"timestamp": datetime(2026,4,23,6,0),  "equity": 10000.0, "source": "m", "note": "init"},
        {"timestamp": datetime(2026,4,23,8,0),  "equity": 10080.0, "source": "trade", "note": "BTC TP1"},
        {"timestamp": datetime(2026,4,23,11,0), "equity": 10050.0, "source": "trade", "note": "ETH SL"},
    ]
    trade = {"asset": "BTCUSD", "entry": 77538, "sl": 77238, "loss_if_sl": 50}
    result = guardian.check_entry(CFG_DEFAULT, curve, trade, now=datetime(2026,4,23,12,0))
    assert result["verdict"] == "BLOCK_HARD"
    assert "trades" in result["reason"].lower()
```

- [ ] **Step 3: Run tests, verify fail**

```bash
python3 -m pytest .claude/scripts/test_guardian.py -v 2>&1 | tail -10
```

- [ ] **Step 4: Implement config loader**

Add to `guardian.py`:

```python
import re

def load_profile_config(config_md_path):
    """Parse the YAML block inside config.md. Returns dict."""
    text = Path(config_md_path).read_text()
    # Find first ```yaml ... ``` block
    m = re.search(r"```yaml\s*\n(.*?)\n```", text, re.DOTALL)
    if not m:
        raise ValueError(f"No YAML block in {config_md_path}")
    yaml_text = m.group(1)
    # Simple YAML parse (numeric/string values only, no nesting)
    result = {}
    for line in yaml_text.splitlines():
        line = line.split("#", 1)[0].strip()  # strip inline comments
        if not line:
            continue
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()
        # Try numeric
        try:
            if "." in val:
                result[key] = float(val)
            else:
                result[key] = int(val)
        except ValueError:
            result[key] = val
    return result
```

- [ ] **Step 5: Implement check_entry**

Add to `guardian.py`:

```python
def _count_trades_today(curve, target_date):
    """Rows with source == 'trade' dated today."""
    return sum(
        1 for r in curve
        if r["timestamp"].date() == target_date and r["source"] == "trade"
    )


def _consecutive_sl_today(curve, target_date):
    """Count trailing consecutive SL events today (based on 'SL' substring in note)."""
    today_trades = [
        r for r in curve
        if r["timestamp"].date() == target_date and r["source"] == "trade"
    ]
    if not today_trades:
        return 0
    today_trades.sort(key=lambda x: x["timestamp"])
    count = 0
    for r in reversed(today_trades):
        if "SL" in r["note"].upper():
            count += 1
        else:
            break
    return count


def check_entry(cfg, curve, trade, now=None):
    """Evaluates whether the proposed trade respects all rules.

    trade dict must include: asset, entry, sl, loss_if_sl (pre-computed USD at SL).
    Returns dict with: verdict, blocking, reason, warnings, size_adjustment.
    """
    if now is None:
        now = datetime.now()
    today = now.date()
    initial = cfg.get("initial_capital", 10000)
    daily_limit_usd = initial * cfg.get("max_daily_loss_pct", 3) / 100.0
    trailing_limit_usd = initial * cfg.get("max_total_trailing_pct", 10) / 100.0
    trailing_warn_threshold_usd = trailing_limit_usd * 0.8
    best_day_cap_pct = cfg.get("best_day_cap_pct", 50)
    best_day_info_threshold = best_day_cap_pct / 100.0 * 0.9  # 0.45 if cap is 50

    loss_if_sl = trade["loss_if_sl"]
    warnings = []

    # REGLA 4: Max trades/día
    trades_today = _count_trades_today(curve, today)
    if trades_today >= cfg.get("max_trades_per_day", 2):
        return {
            "verdict": "BLOCK_HARD",
            "blocking": True,
            "reason": f"Max trades/día ({trades_today}/{cfg['max_trades_per_day']}) alcanzado.",
            "warnings": [],
            "size_adjustment": None,
        }

    # REGLA 5: 2 SLs consecutivos
    if _consecutive_sl_today(curve, today) >= cfg.get("max_sl_consecutive", 2):
        return {
            "verdict": "BLOCK_HARD",
            "blocking": True,
            "reason": "2 SLs consecutivos hoy. STOP por regla psicológica.",
            "warnings": [],
            "size_adjustment": None,
        }

    # REGLA 1: Daily 3%
    daily = daily_pnl(curve, today)
    daily_after_sl = daily - loss_if_sl
    if daily_after_sl <= -daily_limit_usd:
        # Check if ANY size avoids breach
        margin_remaining = daily_limit_usd + daily  # how much more we can lose today
        if margin_remaining <= 0:
            return {
                "verdict": "BLOCK_HARD",
                "blocking": True,
                "reason": (
                    f"Daily loss ya en ${-daily:.2f} ({-daily/initial*100:.2f}%). "
                    f"Ningún size permitido hoy. Reset mañana 06:00 MX."
                ),
                "warnings": [],
                "size_adjustment": None,
            }
        # Size adjustment
        if loss_if_sl > 0:
            size_adj_factor = margin_remaining / loss_if_sl
            return {
                "verdict": "BLOCK_SIZE",
                "blocking": True,
                "reason": (
                    f"Size propuesto pierde ${loss_if_sl:.2f} si SL. "
                    f"Daily margin restante ${margin_remaining:.2f}. "
                    f"Reduce size a {size_adj_factor:.2%} del propuesto."
                ),
                "warnings": [],
                "size_adjustment": size_adj_factor,
            }

    # REGLA 2: Trailing 10% WARN
    dd = trailing_dd(curve)
    dd_after_sl = dd + loss_if_sl
    if dd_after_sl >= trailing_warn_threshold_usd:
        warnings.append(
            f"Trailing DD iría a ${dd_after_sl:.2f} "
            f"({dd_after_sl/initial*100:.1f}% del capital) — cerca del límite 10%."
        )

    # REGLA 3: Best Day INFO
    best, total = best_day_ratio(curve)
    if total > 0:
        ratio = best / total
        if ratio >= best_day_info_threshold:
            warnings.append(
                f"Best day ratio {ratio*100:.0f}% (cap {best_day_cap_pct}%). "
                "Distribuye más en próximos días."
            )

    verdict = "OK_WITH_WARN" if warnings else "OK"
    return {
        "verdict": verdict,
        "blocking": False,
        "reason": "Todas las reglas OK" if not warnings else "OK con advertencias",
        "warnings": warnings,
        "size_adjustment": None,
    }
```

- [ ] **Step 6: Run tests**

```bash
python3 -m pytest .claude/scripts/test_guardian.py -v
```

Expected: all tests pass (~22 total).

- [ ] **Step 7: Commit**

```bash
git add .claude/scripts/guardian.py .claude/scripts/test_guardian.py
git commit -m "feat: guardian check_entry rules engine + config loader"
```

---

## Task 14: Guardian — CLI interface with argparse

**Files:**
- Modify: `.claude/scripts/guardian.py`
- Modify: `.claude/scripts/test_guardian.py`

- [ ] **Step 1: Write failing test for CLI dispatch**

Append to `test_guardian.py`:

```python
import subprocess
import json

def test_cli_status_returns_json(tmp_path):
    """End-to-end: run guardian.py --action status with an empty profile."""
    # Setup temp profile structure
    profile_dir = tmp_path / "profiles" / "ftmo"
    (profile_dir / "memory").mkdir(parents=True)
    (profile_dir / "config.md").write_text("""```yaml
challenge_type: 1-step
initial_capital: 10000
max_daily_loss_pct: 3
max_total_trailing_pct: 10
best_day_cap_pct: 50
risk_per_trade_pct: 0.5
max_trades_per_day: 2
max_sl_consecutive: 2
```""")
    (profile_dir / "memory" / "equity_curve.csv").write_text("timestamp,equity,source,note\n")

    script = str(Path(__file__).parent / "guardian.py")
    result = subprocess.run(
        [sys.executable, script, "--profile", "ftmo", "--action", "status",
         "--profile-root", str(tmp_path / "profiles")],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["profile"] == "ftmo"
    assert "equity_current" in data
```

- [ ] **Step 2: Run tests to verify fail**

```bash
python3 -m pytest .claude/scripts/test_guardian.py::test_cli_status_returns_json -v
```

Expected: fail (CLI doesn't return structured JSON yet).

- [ ] **Step 3: Rewrite `main()` in guardian.py**

Replace the existing `main()` with:

```python
def _action_status(cfg, curve):
    """Build status payload for --action status."""
    initial = cfg.get("initial_capital", 10000)
    if not curve:
        return {
            "equity_current": initial,
            "equity_peak": initial,
            "daily_pnl": 0.0,
            "daily_pnl_pct": 0.0,
            "trailing_dd": 0.0,
            "trailing_dd_pct": 0.0,
            "best_day": 0.0,
            "total_profit": 0.0,
            "best_day_ratio": 0.0,
        }
    today = date.today()
    current = curve[-1]["equity"]
    peak = peak_equity(curve)
    daily = daily_pnl(curve, today)
    dd = trailing_dd(curve)
    best, total = best_day_ratio(curve)
    return {
        "equity_current": current,
        "equity_peak": peak,
        "daily_pnl": daily,
        "daily_pnl_pct": (daily / initial) * 100,
        "trailing_dd": dd,
        "trailing_dd_pct": (dd / initial) * 100,
        "best_day": best,
        "total_profit": total,
        "best_day_ratio": (best / total) if total > 0 else 0.0,
    }


def _action_equity_update(curve_path, value, note=""):
    """Append a new row to equity_curve.csv."""
    ts = datetime.utcnow().replace(microsecond=0).isoformat()
    with open(curve_path, "a") as f:
        f.write(f"{ts},{value},manual,{note}\n")


def _action_check_entry(cfg, curve, args):
    trade = {
        "asset": args.asset,
        "entry": float(args.entry),
        "sl": float(args.sl),
        "loss_if_sl": float(args.loss_if_sl),
    }
    return check_entry(cfg, curve, trade)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True, choices=["ftmo", "retail"])
    parser.add_argument("--action", required=True,
                        choices=["status", "check-entry", "equity-update"])
    parser.add_argument("--profile-root",
                        default=str(Path(__file__).parent.parent / "profiles"))
    parser.add_argument("--brief", action="store_true",
                        help="Terse one-line output for statusline")
    # check-entry args
    parser.add_argument("--asset")
    parser.add_argument("--entry")
    parser.add_argument("--sl")
    parser.add_argument("--loss-if-sl", dest="loss_if_sl")
    # equity-update args
    parser.add_argument("--value")
    parser.add_argument("--note", default="")

    args = parser.parse_args()

    profile_root = Path(args.profile_root)
    config_path = profile_root / args.profile / "config.md"
    curve_path = profile_root / args.profile / "memory" / "equity_curve.csv"

    if args.action == "equity-update":
        if args.value is None:
            print("ERROR: --value required", file=sys.stderr)
            sys.exit(2)
        _action_equity_update(str(curve_path), float(args.value), args.note)
        print(json.dumps({"profile": args.profile, "action": "equity-update",
                          "equity": float(args.value), "ok": True}))
        return

    # For status and check-entry, load config and curve
    cfg = load_profile_config(str(config_path))
    curve = load_equity_curve(str(curve_path))

    if args.action == "status":
        payload = _action_status(cfg, curve)
        payload["profile"] = args.profile
        if args.brief:
            # One-line for statusline
            daily = payload["daily_pnl"]
            dd = payload["trailing_dd"]
            print(
                f"Daily: ${daily:+.0f} ({daily/cfg['initial_capital']*100:+.1f}%) "
                f"• DD: ${dd:.0f} ({dd/cfg['initial_capital']*100:.1f}%/10%)"
            )
        else:
            print(json.dumps(payload, indent=2))
        return

    if args.action == "check-entry":
        result = _action_check_entry(cfg, curve, args)
        result["profile"] = args.profile
        print(json.dumps(result, indent=2))
        return


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run all tests**

```bash
python3 -m pytest .claude/scripts/test_guardian.py -v
```

Expected: all tests pass (~23 total).

- [ ] **Step 5: Manual smoke test**

```bash
bash .claude/scripts/profile.sh set ftmo
python3 .claude/scripts/guardian.py --profile ftmo --action status
```

Expected: JSON with equity_current=10000, all metrics 0.

```bash
python3 .claude/scripts/guardian.py --profile ftmo --action status --brief
```

Expected: one-line summary.

```bash
bash .claude/scripts/profile.sh set retail
```

- [ ] **Step 6: Commit**

```bash
git add .claude/scripts/guardian.py .claude/scripts/test_guardian.py
git commit -m "feat: guardian CLI interface (status, check-entry, equity-update)"
```

---

## Task 15: /equity command

**Files:**
- Create: `.claude/commands/equity.md`

- [ ] **Step 1: Write command definition**

```markdown
Actualiza el equity actual del profile FTMO (no aplica a retail).

Uso:
- `/equity <valor>` — registra nuevo equity en USD
- `/equity <valor> "<nota>"` — con nota descriptiva opcional
- `/equity` (sin arg) — muestra último equity conocido

Pasos que ejecuta Claude:

1. Lee profile activo: `bash .claude/scripts/profile.sh get`

2. Si profile != "ftmo":
   - Mensaje: "/equity solo aplica al profile FTMO. Profile activo: <X>. Usa /profile ftmo para switchear."
   - NO ejecutar

3. Si sin argumentos:
   - Lee última línea de `.claude/profiles/ftmo/memory/equity_curve.csv`
   - Muestra: "Último equity: $X @ YYYY-MM-DDThh:mm (source, nota)"
   - Si curve vacío: "Sin actualizaciones. Initial: $10,000"

4. Si hay argumento numérico:
   - Valida que es número positivo razonable (entre 1000 y 50000)
   - Ejecuta: `python3 .claude/scripts/guardian.py --profile ftmo --action equity-update --value <valor> [--note "<nota>"]`
   - Devuelve: JSON del update + recalcula status
   - Ejecuta: `python3 .claude/scripts/guardian.py --profile ftmo --action status` y muestra formateado:
     - Equity actual: $X (+N.NN%)
     - Daily PnL: $X (N.NN% / 3% limit)
     - Trailing DD: $X (N.NN% / 10% limit)
     - Best Day ratio: N% (cap 50%)

5. Si el valor sube contra peak anterior → nota visual: "🎯 Nuevo peak!"

6. Si el valor cruza algún threshold peligroso → aviso en rojo:
   - daily_pnl_pct <= -2.5% → "⚠️ 2.5% daily loss, cerca del 3% limit"
   - trailing_dd_pct >= 8.0% → "⚠️ Trailing DD 80% del límite"
   - best_day_ratio >= 0.45 → "ℹ️ Best day cerca del cap 50%"
```

- [ ] **Step 2: Verify file**

```bash
wc -l .claude/commands/equity.md
```

Expected: >30 lines.

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/equity.md
git commit -m "feat: /equity command for FTMO equity updates"
```

---

## Task 16: /challenge command

**Files:**
- Create: `.claude/commands/challenge.md`

- [ ] **Step 1: Write command definition**

```markdown
Dashboard de progreso del challenge FTMO.

Uso:
- `/challenge` — muestra estado completo del challenge

Pasos que ejecuta Claude:

1. Lee profile activo. Si != "ftmo":
   - Mensaje: "/challenge solo aplica al profile FTMO. Profile activo: <X>."
   - NO ejecutar

2. Lee `.claude/profiles/ftmo/config.md` y `.claude/profiles/ftmo/memory/challenge_progress.md`

3. Invoca: `python3 .claude/scripts/guardian.py --profile ftmo --action status`

4. Formatea el output:

```
╔══════════════════════════════════════════════╗
║  FTMO CHALLENGE DASHBOARD                     ║
║  Tipo: 1-Step $10,000                         ║
║  Status: <ACTIVE | PREPARING | BREACHED>       ║
╠══════════════════════════════════════════════╣
║  PROFIT TARGET 10% ($1,000)                   ║
║  Acumulado: $X ($P%)                          ║
║  Faltan:    $Y                                ║
║                                               ║
║  EQUITY                                       ║
║  Actual: $X (YY% desde inicio)                ║
║  Peak:   $X                                   ║
║                                               ║
║  REGLAS                                       ║
║  □ Daily 3%:     Used $X (Y% / 3% hoy)        ║
║  □ Trailing 10%: Used $X (Y% / 10% from peak) ║
║  □ Best Day 50%: Ratio Y% (cap 50%)           ║
║  □ Max trades/día: N/2 usados hoy             ║
║                                               ║
║  MÉTRICAS ROLLING                             ║
║  Días activos: N                              ║
║  WR: Y%                                       ║
║  Avg R: Y                                     ║
║  Profit factor: Y                             ║
║                                               ║
║  OVERRIDES GUARDIAN: N (review needed si >0)  ║
╚══════════════════════════════════════════════╝
```

5. Alertas si aplica:
   - Si profit_pct >= 10.0 → "🎯 CHALLENGE PASSED — Contacta FTMO para verificación"
   - Si cualquier regla BREACHED → "🚫 CHALLENGE BREACHED — <regla>. Cuenta nueva requerida."
   - Si overrides > 0 → "📋 Revisa overrides.log al /journal"
```

- [ ] **Step 2: Verify file**

```bash
wc -l .claude/commands/challenge.md
```

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/challenge.md
git commit -m "feat: /challenge command dashboard"
```

---

## Task 17: Modify /status to be profile-aware

**Files:**
- Modify: `.claude/commands/status.md`

- [ ] **Step 1: Read current status.md**

```bash
cat .claude/commands/status.md
```

- [ ] **Step 2: Rewrite to branch by profile**

Replace full content of `.claude/commands/status.md` with:

```markdown
Muestra el estado completo del sistema según el profile activo.

Pasos que ejecuta Claude:

1. Lee profile activo: `PROFILE=$(bash .claude/scripts/profile.sh get)`

2. SI profile == "retail":
   - Lee `.claude/profiles/retail/config.md` (capital, estrategia activa)
   - Lee `.claude/profiles/retail/memory/trading_log.md` (últimos trades)
   - Lee `.claude/profiles/retail/memory/market_regime.md` (niveles vigentes)
   - Muestra statusline retail expandido:
     ```
     [RETAIL $13.63]
     Estrategia: Mean Reversion 15m
     Régimen: <detecta vía regime-detector rápido o cachea>
     Hora MX: HH:MM
     Trades hoy: 0/3
     Último trade: <fecha> <resultado>
     ```

3. SI profile == "ftmo":
   - Invoca: `python3 .claude/scripts/guardian.py --profile ftmo --action status`
   - Lee `.claude/profiles/ftmo/memory/challenge_progress.md`
   - Muestra statusline FTMO expandido:
     ```
     [FTMO $10k]
     Equity: $X (+Y%)
     Daily PnL: $X (Y% / 3% limit)
     Trailing DD: $X (Y% / 10% limit)
     Best Day ratio: Y% (cap 50%)
     Trades hoy: N/2
     Estrategia: FTMO-Conservative
     Asset vigilancia: <top 1-2 del morning-analyst-ftmo>
     ```

4. SI profile no reconocido:
   - Muestra warning: "Profile desconocido: <X>. Corre /profile ftmo o /profile retail."

5. Al final de cualquier output, incluye una línea: "Última actualización: <timestamp>. Cambiar profile: /profile ftmo|retail"
```

- [ ] **Step 3: Verify**

```bash
wc -l .claude/commands/status.md
```

- [ ] **Step 4: Commit**

```bash
git add .claude/commands/status.md
git commit -m "refactor: /status profile-aware"
```

---

## Task 18: Modify /risk to call guardian for FTMO

**Files:**
- Modify: `.claude/commands/risk.md`

- [ ] **Step 1: Read current risk.md**

```bash
cat .claude/commands/risk.md
```

- [ ] **Step 2: Prepend profile-aware logic**

Replace full content with:

```markdown
Calcula position sizing según el profile activo.

Pasos que ejecuta Claude:

1. Lee profile: `PROFILE=$(bash .claude/scripts/profile.sh get)`

2. SI profile == "retail":
   - Usa regla clásica 2% del capital actual (desde profiles/retail/config.md)
   - Despacha al agente `risk-manager` con parámetros retail
   - Fórmula: `risk_usd = capital * 0.02; size = risk_usd / (sl_distance / entry) / leverage`

3. SI profile == "ftmo":
   - Carga config desde `.claude/profiles/ftmo/config.md` (risk_per_trade_pct, leverage)
   - Lee equity actual via `python3 .claude/scripts/guardian.py --profile ftmo --action status`
   - Lee pip_value del asset desde `.claude/profiles/ftmo/memory/mt5_symbols.md`
   - Si pip_value es "PENDING" → ERROR: "Pip value de <asset> no validado. Pega screenshot MT5 Specification."
   - Fórmula:
     ```
     risk_usd = equity * (risk_per_trade_pct / 100)  # 0.5% por default
     sl_pips = abs(entry - sl)
     lots = risk_usd / (sl_pips * pip_value_per_lot)
     lots = round(lots, 2)
     ```
   - Simula worst-case en guardian:
     `python3 guardian.py --profile ftmo --action check-entry --asset <X> --entry <E> --sl <SL> --loss-if-sl <risk_usd>`
   - Si guardian retorna BLOCK_SIZE → aplica size_adjustment factor
   - Si BLOCK_HARD → NO-GO total

4. Output:
   - Lots (FTMO) o BTC size + margin (retail)
   - Capital a arriesgar ($X)
   - Leverage
   - Guardian veredicto (solo FTMO)

5. Siempre incluye disclaimer: "Leverage con dinero real puede liquidar capital. Tu decides."
```

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/risk.md
git commit -m "refactor: /risk profile-aware with guardian integration"
```

---

## Task 19: Modify /validate to call guardian after 4 filters

**Files:**
- Modify: `.claude/commands/validate.md`

- [ ] **Step 1: Read current validate.md**

```bash
cat .claude/commands/validate.md
```

- [ ] **Step 2: Rewrite for dual-profile validation**

Replace full content with:

```markdown
Valida un setup de entrada ANTES de ejecutar el trade.

Pasos que ejecuta Claude:

1. Lee profile: `PROFILE=$(bash .claude/scripts/profile.sh get)`

2. SI profile == "retail":
   - Despacha agente `trade-validator`
   - Verifica los 4 filtros técnicos del config retail (Donchian + RSI + BB + close color)
   - Además 5° filtro ML opcional (vía /ml si el setup es 4/4)
   - Veredicto: GO / NO-GO tradicional

3. SI profile == "ftmo":
   - Despacha agente `trade-validator` con instrucción "usar filtros de FTMO-Conservative"
   - Verifica los 7 filtros (ver `profiles/ftmo/strategy.md` sección 5.4)
   - Si todos los 7 OK:
     - Invoca guardian:
       ```
       python3 .claude/scripts/guardian.py --profile ftmo --action check-entry \
         --asset <ASSET> --entry <ENTRY> --sl <SL> --loss-if-sl <USD_LOSS>
       ```
     - Procesa veredicto:
       - OK → "GO absoluto"
       - OK_WITH_WARN → muestra warnings en rojo, pide confirmación explícita del usuario
       - BLOCK_SIZE → "size reducir a X% del propuesto, luego confirmar"
       - BLOCK_HARD → "NO-GO. Razón: <reason>. Opción override: escribir literalmente 'OVERRIDE GUARDIAN'"

4. Formato de output estándar:

```
TÉCNICO: N/N filtros ✓
GUARDIAN: <VEREDICTO> — <razón>

Setup:
  Asset:  <X>
  Entry:  <P>
  SL:     <P> (dist <D%>)
  TP1:    <P> (R:R 1.5)
  TP2:    <P> (R:R 3.0)
  Size:   <lots/BTC> (risk $<X>)

Acción: <GO | CONFIRM | NO-GO>
```

5. Si usuario escribe "OVERRIDE GUARDIAN":
   - Append a `.claude/profiles/ftmo/memory/overrides.log`:
     `<timestamp>|ftmo|<rule_violated>|<equity>|<trade_json>|<user_reason>`
   - Procede con "GO" pero con warning grande
```

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/validate.md
git commit -m "refactor: /validate profile-aware with guardian gate for FTMO"
```

---

## Task 20: Modify /journal to be profile-aware

**Files:**
- Modify: `.claude/commands/journal.md`

- [ ] **Step 1: Read current journal.md**

```bash
cat .claude/commands/journal.md
```

- [ ] **Step 2: Rewrite**

Replace full content with:

```markdown
Cierra el día y actualiza el log del profile activo.

Pasos que ejecuta Claude:

1. Lee profile: `PROFILE=$(bash .claude/scripts/profile.sh get)`

2. Despacha `journal-keeper` agent con el profile explícito.

3. Agent escribe al log correspondiente:
   - retail → `.claude/profiles/retail/memory/trading_log.md`
   - ftmo   → `.claude/profiles/ftmo/memory/trading_log.md` + actualiza `challenge_progress.md`

4. SI profile == "ftmo":
   - Lee trades del día del user (input manual: pega texto o screenshot MT5)
   - Para cada trade, append row a `equity_curve.csv` vía guardian --action equity-update
   - Recalcula: WR, avg R, best day ratio, profit factor
   - Update `challenge_progress.md` con nuevas métricas
   - Si overrides.log tiene eventos del día → lista para revisión
   - Muestra al usuario:
     - Trades del día con resultado
     - PnL neto
     - Status rules post-cierre
     - "Brechas cerca: none / <rule>"
     - Próximo paso: "/profile retail para mañana" o "continuar FTMO"

5. SI profile == "retail":
   - Comportamiento actual (3 wins log pattern).
   - journal-keeper append a `.claude/profiles/retail/memory/trading_log.md`.

6. Auto-commit al final:
   `git add <archivos profile> && git commit -m "journal: auto-save sesión <profile> <YYYY-MM-DD>"`
```

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/journal.md
git commit -m "refactor: /journal profile-aware"
```

---

## Task 21: Modify /morning to be profile-aware

**Files:**
- Modify: `.claude/commands/morning.md`

- [ ] **Step 1: Read current morning.md**

```bash
cat .claude/commands/morning.md
```

- [ ] **Step 2: Rewrite**

Replace full content with:

```markdown
Análisis matutino adaptado al profile activo.

Pasos que ejecuta Claude:

1. Lee profile: `PROFILE=$(bash .claude/scripts/profile.sh get)`

2. SI profile == "retail":
   - Despacha `morning-analyst` (el agente actual, BTC-BingX single-asset, 17 fases)
   - El agente usa niveles/memoria de `profiles/retail/memory/`

3. SI profile == "ftmo":
   - Despacha `morning-analyst-ftmo` (nuevo agente multi-asset)
   - El agente analiza los 6 assets del universo FTMO
   - Incluye guardian pre-check antes de proponer setups
   - Usa niveles/memoria de `profiles/ftmo/memory/`

4. Si argumento opcional: pasa como contexto adicional al agente (ej: "/morning sin café")
```

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/morning.md
git commit -m "refactor: /morning profile-aware dispatch"
```

---

## Task 22: Agents profile-awareness header

**Files:**
- Modify: `.claude/agents/trade-validator.md`
- Modify: `.claude/agents/journal-keeper.md`
- Modify: `.claude/agents/regime-detector.md`
- Modify: `.claude/agents/risk-manager.md`
- Modify: `.claude/agents/chart-drafter.md`
- Modify: `.claude/agents/backtest-runner.md`
- Modify: `.claude/agents/morning-analyst.md` (mark as retail-only)

- [ ] **Step 1: Define the standard header block**

This block (in Spanish, matching the codebase) must be prepended to the 6 general agents:

```markdown
## Profile awareness (obligatorio)

Antes de cualquier acción:
1. Lee `.claude/active_profile` para saber el profile activo (retail o ftmo)
2. Carga `.claude/profiles/<profile>/config.md` para capital, leverage, assets operables
3. Carga `.claude/profiles/<profile>/strategy.md` para reglas de entrada/salida
4. Escribe SOLO a memorias de `.claude/profiles/<profile>/memory/` (nunca al otro profile)
5. Las memorias globales en `.claude/memory/` aplican a ambos profiles (user_profile, morning_protocol, etc.)

Si el profile es FTMO, invoca `python3 .claude/scripts/guardian.py --profile ftmo --action <X>` donde corresponda antes de emitir veredicto final.
```

- [ ] **Step 2: Prepend to trade-validator.md**

```bash
# Read current content
cat .claude/agents/trade-validator.md | head -5
```

Use Edit tool to add the profile awareness block after the frontmatter (after the second `---` line).

- [ ] **Step 3: Repeat for 5 more agents**

Same insertion for:
- `journal-keeper.md`
- `regime-detector.md`
- `risk-manager.md`
- `chart-drafter.md`
- `backtest-runner.md`

- [ ] **Step 4: Mark morning-analyst as retail-only**

Edit `.claude/agents/morning-analyst.md` frontmatter description to add:

```markdown
**IMPORTANTE:** Este agente es específico para profile RETAIL (BTCUSDT.P BingX single-asset, 17 fases). Para profile FTMO (multi-asset) usa `morning-analyst-ftmo`.
```

Also add a guard clause at the top of the body:

```markdown
## Guard: profile retail-only

Al inicio, lee `.claude/active_profile`:
- Si profile == "ftmo" → ABORTA y devuelve: "Este agente es retail-only. Usa morning-analyst-ftmo para FTMO multi-asset."
- Si profile == "retail" → procede con protocolo 17 fases actual
```

- [ ] **Step 5: Verify each agent has the profile block**

```bash
for f in .claude/agents/{trade-validator,journal-keeper,regime-detector,risk-manager,chart-drafter,backtest-runner}.md; do
  echo "=== $f ==="
  grep -q "Profile awareness" "$f" && echo "OK" || echo "MISSING"
done
```

Expected: all 6 say OK.

- [ ] **Step 6: Commit**

```bash
git add .claude/agents/
git commit -m "feat: agents profile-aware headers + morning-analyst retail-guard"
```

---

## Task 23: Create morning-analyst-ftmo agent

**Files:**
- Create: `.claude/agents/morning-analyst-ftmo.md`

- [ ] **Step 1: Write the new agent**

```markdown
---
name: morning-analyst-ftmo
description: Multi-asset morning analyst for FTMO profile. Analyzes BTC+ETH+EURUSD+GBPUSD+NAS100+SPX500, applies asset-level regime detection, filters by session and conditions, picks 1 A-grade setup/day, integrates guardian check before proposing entry. Use PROACTIVELY cuando profile es FTMO y user inicia sesión (MX 06:00-09:00) o pide análisis matutino.
tools: WebFetch, Bash, Read, Grep, Glob, mcp__tradingview__tv_health_check, mcp__tradingview__tv_launch, mcp__tradingview__quote_get, mcp__tradingview__chart_set_symbol, mcp__tradingview__chart_set_timeframe, mcp__tradingview__data_get_ohlcv, mcp__tradingview__data_get_study_values, mcp__tradingview__draw_shape, mcp__tradingview__ui_mouse_click
---

Analista matutino multi-asset para profile FTMO. Adapta el protocolo del morning-analyst retail a las reglas FTMO-Conservative (multi-asset, guardian, Best Day compliance).

## Profile awareness

Verifica primero:
```bash
PROFILE=$(bash .claude/scripts/profile.sh get)
if [ "$PROFILE" != "ftmo" ]; then
  echo "Este agente es FTMO-only. Profile activo: $PROFILE. Aborto."
  exit 1
fi
```

## Protocolo 14 fases (adaptado de retail 17 fases)

### FASE 0 — Pre-flight TV
- `tv_health_check`, si cerrado `tv_launch`
- Valida conexión a 6 símbolos del universo

### FASE 1 — Auto-check personal
- Dormiste 6+h? Comiste? Estrés externo? Preguntar al usuario si no lo dijo.

### FASE 2 — Guardian pre-check
- `python3 .claude/scripts/guardian.py --profile ftmo --action status`
- Si trades_hoy >= 2 → ABORTA con "Max trades/día alcanzado. No hay espacio para setup."
- Si daily_pnl_pct <= -2.5% → ABORTA con "Daily loss al 80% del límite. Cierra terminal."
- Si trailing_dd_pct >= 8% → WARNING ámbar: "Trailing DD 80%+. Setups deben ser A-grade estrictamente."
- Si best_day_ratio >= 0.45 → INFO: "Best day cerca del cap. Prioriza días chicos."

### FASE 3 — Contexto macro
- F&G, DXY, VIX (FRED), noticias 12h próximas (calendar económico)
- Eventos alto impacto (NFP, CPI, FOMC) en próximas 4h → skip día o skip hasta post-dato

### FASE 4 — Régimen por asset
Por cada asset en `profiles/ftmo/config.md` (BTC, ETH, EURUSD, GBPUSD, NAS100, SPX500):
- Carga OHLCV 4H (últimas 50 velas) + 1H (últimas 30 velas) vía TV MCP
- Clasifica: RANGE | TRENDING | VOLATILE | NO_DATA
- Guarda resultado en memoria temporal

### FASE 5 — Filtros de sesión + volatilidad
- Para cada asset: ¿estamos dentro de su sesión óptima ahora o en próximas 2h?
- Para cada asset: ATR actual vs ATR medio 30d — si >1.8x → marca VOLATILE

### FASE 6 — Scoring A/B/C/D
Para cada asset operable ahora:
- A = régimen RANGE + RSI en zona (≤30 o ≥70) + BB extremo + volumen OK
- B = RANGE + 2/3 condiciones técnicas
- C = régimen ambiguo
- D = VOLATILE o NO_DATA → skip

### FASE 7 — Selección del trade del día
- 1 A-grade → ese es
- 2+ A-grades → menor spread + sesión más activa
- Todos B o peor → NO OPERAR HOY, cierra terminal

### FASE 8 — Correlaciones
- Verifica: si el setup es LONG BTC, ¿también estás long ETH por correlación?
- Si ya ganaste hoy en asset correlacionado, evita doble exposición

### FASE 9 — Niveles técnicos del asset seleccionado
- Donchian(20), BB(20,2), RSI(14), ATR
- Niveles específicos: entry zone, SL, TP1, TP2

### FASE 10 — Position sizing + guardian check
- Calcula lots con `calc_lots(asset, entry, sl, equity, risk_pct=0.5)`
- Pip value desde `profiles/ftmo/memory/mt5_symbols.md`
- Si pip_value "PENDING" → ERROR: "Valida pip value antes de operar. Pega screenshot MT5 Specification."
- Guardian check: `python3 .claude/scripts/guardian.py --profile ftmo --action check-entry --asset <X> --entry <E> --sl <SL> --loss-if-sl <USD>`
- Procesa veredicto

### FASE 11 — Dibujo en TradingView
- Limpia setup previo
- Dibuja: entry, SL, TP1, TP2 sobre el asset seleccionado

### FASE 12 — Plan entrada + checklist 12 items
- Asset, entry, SL, TP1, TP2, lots, sesión óptima
- Los 7 filtros a cumplir simultáneamente
- Hora óptima de entrada

### FASE 13 — Reglas duras recordatorio
- Max 2 trades/día
- 2 SLs → STOP
- Force exit 16:00 MX
- No overnight

### FASE 14 — VEREDICTO FINAL
Resumen ejecutivo:
- Asset seleccionado (o SKIP HOY)
- Setup exacto
- Guardian status
- Veredicto: OPERAR AHORA / ESPERAR ZONA / SKIP DAY

## Outputs
- Análisis por asset en markdown estructurado
- Niveles dibujados en TV
- Size calculada
- Guardian verdict
- Plan de acción claro con hora esperada de entry
```

- [ ] **Step 2: Verify**

```bash
wc -l .claude/agents/morning-analyst-ftmo.md
grep -c "FASE" .claude/agents/morning-analyst-ftmo.md
```

Expected: ~120 lines; 14+ FASE markers.

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/morning-analyst-ftmo.md
git commit -m "feat: morning-analyst-ftmo agent (multi-asset 14 fases)"
```

---

## Task 24: Update MEMORY.md with dual-profile index

**Files:**
- Modify: `.claude/memory/MEMORY.md`

- [ ] **Step 1: Read current**

```bash
cat .claude/memory/MEMORY.md
```

- [ ] **Step 2: Rewrite**

Full replacement:

```markdown
# Memory Index — Trading Project (Dual Profile)

## GLOBAL (ambos profiles leen)
- [User profile](user_profile.md) — Trader retail México, dual-profile FTMO + retail, capital $13.63 real + $10k FTMO demo
- [Operating window](operating_window.md) — Retail MX 06:00–23:59, FTMO 06:00–16:00
- [Communication prefs](communication_prefs.md) — Español, directo, honest-first, disclaimers
- [User goals vs reality](user_goals_reality.md) — WR realistico, expectativas calibradas
- [Morning protocol](morning_protocol.md) — Protocolo base, variantes en cada profile
- [Market context APIs](market_context_refs.md) — F&G, funding, on-chain endpoints
- [ML System](ml_system.md) — Sentiment + XGBoost (usable en ambos profiles)
- [External signals tracker](external_signals_tracker.md) — Registro de señales de comunidades

## RETAIL profile (`.claude/profiles/retail/`)
- [Config retail](../profiles/retail/config.md) — Capital $13.63, BingX, 10x leverage, BTCUSDT.P
- [Strategy retail](../profiles/retail/strategy.md) — Mean Reversion 15m
- [Trading log retail](../profiles/retail/memory/trading_log.md) — 3 wins registrados
- [Trading strategy detail](../profiles/retail/memory/trading_strategy.md)
- [Entry rules](../profiles/retail/memory/entry_rules.md) — 4 filtros
- [Backtest findings](../profiles/retail/memory/backtest_findings.md)
- [Market regime retail](../profiles/retail/memory/market_regime.md) — niveles BTC BingX
- [TradingView setup](../profiles/retail/memory/tradingview_setup.md)
- [Liquidations data](../profiles/retail/memory/liquidations_data.md)

## FTMO profile (`.claude/profiles/ftmo/`)
- [Config FTMO](../profiles/ftmo/config.md) — $10k, 1-Step, MT5, leverage 1:100, multi-asset
- [Strategy FTMO](../profiles/ftmo/strategy.md) — FTMO-Conservative (0.5%/trade, 1.5%/día)
- [Rules FTMO](../profiles/ftmo/rules.md) — 3% daily, 10% trailing, Best Day 50%
- [Challenge progress](../profiles/ftmo/memory/challenge_progress.md) — status actual
- [Trading log FTMO](../profiles/ftmo/memory/trading_log.md)
- [Equity curve](../profiles/ftmo/memory/equity_curve.csv)
- [MT5 symbols](../profiles/ftmo/memory/mt5_symbols.md) — pip values
- [Paper trading log](../profiles/ftmo/memory/paper_trading_log.md)
- [Overrides log](../profiles/ftmo/memory/overrides.log)
- [Session notes](../profiles/ftmo/memory/session_notes.md)

## Cómo Claude usa este index
1. Lee `.claude/active_profile` al inicio de cada sesión
2. Siempre carga las memorias GLOBALES
3. Carga las memorias del profile activo únicamente
4. Nunca cruza escrituras entre profiles
```

- [ ] **Step 3: Commit**

```bash
git add .claude/memory/MEMORY.md
git commit -m "docs: MEMORY.md restructured for dual-profile index"
```

---

## Task 25: CLAUDE.md — document dual-profile system

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Read current CLAUDE.md**

```bash
cat CLAUDE.md | head -40
```

- [ ] **Step 2: Add dual-profile section after the "Perfil del trader" section**

Insert this block after line with "Estilo: scalping intraday...":

```markdown
## Profile System (Dual)

El sistema soporta **2 profiles aislados**. Se switchean al inicio del día con `/profile`.

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

### Reglas de operación dual
1. **No operar ambos profiles el mismo día.** Switch al inicio de sesión.
2. **Nunca cruzar memorias** — trade FTMO no se escribe al log retail y viceversa.
3. **Guardian** (`.claude/scripts/guardian.py`) obligatorio en FTMO antes de cada entry.
4. **Statusline** muestra `[PROFILE]` en todo momento para prevenir confusión.

### Comandos específicos dual-profile
- `/profile` — ver/cambiar profile activo
- `/equity <valor>` — actualizar equity FTMO manualmente
- `/challenge` — dashboard progreso FTMO (solo ftmo)
- `/status` — estado adaptado al profile activo
- Los demás (`/morning`, `/validate`, `/risk`, `/journal`) son profile-aware
```

- [ ] **Step 3: Verify**

```bash
grep -c "Profile" CLAUDE.md
```

Expected: count increased.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: CLAUDE.md documents dual-profile system"
```

---

## Task 26: Backtest script for FTMO-Conservative strategy

**Files:**
- Create: `.claude/scripts/backtest_ftmo.py`

- [ ] **Step 1: Write the backtest script skeleton**

```python
"""
backtest_ftmo.py — Historical backtest of FTMO-Conservative strategy.

Usage:
    python backtest_ftmo.py --asset BTCUSDT --start 2026-01-22 --end 2026-04-22

Data source: uses TradingView MCP if available, else yfinance for FX.
Output: JSON summary + CSV of simulated trades.

Pass criteria (for Go to paper trading):
- WR >= 55%
- Max DD <= 5% of initial capital ($500 in $10k)
- 0 daily breaches (3% rule simulated)
- best_day_ratio <= 0.50 across backtest period
"""
import argparse
import csv
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import guardian


INITIAL_CAPITAL = 10000
RISK_PCT = 0.5
SL_PCT = 0.004
TP1_PCT = 0.006
TP2_PCT = 0.012


def load_ohlcv(asset, start, end):
    """Stub: load OHLCV data. Implementation depends on data source.

    Returns: list of dicts with keys: ts, open, high, low, close, volume
    """
    # Placeholder: in real implementation, read from CSV or call yfinance/TV
    raise NotImplementedError("Implement data loader in actual run")


def simulate_strategy(asset, ohlcv):
    """Walk forward bar-by-bar, apply FTMO-Conservative 7 filters, simulate trades."""
    trades = []
    equity = INITIAL_CAPITAL
    equity_curve = [{"timestamp": ohlcv[0]["ts"], "equity": equity, "source": "init", "note": ""}]

    for i in range(20, len(ohlcv)):  # start after warmup
        # ... compute Donchian(20), RSI(14), BB(20,2), session filter
        # ... check 7 filters
        # ... if LONG or SHORT signal triggered:
        #       simulate fill at close of current bar
        #       compute SL, TP1, TP2
        #       walk forward until one of them hits
        #       close trade, update equity, append to trades + equity_curve
        pass

    return {
        "trades": trades,
        "equity_curve": equity_curve,
        "final_equity": equity,
    }


def compute_metrics(result):
    trades = result["trades"]
    curve = result["equity_curve"]
    if not trades:
        return {"trades": 0, "wr": 0, "avg_r": 0, "max_dd": 0, "best_day_ratio": 0, "daily_breaches": 0}

    wins = sum(1 for t in trades if t["result"] in ("TP1", "TP2"))
    wr = wins / len(trades) * 100

    # Max DD
    peak = INITIAL_CAPITAL
    max_dd = 0
    for r in curve:
        peak = max(peak, r["equity"])
        dd = peak - r["equity"]
        max_dd = max(max_dd, dd)

    # Daily breaches
    breaches = 0
    # Group by date, check if daily delta ever <= -3% of initial
    by_date = {}
    for r in curve:
        d = r["timestamp"].date() if hasattr(r["timestamp"], "date") else r["timestamp"]
        by_date.setdefault(d, []).append(r)
    for d, rows in by_date.items():
        if len(rows) >= 2:
            delta = rows[-1]["equity"] - rows[0]["equity"]
            if delta <= -INITIAL_CAPITAL * 0.03:
                breaches += 1

    # Best day ratio
    best, total = guardian.best_day_ratio(curve)
    ratio = (best / total) if total > 0 else 0

    avg_r = sum(t.get("r", 0) for t in trades) / len(trades)

    return {
        "trades": len(trades),
        "wr": round(wr, 2),
        "avg_r": round(avg_r, 2),
        "max_dd": round(max_dd, 2),
        "max_dd_pct": round(max_dd / INITIAL_CAPITAL * 100, 2),
        "best_day_ratio": round(ratio, 3),
        "daily_breaches": breaches,
        "final_equity": result["final_equity"],
        "return_pct": round((result["final_equity"] - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100, 2),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--data-csv", help="Pre-downloaded OHLCV CSV instead of API")
    args = parser.parse_args()

    ohlcv = load_ohlcv(args.asset, args.start, args.end)  # will raise if not implemented
    result = simulate_strategy(args.asset, ohlcv)
    metrics = compute_metrics(result)

    # Write trades CSV
    out_path = Path(__file__).parent / f"backtest_{args.asset}_{args.start}_{args.end}.csv"
    with open(out_path, "w", newline="") as f:
        if result["trades"]:
            w = csv.DictWriter(f, fieldnames=result["trades"][0].keys())
            w.writeheader()
            w.writerows(result["trades"])

    # Print metrics JSON
    print(json.dumps(metrics, indent=2))

    # Pass/fail summary
    pass_criteria = (
        metrics["wr"] >= 55 and
        metrics["max_dd_pct"] <= 5 and
        metrics["daily_breaches"] == 0 and
        metrics["best_day_ratio"] <= 0.50
    )
    print(f"\nBACKTEST VERDICT: {'PASS — OK para paper trading' if pass_criteria else 'FAIL — refinar estrategia'}")
    sys.exit(0 if pass_criteria else 1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Note the NotImplementedError**

The `load_ohlcv` is intentionally a stub. The person implementing Fase 6 will need to plug in the real data source (TV MCP, yfinance, or pre-downloaded CSV via `--data-csv`). The skeleton is complete enough that only the data loader and the signal logic in `simulate_strategy` need filling in.

- [ ] **Step 3: Verify script is syntactically valid**

```bash
python3 -c "import ast; ast.parse(open('.claude/scripts/backtest_ftmo.py').read()); print('OK')"
```

Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add .claude/scripts/backtest_ftmo.py
git commit -m "feat: backtest_ftmo.py skeleton (load_ohlcv + simulate_strategy stubs)"
```

---

## Task 27: End-to-end integration test

**Files:**
- Create: `.claude/scripts/test_integration.sh`

- [ ] **Step 1: Write the integration test script**

```bash
#!/usr/bin/env bash
# End-to-end integration test for dual-profile system.
# Run from repo root: bash .claude/scripts/test_integration.sh

set -euo pipefail

cd "$(dirname "$0")/../.."

echo "=== TEST 1: profile.sh show/get/set ==="
bash .claude/scripts/profile.sh set retail
test "$(bash .claude/scripts/profile.sh get)" = "retail" && echo "  ✓ retail set"

bash .claude/scripts/profile.sh set ftmo
test "$(bash .claude/scripts/profile.sh get)" = "ftmo" && echo "  ✓ ftmo set"

echo ""
echo "=== TEST 2: statusline under retail ==="
bash .claude/scripts/profile.sh set retail
OUT=$(bash .claude/scripts/statusline.sh)
echo "  output: $OUT"
echo "$OUT" | grep -q "RETAIL" && echo "  ✓ retail statusline" || { echo "  ✗ retail missing"; exit 1; }

echo ""
echo "=== TEST 3: statusline under ftmo ==="
bash .claude/scripts/profile.sh set ftmo
OUT=$(bash .claude/scripts/statusline.sh)
echo "  output: $OUT"
echo "$OUT" | grep -q "FTMO" && echo "  ✓ ftmo statusline" || { echo "  ✗ ftmo missing"; exit 1; }

echo ""
echo "=== TEST 4: guardian status ==="
python3 .claude/scripts/guardian.py --profile ftmo --action status > /tmp/guardian_status.json
python3 -c "import json; d=json.load(open('/tmp/guardian_status.json')); assert d['profile']=='ftmo'; assert d['equity_current']==10000; print('  ✓ guardian status OK')"

echo ""
echo "=== TEST 5: guardian equity-update + re-read ==="
python3 .claude/scripts/guardian.py --profile ftmo --action equity-update --value 10150 --note "integration test"
python3 .claude/scripts/guardian.py --profile ftmo --action status > /tmp/guardian_after.json
AFTER=$(python3 -c "import json; d=json.load(open('/tmp/guardian_after.json')); print(d['equity_current'])")
test "$AFTER" = "10150.0" && echo "  ✓ equity updated to $AFTER" || { echo "  ✗ expected 10150.0, got $AFTER"; exit 1; }

# Cleanup test curve row
python3 -c "
import csv
from pathlib import Path
p = Path('.claude/profiles/ftmo/memory/equity_curve.csv')
rows = list(csv.reader(open(p)))
# Keep header + drop test row (last)
filtered = [rows[0]] + [r for r in rows[1:] if 'integration test' not in ' '.join(r)]
with open(p, 'w', newline='') as f:
    w = csv.writer(f)
    w.writerows(filtered)
"

echo ""
echo "=== TEST 6: guardian check-entry OK on fresh profile ==="
RESULT=$(python3 .claude/scripts/guardian.py --profile ftmo --action check-entry \
  --asset BTCUSD --entry 77538 --sl 77238 --loss-if-sl 50)
echo "$RESULT" | python3 -c "import sys, json; d=json.load(sys.stdin); assert d['verdict']=='OK'; print('  ✓ OK verdict')"

echo ""
echo "=== TEST 7: memory structure integrity ==="
test -d .claude/profiles/retail/memory && echo "  ✓ retail memory dir"
test -d .claude/profiles/ftmo/memory && echo "  ✓ ftmo memory dir"
test -f .claude/profiles/retail/memory/trading_log.md && echo "  ✓ retail trading_log migrated"
test -f .claude/memory/user_profile.md && echo "  ✓ global user_profile kept"
test ! -f .claude/memory/trading_log.md && echo "  ✓ retail log NOT in global" || { echo "  ✗ trading_log still in global"; exit 1; }

echo ""
echo "=== TEST 8: reset to retail ==="
bash .claude/scripts/profile.sh set retail
test "$(bash .claude/scripts/profile.sh get)" = "retail" && echo "  ✓ back to retail"

echo ""
echo "╔═══════════════════════════════════╗"
echo "║  ALL INTEGRATION TESTS PASSED  ✓  ║"
echo "╚═══════════════════════════════════╝"
```

- [ ] **Step 2: Make executable and run**

```bash
chmod +x .claude/scripts/test_integration.sh
bash .claude/scripts/test_integration.sh
```

Expected: all 8 tests print `✓` and final "ALL INTEGRATION TESTS PASSED".

- [ ] **Step 3: Commit**

```bash
git add .claude/scripts/test_integration.sh
git commit -m "test: end-to-end integration test for dual-profile system"
```

---

## Task 28: Final verification + merge to main

**Files:** None (git operations only)

- [ ] **Step 1: Run all tests one more time**

```bash
python3 -m pytest .claude/scripts/test_guardian.py -v
bash .claude/scripts/test_integration.sh
```

Expected: all pass.

- [ ] **Step 2: Verify retail system still works (regression)**

```bash
bash .claude/scripts/profile.sh set retail
bash .claude/scripts/session_start.sh
```

Expected: output mentions "RETAIL", capital $13.63, Mean Reversion strategy.

- [ ] **Step 3: Manual sanity checks on key paths**

```bash
# Verify no orphan files in old location
ls .claude/memory/ | grep -E "trading_log|trading_strategy|entry_rules|backtest_findings|market_regime|tradingview_setup|liquidations_data" && echo "ORPHANS FOUND" || echo "  ✓ no orphans"

# Verify profile configs
test -f .claude/profiles/retail/config.md && test -f .claude/profiles/ftmo/config.md && echo "  ✓ both configs exist"

# Verify guardian is callable
python3 .claude/scripts/guardian.py --profile ftmo --action status >/dev/null && echo "  ✓ guardian runs"
```

- [ ] **Step 4: Log summary of the branch**

```bash
git log --oneline main..feature/ftmo-profile
```

Expected: ~25 commits, one per task.

- [ ] **Step 5: Final commit with summary doc**

Create `docs/superpowers/plans/2026-04-22-ftmo-profile-IMPLEMENTATION-LOG.md` summarizing what was built and linking to key files. Then:

```bash
git add docs/
git commit -m "docs: implementation log for FTMO profile system"
```

- [ ] **Step 6: Ask user before merging**

Don't merge automatically. Present the branch summary and ask:
> "Implementación completa en feature/ftmo-profile (~28 commits, ~23 tests pasando). ¿Merge a main ahora, o quieres revisar un archivo específico primero?"

---

## Post-implementation (not part of this plan, user operates)

### Fase 6 (external): Run the backtest
- User (or Claude in a session) plugs a data source into `backtest_ftmo.py`
- Runs over 3 months of BTC + ETH + EURUSD
- Commits results + verdict to `profiles/ftmo/memory/backtest_results.md`

### Fase 7 (external): Paper trading with FTMO Free Trial
- User opens FTMO Free Trial (14 days, no cost)
- Configures MT5, validates pip values in `mt5_symbols.md`
- Operates 10+ trades using the system (morning-analyst-ftmo, validate, equity updates, journal)
- Logs to `paper_trading_log.md`

### Fase 8 (external): Go/No-Go decision
- Review backtest + paper metrics
- If pass criteria (WR≥55%, 0 breaches, 0 overrides) met → purchase challenge $93.43
- If not → refine strategy, repeat 6-7

---

## Execution choice

Plan complete and saved to `docs/superpowers/plans/2026-04-22-ftmo-profile.md`. Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
