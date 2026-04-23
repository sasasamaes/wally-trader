# /profile

Muestra o cambia el profile activo del sistema.

Uso:
- `/profile` — muestra profile activo y timestamp
- `/profile ftmo` — switch a FTMO
- `/profile retail` — switch a retail
- `/profile status` — resumen rápido de ambos profiles

Pasos que ejecuta Claude:

1. Si el argumento es vacío:
   - Corre `bash .claude/scripts/profile.sh show`
   - Devuelve el profile actual + timestamp

2. Si el argumento es `status`:
   - Lee `.claude/profiles/retail/config.md` y resume (capital, strategy)
   - Lee `.claude/profiles/ftmo/config.md` y resume (challenge progress)
   - Si FTMO tiene `equity_curve.csv` no vacío, muestra equity actual + daily PnL
   - Marca con ▶ el profile activo

3. Si el argumento es `ftmo` o `retail`:
   - **Validación previa**: pregunta al usuario "¿tienes trade abierto en el profile actual?" — si sí, BLOCK switch con mensaje "cierra primero"
   - Corre `bash .claude/scripts/profile.sh set <arg>`
   - Confirma con el nuevo statusline

4. Si el argumento no es reconocido:
   - Devuelve error: "uso: /profile [ftmo|retail|status]"

Reglas:
- NUNCA cambiar profile si hay trade abierto (evita cross-contamination)
- Después de switch, recordar al usuario que las memorias del otro profile quedan intactas
- Si el profile destino es FTMO, prompteear al usuario: "¿actualizar equity FTMO ahora? (último: $X @ <timestamp>)"
