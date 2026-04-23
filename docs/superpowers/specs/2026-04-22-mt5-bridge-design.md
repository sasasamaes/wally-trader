# MT5 Bridge + Order Management — Design Spec

**Fecha:** 2026-04-22 (noche, 20:55 MX)
**Branch:** `feature/mt5-bridge` (worktree `.worktrees/mt5-bridge`)
**Status:** Approved via iterative section sign-off (sec 1-4)
**Context:** Extensión del FTMO Profile System (mergeado en `086e754`). Agrega capacidad de encolar órdenes + ejecutarlas en MT5 (manual o vía EA bridge) + leer estado.

## Decisiones de scope aprobadas

| # | Decisión | Elegido |
|---|---|---|
| 1 | Credenciales FTMO | `.claude/.env` gitignored + `.env.example` template |
| 2 | Ejecución | **Dual: manual-asistido + MQL5 EA bridge** — Claude detecta si EA vivo, cae a manual si no |
| 3 | Bridge medium | File-based JSON (shared vía symlinks a MT5 bottle en macOS) |
| 4 | Confirmación orden | **YES obligatorio** antes de encolar al EA (disciplina FTMO) |
| 5 | EA heartbeat | 5 segundos |
| 6 | Magic number | 77777 (identifica órdenes de Claude) |
| 7 | Command expiry default | 120 minutos |

## Arquitectura

```
.claude/
├── .env                          # GITIGNORED — MT5 creds
├── .env.example                  # template committed
├── profiles/ftmo/
│   ├── memory/
│   │   ├── pending_orders.json   # Claude-side queue
│   │   ├── mt5_state.json        # symlink → bottle Files/claude_mt5_state.json
│   │   └── mt5_commands.json     # symlink → bottle Files/claude_mt5_commands.json
│   └── mt5_ea/
│       ├── ClaudeBridge.mq5      # EA source (~200 líneas)
│       ├── install.sh            # detecta bottle path, copia EA, crea symlinks
│       └── README.md             # user guide paso a paso
├── commands/
│   ├── order.md                  # /order
│   ├── trades.md                 # /trades
│   └── sync.md                   # /sync
└── scripts/
    ├── load_env.sh               # source .env → vars bash
    ├── mt5_bridge.py             # helpers JSON read/write + status calc
    └── test_mt5_bridge.py        # unit tests del helper
```

## Bridge protocol

### `mt5_commands.json` (Claude → EA)
```json
{
  "commands": [
    {
      "id": "cmd_<ts>_<seq>",
      "type": "place_order",       // place_order|modify_order|cancel_order|close_position
      "symbol": "BTCUSD",
      "side": "BUY_LIMIT",          // BUY|SELL|BUY_LIMIT|SELL_LIMIT|BUY_STOP|SELL_STOP
      "entry": 77538.0,
      "sl": 77238.0,
      "tp": 78288.0,
      "lots": 0.07,
      "magic": 77777,
      "comment": "MR-LONG-BTC-20260423",
      "expiry_minutes": 120,
      "created_at": "2026-04-23T08:30:00Z",
      "processed": false,
      "result": null                // { ok, ticket, fill_price, executed_at, error }
    }
  ]
}
```

### `mt5_state.json` (EA → Claude)
```json
{
  "last_update": "<iso>",           // EA reescribe cada 5s
  "account": { "login", "server", "balance", "equity", "margin", "free_margin", "currency" },
  "positions": [ { "ticket", "symbol", "type", "volume", "open_price", "sl", "tp", "open_time", "current_price", "profit", "swap", "comment", "magic" } ],
  "pending_orders": [ { "ticket", "symbol", "type", "volume", "price", "sl", "tp", "created_at", "expiry" } ],
  "closed_today": [ { "ticket", "symbol", "type", "volume", "open_price", "close_price", "profit", "open_time", "close_time", "close_reason" } ]
}
```

### `pending_orders.json` (Claude internal)
```json
{
  "pending": [
    {
      "id": "cmd_<ts>_<seq>",
      "symbol": "BTCUSD",
      "setup": "Mean Reversion LONG",
      "proposed_at": "<iso>",
      "entry", "sl", "tp1", "tp2", "lots",
      "status": "queued|sent_to_ea|filled|expired|canceled|manual_pending",
      "guardian_verdict": "OK",
      "filters_passed": 7
    }
  ]
}
```

## Comandos

### `/order [symbol side entry sl tp lots]`
- Sin args: deriva del último análisis en memoria
- Con args: override
- Flujo:
  1. Verifica profile==ftmo
  2. Guardian check (si BLOCK → abortar)
  3. Append a pending_orders.json status=queued
  4. Detecta EA: si `mt5_state.json.last_update < 60s` → EA vivo
  5. EA vivo: append a mt5_commands.json → status=sent_to_ea → espera 10s → lee result
  6. EA offline: status=manual_pending → muestra params para copiar
  7. **Antes del paso 3, pide YES typed** (guardian OK no es suficiente)

### `/trades`
- Dashboard: account + positions + pending MT5 + Claude queue + closed_today
- Warnings si EA stale (>60s), offline (>1h)
- Daily PnL + trailing DD + trades count

### `/sync`
- Lee mt5_state.json
- Cruza con pending_orders.json: matches → `filled`, expired → `expired`
- Si EA offline >1h: pide al user pegar texto MT5 terminal y parsea regex

### Integraciones

**`/validate` (refactor):** después de 7/7 filtros OK + guardian OK, pregunta "¿Ejecutar orden ahora? (YES/no/ajustar)". Si YES → invoca lógica de `/order` con los params del setup validado.

**`/journal` (refactor):** además de los appends actuales, lee `closed_today` del state, escribe a `trading_log.md` cada trade con ticket/price/profit. Marca pending `expired` si no fillearon.

**`statusline.sh` (refactor FTMO branch):** si EA fresh → agrega `• EA ✓ 3s ago • Positions: 1`, si stale/offline → warning.

## EA `ClaudeBridge.mq5` — estructura

```mql5
input int    HeartbeatSec = 5;
input int    Magic = 77777;
input string CommandsFile = "claude_mt5_commands.json";
input string StateFile = "claude_mt5_state.json";
input bool   AllowExecution = true;   // kill-switch si se quiere solo lectura

OnInit()        // set timer, print version
OnTimer()       // 1) procesar cmds nuevos 2) escribir state
OnDeinit()      // cleanup

// Helpers internos:
ReadCommandsJSON(), WriteCommandsJSON(), WriteStateJSON()
ExecuteCommand(cmd) → result
BuildAccountDict(), BuildPositionsArray(), BuildPendingArray(), BuildClosedTodayArray()
```

**Restricciones:**
- Solo toca órdenes con magic=77777 (no afecta trades manuales del user)
- No spam-reprocesa: comandos con `processed:true` se ignoran
- Idempotencia: mismo `id` procesado 2x no dispara 2 órdenes
- Error handling: si OrderSend falla, escribe `result.ok=false` con error code

## Instalación EA (macOS específico)

MT5 en Mac corre sobre wrapper Wine oficial de MetaQuotes. Files bottle en:
```
~/Library/Application Support/MetaTrader 5/Bottles/metatrader5/drive_c/users/<user>/AppData/Roaming/MetaQuotes/Terminal/<hash>/MQL5/
```

`install.sh`:
1. `find ~/Library -name "MQL5" -path "*MetaTrader*"` → detecta bottle path
2. Si múltiples hashes: lista y pregunta usuario cuál
3. Copia `ClaudeBridge.mq5` → `$BOTTLE/MQL5/Experts/`
4. Pre-crea `$BOTTLE/MQL5/Files/claude_mt5_state.json` (vacío) y `claude_mt5_commands.json` (empty commands)
5. Crea symlinks:
   - `profiles/ftmo/memory/mt5_state.json → $BOTTLE/MQL5/Files/claude_mt5_state.json`
   - `profiles/ftmo/memory/mt5_commands.json → $BOTTLE/MQL5/Files/claude_mt5_commands.json`
6. Instruye al user:
   - Abrir MT5
   - Navigator → Expert Advisors → F5 refresh
   - Drag `ClaudeBridge` a chart BTCUSD (timeframe cualquiera)
   - Marcar "Allow AutoTrading"
   - Verificar: Expert tab debe mostrar "ClaudeBridge EA starting magic=77777"
7. Verifica primera escritura en 15s con `cat mt5_state.json` (via symlink)

## Seguridad

- `.env` en `.gitignore` desde task 0
- `.env.example` template SIN valores
- Claude NUNCA imprime el FTMO_PASSWORD en output
- Al imprimir login en statusline, OK (es el número de cuenta)
- EA kill-switch: `AllowExecution=false` deja solo lectura
- Magic 77777 aísla órdenes de Claude del resto

## Testing

- `test_mt5_bridge.py`: parsea/escribe JSON, maneja archivos inexistentes, detecta EA stale
- Integration: simular `mt5_state.json` manual, correr `/trades`, verificar parseo
- EA: no se testea automáticamente (requiere MT5 running). Validación = manual en MT5 con test_order deliberado

## Fases EXTERNAS

- **Hoy (esta sesión):** implementar las 10 tareas, dejar todo listo sin MT5 abierto
- **Mañana (user):** correr `install.sh`, abrir MT5, drag EA, verificar heartbeat, primer test manual con 0.01 lots
- **Post-test-manual:** usar normal con /morning → /validate → /order → /trades

## Plan de tareas

Ver `docs/superpowers/plans/2026-04-22-mt5-bridge.md` (commit siguiente).
