# Profile: RETAIL-BINGX (BingX Real, cuenta micro)

**Capital actual:** $0.93 (cuenta residual tras mover fondos a Binance 2026-04-23)
**Exchange:** BingX (BTCUSDT.P perpetual)
**Símbolo TV:** `BINGX:BTCUSDT.P`
**Leverage máximo:** 10x
**Plataforma análisis:** TradingView (Basic, Neptune Signals + Neptune Oscillator)

## Histórico

Este profile hereda el **trading_log original** (3 wins: $10 → $13.63 en 04-20/21/22) con strategy Mean Reversion 15m. El balance actual es residual ($0.93) porque los fondos se migraron a Binance para operar ahí como main retail.

## Assets operables

- Único: `BTCUSDT.P` (BingX perpetual)

## Estrategia activa

Ver `strategy.md` — **Mean Reversion 15m** (idéntica a profile `retail`/Binance).

## Ventana operativa

- Inicio: CR 06:00
- Force exit: CR 23:59 (regla "no dormir con posición abierta")

## Reglas duras

1. Max 2% riesgo por trade (del capital actual, no del inicial)
2. Max 3 trades/día
3. 2 SLs consecutivos → STOP día
4. Nunca mover SL en contra (solo a BE tras TP1)
5. Nunca leverage >10x
6. 4/4 filtros obligatorios simultáneos

## Uso sugerido

Con $0.93 el position sizing es cosmético ($0.019 de riesgo al 2%). **Uso pedagógico**: validar setups/ejecución sin riesgo material. El profile real-money ahora es `retail` (Binance).

## Operación multi-terminal

```bash
WALLY_PROFILE=retail-bingx claude       # terminal dedicada a BingX
WALLY_PROFILE=retail claude             # terminal dedicada a Binance
```

## Memorias específicas

Ver archivos en `./memory/`:
- `trading_log.md` — journal histórico (3 wins BingX preservados)
- `trading_strategy.md` — detalle Mean Reversion
- `entry_rules.md` — 4 filtros
- `market_regime.md` — niveles actuales BTC BingX
- `tradingview_setup.md` — config TV
- `liquidations_data.md` — fuentes datos BingX/Binance
- `backtest_findings.md` — aprendizajes de 144 configs

## Cost Reality (added 2026-05-12)

Capital $0.93 + BingX taker fee 0.05% + leverage 10× makes real execution non-viable:

| Metric | Value |
|---|---|
| Capital | $0.93 |
| Size at 2% risk | $0.0186 margin |
| Notional at 10× | $0.186 |
| Taker fee/side | 0.05% |
| Round-trip cost | $0.0002 (0.02% of capital) |

Cost as % of capital is negligible *in absolute terms*, but:
- **Minimum tick size** on BTCUSDT.P (BingX) is $0.10, larger than the price move that
  $0.0002 fee implies — so any single tick of adverse slippage equals multiple round-trips.
- **Funding** at 0.01% per 8h on $0.186 notional = $0.0000186/cycle — tiny, but on a runner
  held overnight (regulation violation per CLAUDE.md anyway) it stacks.
- **Practical minimum** order size on BingX perp can exceed what a $0.93 account permits at
  10×, forcing oversize or no-fill.

**Operating rule:** `retail-bingx` is a **pedagogical / observation-only** profile. Use it
for replay analysis, signal validation rehearsal, and journal-entry practice — do not
execute real fills. Inherited from the three historical wins ($10 → $13.63) preserved in
`memory/trading_log.md`, the profile retains learning value without continued execution
exposure.
