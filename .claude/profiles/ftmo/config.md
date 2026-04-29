# Profile: FTMO (Challenge Demo $10k)

**Challenge type:** 1-Step $10,000 USD
**Coste challenge:** $93.43 (único pago)
**Plataforma:** MetaTrader 5 (MT5)
**Leverage:** 1:100

## Constantes (YAML, consumidas por guardian.py)

```yaml
challenge_type: 1-step
initial_capital: 10000
profit_target_pct: 10           # $1000
max_daily_loss_pct: 3           # $300 diario
max_total_trailing_pct: 10      # $1000 desde peak equity
best_day_cap_pct: 50            # cap 50% del profit total
leverage: 100
risk_per_trade_pct: 0.5         # $50 por trade inicial
max_trades_per_day: 2           # hard cap
max_sl_consecutive: 2           # 2 SL seguidos → STOP día
```

## Assets operables (multi-asset)

Ver `memory/mt5_symbols.md` para símbolos exactos en MT5 y pip values.

| Asset | Sesión óptima CR | Régimen ideal |
|---|---|---|
| BTCUSD | 06:00-10:00 | RANGE |
| ETHUSD | 06:00-10:00 | RANGE/TREND leve |
| EURUSD | 07:00-10:00, 14:00-16:00 | RANGE |
| GBPUSD | 07:00-11:00 | TREND leve |
| NAS100 | 08:30-15:00 | TREND (ADX>25) |
| SPX500 | 08:30-15:00 | TREND/RANGE |

## Ventana operativa

- Inicio: CR 06:00
- Force exit: CR 16:00 (cierre sesión US)
- NO overnight — obligatorio cerrar trades antes de 16:00

## Reglas duras (ver `rules.md` para detalle formal)

1. Daily 3% loss → BLOQUEO DURO del guardian
2. Trailing 10% DD → WARNING fuerte del guardian
3. Best Day 50% → INFO del guardian
4. Max 2 trades/día
5. 2 SLs consecutivos → STOP día
6. Size fijo 0.5% risk per trade

## Estrategia activa

Ver `strategy.md` — **FTMO-Conservative** (diseñada para pasar challenge en 10-30 días).
