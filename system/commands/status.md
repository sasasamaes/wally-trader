Muestra el estado completo del sistema según el profile activo.

Pasos que ejecuta Claude:

1. Lee profile activo: `PROFILE=$(bash .claude/scripts/profile.sh get)`

2. SI profile == "retail":
   - Lee `.claude/profiles/retail/config.md` (capital, estrategia activa)
   - Lee `.claude/profiles/retail/memory/trading_log.md` (últimos trades)
   - Lee `.claude/profiles/retail/memory/market_regime.md` (niveles vigentes)
   - Muestra statusline retail expandido:
     ```
     [RETAIL $13.63]
     Estrategia: Mean Reversion 15m
     Régimen: <detecta vía regime-detector rápido o cachea>
     Hora MX: HH:MM
     Trades hoy: 0/3
     Último trade: <fecha> <resultado>
     ```

3. SI profile == "ftmo":
   - Invoca: `python3 .claude/scripts/guardian.py --profile ftmo --action status`
   - Lee `.claude/profiles/ftmo/memory/challenge_progress.md`
   - Muestra statusline FTMO expandido:
     ```
     [FTMO $10k]
     Equity: $X (+Y%)
     Daily PnL: $X (Y% / 3% limit)
     Trailing DD: $X (Y% / 10% limit)
     Best Day ratio: Y% (cap 50%)
     Trades hoy: N/2
     Estrategia: FTMO-Conservative
     Asset vigilancia: <top 1-2 del morning-analyst-ftmo>
     ```

4. SI profile no reconocido:
   - Muestra warning: "Profile desconocido: <X>. Corre /profile ftmo o /profile retail."

5. Al final de cualquier output, incluye una línea: "Última actualización: <timestamp>. Cambiar profile: /profile ftmo|retail"

