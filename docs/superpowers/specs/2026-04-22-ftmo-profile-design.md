# FTMO Profile System — Design Spec

**Fecha:** 2026-04-22
**Autor:** Diseño colaborativo trader + Claude (brainstorming)
**Status:** Approved by user, ready for implementation plan
**Branch target:** `feature/ftmo-profile`

## Contexto y Problema

El trader opera actualmente BTCUSDT.P perpetual en BingX con capital real de $13.63 y estrategia Mean Reversion 15m (3 wins consecutivos). Quiere ampliar el sistema para operar en paralelo un challenge de FTMO 1-Step ($10k virtual, costo $93.43 del challenge), con reglas distintas:

- Profit target 10%
- Max loss diaria 3% (hard)
- Max trailing drawdown 10%
- Best Day Rule 50% (ningún día puede ser >50% del profit total)
- Leverage 1:100 en MT5
- Multi-asset: BTC + ETH + FX majors + Índices

El sistema de Claude actual (17 commands, 7 agents, 16 memorias) está hardcoded a retail/BingX/BTC/$13.63. Necesitamos extenderlo para soportar múltiples profiles **aislados**, con comandos compartidos que cambian comportamiento según profile activo.

## Decisiones de scope (tomadas en brainstorming)

| # | Decisión | Elegido |
|---|---|---|
| 1 | Usage pattern | **Dedicado por día** — switcheas al inicio de cada día, no operas ambos simultáneamente |
| 2 | Assets FTMO | **BTC + ETH + FX majors (EURUSD, GBPUSD) + Índices (NAS100, SPX500)** |
| 3 | Enforcement level | **Híbrido por regla**: bloqueo duro 3% daily, advertencia fuerte 10% trailing, info Best Day |
| 4 | Estrategia FTMO | **FTMO-Conservative** — estrategia nueva (SL tight 0.4%, target 1.5%/día, size fijo 0.5%) |
| 5 | Switch mechanism | **Flag file `.claude/active_profile` + prompt en sessionStart si stale >12h** |
| 6 | Timing / urgencia | **Sin deadline** — hacerlo bien, con backtest + paper trading antes de pagar |

## Approach elegido: Config System por Profile

Directorio `.claude/profiles/{retail,ftmo}/` con configuración y memoria aislada por profile. Los 17 comandos y 7 agentes existentes se vuelven profile-agnostic leyendo `active_profile` y cargando la config correspondiente. Un `guardian.py` centralizado aplica las reglas del profile activo.

Aprobado sobre alternativas:
- **Overlay Mínimo** (rechazado — no escala, ensucia comandos con dual-logic)
- **Guardian Layer only** (rechazado — no soporta estrategia FTMO-específica ni multi-asset limpiamente)

## Sección 1 — Arquitectura de directorios

```
.claude/
├── active_profile                    # flag file: "ftmo | <iso timestamp>"
├── profiles/
│   ├── retail/
│   │   ├── config.md                 # capital $13.63, BingX, 10x, assets BTCUSDT.P
│   │   ├── strategy.md               # Mean Reversion 15m (estrategia actual)
│   │   └── memory/
│   │       ├── trading_log.md
│   │       ├── trading_strategy.md
│   │       ├── entry_rules.md
│   │       ├── backtest_findings.md
│   │       ├── market_regime.md
│   │       ├── tradingview_setup.md
│   │       └── liquidations_data.md
│   │
│   └── ftmo/
│       ├── config.md                 # capital $10k, MT5, leverage 1:100, multi-asset
│       ├── strategy.md               # FTMO-Conservative
│       ├── rules.md                  # spec formal de 3%/10%/Best Day
│       └── memory/
│           ├── trading_log.md
│           ├── equity_curve.csv
│           ├── challenge_progress.md
│           ├── mt5_symbols.md
│           ├── paper_trading_log.md
│           ├── overrides.log
│           └── session_notes.md
│
├── commands/                         # 17 comandos existentes + /profile + /equity + /challenge
├── agents/                           # 7 agentes existentes + morning-analyst-ftmo
├── scripts/
│   ├── guardian.py                   # NUEVO: rules engine centralizado
│   ├── profile.sh                    # NUEVO: switch/show/validate profile
│   ├── session_start.sh              # MODIFICADO: prompt profile si stale
│   ├── statusline.sh                 # MODIFICADO: muestra [profile] + métricas
│   └── test_guardian.py              # NUEVO: unit tests del guardian
│
└── memory/                           # GLOBAL (ambos profiles leen)
    ├── user_profile.md
    ├── communication_prefs.md
    ├── operating_window.md
    ├── user_goals_reality.md
    ├── morning_protocol.md
    ├── market_context_refs.md
    ├── ml_system.md
    └── MEMORY.md
```

### Reglas de migración

1. Memorias retail-específicas (7 archivos) → mueven a `profiles/retail/memory/`
2. Memorias globales (8 archivos) → se quedan en `.claude/memory/`
3. Durante Fase 1 se crean symlinks temporales en `.claude/memory/` apuntando a los archivos migrados para no romper comandos legacy antes de terminar la refactorización
4. `MEMORY.md` actualizado con nuevo índice dual (ver Sección 6)

### Decisiones abiertas tomadas como defaults

- Niveles técnicos actuales BTC BingX → viven en `profiles/retail/memory/market_regime.md`
- `active_profile` contiene nombre + timestamp ISO (`retail | 2026-04-23T06:00:00`) para permitir stale detection

## Sección 2 — Componentes

### 2.1 Guardian (`scripts/guardian.py`)

Script Python standalone. Core del sistema FTMO. Invocado por comandos `/validate`, `/risk`, `/status`, `/equity`, `/challenge`.

**Interfaz CLI:**
```
python guardian.py --profile {ftmo|retail} --action {check-entry|status|equity-update} [...flags]
```

**Output:** JSON estructurado con equity, rules status, verdict, size_adjustment.

**Funciones core:**
- `load_equity_curve(profile) -> list[dict]`
- `peak_equity(curve) -> float`
- `daily_pnl(curve, today) -> float`
- `trailing_dd(curve) -> float`
- `best_day_ratio(curve) -> (best, total)`
- `check_entry(profile_cfg, curve, trade) -> Verdict`

### 2.2 Comandos

Los 17 comandos existentes se mantienen. Header adicional:
```
1. Lee .claude/active_profile → $PROFILE
2. Carga profiles/$PROFILE/config.md + strategy.md
3. Invoca guardian con contexto
4. Procesa según veredicto
```

**Comandos nuevos:**
- `/profile [ftmo|retail|status]` — ver/cambiar profile activo
- `/equity <valor>` — update manual de equity FTMO
- `/challenge` — dashboard de progreso hacia 10% (solo FTMO)

### 2.3 Scripts modificados

**`session_start.sh`:** detecta flag stale (>12h) y prompteea profile. Muestra contexto del profile activo.

**`statusline.sh`:**
- Retail: `[RETAIL $13.63] PnL día: $0 • Setup: Mean Reversion • Régimen: RANGE`
- FTMO: `[FTMO $10k] Equity: $10,247 (+2.47%) • Daily: -$180 (-1.8%/-3%) • Peak DD: -$153 (-1.5%/-10%)`

### 2.4 Agentes

Los 7 agentes existentes reciben instrucción de leer `active_profile` y cargar config profile-specific. NO se duplican.

**Excepción:** `morning-analyst-ftmo` es un agente nuevo porque el protocolo 17-fase actual es muy BTC-BingX específico, y el flow FTMO multi-asset requiere análisis por asset + correlaciones + filtrado diario — suficientemente distinto para justificar variante propia.

### 2.5 Equity input

Manual via `/equity <valor>`. Guardian persiste en `profiles/ftmo/memory/equity_curve.csv` con timestamp. Statusline y guardian leen siempre el último valor.

Opcionalmente, al inicio de sesión FTMO, sessionStart prompteea "¿actualizar equity? (último: $X @ YYYY)".

## Sección 3 — Data Flow

### 3.1 Inicio de día
```
sessionStart → lee active_profile → si stale, prompt usuario → actualiza flag → muestra statusline
```

### 3.2 Análisis matutino (FTMO)
```
/morning → lee profile=ftmo → despacha morning-analyst-ftmo
  → regime detection POR ASSET (BTC, ETH, EURUSD, GBPUSD, NAS100, SPX500)
  → filtrado según sesión + régimen ideal (tabla en strategy.md)
  → guardian check (margen diario/trailing/best day)
  → niveles técnicos por asset filtrado
  → size fijo calculado vía pip_value
  → dibujo TV (1 chart por asset seleccionado)
  → plan de entrada con setups A/B/C
  → VEREDICTO: operar asset X, esperar, o skip day
```

### 3.3 Validación de entrada
```
/validate → 4 filtros técnicos
  → si 4/4 → guardian check_entry(trade)
    → OK / OK_WITH_WARN / BLOCK_SIZE / BLOCK_HARD
  → Claude devuelve al usuario con size ajustado si aplica
```

### 3.4 Post-trade
```
MT5 cierra trade → usuario corre /equity <nuevo_valor>
  → guardian append curve + recalcula
  → statusline actualiza
```

### 3.5 Cierre de día
```
/journal → lee profile → journal-keeper
  → lee trades del día (input manual desde MT5)
  → append profiles/ftmo/memory/trading_log.md
  → update challenge_progress.md
  → calcula métricas
```

### 3.6 Switch profile
```
/profile retail → si hay trade FTMO abierto BLOCK
  → si clean, escribe flag, cambia statusline, memorias del otro profile quedan intactas
```

## Sección 4 — Guardian: Rules Engine

### 4.1 Estado persistido

**`profiles/ftmo/memory/equity_curve.csv`**
```csv
timestamp,equity,source,note
2026-04-23T06:05:00,10000.00,manual,initial
2026-04-23T09:45:00,10180.00,manual,BTC long TP2 +180
```

**`profiles/ftmo/config.md`**
```yaml
challenge_type: 1-step
initial_capital: 10000
profit_target_pct: 10
max_daily_loss_pct: 3
max_total_trailing_pct: 10
best_day_cap_pct: 50
leverage: 100
risk_per_trade_pct: 0.5
max_trades_per_day: 2
max_sl_consecutive: 2
```

### 4.2 Lógica de veredicto

Pseudocódigo en `check_entry(profile_cfg, curve, trade)`:

```
1. Calcula equity actual, daily_pnl, trailing_dd, best_day_ratio
2. loss_if_sl = calc_loss(trade)
3. REGLA 1 (3% daily, blocking):
   si (daily_pnl - loss_if_sl) / 10000 <= -3% →
     si margen_restante_hoy <= 0 → BLOCK_HARD
     sino propone size_adj → BLOCK_SIZE con recomendación
4. REGLA 2 (10% trailing, warn):
   si (trailing_dd + loss_if_sl) / 10000 >= 8% → warn en output
5. REGLA 3 (Best Day, info):
   si best / total >= 0.45 → info en output
6. REGLA 4 (max 2 trades/día):
   si trades_hoy >= 2 → BLOCK_HARD
7. REGLA 5 (2 SLs consecutivos):
   si consecutive_sl_today >= 2 → BLOCK_HARD
8. Si todas OK → OK (con warnings si aplica)
```

### 4.3 Veredictos

| Veredicto | Acción de Claude |
|---|---|
| `OK` | Procede con validación normal |
| `OK_WITH_WARN` | Muestra warning rojo, pide confirmación |
| `BLOCK_SIZE` | Propone size reducido, usuario confirma |
| `BLOCK_HARD` | NO-GO total, sugiere cerrar terminal |

### 4.4 Override escape hatch

Usuario puede escribir `OVERRIDE GUARDIAN` para ignorar BLOCK_HARD. Queda loggeado en `overrides.log` con razón + equity + rule violada. Para post-mortem.

### 4.5 Edge cases manejados

1. Curve vacío → asume equity = initial_capital
2. Timestamps desordenados → sort antes de calcular
3. Gap varios días → daily_pnl = 0 si no hay datos nuevos
4. MT5 cambia equity sin /equity → curve stale, guardian usa último conocido
5. Trades múltiples sin update intermedio → tratados como agregado hasta siguiente update

## Sección 5 — Estrategia FTMO-Conservative

### 5.1 Principios

1. Target diario **1.0-1.5%** (no persigues más aunque tengas setup)
2. **SL 0.4% fijo** por trade (no ATR-based)
3. **Size 0.5% risk** = $50 inicial por trade
4. **Multi-asset selection**: 1 setup A-grade por día
5. **Asset rotation**: elige por EV diario
6. **Best Day compliance natural**: cierras terminal si ya +1.5% del día

### 5.2 Universo de assets

| Asset | MT5 Symbol | Sesión óptima CR | Régimen ideal |
|---|---|---|---|
| BTCUSD | `BTCUSD` | 06:00-10:00 | RANGE |
| ETHUSD | `ETHUSD` | 06:00-10:00 | RANGE/TREND leve |
| EURUSD | `EURUSD` | 07:00-10:00, 14:00-16:00 | RANGE |
| GBPUSD | `GBPUSD` | 07:00-11:00 | TREND leve |
| NAS100 | `US100.cash` | 08:30-15:00 | TREND (ADX>25) |
| SPX500 | `US500.cash` | 08:30-15:00 | TREND/RANGE |

Ventana operativa FTMO: **CR 06:00–16:00**.

### 5.3 Filtros de selección diaria

Score A/B/C/D por asset basado en régimen + condiciones:
- A: régimen RANGE + RSI en zona + BB extremo + volumen OK
- B: RANGE pero solo 2/3 condiciones
- C: régimen ambiguo
- D: VOLATILE o NO DATA → skip

Selección: 1 A-grade → trade. 2+ A → menor spread + sesión activa. Todos B o peor → no operar.

### 5.4 Entradas (7 filtros simultáneos)

**LONG:**
1. Precio toca Donchian Low(20) (no 15)
2. RSI(14) < 30 (no 35)
3. BB(20,2) Lower toca
4. Vela 15m cierra verde con cuerpo ≥ 60% del rango
5. Spread ≤ 1.5× spread promedio
6. Hora válida según tabla 5.2
7. Guardian OK o OK_WITH_WARN

**SHORT:** espejo.

### 5.5 Gestión de trade

| Componente | Valor |
|---|---|
| Entry | Mercado o limit 0.1% |
| SL | 0.4% del entry |
| TP1 (50%) | 0.6% (1.5R) → mueve SL a BE |
| TP2 (50%) | 1.2% (3.0R) |
| Trailing post-TP1 | Stop a mid |
| Force exit | 16:00 CR |
| Overnight | Prohibido |

R:R efectivo: +0.9% notional / trade exitoso = **+0.45% equity** con size 0.5%.

Matemática: 3-4 trades/semana × 0.45% = ~1.8%/sem ≈ 10% en 6-8 semanas. Best Day Rule se cumple naturalmente.

### 5.6 Position sizing

Función `calc_lots(asset, entry, sl, equity, risk_pct=0.5)` que lee pip_value por asset desde `mt5_symbols.md` (tabla que el usuario valida el primer día con screenshots de MT5 Specification).

### 5.7 Validación obligatoria antes de challenge pago

1. Implementar sistema completo
2. Backtest python (3 meses BTC + ETH + EURUSD) → WR>55%, DD<5%, 0 daily breaches simulados
3. Paper trading en FTMO Free Trial (14 días, 10+ trades)
4. Si cumple → comprar challenge $93.43
5. Si no cumple → refinar estrategia, repetir

## Sección 6 — Journal y Memoria separada

### 6.1 Memorias globales (no se mueven)

`user_profile.md`, `communication_prefs.md`, `operating_window.md`, `user_goals_reality.md`, `morning_protocol.md`, `market_context_refs.md`, `ml_system.md`, `MEMORY.md`.

### 6.2 Memorias retail-específicas (migran a `profiles/retail/memory/`)

`trading_log.md`, `trading_strategy.md`, `entry_rules.md`, `backtest_findings.md`, `market_regime.md`, `tradingview_setup.md`, `liquidations_data.md`.

### 6.3 Memorias FTMO (nuevas, en `profiles/ftmo/memory/`)

`trading_log.md`, `challenge_progress.md`, `equity_curve.csv`, `mt5_symbols.md`, `strategy_ftmo_conservative.md`, `paper_trading_log.md`, `overrides.log`, `session_notes.md`.

### 6.4 MEMORY.md reestructurado

Índice dual con secciones GLOBAL, RETAIL, FTMO — cada una con links a sus archivos.

### 6.5 Reglas de escritura

1. Nunca cruzar: trade FTMO no se anota en retail log y viceversa
2. `journal-keeper` lee active_profile y escribe al log correspondiente
3. Aprendizajes psicológicos generales (revenge trading, ansiedad) → memoria global
4. Patrones técnicos asset-específicos → log del profile donde se observaron

## Sección 7 — Testing + Plan de Migración

### 7.1 Fases (cada una termina con commit verificable)

| Fase | Entregable | Test |
|---|---|---|
| 0 | Baseline documentado, branch creado | `test_baseline.sh` pasa en retail |
| 1 | Estructura dirs + migración retail + symlinks | `/status`, `/morning`, `/journal` retail igual que antes |
| 2 | Flag file + `/profile` + session_start + statusline | Switch retail↔ftmo visible, statusline refleja |
| 3 | Guardian standalone + tests unitarios | 15+ escenarios guardian pasan |
| 4 | Comandos FTMO integrados (`/equity`, `/challenge`) + integración validate/risk | Simulación 6 trades bloquea correctamente |
| 5 | Estrategia FTMO-Conservative + morning-analyst-ftmo | `/morning` en ftmo devuelve análisis multi-asset |
| 6 | Backtest 3 meses | WR>55%, DD<5%, 0 breach simulado |
| 7 | Paper trading Free Trial FTMO (10+ trades reales) | WR>55%, 0 overrides, 0 breach |
| 8 | Go/No-Go decisión compra challenge | Usuario decide |

### 7.2 Testing

- **Unit tests** (pytest): `test_guardian.py` con 15+ casos
- **Integration tests**: flujo end-to-end sessionStart → morning → validate → equity → journal → switch → status
- **Regression tests**: profile=retail debe producir resultado IDÉNTICO al pre-migración

### 7.3 Criterios de éxito global

- ✅ Las 7 fases con commits verdes
- ✅ Paper WR>55%, 0 daily breaches, 0 overrides
- ✅ Statusline nunca confunde profiles (verificación 5 sesiones)
- ✅ 10 switches limpios sin cross-contamination
- ✅ Backtest + paper log commiteados como evidencia

### 7.4 Rollback

- Branch `feature/ftmo-profile` no se mergea hasta Fase 4 verde
- Symlinks temporales garantizan compatibilidad durante migración
- Rollback = `git revert` + `rm -rf .claude/profiles/`
- Memorias globales nunca se tocan en migración, solo se agregan

### 7.5 Timeline estimado

- Fases 1-5 (código): ~10-12h trabajo (~2-3 sesiones de 3-4h)
- Fase 6 (backtest): ~2h
- Fase 7 (paper trading): 10-14 días calendario (real-time, el usuario opera)
- Fase 8: instantáneo
- **Total hasta challenge pagado: ~2-3 semanas**

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Migración rompe sistema retail actual | Symlinks temporales Fase 1, tests regresión |
| Estrategia FTMO no pasa backtest | Fase 6 es gate para Fase 7, no se compra challenge |
| Guardian tiene bug y deja pasar breach | Unit tests 15+ casos, paper trading valida |
| Usuario cruza profiles accidentalmente | Statusline gigante con [PROFILE], sessionStart prompt |
| Override guardian se vuelve costumbre | overrides.log visible en /status, review en /journal |
| Equity stale por olvido de `/equity` | Statusline muestra "última actualización Xh ago" si >2h |

## Preguntas abiertas (decisiones diferidas a implementación)

- Exact pip_value por asset → usuario valida primer día con screenshots MT5 Specification
- Exact formulas de scoring A/B/C/D por asset → se afina durante Fase 5
- Schema exacto de `trading_log.md` FTMO → se define en Fase 4 cuando hay primer trade

## Próximo paso

Invocar `writing-plans` skill para traducir este spec a un plan de implementación ejecutable con tareas discretas, orden, y criterios de aceptación por tarea.
