# Phase Progress — Fotmarkets

Fuente de verdad del capital y fase activa del profile `fotmarkets`.
Actualizado por `/journal` al cierre de cada día.

## Estado actual

```yaml
capital_current: 33.84  # Equidad MT5 al momento de entry (Balance 5.07 + Crédito 30 + Floating -1.23)
capital_previous: 27.09
phase: 1
phase_since: "2026-04-23"
trades_total: 2
trades_wins: 0
trades_losses: 1
trades_open: 1
pnl_total_usd: -2.91  # cerrado; floating live no contado hasta cierre
last_updated: "2026-04-27T15:14:00Z"
sls_today: 0
sls_today_cap: 1
trades_today: 1
trades_today_cap: 1
day_locked: false  # cartucho gastado; locked si SL llega
open_position:
  asset: EURUSD
  side: LONG
  lots: 0.03
  entry: 1.17367
  sl: 1.17287
  tp: 1.17580
  risk_usd: 2.40
  risk_r: 1.0
  rr_target: 2.66
  invalidation_5m_close_below: 1.17320
  opened_at: "2026-04-27T15:14:00Z"
```

## Nota deposit propio (2026-04-27)

Equidad MT5 mañana del 2do trade: $33.84 (Balance $5.07 + Crédito $30 + Floating -$1.23).
El crédito-bonus está intacto en $30 → significa que las pérdidas se restaron del Balance,
no del Crédito. Eso solo es posible si hubo deposit propio adicional al bonus inicial.
Estimación: ~$8 USD depositados en algún momento entre 2026-04-23 y 2026-04-27.

Esto **contradice la filosofía del profile** documentada en `config.md`:
> "NO depositar dinero propio en este broker bajo ninguna circunstancia."

Acción requerida (no hoy, post-trade): preguntar al usuario si fue intencional y revisar
si conviene retirar el balance propio cuando se desbloquee (T&C bonus pueden bloquear retiros
hasta cumplir requisitos de volumen).

## Historial de migraciones

| Fecha | Capital | Fase | Evento |
|---|---|---|---|
| 2026-04-23 | $30.00 | 1 | Profile creado, bonus inicial |
| 2026-04-23 | $27.09 | 1 | Trade #1 EURUSD LONG SL (-$2.91, -0.97R). 1/1 trade y 1/1 SL fase 1. STOP día. Sizing 0.03 respetado ✅. |

## Thresholds recordatorio

- Fase 1 → 2: capital ≥ $100 (assets desbloqueados: USDJPY, XAUUSD, NAS100)
- Fase 2 → 3: capital ≥ $300 (assets desbloqueados: SPX500, BTCUSD, ETHUSD)
