# Plan — AI Strategy Optimization Bundle (Bundle 6)

**Fecha:** 2026-05-31 · **Spec:** `../specs/2026-05-31-ai-strategy-optimization-bundle-design.md`

Implementa las mejoras del video *"I Let Claude AI Opus 4.8 Trade For Me"* (DaviddTech):
loop de optimización con gates anti-overfit + export Pine + scaffold Trader Dev MCP.
Excluye auto-ejecución live (contra la filosofía del proyecto).

## Estado: ✅ COMPLETO

- [x] `.claude/scripts/optimize_strategy.py` — `optimize()`, `backtest_config()`,
  `compute_metrics()`, `validate_config()` (RST+OOS+MC), `to_pine_strategy()`, `write_pine()`.
  CLI con `--iterations/--minutes/--validate-top/--export-pine`. Exit 0=RECOMMEND / 2=NONE / 3=error.
- [x] `.claude/scripts/tests/test_optimize_strategy.py` — 13 tests (métricas, backtest, loop
  determinista, presupuesto minutes=0, Pine long/short, write_pine).
- [x] `system/commands/optimize.md` — `/optimize`.
- [x] `integrations/trader-dev/README.md` — scaffold ready-to-connect + caveat honesto + tabla
  de solapamiento con el stack nativo.
- [x] Wire-in `system/agents/backtest-runner.md` — nota referenciando `/optimize`.
- [x] Sanity check en `test_pdf_helpers.py` (harness horario).
- [x] Sección "AI Strategy Optimization Bundle" en `CLAUDE.md`.
- [x] Spec + este plan.

## Verificación
- 13/13 tests nuevos green; harness horario verde.
- CLI `/optimize BTCUSDT 4h long --iterations 20 --export-pine` con data real →
  **NONE_SURVIVED** honesto (todas las configs fallan RST+OOS; ninguna se exporta).
- Pine generado: v6 válido (statements top-level sin indentar, `ta.*`, `input.*`).
  No compilado live (TV Desktop apagado) → queda como draft a verificar.

## Excluido / futuro
- Auto-ejecución en exchange (Bybit): fuera de alcance por filosofía de riesgo.
- Trader Dev MCP: sin endpoint público; conectar cuando el usuario obtenga la URL.
- Familias de estrategia adicionales en el search space (hoy solo donchian_ema).
- Compilar el Pine exportado vía MCP cuando TV Desktop esté arriba.
