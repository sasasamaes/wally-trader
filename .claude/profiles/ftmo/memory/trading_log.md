# FTMO Trading Log

Registro de cada trade en FTMO demo/real. `journal-keeper` agent lo actualiza al `/journal`.

## Esquema por trade

- **Fecha / Hora MX:** apertura y cierre
- **Asset:** BTCUSD / ETHUSD / EURUSD / etc.
- **Dirección:** LONG / SHORT
- **Entry / SL / TP1 / TP2:** precios exactos
- **Size (lots):** decimal
- **Resultado:** TP1 / TP2 / SL / BE / partial
- **Equity pre / post:** valores
- **PnL $:** neto
- **R múltiplo:** pnl / risk
- **Filtros cumplidos:** 7/7 u otros
- **Guardian veredicto:** OK / WARN / BLOCK_SIZE (con reason)
- **Aprendizaje:** qué aprendí del trade

---

(No hay trades aún. Primer trade se registra al completar Fase 7 paper trading.)
