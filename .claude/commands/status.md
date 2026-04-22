---
description: Estado actual completo (capital, PnL, régimen, hora, setup)
allowed-tools: Read, Bash, mcp__tradingview__quote_get, mcp__tradingview__data_get_ohlcv
---

Muéstrame el estado actual del sistema de trading:

1. **Capital actual** (lee `~/.claude/projects/<project-path-encoded>/memory/trading_log.md`)
2. **Precio BTC actual** (quote_get)
3. **Régimen del día** (si ya se definió hoy, lee de memoria)
4. **Trades hoy** (count de trading_log)
5. **Hora actual MX** (date +%H:%M) y si estamos en ventana (MX 06:00-23:59)
6. **PnL del día** (si hay trades)
7. **Setup status:** ¿cuántos filtros alineados ahora mismo? (0/4 a 4/4)
8. **Próximo evento** (si hay noticia en <4h, alertar)
9. **Recordatorio de reglas:**
   - Max trades/día: ___
   - SLs hoy: ___
   - Stop sesión: activo/inactivo

Formato compacto en 1 tabla fácil de leer. 30 segundos máximo.
