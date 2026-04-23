---
description: Cierra el día y actualiza el log del profile activo
allowed-tools: Agent
---

Cierra el día y actualiza el log del profile activo.

Pasos que ejecuta Claude:

1. Lee profile: `PROFILE=$(bash .claude/scripts/profile.sh get)`

2. Despacha `journal-keeper` agent con el profile explícito.

3. Agent escribe al log correspondiente:
   - retail → `.claude/profiles/retail/memory/trading_log.md`
   - ftmo   → `.claude/profiles/ftmo/memory/trading_log.md` + actualiza `challenge_progress.md`

4. SI profile == "ftmo":
   
   **E. Auto-ingest trades MT5 cerrados hoy:**
   - Lee `.claude/profiles/ftmo/memory/mt5_state.json` (via python3 scripts/mt5_bridge.py si symlink falla)
   - Busca array `closed_today` (si existe) o `positions` cerradas con `close_time` = hoy
   - Para cada trade con magic=77777 (filtra trades de ClaudeBridge EA):
     - Parsea: ticket, symbol, type (BUY/SELL), volume, open_price, close_price, profit_usd, close_reason
     - Append row a `.claude/profiles/ftmo/memory/trading_log.md`:
       ```
       | 2026-04-22 14:32 | BTCUSD | LONG | 0.05 | 77542→77482 | -$50.00 | sl | #cmd_20260422_143015_01 |
       ```
     - Si equity cambió respecto a state previo (`state.account.equity_prev` vs `equity`):
       - Ejecuta: `python3 scripts/guardian.py --profile ftmo --action equity-update --value <new_equity>`
       - Guarda nuevo equity en state para próxima comparación
   
   **F. Marca pending expired:**
   - Lee `.claude/profiles/ftmo/memory/pending_orders.json`
   - Para cada pending order con `status != "filled"`:
     - Si `proposed_at` + `expiry_minutes` < now → status = "expired"
   - Save pending_orders.json
   
   **G. Summary output:**
   - "Trades del día: X filled + Y expired"
   - "PnL neto: +$X.XX" (suma de profits en trading_log del día)
   - "Overrides guardian hoy: Z" (si overrides.log tiene eventos de hoy, lista las razones)
   - "Próximo reset FTMO: 00:00 UTC"
   - Muestra al usuario:
     - Trades del día con resultado
     - PnL neto
     - Status rules post-cierre
     - "Brechas cerca: none / <rule>"
     - Próximo paso: "/profile retail para mañana" o "continuar FTMO"

5. SI profile == "retail":
   - Comportamiento actual (3 wins log pattern).
   - journal-keeper append a `.claude/profiles/retail/memory/trading_log.md`.

6. Auto-commit al final:
   `git add <archivos profile> && git commit -m "journal: auto-save sesión <profile> <YYYY-MM-DD>"`

Input (opcional):
$ARGUMENTS
