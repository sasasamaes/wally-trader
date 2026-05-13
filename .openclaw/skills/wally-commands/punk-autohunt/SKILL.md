---
name: punk-autohunt
description: Cazador autónomo horario — 1 setup con TP dinámico ($10 floor, techo
  libre) [solo bitunix, MVP en --paper]
version: 1.0.0
metadata:
  openclaw:
    tags:
    - wally-trader
    - command
    - slash
    category: trading-command
    requires_toolsets:
    - terminal
    - subagents
---
<!-- generated from system/commands/punk-autohunt.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /punk-autohunt -->


**Cazador autónomo horario.** Genera **1 setup ejecutable** por tick (cada ~60 min) usando la pipeline de 9 stages: kill-switch + macro tier + session quality + universe + analytics fan-out + vetos + confluence score + PnL floor + single-best-pick.

**Estado MVP (2026-05-12):** modo `--paper` recomendado hasta validar con 20 picks. Live mode también disponible para uso consciente.

## Diferencia vs comandos existentes

| Comando | Frecuencia | Modo | Output |
|---|---|---|---|
| `/signal` | manual | validar Discord | GO/NO-GO sobre señal externa |
| `/punk-hunt` | manual | escanear 24 cripto | top setup por score elite-crypto |
| `/punk-smart` | manual | regime router | N setups por R:R, sin TPs adaptativos |
| **`/punk-autohunt`** | **horaria** ⏱ | **autónomo single-pick** | **1 pick con TP dinámico $10 floor** |

`/punk-autohunt` es la **única evolución** de `/punk-smart` que añade:
- ✅ Score de confluencia 0-100 fusionado de 11 componentes
- ✅ TP dinámico (TP1/TP2/TP3 escalados al expected_move + cap por liq magnet)
- ✅ Floor obligatorio $10 — si TP3 < $10 → drop silent
- ✅ ATR-extreme gate (Apéndice B del spec — protege contra modo SAGA)
- ✅ Honest "no setup this hour" en lugar de forzar pick mediocre
- ✅ Paper-mode con CSV paralelo para validar antes de graduar a live

## Flags

```
/punk-autohunt              # live mode (loggea a autohunt_signals.csv + propone TV draw)
/punk-autohunt --paper      # paper mode (loggea a autohunt_paper_log.csv, sin TV)
/punk-autohunt --dry-run    # no CSV, no TV — solo reporta
/punk-autohunt --asset SYM  # fuerza un único asset (skip universe)
/punk-autohunt --json       # JSON a stdout (para automation)
```

**Recomendación inicial:** correr `--paper` durante 20 picks. Acceptance criteria para graduar a live:
- WR ≥ 50%, PF ≥ 1.40, avg $/pick ≥ $5, max losing streak ≤ 3, DD ≤ 15%, picks A-GRADE ganan ≥ 60%.

## Pasos que ejecuta Claude

1. **Profile guard (bitunix-only):**
   ```bash
   [ "$(python3 .claude/scripts/profile.py get | awk '{print $1}')" = "bitunix" ] || { echo "Solo bitunix"; exit 1; }
   ```

2. **Run autohunt (paper recomendado en MVP):**
   ```bash
   python3 .claude/scripts/autohunt.py --paper --json $ARGUMENTS
   ```
   o para live:
   ```bash
   python3 .claude/scripts/autohunt.py --json $ARGUMENTS
   ```

3. **Parse JSON output:**
   - `status: BLOCKED` → muestra razón (macro HARD, session BLOCK, daily cap, kill-switch, slot full)
   - `status: NO_PICK` → muestra top-5 drops + ventana próxima
   - `status: PICK` → procede

4. **Si hay PICK y modo live (no --paper, no --dry-run):**
   El JSON incluye `draw_instructions: [{symbol, shape, price, label, color}, ...]`.
   Ejecutar **en orden**:
   ```
   mcp__tradingview__chart_set_symbol(symbol=BITUNIX:<sym>.P)
   mcp__tradingview__chart_set_timeframe("15")
   mcp__tradingview__draw_list()      # localizar dibujos previos con prefix "autohunt:"
   # remover via draw_remove_one cada uno; fallback context-menu si draw_clear falla
   # luego, por cada instruction del JSON:
   mcp__tradingview__draw_shape(shape=horizontal_line, price=..., label=..., color=...)
   ```

5. **Mostrar reporte humano del pick** (formato del JSON `pick`):
   - Header: símbolo, side, score, tier
   - Entry/SL/TP1/TP2/TP3 con $ y % y close_pct
   - Expected move, ATR%, sizing
   - Floor status (OK / TP3_ONLY / DROP)
   - Flags: margin_bumped, atr_extreme

6. **Si modo `--paper`:** confirmar logueado a `autohunt_paper_log.csv` con `origin=autohunt-paper`.

7. **Cierre del outcome (manual):** cuando el trade cierre, ejecutar:
   ```bash
   /log-outcome <SYMBOL> TP1|TP2|TP3|SL <EXIT_PRICE> --pnl <USD>
   ```
   (NOTA: el `/log-outcome` actual escribe a `signals_received.csv`; el paper log de autohunt es separado — se cierra manualmente editando el CSV o vía un comando dedicado en v2)

## Output esperado

**Caso A — Pick encontrado (A-GRADE):**

```
========================================================================
PUNK-AUTOHUNT — hourly tick 14:00 CR  |  pick 3/7 today, 1/2 concurrent  |  ORIGIN: autohunt-paper
========================================================================

ASSET: SOLUSDT  SIDE: 🔴 SHORT  SCORE: 82/100  TIER: A-GRADE
Regime: STRONG_TREND_DOWN 15m  |  Strategy: B_TrendPullback  (BT $/trade $+1.19)

  Entry: 145.20  SL: 146.95
  TP1:   143.10  (+1.45%, +$10.55)   close 40%
  TP2:   141.00  (+2.89%, +$21.10)   close 30%
  TP3:   137.40  (+5.37%, +$39.20)   close 30%

  Expected move: 5.37%  |  ATR(15m)%: 0.450
  Sizing: $50 margin × 15x = $750 notional
  Session: OK  |  Macro: OK
  Floor status: OK

📤 Logged to autohunt_paper_log.csv
🎨 TV draw instructions emitted (5 shapes)
```

**Caso B — No pick (honest output):**

```
⏳ PUNK-AUTOHUNT — no A/B-grade setup at 14:00 CR

  Evaluated 10 assets. Top-5 drops:
  - BTCUSDT     LONG  reason: score 64 < 60 (C-GRADE)
  - INJUSDT     SHORT reason: PnL_FLOOR (TP3_ONLY, TP3=$4.20)
  - AVAXUSDT    LONG  reason: VETOED (sentiment,funding)
  - DOGEUSDT    SHORT reason: STAND_ASIDE: regime VOLATILE not tradeable
  - SOLUSDT     LONG  reason: NO_SETUP: A_VWAP no triggea

  Slot: 3/7 today, 1/2 concurrent
  Next tick: in ~60 min
```

**Caso C — Pre-flight blocked:**

```
🚫 PUNK-AUTOHUNT — blocked: kill-switch active until 2026-05-13T00:00:00-06:00
```

## Auto-pace recomendado

Para ejecución horaria automática:
```
/loop 60m /punk-autohunt --paper
```

Para uso manual on-demand: simplemente invocar `/punk-autohunt` cuando el usuario quiera.

## Reglas de invalidación

- Profile ≠ `bitunix` → exit
- Kill-switch activo (2 SLs en 4h ventana) → block
- Macro tier `HARD` (±30 min de FOMC/CPI/NFP) → block
- Session quality `BLOCK` (VWAP-flat / dead session) → block
- 7+ signals/día ya logged → block
- 2 trades concurrent → block
- ATR(15m) en top 5% del histórico → drop asset (Apéndice B)
- Score < 60 → DROP tier
- TP3 < $10 → DROP_BELOW_FLOOR (salvo A-GRADE strong+OK session con TP3_ONLY)

## Limitaciones MVP

- **On-chain bias** (BTC/ETH only): no wired. Componente skip → weight redistribute.
- **Pump detector alignment**: no wired. Componente skip.
- **Smart money L/S**: no extraído a helper standalone. Componente skip.
- **Fib retracement zone**: no wired (placeholder None). Componente skip.
- **Liq magnet alignment**: no wired (placeholder None). Componente skip.
- **Dynamic universe** (`--dynamic`): no en MVP. Usa universe estático de 10 majors+alts.

Estos se wirearán post-graduación a live, basado en feedback del paper run.

## Referencias

- Spec completo: `/tmp/punk-autohunt-spec.md` (también copiable a `docs/superpowers/specs/2026-05-12-punk-autohunt-design.md`)
- Módulos: `.claude/scripts/autohunt.py`, `autohunt_tp.py`, `autohunt_score.py`
- Paper log: `.claude/profiles/bitunix/memory/autohunt_paper_log.csv`
- Live log: `.claude/profiles/bitunix/memory/autohunt_signals.csv`
