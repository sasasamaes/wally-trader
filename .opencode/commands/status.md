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

4. SI profile == "fotmarkets":
   - Lee `.claude/profiles/fotmarkets/memory/phase_progress.md` (capital + fase)
   - Lee `.claude/profiles/fotmarkets/memory/trading_log.md` (trades hoy)
   - Invoca: `bash .claude/scripts/fotmarkets_phase.sh detail`
   - Invoca: `bash .claude/scripts/fotmarkets_guard.sh check` (captura PASS/BLOCK)
   - Muestra statusline fotmarkets expandido:
     ```
     [FOTMARKETS $30.00]
     Fase: 1 (rango [0, 100))
     Próximo threshold: $100 (desbloquea USDJPY, XAUUSD, NAS100)
     Risk por trade: 10% ($3.00)
     Max trades hoy: 1
     Estrategia: Fotmarkets-Micro
     Ventana MX: 07:00–11:00
     Guardian: PASS/BLOCK <razón>
     Trades hoy: 0/1
     Último trade: <fecha> <resultado>
     ```

5. SI profile no reconocido:
   - Muestra warning: "Profile desconocido: <X>. Corre /profile ftmo|retail|fotmarkets."

6. Al final de cualquier output, incluye: "Última actualización: <timestamp>. Cambiar profile: /profile ftmo|retail|fotmarkets"
