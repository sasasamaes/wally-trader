# Spec — `/fot-scout`: Router regime-aware multi-estrategia (fotmarkets)

**Fecha:** 2026-05-31 · **Profile:** fotmarkets · **Objetivo del usuario:** correr el comando
repetidamente para scalpear y crecer la cuenta **$50 → $500**.

## Problema / contexto

El usuario quiere un comando que, cada vez que se corre, escanee los 8 activos del universo
fotmarkets, detecte el régimen por activo, elija **la mejor estrategia para ese momento+activo**,
valide, y entregue el mejor setup (entry/SL/TP + sizing) para ejecución **manual en MT5**.

Dos backtests empíricos (sesión 2026-05-31) fijaron las restricciones honestas:
- **Solo Mean Reversion (gate ADX<20/25) tiene edge que sobrevive el spread ancho del CFD bonus.**
  Breakout/MA-Cross/Pullback/VWAP dieron PF ~0.9–1.07 y mueren al spread.
- **Oro (XAUUSD)** fue el mejor activo (~0.89 setups/día, +0.46R IS, WARN OOS). Sobre $50 el mejor
  caso realista es ~$8.65/mes; $50→$500 son años a risk seguro o blow-up a risk agresivo.

Por eso el comando es un **router que protege**, no un generador de señales: elige la estrategia
del régimen, la gatea por edge validado + cadena de validación, dice **WAIT honesto** cuando no hay
edge, y fuerza disciplina (sizing phase-aware + guardian).

## Decisiones

1. **Multi-estrategia con label honesto.** MR (RANGE_CHOP) es el único edge `VALIDATED` → puede
   llegar a GO. Tendencia (TREND_LEVE→MA-Cross, TREND_FUERTE→Donchian) se capa a `TENTATIVE` con
   `⚠️ edge no validado` + penalidad de score; nunca GO. VOLATILE/EXTREMO → stand aside.
2. **Override permanente en config:** `phase_1.allowed_assets = [EURUSD, XAUUSD, BTCUSD, ETHUSD]`.
3. Log de propuestas en `memory/scout_proposals.md` (no contamina el day-count del guardian).
4. Overlay `VOLATILE` local en el router (no se toca `wally_core/regime.py`).
5. TP fijo **2R** en Fase 1/2, 2.5R en Fase 3 (mirror config).

## Arquitectura (split, precedente `/punk-smart`)

- **`system/commands/fot-scout.md`** (thin): profile guard → `fotmarkets_guard.py check` (BLOCK ⇒
  stop) → corre router `--json` → dispatch a `fot-scout-analyst`. Args: `--asset`, `--show-all`,
  `--experimental-trend`.
- **`.claude/scripts/fot_scout_router.py`** (motor determinista, importable + CLI `--json`, sin MCP):
  data pull (Binance BTC/ETH, yfinance resto) → regime (ADX 1h + overlay VOLATILE ATR 5m) →
  selección de estrategia (`fot_strategy_mapping.json`) → eval setup → score 0-100 → edge-gate →
  sizing phase-aware → rank → status. Reusa `wally_core.{regime,validate,hunt,multifactor}`,
  `per_asset_backtest.{fetch_*,atr,donchian,rsi}`, `macross.detect_cross`.
- **`system/agents/fot-scout-analyst.md`** (live/narrativo): refina el quote del ganador vía TV MCP
  (anti-delay yfinance), corre la cadena `macro_gate → session_quality → volume_divergence →
  min_rr_gate`, arma GO/NO-GO + instrucciones MT5, loggea a `scout_proposals.md`.
- **`.claude/scripts/fot_strategy_mapping.json`**: mapping tunable régimen→estrategia + edge-gates +
  per_asset_edge (oro/BTC/SPX/EUR con expectancy + oos del backtest).

## Edge-gate (contrato de honestidad)

- `edge==VALIDATED` (MR) → `APPROVED` si `score≥global_threshold` (70) y activo unlocked; si
  bloqueado → `OVERRIDE_LOCKED`; si score bajo → `BELOW_THRESHOLD`.
- `edge==WEAK` (trend) → máximo `TENTATIVE` + label, nunca en `approved[]`.
- `edge==NONE` → `STAND_ASIDE`.
- `oos: WARN` per-asset → penalidad −10; `FAIL` → −20.
- Sizing: si lots < 0.01 → `UNTRADEABLE_SIZE` (a $50/1% pasa seguido en FX/oro — honestidad).

## Verificación

- `pytest shared/wally_core/tests/test_fot_scout.py` (17 casos: regime→strategy, MR APPROVED,
  honesty contract, threshold, sizing phase-aware, SL floor, override flag, rank, no-data, remap seam).
- CLI: `.venv/bin/python .claude/scripts/fot_scout_router.py --asset BTCUSD --phase 1 --capital 50 --json`.
- Slash: `/fot-scout`, `/fot-scout --show-all`. Loop: `/loop 30m /fot-scout`.

## Caveats honestos

- yfinance ~15 min delay (FX/índices) → el agente refina el ganador con TV live; si decayó → NO-GO.
- Sizing en lots es APROXIMADO (pip value broker-específico) — validar en MT5 Specification.
- Sobre $50 el revenue es centavos/día; es semilla compuesta, no ingreso. El comando lo dice.
- Backtest base: 60-180d, muestras chicas (16-63 trades/asset), un solo régimen — no concluyente.
