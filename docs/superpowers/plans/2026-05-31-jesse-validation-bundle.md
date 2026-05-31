# Plan — Jesse Validation Bundle (RST + Monte Carlo + Jesse lab)

**Fecha:** 2026-05-31 · **Spec:** `../specs/2026-05-31-jesse-validation-bundle-design.md`

Implementa las mejoras del video *"Opus 4.8 + Claude Code + MCP = Algo Trading on Autopilot"*
en dos pistas: helpers nativos portables (durable) + Jesse como laboratorio paralelo.

## Estado: ✅ COMPLETO

### Pista 1 — Helpers nativos
- [x] `.claude/scripts/rule_significance.py` — RST permutation test. API: `significance_test`,
  `make_donchian_atr_exit`, `make_fixed_horizon_exit`, `donchian_ema_entries`, `fetch_paginated`.
  CLI `--strategy donchian_ema`. Exit 0=PASS / 2=FAIL|INSUFFICIENT / 3=error.
- [x] `.claude/scripts/monte_carlo.py` — `monte_carlo_trades` (reshuffle/bootstrap) +
  `monte_carlo_candles` (block-bootstrap) + `synthetic_bars` + `default_strategy_sharpe`.
  CLI `--mode trades|candles`. Exit 0=OK / 2=WARN / 3=error.
- [x] `.claude/scripts/tests/test_rule_significance.py` (8 tests)
- [x] `.claude/scripts/tests/test_monte_carlo.py` (12 tests)
- [x] `system/commands/rst.md` (`/rst`)
- [x] `system/commands/montecarlo.md` (`/montecarlo`)
- [x] Wire-in `system/agents/backtest-runner.md` — pasos 5.6 (RST), 5.7 (Monte Carlo),
  5.8 (veredicto combinado) + reglas críticas 8-9 + bloque VALIDACIÓN en el reporte.

### Pista 2 — Jesse lab
- [x] `integrations/jesse/README.md` — setup Docker/pip, caveats, flujo.
- [x] `integrations/jesse/docker-compose.yml` — jesse + postgres + redis.
- [x] `integrations/jesse/.env.example` — puertos/credenciales.
- [x] `integrations/jesse/connect_mcp.md` — `claude mcp add --transport http`.
- [x] `integrations/jesse/import_candles.sh` — import REST.
- [x] `integrations/jesse/strategies/DonchianEMATrend.py` — port del video.
- [x] `integrations/jesse/strategies/_TEMPLATE.py` — esqueleto.

### Docs
- [x] Spec + este plan.
- [x] Sección "Strategy Validation Bundle" en `CLAUDE.md`.

## Verificación
- 20/20 tests nuevos green (`pytest test_rule_significance.py test_monte_carlo.py`).
- CLI RST sobre BTCUSDT 30m → FAIL honesto (BTC sin uptrend limpio → entrada trend no bate azar).
- CLI Monte Carlo trades (WARN dd_p95) y candles (zona FRAGILE) → output coherente.

## Pendiente / futuro (intencional)
- Jesse setup (Docker/Postgres/Redis) lo ejecuta el usuario — no automatizable desde Claude.
- El CLI built-in solo cubre `donchian_ema`; otras estrategias usan la API importable.
- Confirmar imagen/tag de Jesse y URL exacta del MCP contra docs.jesse.trade (bloquean fetch).
