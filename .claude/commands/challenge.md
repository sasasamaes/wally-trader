Dashboard de progreso del challenge FTMO.

Uso:
- `/challenge` — muestra estado completo del challenge

Pasos que ejecuta Claude:

1. Lee profile activo. Si != "ftmo":
   - Mensaje: "/challenge solo aplica al profile FTMO. Profile activo: <X>."
   - NO ejecutar

2. Lee `.claude/profiles/ftmo/config.md` y `.claude/profiles/ftmo/memory/challenge_progress.md`

3. Invoca: `python3 .claude/scripts/guardian.py --profile ftmo --action status`

4. Formatea el output:

```
╔══════════════════════════════════════════════╗
║  FTMO CHALLENGE DASHBOARD                     ║
║  Tipo: 1-Step $10,000                         ║
║  Status: <ACTIVE | PREPARING | BREACHED>       ║
╠══════════════════════════════════════════════╣
║  PROFIT TARGET 10% ($1,000)                   ║
║  Acumulado: $X ($P%)                          ║
║  Faltan:    $Y                                ║
║                                               ║
║  EQUITY                                       ║
║  Actual: $X (YY% desde inicio)                ║
║  Peak:   $X                                   ║
║                                               ║
║  REGLAS                                       ║
║  □ Daily 3%:     Used $X (Y% / 3% hoy)        ║
║  □ Trailing 10%: Used $X (Y% / 10% from peak) ║
║  □ Best Day 50%: Ratio Y% (cap 50%)           ║
║  □ Max trades/día: N/2 usados hoy             ║
║                                               ║
║  MÉTRICAS ROLLING                             ║
║  Días activos: N                              ║
║  WR: Y%                                       ║
║  Avg R: Y                                     ║
║  Profit factor: Y                             ║
║                                               ║
║  OVERRIDES GUARDIAN: N (review needed si >0)  ║
╚══════════════════════════════════════════════╝
```

5. Alertas si aplica:
   - Si profit_pct >= 10.0 → "🎯 CHALLENGE PASSED — Contacta FTMO para verificación"
   - Si cualquier regla BREACHED → "🚫 CHALLENGE BREACHED — <regla>. Cuenta nueva requerida."
   - Si overrides > 0 → "📋 Revisa overrides.log al /journal"
