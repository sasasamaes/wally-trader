# FundingPips Zero — Notas de sesión

## Account state (al 2026-04-30)

- **Status:** PENDING — cuenta no comprada aún
- **Plan declarado:** comprar cuenta Zero $10k ($99 con código HELLO -20% = $79.20)
- **Plataforma:** MT5 (FundingPips-Live server)
- **Universo:** multi-asset (forex/indices/crypto/oro)

## Plan declarado del usuario

1. Comprar cuenta FundingPips Zero $10k → operar conservador 7 días min
2. Bi-weekly payout (95%) → transferir a retail (Binance) para fondear cuenta real
3. Eventualmente comprar otra cuenta FTMO $100k

## Pre-activación checklist

- [ ] Comprar cuenta en https://fundingpips.com con código HELLO
- [ ] Recibir credenciales MT5 por email
- [ ] Login MT5 con credenciales reales (server: FundingPips-Live)
- [ ] Verificar conexión + symbol availability
- [ ] Llenar `.claude/.env`:
      - `FUNDINGPIPS_LOGIN=<...>`
      - `FUNDINGPIPS_PASSWORD=<...>`
      - `FUNDINGPIPS_READONLY_PASSWORD=<...>`
      - `FUNDINGPIPS_SERVER=FundingPips-Live`
- [ ] Adaptar EA `ClaudeBridge.mq5` (mismo binary, distinto magic number — usar 88888 para fundingpips, 77777 para ftmo)
- [ ] Test inicial con 0.01 lots en BTCUSD o EURUSD para validar conexión

## Reglas oficiales a verificar al comprar

1. ¿Daily loss vs balance inicio del día (00:00 UTC) o vs equity peak?
2. ¿Total DD vs balance inicial fijo $10k o trailing equity high?
3. ¿Consistency formula exacta: `biggest_day / total_profit` o `biggest_day / sum_of_winning_days`?
4. ¿Weekend hold permitido?
5. ¿Hedging permitido?
6. ¿EAs/algos permitidos? (importante para nuestro EA bridge)
7. ¿News trading restrictions específicas?
8. ¿Add-on Swap Free es worth it ($10 más)? Solo si haces hold overnight crypto.

## Diferencias clave vs FTMO existente

| Concepto | FTMO actual | FundingPips Zero |
|---|---|---|
| Modelo | 1-Step challenge demo | Direct funded (zero eval) |
| Cuenta | $10k virtual demo | $10k real-money funded |
| Max total DD | 10% trailing | 5% from initial fixed |
| Consistency | 50% best-day | 15% biggest-day-vs-total |
| Leverage | 1:100 | 1:50 |
| Costo | $93.43 (challenge fee) | $99 (cuenta fee, NO challenge) |
| Payout | Variable post-challenge | Bi-weekly 95% |

## Filosofía operativa específica

> "There's no room for error. The daily drawdown and max drawdown limits are tighter, compared to evaluation accounts." — FundingPips oficial

Por eso:
- Risk 0.3% (vs FTMO 0.5%)
- Max 2 trades/día
- TP fijo (NO trailing — incompatible con consistency 15%)
- Target diario 0.5-0.7% (no 1.5% como FTMO)
- "El edge no es ganar — es no perder."
