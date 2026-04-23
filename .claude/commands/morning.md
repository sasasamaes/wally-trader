---
description: Análisis matutino completo BTCUSDT.P — protocolo 17 fases
allowed-tools: Agent
---

Invoca el agente `morning-analyst` con el protocolo completo de 17 fases documentado en `MORNING_PROMPT.md`.

El agente ejecutará:
0. **Pre-flight TV** — `tv_health_check`; si está cerrado → `tv_launch` (auto `--remote-debugging-port=9222`), espera 10s, re-verifica. Valida símbolo = BINGX:BTCUSDT.P.
1. Auto-check personal (sueño, comida, estado mental)
2. Contexto global (F&G, funding, on-chain, sentiment)
3. Correlaciones (ETH, SPX, DXY)
4. Noticias / eventos próximas 6h
5. Detección de régimen (4H + 1H)
6. Selección de estrategia
7. Niveles técnicos multi-TF
8. Money flow + patrones
9. Position sizing con capital actual
10. Dibujo en TradingView (limpia + redibuja)
11. Plan de entrada (entry, SL, TP1/2/3)
12. Checklist pre-entry (12+ items)
13. Reglas duras recordatorio
14. VEREDICTO FINAL

Si hay argumentos, úsalos como contexto adicional:
$ARGUMENTS
