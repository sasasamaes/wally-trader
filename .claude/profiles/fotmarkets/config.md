# Profile: FOTMARKETS (Bonus $30 no-deposit)

**Broker:** Fotmarkets (Mauritius, sin regulación tier-1)
**Plataforma:** MetaTrader 5 (cliente desktop)
**Tipo cuenta:** MT5 Standard
**Leverage:** 1:500 (forzado por bonus T&C)
**Capital inicial:** $30 USD (bonus no-deposit, no depositado)
**Moneda:** USD

## Constantes (YAML, consumidas por scripts + comandos)

```yaml
profile: fotmarkets
broker: fotmarkets
regulated: false
account_type: MT5_Standard
leverage: 500
initial_capital: 30.00
currency: USD
min_lot_broker: 0.01

# Assets operables (universo completo, filtrado por fase)
assets_universe:
  - EURUSD
  - GBPUSD
  - USDJPY
  - XAUUSD
  - NAS100
  - SPX500
  - BTCUSD
  - ETHUSD

# Ventana operativa
session_window_mx:
  start: "07:00"
  end: "11:00"
force_exit_mx: "10:55"
no_overnight: true
no_weekend: true

# Fases de escalation (ver rules.md para detalle)
phase_1:
  capital_min: 0
  capital_max: 100
  # 2026-04-30: RECALIBRADO desde 10% → 1% (backtest demostró DD 70% a 10% risk)
  risk_per_trade_pct: 1
  risk_per_trade_usd_cap: 0.30  # $0.30 sobre $30 (1%)
  max_trades_per_day: 1
  max_sl_consecutive: 1
  tp_r_multiple: 2.0
  # 2026-04-30: GBPUSD removido — backtest PF 0.94 / DD 18% incluso a 1% risk
  allowed_assets: [EURUSD]

phase_2:
  capital_min: 100
  capital_max: 300
  # 2026-04-30: RECALIBRADO 5% → 2%
  risk_per_trade_pct: 2
  max_trades_per_day: 2
  max_sl_consecutive: 2
  tp_r_multiple: 2.0
  break_even_trigger_r: 1.0
  # 2026-04-30: GBPUSD desbloqueado solo si backtest fase 2 lo valide
  allowed_assets: [EURUSD, USDJPY, XAUUSD, NAS100]

phase_3:
  capital_min: 300
  capital_max: 999999
  risk_per_trade_pct: 2
  max_trades_per_day: 3
  max_sl_consecutive: 2
  tp_r_multiple: 2.5
  allowed_assets: [ALL]  # todos los del universo

# Strategy config global (todas las fases)
strategy:
  timeframe_primary: "5m"
  timeframe_confirmation: "15m"
  timeframe_context: "1H"
  stop_loss_atr_length: 14
  stop_loss_atr_mult: 1.2
  min_sl_pips:
    EURUSD: 8
    GBPUSD: 10
    USDJPY: 10
    XAUUSD: 20      # 20 pips = $2 en gold con 0.01 lot
    NAS100: 25      # 25 points
    SPX500: 4       # 4 points
    BTCUSD: 50      # 50 pips (CFD spread alto)
    ETHUSD: 40
```

## Estrategia activa

Ver `strategy.md` en este directorio — **Fotmarkets-Micro** (scalping reversal post-pullback).

## Memorias específicas

Ver archivos en `./memory/`:
- `trading_log.md` — journal de trades
- `phase_progress.md` — capital actual + fase vigente
- `session_notes.md` — notas operativas (spread anómalos, MT5 quirks, bonus T&C)

## Filosofía

Profile operativo REAL pero con capital de "casa de juego" ($30 bonus no depositado).
Disciplina estricta: reglas más tight que retail/ftmo por el capital micro.
NO depositar dinero propio en este broker bajo ninguna circunstancia.
