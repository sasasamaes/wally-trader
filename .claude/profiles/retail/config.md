# Profile: RETAIL (Binance Real, main account)

**Capital actual:** $18.09 (cuenta Binance UM Account USD)
**Exchange:** Binance Futures (BTCUSDT perpetual)
**Símbolo TV:** `BINANCE:BTCUSDT.P`
**Leverage máximo:** 10x
**Plataforma análisis:** TradingView (plan Basic, 2 indicadores: Neptune Signals + Neptune Oscillator)

## Contexto

Este es el profile retail **main real-money**. Desde 2026-04-23 opera en Binance después de migrar fondos desde BingX ($13.63 → Binance $18.09 via depósito + movimiento residual). El trading_log arranca fresco aquí (el histórico de BingX quedó en profile `retail-bingx`).

## Assets operables

- Único: `BTCUSDT.P` (Binance perpetual)

## Estrategia activa

Ver `strategy.md` en este directorio — **Mean Reversion 15m** (idéntica a `retail-bingx`, régimen RANGE 73.5k–78.3k).

## Ventana operativa

- Inicio: CR 06:00
- Force exit: CR 23:59 (regla "no dormir con posición abierta")
- Cripto 24/7 pero el trader no duerme con trade abierto

## Reglas duras

1. Max 2% riesgo por trade (del capital actual, no del inicial)
2. Max 3 trades/día
3. 2 SLs consecutivos → STOP día
4. Nunca mover SL en contra (solo a BE tras TP1)
5. Nunca leverage >10x
6. 4/4 filtros obligatorios simultáneos

## Operación multi-terminal

```bash
WALLY_PROFILE=retail claude             # terminal dedicada a Binance (este profile)
WALLY_PROFILE=retail-bingx claude       # terminal dedicada a BingX micro
```

**Nunca operar el mismo setup simultáneamente en ambos exchanges** (doble exposición al mismo riesgo direccional). Uno por sesión/día.

## Memorias específicas retail (Binance)

Ver archivos en `./memory/`:
- `trading_log.md` — journal histórico (arranca vacío, primer trade Binance pendiente)
- `trading_strategy.md` — detalle Mean Reversion
- `entry_rules.md` — 4 filtros
- `market_regime.md` — niveles actuales BTC (Binance — casi idénticos a BingX)
- `tradingview_setup.md` — config TV
- `liquidations_data.md` — fuentes datos
- `backtest_findings.md` — aprendizajes de 144 configs
