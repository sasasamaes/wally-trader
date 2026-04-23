Actualiza el equity actual del profile FTMO (no aplica a retail).

Uso:
- `/equity <valor>` — registra nuevo equity en USD
- `/equity <valor> "<nota>"` — con nota descriptiva opcional
- `/equity` (sin arg) — muestra último equity conocido

Pasos que ejecuta Claude:

1. Lee profile activo: `bash .claude/scripts/profile.sh get`

2. Si profile != "ftmo":
   - Mensaje: "/equity solo aplica al profile FTMO. Profile activo: <X>. Usa /profile ftmo para switchear."
   - NO ejecutar

3. Si sin argumentos:
   - Lee última línea de `.claude/profiles/ftmo/memory/equity_curve.csv`
   - Muestra: "Último equity: $X @ YYYY-MM-DDThh:mm (source, nota)"
   - Si curve vacío: "Sin actualizaciones. Initial: $10,000"

4. Si hay argumento numérico:
   - Valida que es número positivo razonable (entre 1000 y 50000)
   - Ejecuta: `python3 .claude/scripts/guardian.py --profile ftmo --action equity-update --value <valor> [--note "<nota>"]`
   - Devuelve: JSON del update + recalcula status
   - Ejecuta: `python3 .claude/scripts/guardian.py --profile ftmo --action status` y muestra formateado:
     - Equity actual: $X (+N.NN%)
     - Daily PnL: $X (N.NN% / 3% limit)
     - Trailing DD: $X (N.NN% / 10% limit)
     - Best Day ratio: N% (cap 50%)

5. Si el valor sube contra peak anterior → nota visual: "🎯 Nuevo peak!"

6. Si el valor cruza algún threshold peligroso → aviso en rojo:
   - daily_pnl_pct <= -2.5% → "⚠️ 2.5% daily loss, cerca del 3% limit"
   - trailing_dd_pct >= 8.0% → "⚠️ Trailing DD 80% del límite"
   - best_day_ratio >= 0.45 → "ℹ️ Best day cerca del cap 50%"
