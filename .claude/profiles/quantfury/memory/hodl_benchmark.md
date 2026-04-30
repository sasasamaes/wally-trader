# Quantfury — HODL benchmark tracker

> Compara tu performance trading vs simplemente HODLing 0.01 BTC.

## Concepto clave

Si tu BTC stack inicial es 0.01 BTC y solo hubieras HODLeado:
- Tu BTC stack final: 0.01 BTC (sin cambio en BTC)
- Tu USD value: depende del precio BTC

Si has tradeado activamente:
- Tu BTC stack final: X BTC
- Outperformance = (X - 0.01) / 0.01 × 100

**Si outperformance es positivo:** ganaste sats con tu trading.
**Si outperformance es negativo:** HODL hubiera sido mejor.

## Tracking semanal

```
| Semana | BTC stack inicio | BTC stack fin | BTC PnL % | USD inicio | USD fin | HODL USD % | Outperformance |
|---|---|---|---|---|---|---|---|
| W1 | 0.01000 | ? | ? | $750 | ? | ? | ? |
| W2 | ? | ? | ? | ? | ? | ? | ? |
```

## Tracking mensual (decisión clave)

```
| Mes | BTC stack inicio | BTC stack fin | Outperform vs HODL | Decisión |
|---|---|---|---|---|
| M1 | 0.01000 | ? | ? | continuar / conservador / pausar |
| M2 | ? | ? | ? | ? |
| M3 | ? | ? | ? | ? |
```

## Reglas de decisión

- **Outperformance >+5% mensual** → continuar normal
- **Outperformance 0% a +5%** → continuar, evaluar a 60d
- **Outperformance -2% a 0%** → modo conservador (risk 1% en vez de 2%)
- **Outperformance <-2%** → **PAUSAR PROFILE** 30 días, pasar a HODL only, review

## Helper

```bash
bash .claude/scripts/btc_outperform.py --period 30d
# Output:
# - BTC stack actual vs inicial
# - HODL benchmark del período
# - Outperformance %
# - Recomendación según las reglas
```

## Filosofía operativa

> "Si HODL hubiera ganado +20% USD y tú con tu trading ganaste +15% USD, en BTC perdiste el 5% de stack. **No es éxito, es subóptimo.**"

> "El bull market es trampa para traders BTC-stackers — cualquier long captura solo el spot move, mientras los SLs te quitan stack neto."
