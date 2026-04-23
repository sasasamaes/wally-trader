# Memory Index — Trading Project (Dual Profile)

## GLOBAL (ambos profiles leen)
- [User profile](user_profile.md) — Trader retail México, dual-profile FTMO + retail, capital $13.63 real + $10k FTMO demo
- [Operating window](operating_window.md) — Retail MX 06:00–23:59, FTMO 06:00–16:00
- [Communication prefs](communication_prefs.md) — Español, directo, honest-first, disclaimers
- [User goals vs reality](user_goals_reality.md) — WR realistico, expectativas calibradas
- [Morning protocol](morning_protocol.md) — Protocolo base, variantes en cada profile
- [Market context APIs](market_context_refs.md) — F&G, funding, on-chain endpoints
- [ML System](ml_system.md) — Sentiment + XGBoost (usable en ambos profiles)
- [External signals tracker](external_signals_tracker.md) — Registro de señales de comunidades

## RETAIL profile (`.claude/profiles/retail/`)
- [Config retail](../profiles/retail/config.md) — Capital $13.63, BingX, 10x leverage, BTCUSDT.P
- [Strategy retail](../profiles/retail/strategy.md) — Mean Reversion 15m
- [Trading log retail](../profiles/retail/memory/trading_log.md) — 3 wins registrados
- [Trading strategy detail](../profiles/retail/memory/trading_strategy.md)
- [Entry rules](../profiles/retail/memory/entry_rules.md) — 4 filtros
- [Backtest findings](../profiles/retail/memory/backtest_findings.md)
- [Market regime retail](../profiles/retail/memory/market_regime.md) — niveles BTC BingX
- [TradingView setup](../profiles/retail/memory/tradingview_setup.md)
- [Liquidations data](../profiles/retail/memory/liquidations_data.md)

## FTMO profile (`.claude/profiles/ftmo/`)
- [Config FTMO](../profiles/ftmo/config.md) — $10k, 1-Step, MT5, leverage 1:100, multi-asset
- [Strategy FTMO](../profiles/ftmo/strategy.md) — FTMO-Conservative (0.5%/trade, 1.5%/día)
- [Rules FTMO](../profiles/ftmo/rules.md) — 3% daily, 10% trailing, Best Day 50%
- [Challenge progress](../profiles/ftmo/memory/challenge_progress.md) — status actual
- [Trading log FTMO](../profiles/ftmo/memory/trading_log.md)
- [Equity curve](../profiles/ftmo/memory/equity_curve.csv)
- [MT5 symbols](../profiles/ftmo/memory/mt5_symbols.md) — pip values
- [Paper trading log](../profiles/ftmo/memory/paper_trading_log.md)
- [Overrides log](../profiles/ftmo/memory/overrides.log)
- [Session notes](../profiles/ftmo/memory/session_notes.md)

## Cómo Claude usa este index
1. Lee `.claude/active_profile` al inicio de cada sesión
2. Siempre carga las memorias GLOBALES
3. Carga las memorias del profile activo únicamente
4. Nunca cruza escrituras entre profiles
