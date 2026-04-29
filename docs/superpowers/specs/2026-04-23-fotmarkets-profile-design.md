# Profile `fotmarkets` — Design Spec

**Fecha:** 2026-04-23
**Autor:** Claude + Francisco Campos
**Estado:** Aprobado por usuario, listo para implementation plan

## 1. Contexto y motivación

Francisco recibió **$30 USD de bonus "no-deposit"** de Fotmarkets, un broker registrado en Mauricio sin regulación tier-1. El bonus fuerza:

- Cuenta tipo **MT5 Standard** (spreads desde 1.2 pips, $0 comisión)
- Apalancamiento **1:500** (obligatorio)
- Moneda **USD**

El sistema de trading actual soporta 2 profiles (`retail` y `ftmo`). El usuario quiere agregar **`fotmarkets` como tercer profile operativo** — no sandbox, sino cuenta real con reglas adaptadas a capital micro ($30) y broker no regulado.

## 2. Principios de diseño

1. **Reuso máximo** de infra existente (ftmo profile tiene ~80% overlap de assets).
2. **Aislamiento total** respecto a `retail` y `ftmo` — memorias nunca se cruzan.
3. **Matemática realista** del capital: con $30 y min lot 0.01, la regla 2% es imposible → usar escalation.
4. **Honestidad sobre riesgo**: capital es bonus ("casa de juego") pero se opera con disciplina.
5. **Ventana compacta** (4h) fuerza selectividad.
6. **Integración profile-aware**: comandos genéricos funcionan, FTMO-specific se skip.

## 3. Identidad del profile

| Campo | Valor |
|---|---|
| Nombre | `fotmarkets` |
| Broker | Fotmarkets (Mauritius, sin regulación FCA/CySEC/ASIC) |
| Plataforma | MetaTrader 5 (cliente desktop) |
| Cuenta | MT5 Standard |
| Leverage | 1:500 (forzado) |
| Capital inicial | $30 USD (bonus no-deposit) |
| Moneda | USD |
| Assets operables | EURUSD, GBPUSD, USDJPY, XAUUSD, NAS100, SPX500, BTCUSD, ETHUSD |
| Ventana operativa | **CR 07:00–11:00** (London/NY overlap) |
| Force exit | CR 10:55 |
| Overnight | Prohibido |
| Weekend | Prohibido |

## 4. Modelo de riesgo — Escalation R1

```yaml
phase_1:  # Capital $30 → $100  (supervivencia)
  risk_per_trade_pct: 10
  risk_per_trade_usd_cap: 3.0
  max_trades_per_day: 1
  max_sl_consecutive: 1           # 1 SL → STOP día
  tp_r_multiple: 2.0
  allowed_assets: [EURUSD, GBPUSD]
  broker_min_lot: 0.01            # piso del broker; sizing real = risk_usd / (SL_pips × pip_value)

phase_2:  # Capital $100 → $300  (consolidación)
  risk_per_trade_pct: 5
  max_trades_per_day: 2
  max_sl_consecutive: 2
  tp_r_multiple: 2.0
  allowed_assets: [EURUSD, GBPUSD, USDJPY, XAUUSD, NAS100]
  break_even_trigger: 1.0R

phase_3:  # Capital $300+  (estándar)
  risk_per_trade_pct: 2
  max_trades_per_day: 3
  max_sl_consecutive: 2
  tp_r_multiple: 2.5
  allowed_assets: [ALL]           # incluye BTCUSD, ETHUSD, SPX500

global:
  force_exit_time_mx: "10:55"
  no_overnight: true
  no_weekend: true
  stop_loss_atr_mult: 1.2         # más tight que FTMO (1.5)
  timeframe_primary: "5m"
  timeframe_confirmation: "15m"
```

### Phase detection
Script `.claude/scripts/fotmarkets_phase.sh` lee `memory/phase_progress.md` y devuelve `phase_1|phase_2|phase_3` según capital actual. Cualquier comando profile-aware lo invoca para aplicar el % correspondiente.

## 5. Estrategia `Fotmarkets-Micro`

Scalping de reversión tras pullback, en dirección de tendencia 15m. Sweet spot para overlap London/NY con capital micro y 4 horas de ventana.

### Filtros de entrada (4 obligatorios, simultáneos)

**LONG:**
1. `EMA50(15m) > EMA200(15m) AND price > EMA50(15m)` (trend alcista)
2. `RSI(14, 5m)` entre **35–55** (rebote desde OS, no extremo)
3. Price within **0.15%** de soporte clave (Donchian Low 20 o pivot clásico S1)
4. Vela 5m cierra **verde** con cuerpo **>60%** del rango total

**SHORT:**
1. `EMA50(15m) < EMA200(15m) AND price < EMA50(15m)`
2. `RSI(14, 5m)` entre **45–65**
3. Price within 0.15% de resistencia (Donchian High 20 o pivot R1)
4. Vela 5m cierra **roja** con cuerpo >60%

### Stop Loss

- Método: **ATR-based** (ATR 14, multiplier 1.2)
- Floor mínimo por asset (para que spread no se lo coma):
  - EURUSD: 8 pips
  - GBPUSD: 10 pips
  - USDJPY: 10 pips
  - XAUUSD: 20 pips ($2)
  - NAS100: 25 points
  - SPX500: 4 points

### Take Profit

| Fase | TP estructura |
|---|---|
| Fase 1 | TP único a **2.0R** (cierre total) — una sola bala |
| Fase 2 | TP1 2.0R (50%), TP2 3.5R (50%) — SL→BE tras TP1 |
| Fase 3 | TP1 2.0R (40%), TP2 3.5R (40%), TP3 5.0R (20%) |

### Hard stops (invalidaciones)

1. `ATR(14, 5m) > 2× promedio 50 velas` → NO operar (volatile)
2. Spread EURUSD > 3 pips → NO operar (condición anormal)
3. 15 min antes de noticia roja (NFP, FOMC, CPI) → cierre + no reentrar 30 min
4. ECB day (jueves 07:00–09:00 CR) → NO operar en EUR pairs

## 6. Integración con sistema existente

### Estructura de archivos

```
.claude/profiles/fotmarkets/
├── config.md              # identidad + constantes YAML
├── strategy.md            # Fotmarkets-Micro detallada
├── rules.md               # reglas por fase + hard stops
└── memory/
    ├── .gitkeep
    ├── trading_log.md
    ├── phase_progress.md  # capital actual + fase vigente
    └── session_notes.md

.claude/scripts/
├── fotmarkets_phase.sh    # detecta fase por capital
└── fotmarkets_guard.sh    # Lite Guardian pre-validate
```

### Matriz de compatibilidad de comandos

| Comando | Status | Adaptación |
|---|---|---|
| `/profile fotmarkets` | ✅ | `profile.sh` ya es genérico |
| `/status` | ✅ | Nueva rama — muestra capital, fase, trades hoy |
| `/morning` | ✅ | Reusa `morning-analyst-ftmo` con asset list del profile |
| `/validate` | ✅ | 4 filtros Fotmarkets-Micro + Lite Guardian + phase-aware sizing |
| `/risk` | ✅ | Detecta fase → aplica % correspondiente |
| `/journal` | ✅ | Escribe a `trading_log.md`, actualiza `phase_progress.md` |
| `/chart` | ✅ | Usa MT5 como fuente; si TV conectado, dibuja en TV |
| `/alert` | ✅ | Sin cambios |
| `/ta` | ✅ | Sin cambios |
| `/levels` | ✅ | Adaptar para cualquier símbolo (no hard-code BTC) |
| `/signal` | ✅ | Sin cambios |
| `/regime` | ⚠️ | Adaptar: ADX para Forex en lugar de lógica BTC |
| `/backtest` | ⚠️ | TODO — data source no disponible para Forex, deferred |
| `/challenge` | ❌ | N/A |
| `/equity` | ❌ | N/A |
| `/trades`, `/sync`, `/order` | ❌ | N/A (ejecución manual MT5, sin EA) |
| `/sentiment`, `/ml`, `/ml-train`, `/neptune` | ❌ | Retail-only (BTC focused) |

### Lite Guardian

`.claude/scripts/fotmarkets_guard.sh` valida antes de cada `/validate`:

1. Hora CR ∈ [07:00, 10:55]
2. No se excedió `max_trades_per_day` de la fase activa
3. No hay SL consecutivos que disparen "stop día" de la fase
4. No es weekend ni holiday

Output: `PASS` o `BLOCK: <razón>`. Es un wrapper liviano (~40 líneas), sin lógica de DD como `guardian.py` FTMO.

### Statusline

Cuando profile activo es `fotmarkets`:
```
[FOTMARKETS] $30.00 | Fase 1 (→$100) | 07:00-11:00 CR | 0/1 trades hoy
```

### CLAUDE.md

Se agrega sección describiendo el 3er profile, su filosofía, y la matriz de comandos compatibles.

## 7. Consideraciones adicionales

### Bonus T&C (pendiente de verificación por usuario)

Antes de la primera ejecución, el usuario debe leer y documentar en `memory/session_notes.md`:
- Volumen mínimo requerido para retirar profits del bonus
- Profit cap (ej. max $500 de bono)
- Ventana temporal del bonus (30/60 días)
- Requisitos KYC para retiro

Si cualquiera de estas condiciones invalida el uso práctico del bonus, se evalúa si mantener el profile.

### No hay regulación tier-1
El usuario opera con pleno conocimiento de que:
- Si el broker quiebra o bloquea retiros, el capital se pierde sin recurso legal
- El bonus es un "chip de casino" — si se pierde no afecta capital propio
- No se deposita dinero adicional al bonus en ningún momento

### Migración de fase
Cuando el capital cruza un umbral ($30→$100, $100→$300), el usuario ejecuta `/journal` que detecta el cambio y:
1. Actualiza `phase_progress.md` con nueva fase
2. Muestra mensaje "⚠️ FASE NUEVA — risk baja a X%, max Y trades, assets desbloqueados: [...]"
3. Requiere confirmación explícita del usuario antes de operar en nueva fase

## 8. Criterios de éxito

1. **Setup completo**: profile switchea limpio con `/profile fotmarkets`, no hay cross-contamination con retail/ftmo.
2. **Statusline correcto**: muestra `[FOTMARKETS]` y fase activa.
3. **Comandos profile-aware**: `/morning`, `/validate`, `/risk`, `/journal`, `/status` responden con lógica Fotmarkets cuando profile activo.
4. **Lite Guardian**: bloquea operación fuera de ventana o excedida de trades.
5. **Phase detection**: `/risk` aplica automáticamente 10%/5%/2% según capital actual en `phase_progress.md`.
6. **CLAUDE.md actualizado**: 3er profile documentado.
7. **Primer trade exitoso (criterio operativo)**: usuario ejecuta ciclo completo morning → validate → trade manual MT5 → journal sin errores de sistema.

## 9. Fuera de scope (explícitamente)

- `/backtest` para Forex (requiere data source distinta, deferred como TODO)
- EA bridge para MT5 Fotmarkets (ejecución manual, no hay `/order` automático)
- Guardian con DD rules (no aplica — no es challenge)
- Integración con `ml_system/` (sentiment + XGBoost son BTC-only)
- Drawing automático en TradingView (TV no carga Fotmarkets directamente, solo via símbolo equivalente)
- Monitoring 24/7 de posiciones (ventana cerrada, force exit automático manual)

## 10. Plan de implementación (high-level)

Se detalla en plan separado (`writing-plans` skill generará el plan paso a paso).

Fases aproximadas:
1. Crear estructura de archivos del profile
2. Implementar scripts (`fotmarkets_phase.sh`, `fotmarkets_guard.sh`)
3. Adaptar comandos profile-aware (`status.md`, `morning.md`, `validate.md`, `risk.md`, `journal.md`, `levels.md`, `regime.md`)
4. Actualizar statusline script
5. Actualizar CLAUDE.md
6. Smoke test: switch a fotmarkets, ejecutar morning + validate + journal sin errores
