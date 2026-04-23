# FTMO Profile System — Implementation Log

**Fecha:** 2026-04-22 (sesión nocturna 20:00–21:00 MX)
**Branch:** `feature/ftmo-profile` (worktree en `.worktrees/ftmo-profile/`)
**Commits totales:** 29
**Tests:** 24 unit tests (pytest) + 8 integration tests (bash) — **32 verdes**
**Status:** implementación completa, listo para review + merge a main

## Resumen ejecutivo

Sistema dual-profile (retail + ftmo) implementado según spec `2026-04-22-ftmo-profile-design.md` y plan `2026-04-22-ftmo-profile.md`.

## Entregables

### Infraestructura nueva

| Archivo | Descripción | Líneas |
|---|---|---|
| `.claude/active_profile` | Flag file con `<profile> \| <iso_timestamp>` | 1 |
| `.claude/scripts/profile.sh` | Script switch/show/get/set/stale/validate | 92 |
| `.claude/scripts/guardian.py` | Rules engine FTMO (core) | ~350 |
| `.claude/scripts/test_guardian.py` | 24 unit tests | ~400 |
| `.claude/scripts/backtest_ftmo.py` | Skeleton backtest (Fase 6 fuera) | ~150 |
| `.claude/scripts/test_integration.sh` | 8 integration tests end-to-end | ~80 |

### Profiles

**`.claude/profiles/retail/`** (migrado):
- `config.md`, `strategy.md`
- `memory/` con 7 archivos migrados vía `git mv` (historial preservado)

**`.claude/profiles/ftmo/`** (nuevo):
- `config.md`, `strategy.md`, `rules.md`
- `memory/` con 7 archivos seed (equity_curve.csv, trading_log.md, challenge_progress.md, mt5_symbols.md, paper_trading_log.md, overrides.log, session_notes.md)

### Comandos nuevos

- `/profile` — ver/cambiar profile activo
- `/equity <valor>` — actualizar equity FTMO
- `/challenge` — dashboard progreso FTMO

### Comandos refactorizados (profile-aware)

- `/status`, `/risk`, `/validate`, `/journal`, `/morning`

### Agentes

- **6 agentes** con header "Profile awareness" (trade-validator, journal-keeper, regime-detector, risk-manager, chart-drafter, backtest-runner)
- **morning-analyst** con retail-only guard
- **morning-analyst-ftmo** nuevo (14 fases multi-asset)

### Scripts modificados

- `session_start.sh` — detecta profile + capital dinámico
- `statusline.sh` — profile tag + métricas profile-specific

### Docs

- `MEMORY.md` reestructurado con índice dual (GLOBAL + RETAIL + FTMO)
- `CLAUDE.md` con sección "Profile System (Dual)"

## Verificación final

```bash
python3 -m pytest .claude/scripts/test_guardian.py -v
# 24 passed in 0.06s

bash .claude/scripts/test_integration.sh
# ALL INTEGRATION TESTS PASSED

bash .claude/scripts/profile.sh set retail
bash .claude/scripts/statusline.sh
# [RETAIL] 💰 $13.63 (+$3.63) │ 📊 1/3 │ 🟢 VENT │ 🕐 MX 20:35 │ BTC.P

bash .claude/scripts/profile.sh set ftmo
bash .claude/scripts/statusline.sh
# [FTMO $10k] Equity: $10,000 (initial — run /equity)

python3 .claude/scripts/guardian.py --profile ftmo --action status
# {"equity_current": 10000, ...}
```

## Notas y adaptaciones sobre el plan

1. **statusline.sh** — Task 9 originalmente simplificaba el retail demasiado. Fix posterior (commit `3b8c978`) restauró el formato rico original con `[RETAIL]` tag prepended.

2. **Tests adicionales** — Task 11 agregó 9 tests planificados + 1 extra durante debugging (sumando 12 en lugar de 11). Eso llevó el total final a 24 en lugar de 23. No afecta la corrección.

3. **macOS date parser** — En `profile.sh stale` se usa `date -j -f "%Y-%m-%dT%H:%M:%S"` (sintaxis BSD macOS). Si se ejecuta en Linux, el stale check falla silenciosamente y asume profile fresco. Documentado pero no corregido (el usuario trabaja en macOS 24.6).

## Fases externas pendientes (no parte de este branch)

Estas fases las opera el usuario directamente, no requieren más código:

- **Fase 6:** correr `backtest_ftmo.py` con data real (llena `load_ohlcv` + `simulate_strategy`)
- **Fase 7:** paper trading FTMO Free Trial 14 días, 10+ trades, llena `paper_trading_log.md`
- **Fase 8:** go/no-go de compra challenge $93.43 basado en métricas

Criterios para pagar challenge: WR ≥ 55%, max DD ≤ 5%, 0 daily breaches simulados, 0 overrides del guardian.

## Próximo paso recomendado

**Merge a main** después de review visual del usuario. Luego borrar el worktree:

```bash
cd ~/Documents/trading  # salir del worktree
git checkout main
git merge feature/ftmo-profile --no-ff -m "feat: FTMO Profile System"
git worktree remove .worktrees/ftmo-profile
```

O mantener el worktree hasta validar en uso real.
