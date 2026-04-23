# /profile

Muestra o cambia el profile activo del sistema.

Uso:
- `/profile` — muestra profile activo y timestamp
- `/profile ftmo` — switch a FTMO
- `/profile retail` — switch a retail
- `/profile fotmarkets` — switch a Fotmarkets (bonus $30)
- `/profile status` — resumen rápido de los 3 profiles

Pasos que ejecuta Claude:

1. Si el argumento es vacío:
   - Corre `bash .claude/scripts/profile.sh show`
   - Devuelve el profile actual + timestamp

2. Si el argumento es `status`:
   - Lee `.claude/profiles/retail/config.md` y resume (capital, strategy)
   - Lee `.claude/profiles/ftmo/config.md` y resume (challenge progress)
   - Lee `.claude/profiles/fotmarkets/config.md` y resume (capital, fase)
   - Si FTMO tiene `equity_curve.csv` no vacío, muestra equity + daily PnL
   - Si FOTMARKETS tiene `phase_progress.md` poblado, muestra capital + fase
   - Marca con ▶ el profile activo

3. Si el argumento es `ftmo`, `retail` o `fotmarkets`:
   - **Validación previa**: pregunta "¿tienes trade abierto en el profile actual?" — si sí, BLOCK switch con mensaje "cierra primero"
   - Corre `bash .claude/scripts/profile.sh set <arg>`
   - Confirma con el nuevo statusline
   - Si destino es `ftmo`: prompt "¿actualizar equity FTMO ahora? (último: $X @ <timestamp>)"
   - Si destino es `fotmarkets`: prompt "¿ya leíste bonus T&C? Ver memory/session_notes.md"

4. Si el argumento no es reconocido:
   - Devuelve error: "uso: /profile [ftmo|retail|fotmarkets|status]"

Reglas:
- NUNCA cambiar profile si hay trade abierto (evita cross-contamination)
- Después de switch, recordar al usuario que las memorias del otro profile quedan intactas
