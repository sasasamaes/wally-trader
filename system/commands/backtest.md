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
- Trade-by-trade log de la mejor
- Hallazgos honestos (incluye limitaciones)

Especifica qué probar:
$ARGUMENTS
