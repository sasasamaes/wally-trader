# /fot-scout Universe Expansion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand `/fot-scout` from 8 to 23 curated liquid instruments by refactoring 6 parallel per-asset dicts into one `ASSETS` config table, making the data layer table-driven, and surfacing an honest "edge not backtested" caveat for new assets — all unlocked in phase 1 with risk still escalating by phase.

**Architecture:** A single `ASSETS: dict[str, dict]` in `fot_scout_router.py` holds every per-instrument field; the legacy module dicts (`PIP_SIZE`, `PIP_VALUE_PER_001_LOT`, `MIN_SL_PIPS`, `TV_SYMBOL`, `ASSET_CURRENCIES`, `_REALTIME`, `UNIVERSE`) are derived from it, so consumers are unchanged and adding an instrument is one row. `fetch_bars` reads `data_source`/`data_symbol` from the table. Candidates carry `mt5_symbol` + `edge_backtested`.

**Tech Stack:** Python 3.11+, pytest. Tests run from `shared/wally_core` using its `.venv`. No new dependencies.

---

## File Structure

- **Modify** `.claude/scripts/fot_scout_router.py` — add `ASSETS` table, derive legacy dicts, table-driven `fetch_bars`, enrich candidate dict, expand to 23, set phase-1-unlocks-all.
- **Modify** `shared/wally_core/tests/test_fot_scout.py` — parity, routing, enrichment, completeness, phase-unlock tests; update 2 locked-asset tests to monkeypatch `r.PHASE_ALLOWED`.
- **Modify** `.claude/profiles/fotmarkets/config.md` — mirror the expanded universe + phase-1 allowed list.
- **Modify** `system/commands/fot-scout.md` and **`CLAUDE.md`** — document the curated universe + edge caveat render.

**Test command (from repo root):**
```bash
cd shared/wally_core && .venv/bin/python -m pytest tests/test_fot_scout.py -q
```

---

## Task 1: Refactor 6 parallel dicts → single `ASSETS` table (no behavior change)

**Files:**
- Modify: `.claude/scripts/fot_scout_router.py`
- Test: `shared/wally_core/tests/test_fot_scout.py`

- [ ] **Step 1: Write the failing parity test**

Append to `shared/wally_core/tests/test_fot_scout.py`:

```python
# ── ASSETS table refactor ─────────────────────────────────────────────────────

def test_assets_table_derives_legacy_dicts():
    """The derived per-asset dicts must equal the original literal values (parity)."""
    expected_pip_size = {
        "EURUSD": 0.0001, "GBPUSD": 0.0001, "USDJPY": 0.01, "XAUUSD": 0.1,
        "NAS100": 1.0, "SPX500": 1.0, "BTCUSD": 1.0, "ETHUSD": 0.1,
    }
    expected_pip_value = {
        "EURUSD": 0.10, "GBPUSD": 0.10, "USDJPY": 0.10, "XAUUSD": 0.10,
        "NAS100": 0.01, "SPX500": 0.01, "BTCUSD": 0.01, "ETHUSD": 0.01,
    }
    expected_min_sl = {
        "EURUSD": 8, "GBPUSD": 10, "USDJPY": 10, "XAUUSD": 20,
        "NAS100": 25, "SPX500": 4, "BTCUSD": 50, "ETHUSD": 40,
    }
    expected_tv = {
        "EURUSD": "OANDA:EURUSD", "GBPUSD": "OANDA:GBPUSD", "USDJPY": "OANDA:USDJPY",
        "XAUUSD": "OANDA:XAUUSD", "NAS100": "OANDA:NAS100USD", "SPX500": "OANDA:SPX500USD",
        "BTCUSD": "BINANCE:BTCUSDT", "ETHUSD": "BINANCE:ETHUSDT",
    }
    expected_ccy = {
        "EURUSD": ("EUR", "USD"), "GBPUSD": ("GBP", "USD"), "USDJPY": ("USD", "JPY"),
        "XAUUSD": ("USD",), "NAS100": ("USD",), "SPX500": ("USD",),
        "BTCUSD": ("USD",), "ETHUSD": ("USD",),
    }
    for a in expected_pip_size:
        assert r.PIP_SIZE[a] == expected_pip_size[a]
        assert r.PIP_VALUE_PER_001_LOT[a] == expected_pip_value[a]
        assert r.MIN_SL_PIPS[a] == expected_min_sl[a]
        assert r.TV_SYMBOL[a] == expected_tv[a]
        assert r.ASSET_CURRENCIES[a] == expected_ccy[a]
    assert r._REALTIME == {"BTCUSD", "ETHUSD"}
    assert set(r.UNIVERSE) == set(expected_pip_size)
```

- [ ] **Step 2: Run it to verify it passes-or-fails meaningfully**

Run: `cd /Users/josecampos/Documents/wally-trader/shared/wally_core && .venv/bin/python -m pytest tests/test_fot_scout.py::test_assets_table_derives_legacy_dicts -q`
Expected: PASS today (the literals still exist). This test pins current values so the refactor can't drift them. Proceed to refactor; it must stay green.

- [ ] **Step 3: Introduce `ASSETS` and derive the legacy names**

In `.claude/scripts/fot_scout_router.py`, replace the block that currently defines `UNIVERSE`, `MIN_SL_PIPS`, `PIP_SIZE`, `PIP_VALUE_PER_001_LOT`, `TV_SYMBOL`, `ASSET_CURRENCIES`, and `_REALTIME` (the `UNIVERSE = [...]` line through the `_REALTIME = {...}` line) with:

```python
# Tabla única de configuración por instrumento. Agregar un activo = una fila.
# Campos: mt5_symbol (símbolo que el usuario opera en MT5), data_source (binance|yfinance),
# data_symbol (ticker de la fuente), tv_symbol (quote live del agente), pip_size,
# pip_value_per_001_lot (APROX — validar en MT5 Spec), min_sl_pips, currencies, realtime.
ASSETS: dict[str, dict] = {
    "EURUSD": {"mt5_symbol": "EURUSD", "data_source": "yfinance", "data_symbol": "EURUSD=X",
               "tv_symbol": "OANDA:EURUSD", "pip_size": 0.0001, "pip_value_per_001_lot": 0.10,
               "min_sl_pips": 8, "currencies": ("EUR", "USD"), "realtime": False},
    "GBPUSD": {"mt5_symbol": "GBPUSD", "data_source": "yfinance", "data_symbol": "GBPUSD=X",
               "tv_symbol": "OANDA:GBPUSD", "pip_size": 0.0001, "pip_value_per_001_lot": 0.10,
               "min_sl_pips": 10, "currencies": ("GBP", "USD"), "realtime": False},
    "USDJPY": {"mt5_symbol": "USDJPY", "data_source": "yfinance", "data_symbol": "USDJPY=X",
               "tv_symbol": "OANDA:USDJPY", "pip_size": 0.01, "pip_value_per_001_lot": 0.10,
               "min_sl_pips": 10, "currencies": ("USD", "JPY"), "realtime": False},
    "XAUUSD": {"mt5_symbol": "GOLD", "data_source": "yfinance", "data_symbol": "GC=F",
               "tv_symbol": "OANDA:XAUUSD", "pip_size": 0.1, "pip_value_per_001_lot": 0.10,
               "min_sl_pips": 20, "currencies": ("USD",), "realtime": False},
    "NAS100": {"mt5_symbol": "US100Cash", "data_source": "yfinance", "data_symbol": "^NDX",
               "tv_symbol": "OANDA:NAS100USD", "pip_size": 1.0, "pip_value_per_001_lot": 0.01,
               "min_sl_pips": 25, "currencies": ("USD",), "realtime": False},
    "SPX500": {"mt5_symbol": "US500Cash", "data_source": "yfinance", "data_symbol": "^GSPC",
               "tv_symbol": "OANDA:SPX500USD", "pip_size": 1.0, "pip_value_per_001_lot": 0.01,
               "min_sl_pips": 4, "currencies": ("USD",), "realtime": False},
    "BTCUSD": {"mt5_symbol": "BTCUSD", "data_source": "binance", "data_symbol": "BTCUSDT",
               "tv_symbol": "BINANCE:BTCUSDT", "pip_size": 1.0, "pip_value_per_001_lot": 0.01,
               "min_sl_pips": 50, "currencies": ("USD",), "realtime": True},
    "ETHUSD": {"mt5_symbol": "ETHUSD", "data_source": "binance", "data_symbol": "ETHUSDT",
               "tv_symbol": "BINANCE:ETHUSDT", "pip_size": 0.1, "pip_value_per_001_lot": 0.01,
               "min_sl_pips": 40, "currencies": ("USD",), "realtime": True},
}

UNIVERSE = list(ASSETS.keys())
MIN_SL_PIPS = {a: c["min_sl_pips"] for a, c in ASSETS.items()}
PIP_SIZE = {a: c["pip_size"] for a, c in ASSETS.items()}
PIP_VALUE_PER_001_LOT = {a: c["pip_value_per_001_lot"] for a, c in ASSETS.items()}
TV_SYMBOL = {a: c["tv_symbol"] for a, c in ASSETS.items()}
ASSET_CURRENCIES = {a: c["currencies"] for a, c in ASSETS.items()}
_REALTIME = {a for a, c in ASSETS.items() if c["realtime"]}
```

Leave `PHASE_ALLOWED`, `PHASE_RISK_PCT`, `PHASE_TP_R`, `GOAL_USD` exactly as they are. Keep the existing comments for those. Remove only the 7 old literal definitions listed above.

- [ ] **Step 4: Run the full router suite**

Run: `cd /Users/josecampos/Documents/wally-trader/shared/wally_core && .venv/bin/python -m pytest tests/test_fot_scout.py -q`
Expected: PASS (all existing + the new parity test).

- [ ] **Step 5: Commit**

```bash
cd /Users/josecampos/Documents/wally-trader && git add .claude/scripts/fot_scout_router.py shared/wally_core/tests/test_fot_scout.py && git commit -m "refactor(fot-scout): single ASSETS table, derive legacy per-asset dicts"
```

---

## Task 2: Table-driven `fetch_bars`

**Files:**
- Modify: `.claude/scripts/fot_scout_router.py`
- Test: `shared/wally_core/tests/test_fot_scout.py`

- [ ] **Step 1: Write the failing test**

Append to `shared/wally_core/tests/test_fot_scout.py`:

```python
# ── data-source routing ───────────────────────────────────────────────────────

def test_fetch_bars_routes_binance_for_crypto(monkeypatch):
    calls = {}
    monkeypatch.setattr(r.pab, "fetch_binance_klines",
                        lambda sym, interval, n: calls.setdefault("binance", (sym, interval, n)) or [])
    monkeypatch.setattr(r.pab, "fetch_yfinance",
                        lambda sym, interval, n: calls.setdefault("yf", (sym, interval, n)) or [])
    r.fetch_bars("BTCUSD", "5m", 120)
    assert calls["binance"] == ("BTCUSDT", "5m", 120)
    assert "yf" not in calls


def test_fetch_bars_routes_yfinance_with_data_symbol(monkeypatch):
    calls = {}
    monkeypatch.setattr(r.pab, "fetch_yfinance",
                        lambda sym, interval, n: calls.setdefault("yf", (sym, interval, n)) or [])
    monkeypatch.setattr(r.pab, "fetch_binance_klines",
                        lambda sym, interval, n: calls.setdefault("binance", (sym, interval, n)) or [])
    r.fetch_bars("XAUUSD", "15m", 80)
    assert calls["yf"] == ("GC=F", "15m", 80)   # passes the resolved data_symbol, not the asset key
    assert "binance" not in calls
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd /Users/josecampos/Documents/wally-trader/shared/wally_core && .venv/bin/python -m pytest tests/test_fot_scout.py -q -k fetch_bars`
Expected: `test_fetch_bars_routes_yfinance_with_data_symbol` FAILS (current code calls `fetch_yfinance("XAUUSD", ...)`, not `"GC=F"`).

- [ ] **Step 3: Make `fetch_bars` table-driven**

In `.claude/scripts/fot_scout_router.py`, replace the entire `fetch_bars` function with:

```python
def fetch_bars(asset: str, interval: str, n: int) -> list[dict]:
    """Pull OHLCV en formato o/h/l/c/v según la fuente declarada en ASSETS.

    binance → real-time; yfinance → delayed ~15min. Pasa data_symbol resuelto
    (no la asset key) para no depender de YF_SYMBOL_MAP en activos nuevos.
    """
    cfg = ASSETS[asset]
    if cfg["data_source"] == "binance":
        return pab.fetch_binance_klines(cfg["data_symbol"], interval, n)
    return pab.fetch_yfinance(cfg["data_symbol"], interval, n)
```

- [ ] **Step 4: Run the suite**

Run: `cd /Users/josecampos/Documents/wally-trader/shared/wally_core && .venv/bin/python -m pytest tests/test_fot_scout.py -q`
Expected: PASS (all, including the 2 routing tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/josecampos/Documents/wally-trader && git add .claude/scripts/fot_scout_router.py shared/wally_core/tests/test_fot_scout.py && git commit -m "feat(fot-scout): table-driven fetch_bars (data_source/data_symbol)"
```

---

## Task 3: Enrich candidate dict with `mt5_symbol` + `edge_backtested`

**Files:**
- Modify: `.claude/scripts/fot_scout_router.py`
- Test: `shared/wally_core/tests/test_fot_scout.py`

- [ ] **Step 1: Write the failing test**

Append to `shared/wally_core/tests/test_fot_scout.py`:

```python
# ── candidate enrichment ──────────────────────────────────────────────────────

def test_candidate_has_mt5_symbol_and_edge_flag(monkeypatch, mapping):
    _mr_long(monkeypatch)
    # XAUUSD HAS per_asset_edge → edge_backtested True; mt5_symbol GOLD
    xau = r.evaluate_asset("XAUUSD", mapping, 1, 50.0, _bars(40), _bars(40), _bars(40))
    assert xau["mt5_symbol"] == "GOLD"
    assert xau["edge_backtested"] is True


def test_candidate_edge_flag_false_for_unbacktested(monkeypatch, mapping):
    _mr_long(monkeypatch)
    # USDJPY has NO per_asset_edge entry → edge_backtested False
    jpy = r.evaluate_asset("USDJPY", mapping, 1, 50.0, _bars(40), _bars(40), _bars(40))
    assert jpy["edge_backtested"] is False
    assert jpy["mt5_symbol"] == "USDJPY"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd /Users/josecampos/Documents/wally-trader/shared/wally_core && .venv/bin/python -m pytest tests/test_fot_scout.py -q -k "mt5_symbol or edge_flag"`
Expected: FAIL with `KeyError: 'mt5_symbol'`.

- [ ] **Step 3: Add the fields to the `base` dict in `evaluate_asset`**

In `.claude/scripts/fot_scout_router.py`, find these lines inside `evaluate_asset`:

```python
    allowed = PHASE_ALLOWED[phase]
    unlocked = (allowed == "ALL") or (asset in allowed)
    base = {"asset": asset, "tv_symbol": TV_SYMBOL.get(asset, asset), "unlocked": unlocked,
            "data_realtime": asset in _REALTIME}
```

Replace that `base = {...}` assignment with:

```python
    base = {"asset": asset, "tv_symbol": TV_SYMBOL.get(asset, asset),
            "mt5_symbol": ASSETS[asset]["mt5_symbol"], "unlocked": unlocked,
            "data_realtime": asset in _REALTIME,
            "edge_backtested": asset in mapping.get("per_asset_edge", {})}
```

- [ ] **Step 4: Run the suite**

Run: `cd /Users/josecampos/Documents/wally-trader/shared/wally_core && .venv/bin/python -m pytest tests/test_fot_scout.py -q`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
cd /Users/josecampos/Documents/wally-trader && git add .claude/scripts/fot_scout_router.py shared/wally_core/tests/test_fot_scout.py && git commit -m "feat(fot-scout): candidate carries mt5_symbol + edge_backtested flag"
```

---

## Task 4: Expand `ASSETS` to 23 + unlock all in phase 1

**Files:**
- Modify: `.claude/scripts/fot_scout_router.py`
- Modify: `.claude/profiles/fotmarkets/config.md`
- Test: `shared/wally_core/tests/test_fot_scout.py`

- [ ] **Step 1: Write the failing tests**

Append to `shared/wally_core/tests/test_fot_scout.py`:

```python
# ── universe expansion ────────────────────────────────────────────────────────

def test_universe_has_23_curated_instruments():
    assert len(r.UNIVERSE) == 23
    for sym in ("XAGUSD", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD", "EURGBP", "EURJPY",
                "GBPJPY", "US30", "GER40", "UK100", "SOLUSD", "XRPUSD", "WTI", "BRENT"):
        assert sym in r.ASSETS, f"{sym} missing from ASSETS"


def test_assets_entries_are_complete_and_valid():
    required = {"mt5_symbol", "data_source", "data_symbol", "tv_symbol", "pip_size",
                "pip_value_per_001_lot", "min_sl_pips", "currencies", "realtime"}
    for sym, cfg in r.ASSETS.items():
        assert required.issubset(cfg), f"{sym} missing fields: {required - set(cfg)}"
        assert cfg["data_source"] in ("yfinance", "binance"), sym
        assert isinstance(cfg["currencies"], tuple) and cfg["currencies"], sym
        assert cfg["pip_size"] > 0, sym


def test_phase1_unlocks_all_curated_assets(monkeypatch, mapping):
    _mr_long(monkeypatch)
    for sym in ("SOLUSD", "USDCHF", "GER40"):
        res = r.evaluate_asset(sym, mapping, 1, 50.0, _bars(40), _bars(40), _bars(40))
        assert res["unlocked"] is True, f"{sym} should be unlocked in phase 1"
```

- [ ] **Step 2: Update the two obsolete locked-asset tests**

Phase 1 now unlocks everything, so the override mechanism is exercised via a monkeypatched
restricted `PHASE_ALLOWED` instead of relying on production config. Replace the existing
`test_btc_unlocked_nas100_locked_phase1` and `test_scan_separates_override_from_approved`
functions with:

```python
def test_btc_unlocked_nas100_locked_phase1(monkeypatch, mapping):
    # Production phase 1 unlocks all; restrict via monkeypatch to test the lock/override path.
    monkeypatch.setattr(r, "PHASE_ALLOWED", {1: ["BTCUSD"], 2: "ALL", 3: "ALL"})
    _mr_long(monkeypatch)
    btc = r.evaluate_asset("BTCUSD", mapping, 1, 50.0, _bars(40), _bars(40), _bars(40))
    nas = r.evaluate_asset("NAS100", mapping, 1, 50.0, _bars(40), _bars(40), _bars(40))
    assert btc["unlocked"] is True
    assert nas["unlocked"] is False
    assert nas["status"] == "OVERRIDE_LOCKED"


def test_scan_separates_override_from_approved(monkeypatch, mapping):
    monkeypatch.setattr(r, "PHASE_ALLOWED", {1: ["BTCUSD"], 2: "ALL", 3: "ALL"})
    _mr_long(monkeypatch)
    out = r.scan(mapping, 1, 50.0, fetch=lambda a, i, n: _bars(40), assets=["NAS100"])
    assert out["approved"] == []
    assert len(out["override_candidates"]) == 1
    assert out["status"] == "OVERRIDE_AVAILABLE"
```

- [ ] **Step 3: Run to verify the new + updated tests fail**

Run: `cd /Users/josecampos/Documents/wally-trader/shared/wally_core && .venv/bin/python -m pytest tests/test_fot_scout.py -q -k "universe or complete or unlocks_all or locked or override"`
Expected: FAIL — `test_universe_has_23...` (only 8 today) and `test_phase1_unlocks_all...` (NAS100 etc. locked today). The two updated tests also fail until `PHASE_ALLOWED` changes (their monkeypatch sets a restricted dict, so they pass once the code change in Step 5 is in — run again in Step 6).

- [ ] **Step 4: Add the 15 new instruments to `ASSETS`**

In `.claude/scripts/fot_scout_router.py`, inside the `ASSETS` dict, after the `"ETHUSD": {...},` entry (before the closing `}`), add:

```python
    # ── Expansión 2026-06-01: subset líquido curado ──
    "XAGUSD": {"mt5_symbol": "SILVER", "data_source": "yfinance", "data_symbol": "SI=F",
               "tv_symbol": "OANDA:XAGUSD", "pip_size": 0.01, "pip_value_per_001_lot": 0.50,
               "min_sl_pips": 30, "currencies": ("USD",), "realtime": False},
    "USDCHF": {"mt5_symbol": "USDCHF", "data_source": "yfinance", "data_symbol": "USDCHF=X",
               "tv_symbol": "OANDA:USDCHF", "pip_size": 0.0001, "pip_value_per_001_lot": 0.10,
               "min_sl_pips": 10, "currencies": ("USD", "CHF"), "realtime": False},
    "USDCAD": {"mt5_symbol": "USDCAD", "data_source": "yfinance", "data_symbol": "USDCAD=X",
               "tv_symbol": "OANDA:USDCAD", "pip_size": 0.0001, "pip_value_per_001_lot": 0.10,
               "min_sl_pips": 10, "currencies": ("USD", "CAD"), "realtime": False},
    "AUDUSD": {"mt5_symbol": "AUDUSD", "data_source": "yfinance", "data_symbol": "AUDUSD=X",
               "tv_symbol": "OANDA:AUDUSD", "pip_size": 0.0001, "pip_value_per_001_lot": 0.10,
               "min_sl_pips": 8, "currencies": ("AUD", "USD"), "realtime": False},
    "NZDUSD": {"mt5_symbol": "NZDUSD", "data_source": "yfinance", "data_symbol": "NZDUSD=X",
               "tv_symbol": "OANDA:NZDUSD", "pip_size": 0.0001, "pip_value_per_001_lot": 0.10,
               "min_sl_pips": 8, "currencies": ("NZD", "USD"), "realtime": False},
    "EURGBP": {"mt5_symbol": "EURGBP", "data_source": "yfinance", "data_symbol": "EURGBP=X",
               "tv_symbol": "OANDA:EURGBP", "pip_size": 0.0001, "pip_value_per_001_lot": 0.10,
               "min_sl_pips": 8, "currencies": ("EUR", "GBP"), "realtime": False},
    "EURJPY": {"mt5_symbol": "EURJPY", "data_source": "yfinance", "data_symbol": "EURJPY=X",
               "tv_symbol": "OANDA:EURJPY", "pip_size": 0.01, "pip_value_per_001_lot": 0.10,
               "min_sl_pips": 10, "currencies": ("EUR", "JPY"), "realtime": False},
    "GBPJPY": {"mt5_symbol": "GBPJPY", "data_source": "yfinance", "data_symbol": "GBPJPY=X",
               "tv_symbol": "OANDA:GBPJPY", "pip_size": 0.01, "pip_value_per_001_lot": 0.10,
               "min_sl_pips": 12, "currencies": ("GBP", "JPY"), "realtime": False},
    "US30":   {"mt5_symbol": "US30Cash", "data_source": "yfinance", "data_symbol": "^DJI",
               "tv_symbol": "OANDA:US30USD", "pip_size": 1.0, "pip_value_per_001_lot": 0.01,
               "min_sl_pips": 30, "currencies": ("USD",), "realtime": False},
    "GER40":  {"mt5_symbol": "GER40Cash", "data_source": "yfinance", "data_symbol": "^GDAXI",
               "tv_symbol": "OANDA:DE40EUR", "pip_size": 1.0, "pip_value_per_001_lot": 0.01,
               "min_sl_pips": 30, "currencies": ("EUR",), "realtime": False},
    "UK100":  {"mt5_symbol": "UK100Cash", "data_source": "yfinance", "data_symbol": "^FTSE",
               "tv_symbol": "OANDA:UK100GBP", "pip_size": 1.0, "pip_value_per_001_lot": 0.01,
               "min_sl_pips": 20, "currencies": ("GBP",), "realtime": False},
    "SOLUSD": {"mt5_symbol": "SOLUSD", "data_source": "binance", "data_symbol": "SOLUSDT",
               "tv_symbol": "BINANCE:SOLUSDT", "pip_size": 0.01, "pip_value_per_001_lot": 0.01,
               "min_sl_pips": 30, "currencies": ("USD",), "realtime": True},
    "XRPUSD": {"mt5_symbol": "XRPUSD", "data_source": "binance", "data_symbol": "XRPUSDT",
               "tv_symbol": "BINANCE:XRPUSDT", "pip_size": 0.0001, "pip_value_per_001_lot": 0.01,
               "min_sl_pips": 30, "currencies": ("USD",), "realtime": True},
    "WTI":    {"mt5_symbol": "OILCash", "data_source": "yfinance", "data_symbol": "CL=F",
               "tv_symbol": "TVC:USOIL", "pip_size": 0.01, "pip_value_per_001_lot": 0.10,
               "min_sl_pips": 20, "currencies": ("USD",), "realtime": False},
    "BRENT":  {"mt5_symbol": "BRENTCash", "data_source": "yfinance", "data_symbol": "BZ=F",
               "tv_symbol": "TVC:UKOIL", "pip_size": 0.01, "pip_value_per_001_lot": 0.10,
               "min_sl_pips": 20, "currencies": ("USD",), "realtime": False},
```

- [ ] **Step 5: Set phase 1 to unlock all**

In `.claude/scripts/fot_scout_router.py`, replace the `PHASE_ALLOWED = {...}` block with:

```python
# Decisión 2026-06-01 (ver spec universe-expansion): el subset curado se desbloquea
# entero en Fase 1; el risk sigue escalando por fase (PHASE_RISK_PCT). El mecanismo
# de lock/override se conserva en el código por si una config futura lo restringe.
PHASE_ALLOWED = {1: "ALL", 2: "ALL", 3: "ALL"}
```

- [ ] **Step 6: Run the full suite**

Run: `cd /Users/josecampos/Documents/wally-trader/shared/wally_core && .venv/bin/python -m pytest tests/test_fot_scout.py -q`
Expected: PASS (all — new universe/completeness/unlock tests + the 2 updated override tests).

- [ ] **Step 7: Mirror the universe in `config.md`**

In `.claude/profiles/fotmarkets/config.md`, find the `assets_universe:` block and the
`phase_1:`/`phase_2:`/`phase_3:` `allowed_assets:` lines. Update them to reflect the curated 23
and phase-1-unlocks-all. Replace the `assets_universe:` list value and the three
`allowed_assets:` lines so they read:

```yaml
# Assets operables (subset líquido curado 2026-06-01, todos en Fase 1)
assets_universe: [XAUUSD, XAGUSD, EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD,
                  EURGBP, EURJPY, GBPJPY, NAS100, SPX500, US30, GER40, UK100,
                  BTCUSD, ETHUSD, SOLUSD, XRPUSD, WTI, BRENT]
```

And under each phase set `allowed_assets: [ALL]  # subset curado completo desbloqueado en Fase 1; risk escala por fase`.
(Keep all other phase fields — risk %, thresholds — unchanged.)

- [ ] **Step 8: Commit**

```bash
cd /Users/josecampos/Documents/wally-trader && git add .claude/scripts/fot_scout_router.py shared/wally_core/tests/test_fot_scout.py .claude/profiles/fotmarkets/config.md && git commit -m "feat(fot-scout): expand to 23 curated instruments, unlock all in phase 1"
```

---

## Task 5: Document the universe + edge caveat render

**Files:**
- Modify: `system/commands/fot-scout.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add the edge-caveat render rule to the command doc**

In `system/commands/fot-scout.md`, inside the "## Reglas de seguridad" section, add this bullet
at the end of that list:

```markdown
- **Edge no backtesteado por activo:** si un candidato APROBADO trae `edge_backtested: false`
  (activo del subset curado sin entrada en `per_asset_edge`), el render añade
  `⚠️ edge no backtesteado en este activo — paper-first`. El MR-RANGE_CHOP es edge de clase
  validado, pero ese activo puntual no se backtesteó aún. Usar `mt5_symbol` del candidato para
  las instrucciones de ejecución en MT5 (p.ej. `US100Cash`, `GOLD`, `OILCash`).
```

- [ ] **Step 2: Add a note to CLAUDE.md**

In `CLAUDE.md`, inside the `### `/fot-scout` (2026-05-31) — fotmarkets-only` section, append:

```markdown
- **Universo curado (2026-06-01):** el router escanea **23 instrumentos líquidos** (oro/plata,
  10 FX, 5 índices, 4 cripto, WTI/Brent) vía una tabla única `ASSETS` (agregar = 1 fila). Todos
  desbloqueados en Fase 1; risk escala 1%→2%→2%. Activos sin `per_asset_edge` backtesteado
  llevan `edge_backtested:false` → caveat "⚠️ edge no backtesteado". Excluye exóticos, futuros
  agrícolas, metales base y acciones (no scalp-friendly en bonus). Feeds: yfinance (FX/índices/
  metales/energía, ~15min delay) + Binance (cripto, realtime). Spec/plan:
  `docs/superpowers/{specs,plans}/2026-06-01-fot-scout-universe-expansion*.md`.
```

- [ ] **Step 3: Commit**

```bash
cd /Users/josecampos/Documents/wally-trader && git add system/commands/fot-scout.md CLAUDE.md && git commit -m "docs(fot-scout): document curated universe + edge caveat render"
```

---

## Self-Review Notes

- **Spec coverage:** Refactor to `ASSETS` (Task 1) ✓; table-driven data layer (Task 2) ✓;
  23-instrument expansion + phase-1-unlock-all (Task 4) ✓; edge caveat + mt5_symbol (Task 3, doc
  render Task 5) ✓; config.md mirror (Task 4 Step 7) ✓; CLAUDE.md note (Task 5) ✓. Tests for
  parity, routing, completeness, edge flag, phase unlock all present. Out-of-scope items
  (no stocks/exotics/ag-futures/base-metals; no mass backtest; no scoring/regime changes; no FF
  news changes) are respected — no task touches them.
- **Placeholder scan:** none — every step shows literal code/edits.
- **Type/name consistency:** `ASSETS` field set `{mt5_symbol, data_source, data_symbol,
  tv_symbol, pip_size, pip_value_per_001_lot, min_sl_pips, currencies, realtime}` is identical in
  Tasks 1, 3, and 4. Derived dict names (`PIP_SIZE`, `PIP_VALUE_PER_001_LOT`, `MIN_SL_PIPS`,
  `TV_SYMBOL`, `ASSET_CURRENCIES`, `_REALTIME`, `UNIVERSE`) match the consumers in
  `evaluate_asset`/`_sl_distance`/`_size_lots`/`scan`. `fetch_bars` signature unchanged.
  Candidate keys `mt5_symbol`/`edge_backtested` consistent between Task 3 code and Task 5 render.
- **Note on data_symbol vs YF_SYMBOL_MAP:** Task 2 passes the resolved `data_symbol` to
  `fetch_yfinance` (which does `YF_SYMBOL_MAP.get(sym, sym)` → idempotent for already-resolved
  tickers), so no `YF_SYMBOL_MAP` edits are needed — simpler than the spec's tentative approach,
  same outcome.
