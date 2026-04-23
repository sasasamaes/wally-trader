---
description: Análisis matutino adaptado al profile activo
allowed-tools: Agent
---

Análisis matutino adaptado al profile activo.

Pasos que ejecuta Claude:

1. Lee profile: `PROFILE=$(bash .claude/scripts/profile.sh get)`

2. SI profile == "retail":
   - Despacha `morning-analyst` (el agente actual, BTC-BingX single-asset, 17 fases)
   - El agente usa niveles/memoria de `profiles/retail/memory/`

3. SI profile == "ftmo":
   - Despacha `morning-analyst-ftmo` (nuevo agente multi-asset)
   - El agente analiza los 6 assets del universo FTMO
   - Incluye guardian pre-check antes de proponer setups
   - Usa niveles/memoria de `profiles/ftmo/memory/`

4. Si argumento opcional: pasa como contexto adicional al agente (ej: "/morning sin café")

Si hay argumentos, úsalos como contexto adicional:
$ARGUMENTS
