# Trading Log — Fotmarkets

Journal de trades ejecutados en el profile Fotmarkets.
Escrito automáticamente por `/journal`.

## Formato de tabla

| Fecha | Hora CR | Asset | Dir | Lots | Entry | SL | TP | Resultado | PnL $ | R | Fase | Notas |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Trades

| Fecha | Hora CR | Asset | Dir | Lots | Entry | SL | TP | Resultado | PnL $ | R | Fase | Notas |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-04-23 | ~09:24 | EURUSD | LONG (Buy Limit) | 0.03 | 1.17000 | 1.16900 | 1.17220 | SL | -2.91 | -0.97R | 1 | 1er trade fotmarkets; entry via Buy Limit llenado en pullback; precio hit SL 1.16900 antes de tocar zona de trigger 1.17020 con confirmación técnica |
| 2026-04-27 | ~09:14 | EURUSD | LONG (Market) | 0.03 | 1.17367 | 1.17287 | 1.17580 | OPEN | — | — | 1 | 2do trade fotmarkets; entrado contra NO-TRADE veredicto matutino (3.5/4 filtros, vela 5m roja en formación). Entró debajo de zona óptima 1.17400-1.17420. Sin SL inicial → corregido post-entry a 1.17287 (8 pips, $2.40 risk, 2.66R). Bias técnico LONG: EMA50(15m)>EMA200(15m), DXY -0.51%. Cierre manual si vela 5m <1.17320 (invalidación bias). Equidad inicial $33.84 (Balance $5.07 + Crédito $30, indica deposit propio ~$8 contra filosofía profile). |

## Lecciones 2026-04-23 (trade #1 EURUSD SL)

### ✅ Qué hice bien
- **Sizing disciplinado:** 0.03 lotes (cap fase 1), tras corregir el 0.11 inicial que hubiera sido $11 risk (36% cuenta)
- **SL respetado:** no movido en contra
- **Stop día aceptado:** no revenge trade tras el SL
- **Journal honesto:** reporté lotaje real y loss exacto

### ⚠️ Qué aprendí
- **Buy Limit en zona sin confirmación 5m:** el plan original era esperar vela 5m verde + RSI>40 + toque BB lower. El Buy Limit se llenó automáticamente al pullback sin que hubiera confirmación del filtro #4 (vela reversal). Filtro 6 del checklist pre-entry (vela reversal confirmatoria) estaba pendiente cuando la orden se llenó.
- **Lección:** para Fotmarkets-Micro, **ejecución Market manual** tras confirmar vela 5m es superior a Buy Limit, porque el Limit no espera confirmación.
- **Pip count:** SL teórico 10 pips = $3.00 risk. Pérdida real $2.91 (9.7 pips) — spread ~0.3 pips consumido. Aceptable para EURUSD pero confirma que el SL estuvo tight al spread.

### 🧠 Estado emocional
- Post-SL: stop día aceptado sin pelea
- Psicología: A-grade (sizing respetado, no mover SL, no revenge)
- Trade #1 fotmarkets = learning trade; el capital educativo vale más que los $2.91.
