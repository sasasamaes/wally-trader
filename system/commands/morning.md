---
description: Análisis matutino adaptado al profile activo
allowed-tools: Agent
---

Análisis matutino adaptado al profile activo.

Pasos que ejecuta Claude:

1. Lee profile: `PROFILE=$(bash .claude/scripts/profile.sh get)`

2. SI profile == "retail":
   - Despacha `morning-analyst` (BTC-BingX single-asset, 17 fases, ver abajo)
   - El agente usa niveles/memoria de `profiles/retail/memory/`

3. SI profile == "ftmo":
   - Despacha `morning-analyst-ftmo` (multi-asset 14 fases)
   - El agente analiza los 6 assets del universo FTMO
   - Incluye guardian pre-check antes de proponer setups
   - Usa niveles/memoria de `profiles/ftmo/memory/`

4. Si argumento opcional: pasa como contexto adicional al agente (ej: "/morning sin café")

## Fases del morning-analyst retail (17 fases, incluye Pre-flight TV)

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
