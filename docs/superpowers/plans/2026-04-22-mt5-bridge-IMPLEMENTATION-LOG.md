# MT5 Bridge — Implementation Log

**Fecha:** 2026-04-22 (noche, 20:55–21:15 MX)
**Branch:** `feature/mt5-bridge` (worktree `.worktrees/mt5-bridge`)
**Commits:** 11
**Tests:** 43 (24 guardian + 19 mt5_bridge) todos verdes
**Status:** Implementación completa del code side. Validación EA queda para mañana contra MT5 real.

## Entregables

### Scripts
| Archivo | Líneas | Función |
|---|---|---|
| `.claude/scripts/load_env.sh` | ~10 | Source `.env` a bash vars |
| `.claude/scripts/mt5_bridge.py` | ~300 | JSON parser + EA status + 8 funciones helper |
| `.claude/scripts/test_mt5_bridge.py` | ~250 | 19 unit tests |

### Configuración
| Archivo | Función |
|---|---|
| `.claude/.env.example` | Template credenciales (committed) |
| `.claude/.env` | **NO committed** (gitignored); usuario llena |
| `.gitignore` | actualizado con `.claude/.env` |

### Commands
| Archivo | Función |
|---|---|
| `.claude/commands/order.md` | `/order` — encolar orden con YES confirm + EA detect |
| `.claude/commands/trades.md` | `/trades` — dashboard MT5 |
| `.claude/commands/sync.md` | `/sync` — reconciliar pending ↔ state |

### Memory
| Archivo | Estado inicial |
|---|---|
| `.claude/profiles/ftmo/memory/pending_orders.json` | `{"pending": []}` (seed) |
| `.claude/profiles/ftmo/memory/mt5_state.json` | **no existe** hasta install.sh (symlink) |
| `.claude/profiles/ftmo/memory/mt5_commands.json` | **no existe** hasta install.sh (symlink) |

### EA (MQL5)
| Archivo | Líneas | Función |
|---|---|---|
| `.claude/profiles/ftmo/mt5_ea/ClaudeBridge.mq5` | 682 | Expert Advisor: timer 5s, JSON parser custom, 4 command types |
| `.claude/profiles/ftmo/mt5_ea/install.sh` | 204 | Auto-detect bottle Mac + copia EA + symlinks |
| `.claude/profiles/ftmo/mt5_ea/README.md` | 216 | Guía instalación + troubleshooting |

### Integraciones (modificados)
- `.claude/commands/validate.md` — auto-ofrece `/order` tras 7/7 OK
- `.claude/commands/journal.md` — auto-ingest `closed_today` del state
- `.claude/scripts/statusline.sh` — muestra "EA ✓/⚠️/✗" en FTMO

## Verificación post-implementación

```bash
python3 -m pytest .claude/scripts/ -v
# 43 passed

bash .claude/scripts/profile.sh set ftmo
bash .claude/scripts/statusline.sh
# [FTMO $10k] Equity: $10,000 (initial — run /equity)  •  EA ✗

bash .claude/scripts/profile.sh set retail
bash .claude/scripts/statusline.sh
# [RETAIL] 💰 $13.63 (+$3.63) │ 📊 1/3 │ 🟢 VENT │ 🕐 MX 21:10 │ BTC.P
```

## Próximos pasos para el usuario (mañana)

### 1. Llenar `.env` con tus credenciales
```bash
cp .claude/.env.example .claude/.env
# Editar .claude/.env con el editor que prefieras:
#   FTMO_LOGIN=<ftmo-login>
#   FTMO_PASSWORD=<tu password>
#   FTMO_READONLY_PASSWORD=<tu read-only password>
#   FTMO_SERVER=FTMO-Demo
#   MT5_FILES_PATH=   (se llena solo con install.sh)
```

### 2. Abrir MT5 al menos una vez
Login con FTMO-Demo, deja el terminal abierto para que cree su bottle wine.

### 3. Correr install.sh
```bash
bash .claude/profiles/ftmo/mt5_ea/install.sh
```
Auto-detecta bottle path, copia EA, crea symlinks.

### 4. Compilar y cargar EA en MT5
- MT5 abierto → Tools → Options → Expert Advisors → marcar "Allow algorithmic trading"
- Navigator (Ctrl+N) → Expert Advisors → F5 refresh → ClaudeBridge aparece
- Si no aparece: MetaEditor F4 → abrir `MQL5/Experts/ClaudeBridge.mq5` → F7 compilar → verificar "0 errors"
- Drag ClaudeBridge a chart BTCUSD → dialog → "Allow Automated Trading" → OK
- Experts tab (Ctrl+T) debe mostrar: "ClaudeBridge EA v1.00 starting magic=77777 heartbeat=5s"

### 5. Verificar heartbeat
Después de 10s:
```bash
cat .claude/profiles/ftmo/memory/mt5_state.json
# Debe mostrar JSON con last_update, account, positions (vacío), etc
bash .claude/scripts/profile.sh set ftmo
bash .claude/scripts/statusline.sh
# Ahora debe mostrar "EA ✓ Xs"
```

### 6. Primer test manual (opcional pero recomendado)
Con cuenta FTMO Demo (cero riesgo):
```bash
# Encolar orden de prueba con 0.01 lots (mínimo)
/order BTCUSD BUY 77500 sl=77400 tp=77600 lots=0.01
# → Claude pide YES, tú confirmas
# → Se escribe a mt5_commands.json
# → EA lo ejecuta en próximo tick 5s
# → /trades muestra la posición
# → Cierras manualmente en MT5 → /journal ingresa el trade
```

### 7. Integración con flujo normal
Próxima sesión FTMO:
1. `/profile ftmo`
2. `/equity <valor>` (si cambió desde ayer)
3. `/morning` → morning-analyst-ftmo da setup A-grade
4. Cuando precio llegue a zona → `/validate` (7/7 filtros)
5. Si GO → `/validate` pregunta "YES para encolar" → tú respondes YES
6. Orden se encola al EA automáticamente
7. Durante el día, `/trades` para checar status
8. Al cerrar día: `/journal` hace auto-ingest

## Seguridad

- `.env` verificado gitignored:
  ```
  git ls-files | grep "\\.env$"
  # (sin output) → OK
  ```
- Claude nunca imprime FTMO_PASSWORD en output
- Magic number 77777 aísla órdenes de Claude; EA no toca trades manuales del usuario
- EA tiene input `AllowExecution=true` — ponerlo `false` deja solo lectura (útil para debug)

## Limitaciones conocidas

1. **EA no testeado** — se compiló a código pero no se corrió en MT5 real. Validar en Paso 4 mañana. Posibles issues:
   - JSON parser edge cases (strings con `"` escapados no soportados; Claude no los usa)
   - FILE_COMMON puede requerir estar habilitado en MT5
   - Atomic write vía `FileMove` puede fallar en algunas versiones MT5 — fallback sería escribir directo
2. **macOS Wine wrapper** — puede que el path de bottle cambie entre versiones de MT5. `install.sh` busca patterns conocidos; si cambia, actualizar.
3. **Commands sin cleanup** — `mt5_commands.json` crece indefinidamente. Pendiente feature: rotar/archive comandos procesados >24h.
4. **No auto-close** — EA ejecuta órdenes pero no cierra automáticamente según trailing stops dinámicos. El TP/SL que se envía al crear orden es lo que rige. Si quieres trailing dinámico, otra feature.

## Timeline real

- Brainstorming + spec + plan: 25 min
- Execution (4 batches via subagents): 12 min total
- Verification + this log: 5 min
- **Total: ~45 min** para 11 commits + EA completo

## Commits

```
cbddcf1 feat: statusline EA heartbeat + positions count
17a3431 refactor: /validate auto-order offer + /journal MT5 auto-ingest
9e521e3 feat: EA install.sh + README with Mac-specific bottle detection
3f1cae1 feat: ClaudeBridge.mq5 EA (MT5 bridge)
d8f696b feat: /sync command
b11bc55 feat: /trades dashboard command
8489779 feat: /order command with pending queue + EA detect
1f1a576 feat: mt5_bridge.py helpers + tests
4de259b feat: load_env.sh for sourcing .env credentials
ec4754d chore: gitignore .env + add .env.example template
7af90cb docs: spec + plan MT5 bridge integration
```
