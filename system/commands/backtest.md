---
description: Ejecuta backtest sobre data histórica
allowed-tools: Agent
---

Invoca el agente `backtest-runner` para probar estrategias.

Tipos de tests:
- "quick" → backtest básico de Mean Reversion actual
- "grid" → grid search de parámetros
- "compare" → compara Mean Reversion vs Breakout
- "custom" → especifica tus propios parámetros

Data disponible:
- 5m: 25 horas (1 día)
- 15m: 3.1 días
- 1h: 12.5 días
- 4h: 50 días

Output:
- Top configs ranked por (WR × PF × Retorno - DD)
- **OOS Validation** (split temporal 70/30) — train vs test con verdict PASS/WARN/FAIL
  - PASS → recomendación con confianza moderada
  - WARN → reportar con advertencia (degradación notable)
  - FAIL → declarado como overfit, NO recomendar
- Trade-by-trade log de la mejor
- Hallazgos honestos (incluye limitaciones)

Especifica qué probar:
$ARGUMENTS

## HMM Diagnostic Mode

`/backtest --hmm-analyze SYMBOL STRATEGY [flags...]` is an alias for `/hmm-analyze SYMBOL STRATEGY [flags...]`. See `.claude/commands/hmm-analyze.md` for full documentation.

When Claude sees `--hmm-analyze` in the args, it must invoke `.claude/scripts/hmm_analyze.py` instead of the regular backtest runner.
