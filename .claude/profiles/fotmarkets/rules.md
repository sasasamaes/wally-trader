# Fotmarkets Rules — Formal Spec

Reglas de operación del profile `fotmarkets`. Este documento es fuente de verdad
para los scripts `fotmarkets_guard.sh` y `fotmarkets_phase.sh`.

## R1 — Phase Detection

**Definición:** La fase activa se determina por capital actual en `memory/phase_progress.md`.

```
phase_1: capital ∈ [0, 100)
phase_2: capital ∈ [100, 300)
phase_3: capital ∈ [300, ∞)
```

**Enforcement:** `fotmarkets_phase.sh` emite la fase; comandos profile-aware la leen.

## R2 — Risk per trade (phase-aware)

| Fase | Risk % | Cap USD |
|---|---|---|
| 1 | 10% | $3.00 fijo |
| 2 | 5% | dinámico |
| 3 | 2% | dinámico |

**Enforcement:** `/risk` aplica automáticamente según fase.

## R3 — Max trades/día (phase-aware)

| Fase | Max trades/día |
|---|---|
| 1 | 1 |
| 2 | 2 |
| 3 | 3 |

**Enforcement:** `fotmarkets_guard.sh` cuenta trades en `trading_log.md` del día
(líneas con fecha actual). Si trades_today >= max → BLOCK.

## R4 — Max SL consecutivos (phase-aware)

| Fase | Max SL consecutivos |
|---|---|
| 1 | 1 (cualquier SL → STOP día) |
| 2 | 2 |
| 3 | 2 |

**Enforcement:** `fotmarkets_guard.sh` lee últimos N trades del día (N = max + 1);
si todos son SL → BLOCK.

## R5 — Ventana operativa CR 07:00–11:00

**Definición:** Entries nuevos solo en [07:00, 10:55]. Force exit a 10:55.

**Enforcement:** `fotmarkets_guard.sh` chequea hora CR actual.

## R6 — No overnight / no weekend

**Definición:** Toda posición debe cerrarse antes de 10:55 CR del día. Nunca entrar
viernes si queda <1h para cierre de mercado (overnight implícito weekend).

**Enforcement:** Semi-automatizado — usuario cierra manualmente en MT5; `/journal`
detecta posiciones abiertas fuera de ventana y warninga.

## R7 — Asset whitelist por fase

Ver config.md (`phase_N.allowed_assets`). Intentar entry en asset fuera del
whitelist de la fase → BLOCK con mensaje "Asset X no desbloqueado hasta Fase Y".

## R8 — Hard stops operativos

Aplican en TODAS las fases:

1. ATR explotado (>2× promedio 50 velas en 5m) → NO operar
2. Spread anómalo (>3 pips EURUSD base, escalado para otros pairs) → NO operar
3. 15 min pre-noticia roja → cerrar posiciones abiertas + no reentrar 30 min post
4. ECB jueves 07:00–09:00 CR → no EUR pairs

**Enforcement:** Manual via checklist en strategy.md + recordatorio en `/morning`.

## R9 — Phase migration

Cuando capital cruza threshold ($100 o $300) durante el día:
1. `/journal` detecta cambio al cierre
2. Actualiza `phase_progress.md` con nueva fase
3. Emite mensaje explícito: "FASE NUEVA → assets desbloqueados: [...], risk baja a X%"
4. Usuario debe confirmar explícitamente antes de operar en fase nueva (al día siguiente)

## R10 — Override escape hatch

Usuario puede escribir literalmente `OVERRIDE FOTMARKETS` en respuesta a un BLOCK.
El guardian:
1. Registra evento en `memory/overrides.log` con timestamp, regla violada, capital, trade
2. Permite proceder

Usar solo en casos extremos. Cada override es material de post-mortem.

## Diferencias con retail y ftmo

| Aspecto | retail | ftmo | fotmarkets |
|---|---|---|---|
| Risk per trade | 2% fijo | 0.5% fijo | 10%/5%/2% por fase |
| Max trades/día | 3 | 2 | 1/2/3 por fase |
| Guardian DD rules | No | Sí (3% daily) | No (es bonus) |
| Override keyword | N/A | `OVERRIDE GUARDIAN` | `OVERRIDE FOTMARKETS` |
| Asset whitelist | BTC fijo | 6 fijos | 2/5/8 por fase |
