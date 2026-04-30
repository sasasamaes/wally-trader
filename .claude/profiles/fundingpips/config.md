# Profile: FUNDINGPIPS (Zero $10k — sin evaluación)

**Capital:** $10,000.00 USD (cuenta fondeada directa, sin challenge previo)
**Costo:** $99 USD ($79 con código HELLO -20%)
**Plataforma:** MT5 (FundingPips-Live server)
**Provider:** [FundingPips](https://fundingpips.com) — modelo "Zero" (no evaluation)
**Leverage:** 1:50 (mucho menor que FTMO 1:100 — NO sobre-apalancar)
**Add-on:** Swap Free disponible (+10% costo si lo activas)

## Filosofía operativa

Cuenta **fondeada con dinero real** desde el día 1. **NO ES DEMO.** Los $99 de compra son reales y se pierden si rompes las reglas (5% max DD total).

> "There's no room for error. The daily drawdown and max drawdown limits are tighter, compared to evaluation accounts." — FundingPips oficial

Por eso la estrategia aquí es **MÁS conservadora** que FTMO-Conservative (que ya lo es). Risk 0.3% per trade, target 0.5-0.7% daily, max 2 trades/día.

## Reglas duras (ver `rules.md`)

| Regla | Valor | Tipo |
|---|---|---|
| Max daily loss | 3% | BLOCK |
| Max total drawdown | 5% (vs balance inicial $10,000) | BLOCK |
| Min trading days | 7 días antes de retirar | INFO |
| Consistency rule | 15% (biggest day vs total profit) | WARN→BLOCK |
| Leverage | 1:50 max | hard cap |
| Payout cycle | Bi-weekly 95% al trader | INFO |

## Assets operables (universo completo MT5 FundingPips)

**Forex majors (London/NY overlap óptimo):**
- EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD

**Forex crosses (mayor volatilidad):**
- EURGBP, EURJPY, GBPJPY

**Indices (NY session only, 14:30-21:00 UTC):**
- NAS100, SPX500, US30 (Dow), GER40 (DAX), UK100 (FTSE), JPN225 (Nikkei)

**Commodities:**
- XAUUSD (oro spot, alta liquidez)
- XAGUSD (plata, menos líquida)
- USOIL / UKOIL (crude — solo si setup excepcional)

**Crypto (24/7, pero liquidez óptima London/NY):**
- BTCUSD, ETHUSD (mayoritariamente)
- XRPUSD, LTCUSD, SOLUSD (si están disponibles, baja prioridad)

**Total: 20+ assets para scan diario.**

## Selección A-grade (filosofía multi-asset)

Cada mañana el `morning-analyst-ftmo` (extendido para fundingpips) recorre los 20+ assets y aplica **filtros sequenciales**:

1. **Sesión válida** — descartar assets fuera de sesión óptima (ej. NAS100 antes de 14:30 UTC)
2. **4 filtros Mean Reversion** — RSI/Donchian/BB/vela color
3. **Multi-Factor score** — pick top scores >+50 (long bias) o <-50 (short bias)
4. **Risk Parity weight** — preferir assets con vol baja (mejor risk-adjusted)
5. **Chainlink cross-check** — para crypto/forex, validar precio agregado vs MT5 broker
6. **VaR sizing** — `/risk-var --target-var-pct 0.5` (aún más estricto que retail 1.5%)

**Solo 1 trade A-grade por día.** Si más de 1 asset califica, pick el de **más alta convicción** (score multi-factor + ML + sentiment).

## Ventana operativa

- **CR 06:00 – 16:00** (London open + NY overlap, evita Asia low-vol)
- **Force exit CR 16:00** (FundingPips no penaliza overnight, pero tu disciplina dice "no dormir con trade abierto")
- **Crypto excepción:** si el setup es BTCUSD/ETHUSD, puedes operar hasta CR 20:00 (NY close)

## Position sizing baseline

Capital $10,000 × 0.3% risk = **$30 max loss per trade**.

Con SL 0.4% del entry:
- Lot size aprox = ($30 / 0.4%) / price → varía por asset
- Helper: `/risk-var --capital 10000 --leverage 50 --target-var-pct 0.5`

Ejemplo BTCUSD @ 75,000 con SL 0.4% (300 USD):
- Notional = $30 / 0.004 = $7,500
- Lots BTC ≈ $7,500 / 75,000 = 0.10 lots BTC

Ejemplo EURUSD @ 1.0850 con SL 30 pips:
- 0.3 lots = ~$3 per pip × 30 = $90 risk → DEMASIADO
- 0.1 lots = $1/pip × 30 = $30 ✅
- **Lots correcto: 0.1**

## Reglas de operación cross-profile

1. **NO operar fundingpips + retail simultáneo en BTC** — doble exposición direccional. Un día por profile.
2. **NO operar fundingpips + ftmo simultáneo en mismo asset** — si vas a operar BTC, elige profile.
3. **NO compartir SL/TP entre cuentas** — cada profile tiene sus propios trades.

## Setup MT5

Reusar 90% del setup FTMO:
- Misma terminal MT5 (puede tener ambas cuentas — switch entre login FTMO-Demo y FundingPips-Live)
- Mismo EA `ClaudeBridge.mq5` ya instalado
- Cambia solo:
  - `FUNDINGPIPS_LOGIN`, `FUNDINGPIPS_PASSWORD`, `FUNDINGPIPS_READONLY_PASSWORD`
  - `FUNDINGPIPS_SERVER` (probablemente `FundingPips-Live`)
- En `.claude/.env` agregar variables análogas a FTMO_*

## Roadmap

1. **Antes de comprar:** dejar el sistema preparado (este profile + memories en estado `pending`)
2. **Al comprar:** activar credenciales en `.env`, login MT5, primer test con 0.01 lots
3. **Primera semana:** 7 días min trading antes de poder retirar. Operar conservador, build equity.
4. **Bi-weekly payout:** después del día 14, retirar 95% del profit.
5. **Plan declarado del usuario:**
   - Usar profits de fundingpips para "fondear retail" (transferir USD a Binance)
   - Eventualmente comprar otra cuenta FTMO de $100k

## Disclaimer

Pierdes $99 si rompes 5% total DD o cualquier regla. NO operar trades de baja convicción. Mejor 0 trades que un trade mediocre. **El edge no es ganar — es no perder.**
