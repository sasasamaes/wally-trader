# PROMPT MAESTRO — STRATEGY BUILDER (WALLY-TRADER, MULTI-VENUE)

> Adapta el prompt original "construir EA MT5 para FTMO" al ecosistema completo
> de wally-trader. Soporta **MT5 (FTMO/FundingPips)**, **Bitunix** (signal-only)
> y **Binance** (signal-only). El "bot" (auto-ejecución) es **opcional** y solo
> aplica a MT5 — Bitunix y Binance generan señales para validación manual,
> respetando la filosofía del proyecto.
>
> **Para usar:** edita las secciones marcadas con ✏️. El resto es contexto fijo.
> Pega el prompt completo a Claude Code dentro del repo `wally-trader`.

---

## 0. INSTRUCCIONES PARA CLAUDE (LEER PRIMERO)

Estás operando dentro de **`/Users/josecampos/Documents/wally-trader`**. Antes
de generar cualquier código:

1. Lee `CLAUDE.md` para conocer profiles activos, reglas duras y filosofía.
2. Identifica el **profile activo** (`echo $WALLY_PROFILE` o por defecto retail).
3. **Reutiliza** los scripts ya existentes en `.claude/scripts/` (listados en §2).
   No reinventes lógica que ya está implementada y testeada.
4. Para cualquier código Python nuevo, sigue **TDD**: escribe los tests primero
   en `.claude/scripts/tests/test_<nombre>.py` (estilo de los tests existentes:
   `test_min_rr_gate.py`, `test_pullback_detector.py`).
5. Para cualquier MQL5 generado, replica el patrón de
   `.claude/profiles/ftmo/mt5_ea/ClaudeBridge.mq5` (file-based JSON I/O,
   heartbeat 5s, magic number único, kill-switch via `AllowExecution`).
6. **NUNCA** hardcodees claves API, `$capital` ni leverage en el código generado.
   Lee de `CLAUDE.md` o de los config files del profile.
7. Respeta la **regla #9** de CLAUDE.md: no abrir el mismo símbolo (BTC, ETH)
   simultáneamente en múltiples profiles. El bot/scan generado debe abortar si
   detecta posición ya abierta en otro profile.

---

## 1. SELECCIÓN DE VENUES ✏️ EDITAR

```
target_venues = [✏️]    # Marca uno o varios:
                        #   MT5_FTMO         → genera EA MQL5 ejecutable
                        #   MT5_FundingPips  → genera EA MQL5 ejecutable
                        #   Bitunix          → genera scan Python signal-only
                        #   Binance          → genera scan Python signal-only
                        #
                        # Reglas:
                        # - MT5_FTMO + MT5_FundingPips comparten EA bridge
                        #   (mismo Magic Number distinto, configs separados)
                        # - Bitunix y Binance NO ejecutan (signal-only)
                        # - Si seleccionas Binance + Bitunix para mismo símbolo:
                        #   el scan debe rechazar la 2da señal (regla #9)
```

**Modo bot (auto-ejecución):**
- MT5: **default ON** (la infra EA bridge ya existe y FTMO/FundingPips la necesitan).
- Bitunix: **siempre OFF** — el proyecto valida señales antes de copiar manualmente.
- Binance: **default OFF** — `binance_real_order.py` es stub. Auto-ejecución requiere implementación separada (out of scope de este prompt).

---

## 2. WALLY-TRADER ENVIRONMENT (CONTEXTO FIJO)

- **Repo:** `/Users/josecampos/Documents/wally-trader`
- **Timezone:** Costa Rica UTC-6 sin DST. Todo horario en formato `CR HH:MM`.
- **Profiles disponibles** (lee `CLAUDE.md` para detalles): `retail`, `retail-bingx`, `ftmo`, `fundingpips`, `fotmarkets`, `bitunix`, `quantfury`.
- **Profile activo:** `$WALLY_PROFILE` (default = `retail`).
- **Python venv:** `.claude/scripts/.venv/bin/python`. Tiene `requests`, `pandas`, `numpy`, `pytest`. NO instales otras deps sin justificar.
- **Statusline:** muestra `$capital ≈ ₡colones` por profile.

### Scripts y skills a REUTILIZAR (NO reimplementar)

| Helper | Path | Para qué |
|---|---|---|
| Macro events gate | `.claude/scripts/macro_gate.py --check-tier` | NO operar ±30min de high-impact event |
| Session quality | `.claude/scripts/session_quality.py` | VWAP-flat = dead session BLOCK |
| Min-R:R adaptive | `.claude/scripts/min_rr_gate.py --profile X --setup-rr Y` | R:R mínimo dinámico por WR rolling 30d |
| Volume divergence | `.claude/scripts/volume_divergence.py` | OBV pre-entry filter |
| ADX régimen | `.claude/scripts/adx_calc.py` | RANGE / TREND_LEVE / FUERTE / EXTREMO |
| Fib retracement | `.claude/scripts/fib_extension.py --mode retracement` | Entry zones 0.382/0.500/0.618 + SL 0.75 |
| Pullback detector | `.claude/scripts/pullback_detector.py` | Patrón impulse → pullback → continuation |
| Asian range | `.claude/scripts/asian_range.py` | EURUSD 5m London grab/fakeout |
| Liquidations heatmap | `.claude/scripts/liq_heatmap.py` | Cluster zones — SL no en honeypot |
| Bitunix log helper | `.claude/scripts/bitunix_log.py` | Append a signals_received.md/.csv |
| MT5 JSON I/O | `.claude/scripts/mt5_bridge.py` | Atomic write `mt5_commands.json` ↔ `mt5_state.json` |

### Skills slash relevantes

`/regime` `/validate` `/signal` `/risk` `/journal` `/macross` `/ml` `/multifactor` `/trail` `/macro-events-calendar` `/punk-hunt` `/punk-morning` `/log-outcome` `/order` `/watch`.

### Templates de output

| Tipo | Path |
|---|---|
| EA MQL5 | `.claude/profiles/<venue>/mt5_ea/ClaudeBridge.mq5` (referencia) |
| Bitunix signal log | `.claude/profiles/bitunix/memory/signals_received.md` (formato actual) |
| Pending order JSON | `.claude/watcher/` + spec `docs/superpowers/specs/2026-04-24-watcher-pending-orders-design.md` |

---

## 3. HORARIO DE ENTRADA Y GATING OBLIGATORIO

### Ventana operativa por profile

| Profile | Ventana CR | Notas |
|---|---|---|
| retail / retail-bingx | 06:00 – 23:59 | Force exit 23:59. No dormir con trade abierto. |
| ftmo | 06:00 – 16:00 | No overnight. |
| fundingpips | 06:00 – 16:00 (forex/indices) o 06:00 – 20:00 (crypto) | |
| fotmarkets | 07:00 – 11:00 | London/NY overlap. |
| bitunix | 24/7 (preferir London/NY overlap CR 06:00-15:00) | |
| quantfury | régimen-aware | TRENDING UP → HODL preferred |

### Gate obligatorio antes de CUALQUIER entrada

El código generado debe ejecutar **en este orden** y abortar si alguno falla:

```bash
# 1. Macro gate (HARD = NO-GO, WARN = reduce size 50%, SOFT = info)
.claude/scripts/.venv/bin/python .claude/scripts/macro_gate.py --check-tier
# exit 0=OK, 1=HARD, 2=WARN, 3=SOFT

# 2. Session quality (BLOCK si VWAP-flat = dead session)
.claude/scripts/.venv/bin/python .claude/scripts/session_quality.py --symbol $SYMBOL --quick
# exit 0=OK, 1=BLOCK, 2=WARN

# 3. Volume divergence (WARN si precio sube sin OBV)
.claude/scripts/.venv/bin/python .claude/scripts/volume_divergence.py \
  --symbol $SYMBOL --direction $DIR --quick

# 4. Min-R:R adaptativo
.claude/scripts/.venv/bin/python .claude/scripts/min_rr_gate.py \
  --profile $WALLY_PROFILE --setup-rr $PROYECTED_RR --json
# exit 0=OK, 2=WARN (degrada score -10)

# 5. Cross-profile BTC exclusion (regla #9)
# Si el setup es BTC/ETH, verificar que no hay posición abierta en otro profile
# (lectura simple de mt5_state.json del FTMO + signals_received.md PENDING bitunix
#  + pending_orders.json retail/binance).
```

Para **MT5** los gates se llaman desde el EA usando `ShellExecute` o se ejecutan
externamente y el EA lee el resultado de un archivo `gate_status.json` (más
limpio). Documentar esto en el EA con un comentario.

Para **Bitunix/Binance scan** los gates se llaman directamente como subprocess
desde el script Python.

---

## 4. ESTRATEGIA DE ENTRADA ✏️ EDITAR ESTA SECCIÓN

```
ESTRATEGIA: ✏️ <NombreEstrategia>
─────────────────────────────────

Indicadores:
  - ✏️ <indicador1 + parámetros>
  - ✏️ <indicador2 + parámetros>

Condición LONG (todas deben cumplirse):
  1. ✏️ <condición 1>
  2. ✏️ <condición 2>
  3. ✏️ <condición 3>
  4. ✏️ <condición 4>

Condición SHORT (espejo):
  1. ✏️ ...

Si no se cumple ninguna → no operar.
```

### Plantilla de ejemplo: Mean Reversion 4-filter (estrategia retail oficial)

```
ESTRATEGIA: Mean Reversion 15m (4 filtros)
──────────────────────────────────────────

Timeframe: 15m
Indicadores:
  - Donchian channel (length 15)
  - RSI(14) — OB 65 / OS 35
  - Bollinger Bands (20, 2)

Condición LONG (4/4 obligatorias):
  1. Precio toca o cruza Donchian Low(15) (dentro de 0.1%)
  2. RSI(14) < 35
  3. Low de la vela toca BB inferior
  4. Vela cierra verde

Condición SHORT (espejo).

Régimen requerido: RANGE_CHOP (ADX < 20). Si ADX ≥ 25 → no operar
(estrategia falla en TRENDING — backtest 2026-04-30 confirmó -34.83%).
```

Otros ejemplos disponibles en el proyecto: **Pullback detector** (impulse →
fib 0.382-0.618 → continuation, ADX≥25), **Asian Range** (London grab/fakeout
EURUSD 5m), **MA Crossover** (EMA 9/21 para TREND_LEVE).

---

## 5. STOP LOSS Y TAKE PROFIT ✏️ ELEGIR UNA OPCIÓN

**Opción A — SL dinámico Donchian/N-bars (recomendado para Mean Reversion)**
```
LONG:  SL = mín(últimas N velas) - buffer_pts
SHORT: SL = máx(últimas N velas) + buffer_pts
```

**Opción B — SL ATR-based (recomendado para breakout/trend)**
```
SL = entry ± (ATR(14) × multiplicador)
```

**Opción C — SL fijo en puntos (pip/tick scalping)**
```
SL = entry ± X puntos
```

**TPs escalonados (estándar wally):**
```
TP1 (40% size) = entry ± (sl_distance × 2.5)  → al hit, SL → BE
TP2 (40% size) = entry ± (sl_distance × 4.0)
TP3 (20% size) = entry ± (sl_distance × 6.0)  o trailing EMA(20) vía /trail
```

`InpRRRatio` configurable (mínimo 1.5; el `min_rr_gate` lo valida dinámicamente).

---

## 6. GESTIÓN DE RIESGO — POR PROFILE

**NO HARDCODEAR.** El bot/scan debe leer del config del profile activo:

| Profile | Risk/trade | Leverage cap | Max trades/día | Daily loss BLOCK | Notas |
|---|---|---|---|---|---|
| retail | 2% | 10x | 5 | -2% | Binance Futures, BTCUSDT.P |
| retail-bingx | observación | 10x | 0 | n/a | $0.93 — pedagógico, no ejecutar |
| ftmo | 0.5% | 1:100 | per rules | -3% (≥-2% del balance inicio día) | EA bridge ClaudeBridge.mq5 |
| fundingpips | 0.3% | 1:50 | 2 | -3% (≥5% trailing prohibido) | EA bridge reusado de FTMO |
| fotmarkets | 10% / 5% / 2% (escalation por fase) | 1:500 | per phase | -2% | Manual MT5, sin EA bridge |
| bitunix | 2% (signal externa, hasta 25% margin si user lo decide) | 20x (excepción 10x global) | 7 | -6% | Signal-only via /signal |
| quantfury | 2% del BTC capital | 5x | régimen-aware | -2% | BTC unit, no USD |

**Cálculo de lotes (ejemplo MT5):**
```mql5
risk_usd  = AccountInfoDouble(ACCOUNT_BALANCE) * (InpRiskPercent / 100);
point_val = SYMBOL_TRADE_TICK_VALUE / SYMBOL_TRADE_TICK_SIZE;
lots      = risk_usd / (sl_distance * point_val);
// Normalizar con SYMBOL_VOLUME_STEP, MIN, MAX
```

**Cálculo de tamaño (ejemplo Bitunix/Binance — signal-only Python):**
```python
# Reutilizar el módulo /risk del proyecto
from risk_helper import compute_size  # adaptar al import real
size = compute_size(profile=WALLY_PROFILE, risk_pct=2.0, sl_distance=ABS(entry-sl))
```

---

## 7. FILTROS Y PROTECCIONES OBLIGATORIAS

### Universales (todos los venues)

1. **Una operación por día** (`InpOneTradePerDay = true`) — flag `gTradedToday` reseteado en bar nuevo de UTC midnight.
2. **EOD close** — cerrar todo a `InpCloseHour:InpCloseMinute` del servidor (recomendado 22:45 server time para FTMO US500).
3. **Spread filter** — abortar si `(ASK-BID)/POINT > InpMaxSpreadPts`.
4. **Símbolo válido** en OnInit/setup (`SymbolSelect(InpSymbol, true)` para MT5; verificar que el ticker existe en Binance/Bitunix).
5. **Posición abierta del mismo Magic+Symbol** — abortar si ya hay una.

### Wally-specific (NUEVOS — obligatorios)

6. **Macro gate** — `macro_gate.py --check-tier` (sección §3).
7. **Session quality** — `session_quality.py` (sección §3).
8. **Min-R:R adaptive** — `min_rr_gate.py` (sección §3).
9. **Volume divergence** — `volume_divergence.py` (sección §3).
10. **Cross-profile BTC exclusion** — regla #9 CLAUDE.md.
11. **Daily loss FTMO-aware** (si target=MT5/FTMO/FundingPips):
    ```mql5
    gDayStartBal = balance al inicio del día
    if ((gDayStartBal - equity) / gDayStartBal * 100 >= InpMaxDailyLoss)
        CloseAllPositions(); gAborted = true;
    ```

### Opcionales (activar con flag)

- Break-even automático: SL → entry cuando PnL ≥ 1× SL distance (TP1 hit)
- Trailing stop EMA(20) vía `/trail` (skill existente)
- ATR mínimo gate (no operar si volatilidad insuficiente)
- ML score gate (`ml_score < 40` con setup 4/4 → reducir size 50%)

---

## 8. OUTPUT POR VENUE

### 8.A. Si target = MT5_FTMO o MT5_FundingPips

**Generar archivo:** `.claude/profiles/<venue>/mt5_ea/<NombreEstrategia>_<symbol>_<TF>.mq5`

**Patrón:** replicar **`ClaudeBridge.mq5`** (production-ready, 1200 líneas). Estructura mínima:

```mql5
//+------------------------------------------------------------------+
//| Wally Trader — <NombreEstrategia> EA for <venue>                 |
//| Generated by docs/prompts/wally-strategy-builder.md              |
//+------------------------------------------------------------------+
#property strict
#property version "1.00"
#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>

//─── INPUTS ──────────────────────────────────────────────────────
input group "Identity"
input int    InpMagicNumber  = 770001; // único 6 dígitos
input string InpSymbol       = "US500.cash"; // ✏️
input ENUM_TIMEFRAMES InpTF  = PERIOD_H1;

input group "Risk (FTMO-compliant)"
input double InpRiskPercent  = 0.5;   // ≤1% FTMO
input double InpRRRatio      = 2.0;
input double InpMaxDailyLoss = 3.0;   // <5% FTMO

input group "Schedule"
input int    InpOpenHour     = 14;    // ✏️ ajustar al servidor (ver CLAUDE de FTMO)
input int    InpOpenMinute   = 0;
input int    InpCloseHour    = 22;
input int    InpCloseMinute  = 45;

input group "Filters"
input bool   InpOneTradePerDay = true;
input bool   InpCheckSpread    = true;
input double InpMaxSpreadPts   = 15.0;
input bool   InpUseGates       = true; // llama a macro_gate / session_quality / min_rr_gate
input bool   AllowExecution    = true; // KILL SWITCH global

//─── GLOBALS ─────────────────────────────────────────────────────
CTrade        trade;
CPositionInfo posInfo;
datetime      gLastBarTime = 0;
double        gDayStartBal = 0;
bool          gTradedToday = false;
bool          gAborted     = false;

//─── LIFECYCLE ───────────────────────────────────────────────────
int OnInit() {
    if (!SymbolSelect(InpSymbol, true)) return INIT_FAILED;
    trade.SetExpertMagicNumber(InpMagicNumber);
    trade.SetDeviationInPoints(30);
    trade.SetTypeFilling(ORDER_FILLING_IOC);
    gDayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);
    PrintFormat("[Wally][%s] EA started. Risk=%.2f%% RR=%.1f Magic=%d",
                InpSymbol, InpRiskPercent, InpRRRatio, InpMagicNumber);
    return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {
    // liberar handles si los hay
}

void OnTick() {
    if (!AllowExecution || gAborted) return;
    datetime barTime = iTime(InpSymbol, InpTF, 0);
    if (barTime == gLastBarTime) return;
    gLastBarTime = barTime;

    // reset diario
    MqlDateTime dt; TimeToStruct(barTime, dt);
    static int lastDay = -1;
    if (dt.day != lastDay) {
        lastDay = dt.day;
        gTradedToday = false;
        gDayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);
    }

    // protección daily loss FTMO
    if (IsDailyLossLimitReached()) {
        CloseAllPositions(); gAborted = true; return;
    }

    // EOD close
    if (dt.hour == InpCloseHour && dt.min == InpCloseMinute) {
        CloseAllPositions(); return;
    }

    // ventana de entrada
    bool isOpeningBar = (dt.hour == InpOpenHour && dt.min == 0);
    if (!isOpeningBar) return;
    if (InpOneTradePerDay && gTradedToday) return;
    if (HasOpenPosition()) return;
    if (InpCheckSpread && IsSpreadTooHigh()) return;

    // gates wally (lee gate_status.json escrito por scheduler externo)
    if (InpUseGates && !PassesWallyGates()) return;

    // ── EVALUAR ESTRATEGIA (sección §4) ──
    int signal = EvaluateStrategy(); // -1 = SHORT, 0 = none, +1 = LONG
    if (signal == 0) return;

    ExecuteTrade(signal);
    gTradedToday = true;
}

//─── TODO: implementar EvaluateStrategy(), ExecuteTrade(),
//        CalculateLotSize(), IsDailyLossLimitReached(),
//        IsSpreadTooHigh(), HasOpenPosition(), CloseAllPositions(),
//        PassesWallyGates() lee .claude/cache/gate_status.json
//─────────────────────────────────────────────────────────────────
```

**Conexión wally:** los gates wally se ejecutan **fuera del EA** (vía cron/launchd Python), escriben resultado a `.claude/cache/gate_status_<symbol>.json`, y el EA lo lee. Esto evita hacer ShellExecute desde MQL5 y mantiene el EA puro.

**Output adicional:** un launchd plist `~/Library/LaunchAgents/com.wally.gate-feeder-<symbol>.plist` que corre cada 5 min ejecutando los 4 gates de §3 y escribe el JSON.

### 8.B. Si target = Bitunix (signal-only — DEFAULT)

**Generar archivo:** `.claude/scripts/scan_<nombre_estrategia>.py`

```python
#!/usr/bin/env python3
"""scan_<nombre>.py — <descripción> para profile bitunix.

Detecta el setup, valida los gates wally, y genera signal markdown que se
appends a signals_received.md + alerta macOS. NO ejecuta ninguna orden.
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent.parent
CR = timezone(timedelta(hours=-6))

def _run(cmd: list[str]) -> tuple[int, str]:
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode, res.stdout.strip()

def gates_ok(symbol: str, direction: str, profile: str, projected_rr: float) -> tuple[bool, list[str]]:
    """Run the 4 wally gates. Return (all_ok, list_of_warnings)."""
    venv_py = SCRIPTS_DIR / ".venv" / "bin" / "python"
    warnings: list[str] = []

    rc, _ = _run([str(venv_py), str(SCRIPTS_DIR / "macro_gate.py"), "--check-tier"])
    if rc == 1: return False, ["MACRO_HARD"]
    if rc == 2: warnings.append("MACRO_WARN_HALF_SIZE")

    rc, _ = _run([str(venv_py), str(SCRIPTS_DIR / "session_quality.py"),
                  "--symbol", symbol, "--quick"])
    if rc == 1: return False, ["DEAD_SESSION"]
    if rc == 2: warnings.append("SESSION_COMPRESSED")

    rc, _ = _run([str(venv_py), str(SCRIPTS_DIR / "min_rr_gate.py"),
                  "--profile", profile, "--setup-rr", str(projected_rr), "--json"])
    if rc == 2: warnings.append("LOW_RR")

    rc, _ = _run([str(venv_py), str(SCRIPTS_DIR / "volume_divergence.py"),
                  "--symbol", symbol, "--direction", direction, "--quick"])
    if rc == 2: warnings.append("VOL_DIV_BEARISH")

    return True, warnings

def detect_setup(symbol: str) -> dict | None:
    """✏️ Implementar la lógica de la estrategia descrita en §4.

    Debe devolver dict con: direction (long/short), entry, sl, tp1, tp2, tp3,
    leverage, score (0-100), filters_passed (list[str]).
    Si no hay setup, devolver None.
    """
    raise NotImplementedError("✏️ Implementar la estrategia §4 aquí")

def append_signal_md(setup: dict, symbol: str, warnings: list[str]) -> None:
    """Append al signals_received.md del profile bitunix con formato canonical."""
    log_path = REPO_ROOT / ".claude" / "profiles" / "bitunix" / "memory" / "signals_received.md"
    ts = datetime.now(CR).strftime("%Y-%m-%d %H:%M CR")
    sl_pct = abs(setup["entry"] - setup["sl"]) / setup["entry"] * 100
    block = f"""

## {ts} — {symbol} {setup['direction'].upper()} [self-generated via scan_<nombre>]
- Entry: {setup['entry']}
- SL: {setup['sl']} ({sl_pct:+.2f}%)
- TP1: {setup['tp1']} | TP2: {setup['tp2']} | TP3: {setup['tp3']}
- Leverage: {setup['leverage']}x
- Score: {setup['score']}/100
- Filters: {len(setup['filters_passed'])}/4 passed ({', '.join(setup['filters_passed'])})
- Warnings: {', '.join(warnings) if warnings else 'none'}
- Outcome: PENDING
"""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as f:
        f.write(block)

def macos_alert(symbol: str, setup: dict) -> None:
    """terminal-notifier alert (best-effort)."""
    try:
        subprocess.run([
            "terminal-notifier",
            "-title", f"Wally signal: {symbol} {setup['direction'].upper()}",
            "-message", f"Entry {setup['entry']}  SL {setup['sl']}  Score {setup['score']}/100",
            "-sound", "default",
        ], capture_output=True, timeout=5)
    except Exception:
        pass

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    p.add_argument("--profile", default="bitunix")
    p.add_argument("--no-emit", action="store_true",
                   help="dry-run: detect but don't append/notify")
    args = p.parse_args()

    setup = detect_setup(args.symbol)
    if setup is None:
        print(f"NO_SETUP — {args.symbol}")
        return 0

    projected_rr = abs(setup["tp1"] - setup["entry"]) / abs(setup["entry"] - setup["sl"])
    ok, warnings = gates_ok(args.symbol, setup["direction"], args.profile, projected_rr)
    if not ok:
        print(f"GATE_FAIL — {warnings}")
        return 0

    if args.no_emit:
        print(f"SETUP DETECTED (dry-run) — {setup}")
        return 0

    append_signal_md(setup, args.symbol, warnings)
    macos_alert(args.symbol, setup)
    print(f"SIGNAL EMITTED — {args.symbol} {setup['direction']} score={setup['score']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

**Tests obligatorios:** `.claude/scripts/tests/test_scan_<nombre>.py` con
fixtures sintéticos (synthetic OHLCV) que verifiquen `detect_setup()` happy
path + 2-3 edge cases. Imitar estilo de `test_pullback_detector.py`.

**Cierre del loop:** el usuario invoca `/log-outcome SYMBOL TP1|TP2|TP3|SL EXIT_PRICE`
para cerrar la señal cuando se materializa el outcome.

### 8.C. Si target = Binance (signal-only — DEFAULT)

**Generar archivo:** `.claude/scripts/scan_<nombre>_binance.py`

Estructura **idéntica a 8.B** con dos diferencias:

1. **No append a `signals_received.md`** (ese log es exclusivo de bitunix). En su lugar, append a `.claude/watcher/pending_orders.json` con status `manual_pending`:

```python
def append_pending_order(setup: dict, symbol: str) -> None:
    pending_path = REPO_ROOT / ".claude" / "watcher" / "pending_orders.json"
    pending_path.parent.mkdir(parents=True, exist_ok=True)
    state = {"pending": []}
    if pending_path.exists():
        state = json.loads(pending_path.read_text())
    cmd_id = f"scan_{int(datetime.now().timestamp())}"
    state["pending"].append({
        "id": cmd_id,
        "symbol": symbol,
        "setup": f"<NombreEstrategia> {setup['direction'].upper()}",
        "entry": setup["entry"],
        "sl": setup["sl"],
        "tp1": setup["tp1"], "tp2": setup["tp2"], "tp3": setup["tp3"],
        "status": "manual_pending",
        "guardian_verdict": "OK",
        "filters_passed": len(setup["filters_passed"]),
        "ts_emit": datetime.now(CR).isoformat(),
    })
    tmp = pending_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(pending_path)  # atomic
```

2. **OHLCV vía Binance public klines** (sin auth): reutilizar el patrón de
   `pullback_detector.py::_fetch_bars_binance`.

**NO incluye `binance_real_order.py`.** Si en el futuro quieren auto-ejecución,
implementar ese stub es out of scope (separate spec).

---

## 9. ESTRUCTURA DEL CÓDIGO Y CONVENCIONES

### MQL5 (MT5 EAs)
- Variables globales con prefijo `g`: `gTradedToday`, `gLastBarTime`, `gDayStartBal`
- Inputs con prefijo `Inp`: `InpRiskPercent`, `InpOpenHour`
- Funciones PascalCase: `CalculateLotSize`, `HasOpenPosition`, `PassesWallyGates`
- `ArraySetAsSeries(buffer, true)` ANTES de `CopyBuffer`
- Usar `shift=1` (vela cerrada anterior) para señales confirmadas; nunca `shift=0`
- Logs: `PrintFormat("[Wally][%s] ...", InpSymbol)` con timestamp implícito

### Python (Bitunix/Binance scans)
- `from __future__ import annotations`
- `SCRIPTS_DIR` y `REPO_ROOT` anchored vía `Path(__file__).resolve()`
- Helpers privados con `_` prefix: `_run`, `_fetch_bars`
- Tests sintéticos en `.claude/scripts/tests/test_scan_<nombre>.py`
- Exit codes: `0=OK 1=BLOCK 2=WARN 3=error`
- `--no-emit` flag para dry-run (testing)
- Logs con `print()` para uso CLI, o structlog si se integra al pipeline

### Tests obligatorios (TDD)
Sigue el patrón superpowers `test-driven-development`:
1. Escribe el test primero
2. Verifica que falla (`pytest -v` con error de import o aserción)
3. Implementa el mínimo código para que pase
4. Refactor

Mínimo por scan: 4-6 tests cubriendo happy path, no-setup, gate failures,
edge cases (boundary RR, sample insuficiente, etc.).

---

## 10. DEPLOY Y SMOKE TEST

### MT5 (FTMO / FundingPips)

1. Compilar `.mq5` en MetaEditor (`F7`) — verificar 0 errores.
2. Copiar a `~/AppData/Roaming/MetaQuotes/Terminal/<ID>/MQL5/Experts/` (Windows) o equivalente macOS Wine.
3. Ajustar `InpOpenHour` según servidor FTMO/FundingPips:
   - Mira la hora del servidor en la esquina inferior derecha de MT5.
   - Si servidor marca `14:30` cuando en CR son `07:30` (NYSE 09:30 EST = CR 07:30) → `InpOpenHour = 14`.
4. Activar **Autotrading** en la barra superior.
5. Verificar en el Journal que el EA imprimió sus parámetros (`[Wally][US500.cash] EA started`).
6. Activar el launchd plist del **gate feeder** (cron 5 min):
   ```bash
   cp .claude/launchd/com.wally.gate-feeder-<symbol>.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.wally.gate-feeder-<symbol>.plist
   ```
7. **Strategy Tester obligatorio antes del challenge real:**
   - `Ctrl+R` → símbolo `US500.cash` (o el ✏️) → modo `Cada tick` → ≥6 meses de histórico → depósito = al de la cuenta FTMO real.
   - Esperar ≥30 trades en backtest. Verificar Sharpe, Max DD, Profit Factor.

### Bitunix (signal-only)

1. Smoke test del scan:
   ```bash
   .claude/scripts/.venv/bin/python .claude/scripts/scan_<nombre>.py \
     --symbol BTCUSDT --no-emit
   ```
2. Tests:
   ```bash
   .claude/scripts/.venv/bin/python -m pytest \
     .claude/scripts/tests/test_scan_<nombre>.py -v
   ```
3. Para corrida automática, programa con launchd (cada 1h o on-demand):
   ```bash
   /loop 60m .claude/scripts/.venv/bin/python .claude/scripts/scan_<nombre>.py --symbol BTCUSDT
   ```
   o invocación manual.
4. Cada signal emitido se cierra con `/log-outcome SYMBOL TP1|TP2|TP3|SL EXIT_PRICE`.

### Binance (signal-only)

1. Mismo smoke test + tests.
2. Las pending orders aparecen en `.claude/watcher/pending_orders.json` con status `manual_pending`.
3. Usuario las ejecuta manualmente en Binance Futures, confirma con `/filled SYMBOL`.
4. **NO ejecutar el scan en cron sin antes verificar 1-2 días de manual review** — evita ruido al watcher.

---

## 11. CHECKLIST FINAL ANTES DE ENTREGAR EL CÓDIGO GENERADO

Claude debe responder con:

- [ ] `Status: DONE | DONE_WITH_CONCERNS | BLOCKED`
- [ ] Lista de archivos creados (paths absolutos)
- [ ] Para cada test creado: `pytest -v` output (X/X passed)
- [ ] Para MT5: confirmar que `MetaEditor` compila sin errores (o nota explicita "no se pudo verificar — requiere MT5 instalado")
- [ ] Smoke test del scan (output del `--no-emit`)
- [ ] Self-review:
  - ¿Reutilicé los scripts de §2 o reimplementé lógica?
  - ¿Los gates de §3 están todos llamados antes de emitir señal?
  - ¿La sección 6 risk se lee de config, no hardcoded?
  - ¿La regla #9 (cross-profile BTC exclusion) está implementada?
- [ ] Cualquier deviación del prompt (justificada con razón)

---

## REFERENCIAS

- `CLAUDE.md` (raíz) — profiles, reglas, filosofía
- `.claude/profiles/ftmo/mt5_ea/ClaudeBridge.mq5` — template MQL5 production-ready
- `.claude/scripts/mt5_bridge.py` — JSON I/O patterns
- `.claude/scripts/macro_gate.py`, `session_quality.py`, `min_rr_gate.py`, `volume_divergence.py` — gates obligatorios
- `.claude/scripts/bitunix_log.py` — append a signals_received.md
- `.claude/profiles/bitunix/memory/signals_received.md` — formato canonical
- `.claude/watcher/` — pending orders queue (Binance)
- `docs/superpowers/specs/2026-04-24-watcher-pending-orders-design.md` — watcher spec
- Bundle 3 (2026-05-12): `pullback_detector.py`, `asian_range.py`, `min_rr_gate.py`, `challenge_readiness.py` — ejemplos completos del estilo target

---

# FIN DEL PROMPT

> **Para usar:** copia desde "PROMPT MAESTRO" hasta este punto, edita las
> secciones marcadas con ✏️, pega a Claude Code dentro del repo wally-trader.
