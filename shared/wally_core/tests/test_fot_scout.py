"""Tests for fot_scout_router (the fotmarkets regime-aware multi-strategy scanner).

The router lives in .claude/scripts/ (not in the wally_core package), so we add that
dir to sys.path. Heavy seams (regime detection, strategy triggers, scoring) are
monkeypatched to isolate the router's own decision logic: edge-gate honesty, phase
gating, sizing, threshold/WAIT behaviour.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[3] / ".claude" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import fot_scout_router as r  # noqa: E402
from wally_core.validate import ValidateResult, Side  # noqa: E402


# ── Helpers ──────────────────────────────────────────────────────────────────

def _flat_bars(n: int, price: float = 100.0) -> list[dict]:
    """n velas planas (o=h=l=c=price). ATR=0 → fuerza el SL floor."""
    return [{"o": price, "h": price, "l": price, "c": price, "v": 1000.0} for _ in range(n)]


def _bars(n: int = 40, price: float = 100.0) -> list[dict]:
    """n velas con micro-variación (suficiente para los min_bars guards)."""
    out = []
    for i in range(n):
        p = price + (i % 3) * 0.01
        out.append({"o": p, "h": p + 0.02, "l": p - 0.02, "c": p + 0.01, "v": 1000.0 + i})
    return out


def _mr_long(monkeypatch, score: int = 80):
    """Forzar régimen RANGE_CHOP + trigger MR LONG + score dado."""
    monkeypatch.setattr(r, "detect_regime", lambda b1h, b5m: "RANGE_CHOP")
    monkeypatch.setattr(
        r, "validate_setup",
        lambda bars, side, dl=15: ValidateResult(go=(side == Side.LONG), filters=[], reason=""),
    )
    monkeypatch.setattr(r, "_score_mr", lambda *a, **k: score)


@pytest.fixture
def mapping():
    return r.load_mapping()


# ── 1. Regime → strategy selection ───────────────────────────────────────────

def test_range_chop_selects_mean_reversion(monkeypatch, mapping):
    _mr_long(monkeypatch)
    res = r.evaluate_asset("EURUSD", mapping, 1, 50.0, _bars(40), _bars(40), _bars(40))
    assert res["strategy"] == "mean_reversion"


def test_volatile_stands_aside(monkeypatch, mapping):
    monkeypatch.setattr(r, "detect_regime", lambda b1h, b5m: "VOLATILE")
    res = r.evaluate_asset("EURUSD", mapping, 1, 50.0, _bars(40), _bars(40), _bars(40))
    assert res["status"] == "STAND_ASIDE"
    assert res["strategy"] == "stand_aside"


def test_trend_fuerte_selects_donchian(monkeypatch, mapping):
    monkeypatch.setattr(r, "detect_regime", lambda b1h, b5m: "TREND_FUERTE")
    res = r.evaluate_asset("EURUSD", mapping, 2, 150.0, _bars(40), _bars(40), _bars(40))
    assert res["strategy"] == "donchian_breakout"
    # Sin ruptura → NO_SETUP (flat-ish bars). Edge igual WEAK.
    assert res["edge"] == "WEAK"


# ── 2. Mean-Reversion APPROVED path ──────────────────────────────────────────

def test_mr_approved_when_unlocked_and_score_high(monkeypatch, mapping):
    _mr_long(monkeypatch, score=80)
    res = r.evaluate_asset("BTCUSD", mapping, 1, 50.0, _bars(40), _bars(40), _bars(40))
    assert res["status"] == "APPROVED"
    assert res["side"] == "LONG"
    assert res["score"] >= mapping["global_threshold"]
    assert "setup" in res and res["setup"]["lots"] >= 0.01


# ── 3. Honesty contract: trend strategies never APPROVED ─────────────────────

def test_trend_setup_is_tentative_never_approved(monkeypatch, mapping):
    monkeypatch.setattr(r, "detect_regime", lambda b1h, b5m: "TREND_LEVE")
    monkeypatch.setattr(r, "detect_cross", lambda closes, f, s: {"signal": "LONG"})
    monkeypatch.setattr(r, "_score_trend", lambda *a, **k: 90)  # incluso con score alto
    res = r.evaluate_asset("BTCUSD", mapping, 1, 50.0, _bars(40), _bars(40), _bars(40))
    assert res["status"] == "TENTATIVE"
    assert "label" in res and "edge no validado" in res["label"]


def test_scan_excludes_tentative_from_approved(monkeypatch, mapping):
    monkeypatch.setattr(r, "detect_regime", lambda b1h, b5m: "TREND_LEVE")
    monkeypatch.setattr(r, "detect_cross", lambda closes, f, s: {"signal": "LONG"})
    monkeypatch.setattr(r, "_score_trend", lambda *a, **k: 90)
    out = r.scan(mapping, 1, 50.0, fetch=lambda a, i, n: _bars(40), assets=["BTCUSD"])
    assert out["status"] == "WAIT"
    assert out["approved"] == []
    assert len(out["tentative_trend"]) == 1


# ── 4. Threshold gate ────────────────────────────────────────────────────────

def test_below_threshold(monkeypatch, mapping):
    _mr_long(monkeypatch, score=55)  # < 70
    res = r.evaluate_asset("BTCUSD", mapping, 1, 50.0, _bars(40), _bars(40), _bars(40))
    assert res["status"] == "BELOW_THRESHOLD"


# ── 5. Phase-aware sizing ────────────────────────────────────────────────────

def test_phase1_50usd_eurusd_untradeable(monkeypatch, mapping):
    """A $50 / 1% risk, EURUSD con 0.01 min lot arriesga 1.6% → untradeable."""
    _mr_long(monkeypatch)
    res = r.evaluate_asset("EURUSD", mapping, 1, 50.0, _flat_bars(40), _bars(40), _bars(40))
    assert res["setup"]["risk_usd"] == 0.5
    assert res["setup"]["risk_pct"] == 1.0
    assert res["status"] == "UNTRADEABLE_SIZE"


def test_phase2_tradeable(monkeypatch, mapping):
    _mr_long(monkeypatch)
    res = r.evaluate_asset("EURUSD", mapping, 2, 150.0, _flat_bars(40), _bars(40), _bars(40))
    assert res["setup"]["risk_pct"] == 2.0
    assert res["setup"]["risk_usd"] == 3.0
    assert res["setup"]["lots"] >= 0.01
    assert res["status"] == "APPROVED"


# ── 6. SL pip floor ──────────────────────────────────────────────────────────

def test_sl_floor_dominates_when_atr_tiny():
    sl = r._sl_distance("XAUUSD", _flat_bars(40))  # ATR=0 → floor
    assert sl == pytest.approx(r.MIN_SL_PIPS["XAUUSD"] * r.PIP_SIZE["XAUUSD"])  # 20 * 0.1 = 2.0


# ── 7/8. Override flagging (locked assets in phase 1) ────────────────────────

def test_btc_unlocked_nas100_locked_phase1(monkeypatch, mapping):
    _mr_long(monkeypatch)
    btc = r.evaluate_asset("BTCUSD", mapping, 1, 50.0, _bars(40), _bars(40), _bars(40))
    nas = r.evaluate_asset("NAS100", mapping, 1, 50.0, _bars(40), _bars(40), _bars(40))
    assert btc["unlocked"] is True
    assert nas["unlocked"] is False
    assert nas["status"] == "OVERRIDE_LOCKED"


def test_scan_separates_override_from_approved(monkeypatch, mapping):
    _mr_long(monkeypatch)
    out = r.scan(mapping, 1, 50.0, fetch=lambda a, i, n: _bars(40), assets=["NAS100"])
    assert out["approved"] == []
    assert len(out["override_candidates"]) == 1
    assert out["status"] == "OVERRIDE_AVAILABLE"


# ── 9. Rank order ────────────────────────────────────────────────────────────

def test_approved_sorted_by_score_desc(monkeypatch, mapping):
    canned = {
        "BTCUSD": {"asset": "BTCUSD", "status": "APPROVED", "score": 72, "regime": "RANGE_CHOP", "setup": {}},
        "ETHUSD": {"asset": "ETHUSD", "status": "APPROVED", "score": 88, "regime": "RANGE_CHOP", "setup": {}},
    }
    monkeypatch.setattr(r, "evaluate_asset",
                        lambda asset, *a, **k: canned[asset])
    out = r.scan(mapping, 1, 50.0, fetch=lambda a, i, n: _bars(40), assets=["BTCUSD", "ETHUSD"])
    assert [c["asset"] for c in out["approved"]] == ["ETHUSD", "BTCUSD"]


def test_score_mr_penalizes_oos_fail_more_than_warn(mapping):
    bars5 = _bars(40)
    bars15 = _bars(40)
    warn = r._score_mr("XAUUSD", bars5, bars15, mapping)   # oos WARN, exp 0.46 (+10 -10)
    fail = r._score_mr("EURUSD", bars5, bars15, mapping)   # oos FAIL, exp 0.16 (-20)
    assert warn > fail


# ── 10. No-data resilience ───────────────────────────────────────────────────

def test_insufficient_data(monkeypatch, mapping):
    res = r.evaluate_asset("EURUSD", mapping, 1, 50.0, _bars(10), _bars(10), _bars(10))
    assert res["status"] == "INSUFFICIENT_DATA"


def test_scan_fetch_error_bucketed(mapping):
    def boom(a, i, n):
        raise RuntimeError("network down")
    out = r.scan(mapping, 1, 50.0, fetch=boom, assets=["EURUSD"])
    assert len(out["insufficient_data"]) == 1
    assert out["status"] == "WAIT"


# ── 11. Key remap seam (o/h/l/c/v → open/high/low/close) ─────────────────────

def test_to_wally_remap_feeds_validate_setup():
    wally = r._to_wally(_bars(25))
    assert set(wally[0].keys()) == {"open", "high", "low", "close", "volume"}
    # validate_setup no debe romper con el formato remapeado
    from wally_core.validate import validate_setup as vs
    result = vs(wally, Side.LONG, 15)
    assert hasattr(result, "go")


# ── news block ────────────────────────────────────────────────────────────────

def test_scan_attaches_news_block(mapping):
    captured = {}
    def fake_news(currencies, hours=48, now=None):
        captured["ccys"] = set(currencies)
        return {"events": [], "nearest": None, "stale": False, "source": "test"}
    out = r.scan(mapping, 1, 50.0, fetch=lambda a, i, n: _bars(40),
                 assets=["XAUUSD"], news_fn=fake_news)
    assert "news" in out
    assert out["news"]["source"] == "test"
    assert captured["ccys"] == {"USD"}


def test_scan_news_currencies_union_over_unlocked(mapping):
    captured = {}
    def fake_news(currencies, hours=48, now=None):
        captured["ccys"] = set(currencies)
        return {"events": [], "nearest": None, "stale": False, "source": None}
    out = r.scan(mapping, 1, 50.0, fetch=lambda a, i, n: _bars(40),
                 assets=["EURUSD", "XAUUSD"], news_fn=fake_news)
    assert captured["ccys"] == {"EUR", "USD"}


def test_scan_news_excludes_locked_asset_currency(mapping):
    # USDJPY is locked in phase 1 → JPY must not leak into the currency set.
    captured = {}
    def fake_news(currencies, hours=48, now=None):
        captured["ccys"] = set(currencies)
        return {"events": [], "nearest": None, "stale": False, "source": None}
    out = r.scan(mapping, 1, 50.0, fetch=lambda a, i, n: _bars(40),
                 assets=["USDJPY", "XAUUSD"], news_fn=fake_news)
    assert "JPY" not in captured["ccys"]
    assert captured["ccys"] == {"USD"}


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
