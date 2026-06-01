# Design — Expansión del universo `/fot-scout` (subset líquido curado)

**Fecha:** 2026-06-01
**Profile:** fotmarkets-only
**Tipo:** refactor + feature (data/config expansion)

## Problema

`/fot-scout` escanea solo 8 activos hardcoded
(`EURUSD/GBPUSD/USDJPY/XAUUSD/NAS100/SPX500/BTCUSD/ETHUSD`). El usuario tiene en su broker
Fotmarkets (MT5) cientos de instrumentos (FX majors+crosses+exóticos, índices globales,
metales spot/base, energías, futuros agrícolas, cripto, acciones US/EU/HK) y quiere que el
scout busque la mejor oportunidad de scalping en un universo más amplio.

**Restricción honest-first:** "no hay estrategia universal". Meter 300+ instrumentos no crea
edge — crea ruido y overfitting. Y muchos no son scalp-friendly en una cuenta bonus B-book
(exóticos = spread enorme; futuros agrícolas = ilíquidos; acciones = horario cash, comisión,
gaps). Por eso se expande a un **subset líquido curado**, no al universo completo.

## Decisiones de alcance (confirmadas con el usuario)

1. **Subset líquido curado** (~23 instrumentos), no el universo completo.
2. **Todos desbloqueados en Fase 1**; el risk sigue escalando por fase (1%→2%→2%).
3. Instrumentos sin backtest per-asset → caveat honesto, no bloqueo.

## Universo curado (23 instrumentos)

Cada uno con feed OHLCV verificable (yfinance o Binance). `mt5_symbol` = lo que el usuario
ve/ejecuta en la app; `data_symbol` = ticker de la fuente de datos; `tv_symbol` = para que el
agente refine el quote live (best-effort, se valida al usarse).

| Clase | asset key | mt5_symbol | data_source | data_symbol | pip_size | ccy |
|---|---|---|---|---|---|---|
| Metal | XAUUSD | GOLD | yfinance | GC=F | 0.1 | (USD,) |
| Metal | XAGUSD | SILVER | yfinance | SI=F | 0.01 | (USD,) |
| FX | EURUSD | EURUSD | yfinance | EURUSD=X | 0.0001 | (EUR,USD) |
| FX | GBPUSD | GBPUSD | yfinance | GBPUSD=X | 0.0001 | (GBP,USD) |
| FX | USDJPY | USDJPY | yfinance | USDJPY=X | 0.01 | (USD,JPY) |
| FX | USDCHF | USDCHF | yfinance | USDCHF=X | 0.0001 | (USD,CHF) |
| FX | USDCAD | USDCAD | yfinance | USDCAD=X | 0.0001 | (USD,CAD) |
| FX | AUDUSD | AUDUSD | yfinance | AUDUSD=X | 0.0001 | (AUD,USD) |
| FX | NZDUSD | NZDUSD | yfinance | NZDUSD=X | 0.0001 | (NZD,USD) |
| FX | EURGBP | EURGBP | yfinance | EURGBP=X | 0.0001 | (EUR,GBP) |
| FX | EURJPY | EURJPY | yfinance | EURJPY=X | 0.01 | (EUR,JPY) |
| FX | GBPJPY | GBPJPY | yfinance | GBPJPY=X | 0.01 | (GBP,JPY) |
| Índice | NAS100 | US100Cash | yfinance | ^NDX | 1.0 | (USD,) |
| Índice | SPX500 | US500Cash | yfinance | ^GSPC | 1.0 | (USD,) |
| Índice | US30 | US30Cash | yfinance | ^DJI | 1.0 | (USD,) |
| Índice | GER40 | GER40Cash | yfinance | ^GDAXI | 1.0 | (EUR,) |
| Índice | UK100 | UK100Cash | yfinance | ^FTSE | 1.0 | (GBP,) |
| Cripto | BTCUSD | BTCUSD | binance | BTCUSDT | 1.0 | (USD,) |
| Cripto | ETHUSD | ETHUSD | binance | ETHUSDT | 0.1 | (USD,) |
| Cripto | SOLUSD | SOLUSD | binance | SOLUSDT | 0.01 | (USD,) |
| Cripto | XRPUSD | XRPUSD | binance | XRPUSDT | 0.0001 | (USD,) |
| Energía | WTI | OILCash | yfinance | CL=F | 0.01 | (USD,) |
| Energía | BRENT | BRENTCash | yfinance | BZ=F | 0.01 | (USD,) |

**Campos numéricos APROXIMADOS** (`pip_value_per_001_lot`, `min_sl_pips`, `tv_symbol`): valores
de arranque razonables; el router ya disclaimea "validar pip value en MT5 Specification" y el
sizing marca `UNTRADEABLE_SIZE` cuando el lote sale sub-mínimo. Los valores finales viven en la
tabla `ASSETS` del plan de implementación.

**Excluidos a propósito** (fuera del subset): XAUEUR y exóticos FX (TRY/ZAR/HUF/MXN/...), futuros
agrícolas (Cocoa/Cotton/Sugar/Coffee), metales base (Copper/Nickel/Zinc/Palladium/Platinum/
Aluminium), acciones US/EU/HK, NGAS. Razón: feed dudoso o no scalp-friendly en bonus B-book.

## Arquitectura

### 1. Refactor: tabla única `ASSETS` (sin cambio de comportamiento)

Hoy el router mantiene **6 dicts paralelos** keyed por asset (`MIN_SL_PIPS`, `PIP_SIZE`,
`PIP_VALUE_PER_001_LOT`, `TV_SYMBOL`, `ASSET_CURRENCIES`, `_REALTIME`). Agregar 23 instrumentos a
6 dicts separados es propenso a error (el code-reviewer ya marcó el riesgo "agregué a TV_SYMBOL
pero olvidé ASSET_CURRENCIES").

Solución: una sola tabla `ASSETS: dict[str, dict]`, una fila por instrumento con todos los
campos (`mt5_symbol`, `data_source`, `data_symbol`, `tv_symbol`, `pip_size`,
`pip_value_per_001_lot`, `min_sl_pips`, `currencies`, `realtime`). Los dicts legacy se
**derivan** de `ASSETS` (comprehensions) → los consumidores existentes no cambian, y agregar un
instrumento es **editar una fila**. `UNIVERSE` se deriva de `ASSETS.keys()`. `PHASE_ALLOWED` se
mantiene aparte (es lógica de fase, no config de activo).

### 2. Data layer

`fetch_bars(asset, interval, n)` deja de hardcodear BTC/ETH→Binance y pasa a leer
`ASSETS[asset]["data_source"]` y `["data_symbol"]`: `binance` → `fetch_binance_klines`,
`yfinance` → `fetch_yfinance`. Se agregan los tickers nuevos a `YF_SYMBOL_MAP` en
`per_asset_backtest.py` (USDCHF, NZDUSD, EURGBP, EURJPY, GBPJPY, WTI=CL=F, BRENT=BZ=F; XAGUSD,
AUDUSD, USDCAD, US30, GER40, UK100 ya existen).

### 3. Expansión + phase gating

`ASSETS` poblado con los 23. `PHASE_ALLOWED[1]` = lista completa del subset curado (config.md
`phase_1.allowed_assets` espejo). `PHASE_RISK_PCT` sin cambio (1%/2%/2%).

### 4. Honestidad de edge

Solo `XAUUSD/EURUSD/BTCUSD/SPX500` tienen `per_asset_edge` backtesteado en
`fot_strategy_mapping.json`. Un setup MR-RANGE_CHOP en un activo SIN entrada `per_asset_edge`
sigue pudiendo llegar a APPROVED (MR-RANGE es el edge VALIDATED de clase), pero el router marca
`edge_backtested: false` en ese candidato y el render añade
**"⚠️ edge no backtesteado en este activo — paper-first"**. No bloquea. Follow-up opcional:
correr `per_asset_backtest.py` sobre el subset para poblar `per_asset_edge`.

## Fuera de alcance (YAGNI)

- ❌ No acciones / exóticos / futuros agrícolas / metales base / XAUEUR / NGAS.
- ❌ No backtest masivo ahora (los nuevos salen con caveat; backtest es follow-up separado).
- ❌ No tocar la lógica de scoring/detección de régimen (ya es genérica por activo).
- ❌ No tocar el feature de noticias FF (recién mergeado).

## Tests

- **Parity**: los dicts derivados de `ASSETS` == los valores originales para los 8 activos
  legacy (garantiza que el refactor no cambia comportamiento).
- **Completitud**: todo entry de `ASSETS` tiene los 9 campos requeridos y tipos válidos;
  `data_source` ∈ {yfinance, binance}; `currencies` no vacío.
- **fetch_bars routing**: rutea a la fuente correcta según `data_source` (con fetcher mockeado,
  sin red).
- **Edge caveat**: un candidato APPROVED en un activo sin `per_asset_edge` lleva
  `edge_backtested: false`; uno con entrada lo lleva `true`.
- **Phase 1 unlock**: con el subset expandido, los nuevos activos figuran como `unlocked: true`
  en Fase 1.
- Las suites existentes (`test_fot_scout.py`, `test_fot_scout` del FF news) siguen verdes.

## Riesgos / caveats

- Feeds yfinance tienen ~15 min delay (FX/índices/energía) — ya documentado; el agente refina
  con TV live antes de dar entry. Cripto vía Binance es realtime.
- Algunos `tv_symbol` de índices/energía pueden necesitar ajuste; si el agente no obtiene quote,
  lo reporta y el setup queda sin refinar (NO-GO en duda).
- `pip_value`/`min_sl` aproximados: a $50/1% muchos FX darán `UNTRADEABLE_SIZE` (esperado y
  honesto); oro/índices/cripto con SL más amplio en $ son los realmente ejecutables.
- Yahoo puede rate-limitar o no devolver data para algún ticker → ese activo cae a
  `INSUFFICIENT_DATA` (bucket ya manejado), no rompe el scan.
