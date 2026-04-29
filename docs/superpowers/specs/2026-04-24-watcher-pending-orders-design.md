# Spec — Watcher + Pending Orders "Set & Forget"

**Fecha:** 2026-04-24
**Autor:** Francisco Campos (brainstormed con Claude)
**Profiles afectados:** retail, retail-bingx, ftmo, fotmarkets
**Status:** draft (pending user review)

## Problema

El usuario hace morning analysis CR 06:00–07:00 y luego trabaja como programador
el resto del día. Hoy debe vigilar el chart manualmente para detectar cuándo se
dan los 4 filtros de entrada — lo cual rompe la concentración o causa que pierda
setups. No existe infraestructura para:

1. Programar orders limit que se ejecuten automáticamente (retail, fotmarkets).
2. Vigilar triggers e invalidaciones sin Claude abierto.
3. Notificar cuando vale la pena volver a mirar el chart.
4. Coordinar pending entre 3 profiles (retail / ftmo / fotmarkets) sin doble
   exposure al mismo underlying.

Hoy `/order` solo funciona para FTMO (via EA bridge); los demás profiles quedan
fuera. `daily_cron.sh` solo dispara notificación 5:30 AM. `alert_setup.sh` es
placeholder sin integración MCP.

## Objetivo

Sistema "set & forget" donde el usuario:

1. Hace `/morning` al arrancar el día.
2. Crea 1+ `/order` con entry/SL/TP/invalidación/TTL.
3. Se va a trabajar.
4. Un watcher autónomo vigila cada hora — invalidando orders que mueren,
   escalando a Claude cuando el precio se acerca, notificando via macOS +
   Telegram + email + dashboard.
5. Cuando recibe trigger GO ejecuta manualmente (o ya ejecutó vía `--real` en
   retail Binance) y confirma con `/filled`.

Soporte en los 3 profiles (retail, ftmo, fotmarkets) reutilizando la
infraestructura de `pending_orders.json` ya existente en ftmo.

## Decisiones de diseño (brainstormed)

1. **Orders virtuales por default + flag `--real` opcional en retail → Binance API.**
   Razón: permite re-validar 4 filtros al momento del toque (un limit order real
   no revalida filtros). `--real` es escalada opcional para quien quiere
   set-and-forget total en Binance.

2. **Watcher híbrido: launchd liviano + escalada a Claude on-demand.**
   Razón: 22/24 horas el precio está lejos del entry — no vale gastar tokens
   Claude. launchd corre script Python stateless cada 1h. Cuando detecta
   distancia <0.3% del entry, spawnea `claude -p "/watch-deep <id>"` headless
   para validación MCP-completa (Neptune, bias, etc.).

3. **Invalidaciones mandatorias: TTL + precio + stop-2SL + force_exit.**
   Invalidación por cambio de régimen opt-in (flag `--check-regime`) porque
   cuesta tokens Claude. News macro y funding flip quedan para v2.

4. **Notificaciones multi-canal con urgencia.**
   `notify_hub.py` abstrae 4 canales: macOS (siempre), Telegram (WARN+),
   email (CRITICAL only), dashboard.md (siempre, auditoría). Telegram/email
   opt-in vía `.claude/.env`; si falta cred → canal no-op silencioso.

5. **Cross-profile con matriz whitelist.**
   Dos pending pueden coexistir si la matriz (YAML) lo permite. Bloquea
   mismo asset-family+dirección entre profiles. Permite hedge opuesto con
   warning. retail vs retail-bingx nunca simultáneos (regla sagrada).

## Non-goals

- **No** implementar cron 15-min dentro de ventana activa (sobreingeniería v1).
- **No** integrar news calendar / funding flip como invalidación (v2).
- **No** soporte para Binance spot (solo futures BTCUSDT.P).
- **No** soporte real-order en BingX (retail-bingx) — residual, no vale la API.
- **No** soporte real-order en fotmarkets (MT5 Standard no tiene API del broker;
  solo manual via MT5 desktop).
- **No** replay histórico de pending (auditoría queda en `notifications.log`
  append-only).

## Arquitectura

### Flujo end-to-end

```
USUARIO: /morning (CR 06:00)
       → Claude propone: entry 77521 LONG, SL 77101, TP 78571, invalidación 76900

USUARIO: /order BTCUSDT.P LONG 77521 sl=77101 tp=78571 ttl=6h
       → Guardian/sanity check según profile
       → Preview ASCII + confirmación YES
       → append a .claude/profiles/retail/memory/pending_orders.json
       → notify INFO "order_created"

USUARIO: se va a trabajar

LAUNCHD (cada 1h):
  → watcher_tick.py corre stateless
  → carga pending de los 4 profiles
  → aplica whitelist matrix (suspende/permite)
  → pulls precio via Binance/OKX/OANDA HTTP
  → evalúa invalidaciones (TTL / precio / 2SL / force_exit)
      ↳ si invalida → status update + notify WARN
  → evalúa distancia a entry
      ↳ >0.3% → heartbeat, update next_recheck, no notif
      ↳ ≤0.3% → spawn `claude -p "/watch-deep <id>"` headless

CLAUDE HEADLESS (on-demand, timeout 120s):
  → /watch-deep <id>
  → chart_set_symbol + MCP completo (RSI/BB/Donchian/ATR, Neptune opcional)
  → evalúa 4 filtros → tabla PASS/FAIL
  → si 4/4 PASS → status=triggered_go + notify CRITICAL
  → si <4 PASS  → status=pending + log "rebote con filtros X/4"
  → si error    → status=check_error + notify WARN "degraded mode"

USUARIO (cuando le llega notif CRITICAL):
  → ejecuta manual en exchange/MT5
  → /filled <id>
  → status=filled, trade pasa a trading_log normal del profile
```

### Archivos

```
.claude/
├── watcher/                                    [NEW]
│   ├── status.json                            # último tick + métricas
│   ├── dashboard.md                           # human-readable estado actual
│   ├── whitelist_matrix.yaml                  # matriz cross-profile
│   └── launchd/
│       └── com.wallytrader.watcher.plist      # template a instalar
│
├── scripts/
│   ├── watcher_tick.py                        [NEW] stateless hourly check
│   ├── watcher_escalate.sh                    [NEW] spawn claude -p headless
│   ├── notify_hub.py                          [NEW] abstracted notify()
│   ├── pending_lib.py                         [NEW] shared CRUD multi-profile
│   ├── binance_real_order.py                  [NEW] --real flag impl
│   ├── price_feeds.py                         [NEW] HTTP price getters
│   └── NOTIFY_SETUP.md                        [NEW] telegram/email setup docs
│
├── profiles/
│   ├── retail/memory/pending_orders.json      [INIT vacío]
│   ├── retail-bingx/memory/pending_orders.json [INIT vacío]
│   ├── fotmarkets/memory/pending_orders.json  [INIT vacío]
│   └── ftmo/memory/pending_orders.json        [EXISTENTE, preservado]
│
└── commands/
    ├── order.md                               [EDIT] extend a 3 profiles + --real
    ├── watch.md                               [NEW]
    ├── watch-deep.md                          [NEW]
    ├── pending.md                             [NEW]
    ├── filled.md                              [NEW]
    ├── profile.md                             [EDIT] handshake pending on switch
    └── status.md                              [EDIT] sección watcher
```

## Data model

### `pending_orders.json` schema (por profile)

```json
{
  "pending": [
    {
      "id": "ord_<YYYYMMDD>_<HHMMSS>_<profile>_<asset>_<side>",
      "profile": "retail | retail-bingx | ftmo | fotmarkets",
      "asset": "BTCUSDT.P",
      "side": "LONG | SHORT",
      "strategy": "mean_reversion_15m",

      "entry_type": "limit",
      "entry": 77521.0,
      "entry_tolerance_pct": 0.1,

      "sl": 77101.0,
      "tp1": 78571.0,
      "tp2": 79201.0,
      "tp3": 80041.0,
      "tp_splits": [0.4, 0.4, 0.2],

      "risk_usd": 0.36,
      "risk_pct": 2.0,
      "qty": 0.00086,
      "leverage": 10,

      "filters_at_creation": {
        "regime": "range",
        "bias_morning": "long_contrarian",
        "fng": 39,
        "funding_pct": -0.001,
        "ls_ratio": 0.70
      },
      "required_filters_at_trigger": [
        "price_touches_donchian_low_15",
        "rsi_15m_lt_35",
        "bb_lower_touch",
        "candle_close_green"
      ],

      "invalidation_price": 76900,
      "invalidation_side": "below",
      "invalidation_close_tf": "4h",
      "check_regime_change": false,

      "created_at": "2026-04-24T10:48:00-06:00",
      "expires_at": "2026-04-24T16:48:00-06:00",
      "force_exit_mx": "2026-04-24T23:59:00-06:00",

      "real_order": {
        "enabled": false,
        "binance_order_id": null,
        "placed_at": null
      },

      "status": "pending",
      "status_history": [
        { "at": "2026-04-24T10:48:00-06:00", "status": "pending", "note": "created via /order" }
      ],

      "next_recheck_suggested_mx": "2026-04-24T11:48:00-06:00"
    }
  ],
  "meta": {
    "last_tick_utc": "2026-04-24T16:48:00Z",
    "last_tick_result": "heartbeat_no_action",
    "active_profile_at_last_tick": "retail"
  }
}
```

### Estados

| Status | Significado | Transiciona a |
|---|---|---|
| `pending` | Esperando toque de entry | `triggered_validating`, `expired_ttl`, `invalidated_*`, `suspended_*`, `canceled_manual` |
| `triggered_validating` | Precio tocó entry, Claude validando filtros | `triggered_go`, `pending`, `check_error` |
| `triggered_go` | 4/4 filtros OK, notificado | `filled`, `canceled_manual` |
| `filled` | Usuario ejecutó (terminal) | — |
| `expired_ttl` | TTL pasó sin toque (terminal) | — |
| `expired_force_exit` | Hit force_exit_mx del día sin fill (terminal). Protege regla "no dormir con trade abierto" cancelando pendings antes de que la ventana del día cierre. Si TTL del usuario excede el force_exit del día de creación, el force_exit gana. | — |
| `invalidated_price` | Precio rompió invalidation_price (terminal) | — |
| `invalidated_regime` | Régimen cambió (opt-in) (terminal) | — |
| `invalidated_stopday` | 2 SLs hoy → regla STOP (terminal) | — |
| `suspended_profile_switch` | Usuario cambió de profile | `pending` (reactivación) |
| `suspended_policy` | Whitelist matrix bloqueó | `pending` (si se resuelve conflicto) |
| `check_error` | Claude headless falló | `pending` (reintenta próximo tick) |
| `canceled_manual` | `/pending cancel` (terminal) | — |

### Whitelist matrix (`.claude/watcher/whitelist_matrix.yaml`)

```yaml
asset_families:
  BTC:
    - retail:BTCUSDT.P
    - retail-bingx:BTCUSDT.P
    - ftmo:BTCUSD
    - fotmarkets:BTCUSD
  ETH:
    - ftmo:ETHUSD
    - fotmarkets:ETHUSD
  EURUSD:
    - ftmo:EURUSD
    - fotmarkets:EURUSD
  GBPUSD:
    - ftmo:GBPUSD
    - fotmarkets:GBPUSD
  NAS100:
    - ftmo:NAS100
    - fotmarkets:NAS100
  SPX500:
    - ftmo:SPX500
    - fotmarkets:SPX500

rules:
  - id: block_retail_and_retail_bingx_simultaneous
    match: { profiles_in: [retail, retail-bingx], count_gte: 2 }
    action: suspend_newest
    reason: "Regla sagrada CLAUDE.md"

  - id: block_ftmo_and_fotmarkets_same_asset_family
    match: { profiles_in: [ftmo, fotmarkets], same_asset_family: true }
    action: suspend_newest
    reason: "Dos brokers MT5 = doble exposure real-ish"

  - id: block_same_family_same_direction
    match: { same_asset_family: true, same_side: true }
    action: suspend_newest
    reason: "Doble exposure direccional al mismo underlying"

  - id: allow_hedge_different_direction
    match: { same_asset_family: true, same_side: false }
    action: allow_with_warning
    warning: "⚠️ Hedge detectado — asegúrate que es intencional"

  - id: allow_default
    match: {}
    action: allow
```

## Componentes

### `watcher_tick.py` (launchd target)

Responsabilidades:
1. Cargar pending de los 4 profiles en memoria.
2. Aplicar matriz whitelist, identificar `active` vs `suspended_policy`.
3. Pulls precios (Binance Futures API `fapi.binance.com/fapi/v1/ticker/price`,
   OKX swap API, TwelveData free tier para forex/índices) — HTTP read-only sin
   credenciales obligatorias. Si TwelveData excede rate limit, fallback a
   OANDA REST con cuenta demo gratuita (decisión diferida al implementar
   `price_feeds.py`).
4. Evaluar invalidaciones **sin MCP** (trivialmente computables desde HTTP):
   - TTL expired (compara `expires_at` con now).
   - Precio rompe `invalidation_price` según `invalidation_side`.
   - Stop-day trigger: parsea `trading_log.md` del profile, cuenta SLs de hoy.
   - Force exit: compara now con `force_exit_mx` del día de creación.
   - Régimen change (opt-in via `check_regime_change=true`) **NO se evalúa aquí**
     — queda delegado a `/watch-deep` cuando el pending escala. Trade-off
     aceptado en brainstorm: una orden con régimen invalidado pero precio
     lejos de entry no se detecta hasta el próximo escalamiento o `/watch`
     manual. Impacto limitado porque invalidación por precio (`invalidation_price`)
     usualmente cubre el mismo evento estructural.
5. Calcular distancia a entry (porcentual).
6. Si distancia <0.3% → spawn `watcher_escalate.sh <id>` en background.
7. Actualizar `next_recheck_suggested_mx` según heurística volatilidad.
8. Escribir `status.json`, `dashboard.md`, append `notifications.log`.
9. Llamar `notify_hub` para eventos que lo requieran.

Exit codes: 0 OK, 1 partial (algún asset sin price), 2 fatal.

Dependencias: `requests`, `python-dateutil`, `pyyaml` (ya usadas en repo).

### `watcher_escalate.sh`

```bash
#!/bin/bash
ORDER_ID="$1"
LOG="/tmp/wally_escalate_${ORDER_ID}.log"
PIDFILE="/tmp/wally_escalate_${ORDER_ID}.pid"

# Si ya hay un escalate corriendo para este id, skip (evita spawns paralelos)
if [ -f "$PIDFILE" ] && kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
    echo "escalate already running for $ORDER_ID" >> "$LOG"
    exit 0
fi

cd "$HOME/Documents/wally-trader"
timeout 120 claude -p "/watch-deep ${ORDER_ID}" \
    --permission-mode acceptEdits \
    > "$LOG" 2>&1 &

echo $! > "$PIDFILE"
```

### `notify_hub.py` — 4 canales abstraídos

```python
class Urgency(IntEnum):
    HEARTBEAT = 0   # solo dashboard + log. No push.
    INFO      = 1   # macOS silent
    WARN      = 2   # macOS sound + Telegram
    CRITICAL  = 3   # macOS sound + Telegram + email

def notify(urgency, event, payload):
    write_to_dashboard(urgency, event, payload)
    append_to_log(urgency, event, payload)
    if urgency >= Urgency.INFO:    macos_notify(...)
    if urgency >= Urgency.WARN:    telegram_send(...)    # no-op si sin token
    if urgency >= Urgency.CRITICAL: email_send(...)      # no-op si sin Resend key
```

Rate limiting: mismo (order_id, event) en <30min → dedupe. CRITICAL nunca
dedupea.

Fallback: canal sin credenciales = no-op silencioso + log warning. MVP funciona
solo con macOS.

### `pending_lib.py` — CRUD compartido

Funciones:
- `load_pendings(profile)` → lista
- `load_all_pendings()` → dict por profile
- `save_pendings(profile, pendings)` → atomic rename
- `append_pending(profile, order)` → crea + append status_history
- `update_status(profile, id, new_status, note)` → append status_history
- `apply_whitelist_matrix(all_pendings)` → retorna (active, suspended_policy)
- `find_by_id(id)` → busca en todos los profiles

Atomic writes (JSON + rename) para evitar corrupción si el watcher corre en
paralelo con `/order`.

### `binance_real_order.py` — opcional `--real`

Solo ejecutado por `/order` cuando `profile == retail` y flag `--real`.

Requiere `.claude/.env`:
```
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
```

Operaciones:
- `submit_limit_order(symbol, side, qty, price, sl, tp)` → retorna order_id
- `cancel_order(order_id)` (llamado al invalidar)
- `get_order_status(order_id)` (para detectar fill desde Binance)

Wrapper mínimo sobre `python-binance` o llamadas directas a
`fapi.binance.com/fapi/v1/order`. Si falta cred → `--real` aborta con mensaje
explícito (no fallback silencioso).

**IMPORTANTE seguridad:** keys con permisos **Futures trade ON, Withdraw OFF,
IP whitelist 1 IP local**. Spec exige setup manual documentado, no auto.

### `price_feeds.py`

```python
def binance_futures_price(symbol) -> float:
    # fapi.binance.com/fapi/v1/ticker/price?symbol=BTCUSDT
    ...

def okx_swap_price(instId) -> float:
    # www.okx.com/api/v5/market/ticker
    ...

def twelvedata_price(symbol) -> float:
    # api.twelvedata.com/price?symbol=EUR/USD&apikey=...
    # 800 req/día free tier → suficiente para 8 assets × 24 ticks
    ...

def oanda_price(instrument) -> float:
    # Fallback si TwelveData rate-limited. api-fxpractice.oanda.com
    ...

def price_for(profile, asset) -> float:
    # dispatch según profile + asset
    ...
```

Cache in-memory durante un tick (un solo HTTP call por asset aunque 3 pending
referencien el mismo).

## Comandos

### `/order` (EDIT — extender)

Uso:
```
/order                                                     # deriva del último /morning
/order BTCUSDT.P LONG 77521 sl=77101 tp=78571 ttl=6h       # explícito
/order BTCUSDT.P LONG 77521 sl=77101 tp=78571 --real       # + Binance API
/order BTCUSDT.P LONG 77521 sl=77101 tp=78571 --check-regime  # invalida si régimen cambia
/order EURUSD SHORT 1.17198 sl=1.17278 tp=1.17038 ttl=3h   # fotmarkets
```

Flow:
1. Lee profile activo.
2. Path profile-specific:
   - `ftmo` → `guardian.py --action check-entry` (preservado).
   - `retail|retail-bingx` → sanity checks **no-bloqueantes** al momento de
     crear (no son las mismas validaciones que en el trigger; aquí solo:
     `sl` está del lado correcto respecto a `entry`, `tp` también, `risk_pct`
     ≤ 2.0, `qty * leverage` coherente con capital del profile). Filtros
     duros (RSI, BB, Donchian, cierre vela) se validan después en `/watch-deep`
     cuando el precio toque entry.
   - `fotmarkets` → `fotmarkets_guard.sh check` + phase sizing.
3. Aplica whitelist matrix. Si bloquea → prompt "¿cancelar existing o abortar?"
4. Preview ASCII + confirmación `YES`.
5. Si `--real` y profile=retail → `binance_real_order.submit_limit_order`,
   guarda `binance_order_id`.
6. `append_pending()` + `notify(INFO, "order_created")`.
7. Para ftmo conserva path EA existente (append a mt5_commands.json + poll).

### `/watch` (NEW)

Sin args. Llama `watcher_tick.py` inline desde Claude, imprime dashboard.

### `/watch-deep <order_id>` (NEW)

Invocado por `watcher_escalate.sh` headless o manual.

Flow:
1. `find_by_id(order_id)` → pending obj.
2. `chart_set_symbol` + TF según strategy del profile.
3. MCP: `data_get_study_values` (RSI, BB, Donchian, ATR, volume).
4. Opcional: lee Neptune outputs si cargados.
5. Evalúa cada filter en `required_filters_at_trigger` → PASS/FAIL.
6. Decide:
   - 4/4 PASS → `update_status(..., "triggered_go", note="all filters aligned")`,
     `notify(CRITICAL, "triggered_go", ...)`.
   - <4 PASS → `update_status(..., "pending", note="touched entry, filters X/4")`.
   - Error → `update_status(..., "check_error")`, `notify(WARN, "degraded_watcher")`.
7. Dibuja en TV si `triggered_go` (entry/SL/TPs con labels).

### `/pending` (NEW)

```
/pending                        # list profile activo
/pending all                    # list cross-profile
/pending cancel <id>            # → canceled_manual
/pending modify <id> tp1=X      # edit limitado: tp1|tp2|tp3|ttl|invalidation_price
/pending show <id>              # detalle + status_history
```

### `/filled <id>` (NEW)

```
/filled ord_xxx                 # status=filled, entry=entry de pending
/filled ord_xxx price=77498     # override si slippage
```

Escribe a `trading_log.md` del profile + update pending status.

### `/profile <target>` (EDIT — handshake)

Extender flow actual con pasos 3-6:

1. Validar no hay trade abierto (como hoy).
2. `load_pendings(current)` + `load_pendings(target)`.
3. Si current tiene active pending → handshake Caso A (suspend/cancel/keep_active).
4. Set profile.
5. Si target tiene suspended pending → handshake Caso B (discard/reopen).
6. Reactivar target suspended según elección.
7. `notify(INFO, "profile_switched")` + dashboard update.

Default si no responde en 10s: `suspend` + notif "decide con /pending".

### `/status` (EDIT — añadir sección watcher)

Añadir bloque:
```
## Watcher
Last tick: 11:00 CR (0.8s OK)
Pendings activos: 2 | suspended: 1
Próximo tick launchd: 12:00 CR
Próxima recomendación re-análisis: 13:00 CR
```

## Notificaciones — templates por evento

| Event | Urgency | macOS | Telegram | Email |
|---|---|---|---|---|
| `order_created` | INFO | ✓ silent | — | — |
| `near_entry` | WARN | ✓ Glass | ✓ | — |
| `triggered_go` | CRITICAL | ✓ Submarine | ✓ | ✓ |
| `invalidated_price` | WARN | ✓ Funk | ✓ | — |
| `invalidated_stopday` | WARN | ✓ Funk | ✓ | — |
| `expired_ttl` | INFO | ✓ silent | — | — |
| `expired_force_exit` | INFO | ✓ silent | — | — |
| `suspended_switch` | INFO | ✓ silent | — | — |
| `re_analysis_suggested` | INFO | ✓ silent | — | — |
| `degraded_watcher` | WARN | ✓ Funk | ✓ | — |
| `filled` | INFO | ✓ silent | — | — |

Heurística `re_analysis_suggested`:
- Distancia entry >2% + ATR normal → next_recheck = +2h
- Distancia 0.5–2% → +1h
- Distancia <0.5% → se escala ya, no re-análisis humano ahora

## Seguridad

1. **Binance API keys** (si `--real` se usa): permisos Futures Trade ON,
   Withdraw OFF, IP whitelist 1 IP local. Setup manual documentado en
   `NOTIFY_SETUP.md`. Never committed (`.env` gitignored).
2. **Telegram bot token**: bot privado, chat_id fijo, solo lectura/escritura
   a un chat. Rate-limited por Telegram por default.
3. **Resend/Email**: API key en `.env`. From: noreply local. Solo envío outbound.
4. **watcher_tick.py**: ejecuta sin credenciales salvo las de `--real`. Todas
   las APIs de price son públicas.
5. **`claude -p` headless**: `--permission-mode acceptEdits`. Scope limitado a
   `.claude/` path.
6. **Atomic JSON writes**: `pending_lib.save_pendings` usa `tempfile + os.rename`.

## Testing

### Unit tests (pytest)

- `test_pending_lib.py`: CRUD + whitelist matrix edge cases.
- `test_watcher_tick.py`: invalidaciones (TTL, precio, 2SL, force_exit) con
  fixtures de pending JSONs mockeados.
- `test_whitelist_matrix.py`: matriz YAML cargada, rules aplicadas en orden,
  ejemplos de la tabla UX.
- `test_notify_hub.py`: urgency dispatching; mocks de osascript/telegram/email.

### Integration tests (`.claude/scripts/test_integration.sh` — extender)

- Dry-run end-to-end: crea pending → simula price feed → assert status
  transitions.
- Smoke: `/order` en retail → watcher_tick → /pending list → /filled.
- Handshake: `/profile ftmo` con pending retail activa → prompt simulado.

### Manual test plan

1. Instalar launchd plist.
2. `/order BTCUSDT.P LONG <precio_actual - 1%> sl=... ttl=2h`.
3. `launchctl start com.wallytrader.watcher` manual.
4. Verificar dashboard.md actualizado + notif INFO.
5. Esperar movimiento de precio que invalide o trigger.
6. Confirmar notifs llegan por todos los canales configurados.

## Acceptance criteria

1. `/order` funciona en los 4 profiles (retail, retail-bingx, ftmo, fotmarkets)
   con al menos 1 smoke test por profile.
2. `watcher_tick.py` detecta TTL expired, precio rompe invalidación, 2 SLs hoy,
   force_exit — cada caso con fixture test pasando.
3. Whitelist matrix bloquea `retail + retail-bingx` simultáneos y `ftmo +
   fotmarkets` mismo asset family.
4. `notify_hub.py` corre en modo macOS-only cuando Telegram/email no
   configurados (fallback silencioso).
5. `/watch-deep` invocado headless via `claude -p` completa en <120s o reporta
   degraded_watcher.
6. `/profile` handshake funciona para suspend + reactivate (test manual
   documentado).
7. Dashboard.md human-readable con estado de todas las pending activas +
   suspended.
8. Binance `--real` flag opcional, aborta con mensaje claro si sin
   credenciales. (No requerido para v1 merge — puede ser stub).

## Plan de rollout

1. **Fase 1 (v1.0):** virtual-only en los 4 profiles. `--real` stub que imprime
   "not implemented". launchd + escalation Claude + notify macOS + dashboard +
   Telegram fallback silencioso.
2. **Fase 2 (v1.1):** Telegram integration activa (setup manual del usuario).
3. **Fase 3 (v1.2):** Email integration activa.
4. **Fase 4 (v1.3):** `--real` Binance API implementado + documentado.
5. **Fase 5 (v2):** News calendar invalidation, funding flip, 15-min interval
   dentro ventana activa.

Cada fase = PR separado. Fase 1 es el scope inmediato de este spec.

## Open questions (none blocking)

- ¿TwelveData o OANDA REST para precio forex del watcher? Decidir al implementar
  `price_feeds.py` — probablemente TwelveData (free tier 800 req/día suficiente
  para 1 tick/h × 8 assets).
- ¿macOS `osascript` sonidos en Big Sur + vs. Ventura+? Testear manualmente.
  Fallback: beep simple si sound name falla.

## References

- `CLAUDE.md` — reglas de profiles, cross-contamination
- `docs/superpowers/specs/2026-04-22-ftmo-profile-design.md` — precedente
  `pending_orders.json`
- `docs/superpowers/specs/2026-04-22-mt5-bridge-design.md` — EA bridge existente
- `docs/superpowers/specs/2026-04-23-fotmarkets-profile-design.md` — profile 3
- `.claude/profiles/ftmo/memory/pending_orders.json` — schema precedente
- `.claude/scripts/daily_cron.sh` — patrón launchd existente
- `.claude/scripts/notify.sh` — notify macOS existente (a ser absorbido por
  `notify_hub.py`)
