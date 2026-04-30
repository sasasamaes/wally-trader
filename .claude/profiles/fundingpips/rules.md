# Reglas FundingPips Zero — niveles BLOCK / WARN / INFO

> Sistema enforcement vía `fundingpips_guard.sh` antes de cada entry.

## 1. MAX DAILY LOSS — 3% del balance del inicio del día

**Cálculo:** `(equity_actual - balance_at_00:00_UTC) / balance_at_00:00_UTC * 100`

| Nivel | Trigger | Acción |
|---|---|---|
| **WARN** | Daily PnL ≤ -1.5% | Mensaje al usuario: "Daily loss 1.5%, no más entries hoy" |
| **BLOCK** | Daily PnL ≤ -2% | Guardian rechaza nuevas órdenes. Force close si hay open. |
| **VIOLATION** (FundingPips) | Daily PnL ≤ -3% | **CUENTA PERDIDA.** $99 perdidos. Empezar de cero. |

**Buffer del sistema:** 1pp antes del límite oficial. Nuestro BLOCK en -2% deja margen para slippage en exit.

## 2. MAX TOTAL DRAWDOWN — 5% del balance INICIAL ($10,000)

**Cálculo:** `(equity_actual - 10000) / 10000 * 100`

NOTA: NO es trailing (a diferencia de FTMO). Es vs balance fijo $10k. Si pasas $11k, tu drawdown se mide vs $10k, no vs $11k. Esto es **más generoso** que FTMO en este aspecto.

| Nivel | Trigger | Acción |
|---|---|---|
| **WARN** | Equity ≤ $9,800 (-2%) | Mensaje "Equity bajo, opera mínimo" |
| **BLOCK** | Equity ≤ $9,700 (-3%) | Guardian rechaza ejecución. Force close. |
| **VIOLATION** | Equity ≤ $9,500 (-5%) | **CUENTA PERDIDA.** |

**Buffer del sistema:** 2pp antes del límite oficial.

## 3. CONSISTENCY RULE — 15% biggest day vs total profit acumulado

**Fórmula:**
```
consistency_pct = (biggest_winning_day_pnl / total_profit_to_date) * 100

Si consistency_pct > 15% → BLOCKEA payout (no PnL, pero tampoco puedes retirar)
```

**Ejemplo violación:**
- Total profit acumulado: $200
- Biggest day: $50
- 50/200 = **25%** → VIOLA regla, NO payout en ese ciclo bi-weekly

**Ejemplo OK:**
- Total profit: $400 (en 7 días)
- Biggest day: $50
- 50/400 = 12.5% → OK, payout aprobado

| Nivel | Trigger | Acción |
|---|---|---|
| **WARN** | Día actual aporta >10% del total | "Cuidado con consistency — considera cerrar trades positivos hoy" |
| **BLOCK** | Día actual aporta >12% del total | Guardian rechaza nuevos longs/profits hoy. Cierra posiciones rentables sin sumar más. |

**Implementación:** `consistency_calc.py` lee trading_log y proyecta cuánto puede el día actual acumular sin violar.

## 4. MIN TRADING DAYS — 7 días

Necesitas **operar al menos 7 días distintos** (cada uno con al menos 1 trade ejecutado) antes de retirar profits.

NO es BLOCK de trading — es BLOCK de payout.

| Nivel | Trigger | Acción |
|---|---|---|
| **INFO** | < 7 días operados | Mensaje "Día N/7, no payout aún" en /journal |
| **OK** | ≥ 7 días | Payout disponible en próximo ciclo bi-weekly |

## 5. LEVERAGE CAP — 1:50

Máximo permitido por FundingPips. Nuestro sistema usa solo **10x effective** para evitar liquidación inesperada por wick (las prop firms tienen "stop-out" en margen).

| Asset | Max leverage broker | Effective leverage objetivo |
|---|---|---|
| Forex majors | 1:50 | 10x |
| Forex crosses | 1:30 | 10x |
| Indices | 1:20 | 5x |
| XAUUSD | 1:30 | 8x |
| Crypto | 1:5 | 2-3x (cap dinámico) |

## 6. PAYOUT — Bi-weekly 95%

Cada 14 días puedes retirar **95% del profit acumulado** (FundingPips se queda 5%).

Requisitos:
- ✅ 7+ días operados
- ✅ Consistency <15%
- ✅ Cuenta no violada (5%/3% rules respetadas)
- ✅ KYC completo

**Filosofía del usuario:** usar payouts para "fondear retail" (transferir a Binance) y eventualmente comprar otra cuenta FTMO $100k.

## Order de checks pre-entry (`fundingpips_guard.sh`)

```
1. ¿Profile == fundingpips? (sino skip checks)
2. ¿Hora dentro de ventana del asset?  → si no → BLOCK
3. ¿Daily PnL > -2%?                    → si no → BLOCK
4. ¿Total equity > $9,700 (>3% DD)?     → si no → BLOCK
5. ¿Consistency: día actual <12% total?  → si no → WARN/BLOCK
6. ¿Trades hoy < 2?                     → si no → BLOCK
7. ¿Risk size <= 0.3% del balance?      → si no → REJECT order
8. ¿Asset en universo allowed?          → si no → BLOCK
9. ¿No hay news high-impact en próx 1h? → si no → BLOCK

→ TODO PASS → APPROVE
→ ALGÚN BLOCK → REJECT con mensaje específico
```

## Si rompes una regla

**5% total DD violation:**
- Cuenta cerrada por FundingPips automáticamente
- $99 perdido (precio cuenta)
- Recompra: 30 días de ban (algunas firmas), verificar T&C
- Lección: el sistema actual MATEMÁTICAMENTE no debería llegar ahí

**3% daily violation:**
- Cuenta cerrada (mismo que arriba)
- Es la causa #1 de fallas en prop firms

**Consistency violation:**
- NO pierdes la cuenta
- Pero NO recibes payout en ese ciclo
- Tu profit queda en la cuenta hasta próximo ciclo (donde se recalcula)

## Disclaimer

Estas reglas son del sistema interno (más estrictas que las oficiales para protección). Las reglas oficiales de FundingPips están en https://fundingpips.com/rules — verifica antes de comprar y antes de cada actualización del programa.
