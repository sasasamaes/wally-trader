---
description: Valida un setup de entrada ANTES de ejecutar el trade
allowed-tools: Agent
---

Valida un setup de entrada ANTES de ejecutar el trade.

Pasos que ejecuta Claude:

1. Lee profile: `PROFILE=$(bash .claude/scripts/profile.sh get)`

2. SI profile == "retail":
   - Despacha agente `trade-validator`
   - Verifica los 4 filtros técnicos del config retail (Donchian + RSI + BB + close color)
   - Además 5° filtro ML opcional (vía /ml si el setup es 4/4)
   - Veredicto: GO / NO-GO tradicional

3. SI profile == "ftmo":
   - Despacha agente `trade-validator` con instrucción "usar filtros de FTMO-Conservative"
   - Verifica los 7 filtros (ver `profiles/ftmo/strategy.md` sección 5.4)
   - Si todos los 7 OK:
     - Invoca guardian:
       ```
       python3 .claude/scripts/guardian.py --profile ftmo --action check-entry \
         --asset <ASSET> --entry <ENTRY> --sl <SL> --loss-if-sl <USD_LOSS>
       ```
     - Procesa veredicto:
       - OK → "GO absoluto"
       - OK_WITH_WARN → muestra warnings en rojo, pide confirmación explícita del usuario
       - BLOCK_SIZE → "size reducir a X% del propuesto, luego confirmar"
       - BLOCK_HARD → "NO-GO. Razón: <reason>. Opción override: escribir literalmente 'OVERRIDE GUARDIAN'"

4. Formato de output estándar:

```
TÉCNICO: N/N filtros ✓
GUARDIAN: <VEREDICTO> — <razón>

Setup:
  Asset:  <X>
  Entry:  <P>
  SL:     <P> (dist <D%>)
  TP1:    <P> (R:R 1.5)
  TP2:    <P> (R:R 3.0)
  Size:   <lots/BTC> (risk $<X>)

Acción: <GO | CONFIRM | NO-GO>
```

5. Si usuario escribe "OVERRIDE GUARDIAN":
   - Append a `.claude/profiles/ftmo/memory/overrides.log`:
     `<timestamp>|ftmo|<rule_violated>|<equity>|<trade_json>|<user_reason>`
   - Procede con "GO" pero con warning grande

6. **[FTMO ONLY] Si veredicto final GO (7/7 filtros + guardian OK/OK_WITH_WARN):**
   
   Pregunta al usuario:
   ```
   ¿Ejecutar orden ahora?
   
   Responde:
   - YES → encolar al EA (o manual si offline)
   - AJUSTAR <size|sl|tp> <valor> → modificar param y re-validar
   - NO → solo guardar setup en memoria, no ejecutar
   ```
   
   a. Si responde **YES**:
      - Invoca flujo de `/order` con los parámetros del setup validado (7/7 + guardian OK)
      - Pasa directamente a la confirmación YES de `/order` (usuario ya aprobó en /validate)
      - Usa mismo `guardian_verdict` y `filters_passed=7`
      - Output: muestra tabla ASCII de orden encolada (mismo formato que `/order`)
   
   b. Si responde **AJUSTAR X Y**:
      - Actualiza param (size, sl, o tp)
      - Re-valida guardian con nuevo param
      - Re-pide confirmación (vuelve a paso 6)
   
   c. Si responde **NO** o nada:
      - Display: "Setup guardado en memoria. Usa `/order` después para ejecutar."
      - NO escribe a pending_orders.json ni mt5_commands.json

Contexto adicional (opcional):
$ARGUMENTS
