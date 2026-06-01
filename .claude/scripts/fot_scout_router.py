#!/usr/bin/env python3
"""
fot_scout_router.py — Router regime-aware multi-estrategia para el profile fotmarkets.

Escanea los 8 activos del universo fotmarkets y, POR CADA ACTIVO:
1. Pull data (5m + 15m + 1h) — Binance para BTC/ETH, yfinance para FX/metales/índices.
2. Clasifica el régimen (ADX 1h + overlay VOLATILE por spike de ATR 5m).
3. Selecciona la estrategia ganadora de ese régimen (fot_strategy_mapping.json).
4. Evalúa el setup con la estrategia matcheada.
5. Scorea 0-100 + aplica edge-gate honesto (solo Mean Reversion puede llegar a APPROVED;
   las de tendencia se capan a TENTATIVE con label "⚠️ edge no validado").
6. Construye entry/SL/TP + sizing phase-aware.
7. Rankea y decide (WAIT honesto si nada tiene edge).

HONESTIDAD (backtest 2026-05-31): solo MR sobrevive el spread CFD bonus. Breakout/MA-cross/
pullback dieron PF ~0.9-1.07 → edge WEAK, nunca recomendados como GO por default.

Determinista, importable y sin dependencia de MCP → corre en segundos y es testeable.

Uso CLI:
    .claude/scripts/.venv/bin/python .claude/scripts/fot_scout_router.py --json
    .claude/scripts/.venv/bin/python .claude/scripts/fot_scout_router.py --show-all
    .claude/scripts/.venv/bin/python .claude/scripts/fot_scout_router.py --asset XAUUSD
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_SHARED = HERE.parent.parent / "shared" / "wally_core" / "src"
if _SHARED.exists() and str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

# Reusables del proyecto (no reinventar)
from wally_core.regime import compute_adx, label_regime, RegimeLabel  # noqa: E402
from wally_core.validate import validate_setup, Side  # noqa: E402
from wally_core.hunt import score_asset  # noqa: E402
from wally_core.multifactor import composite_score  # noqa: E402
from wally_core.macro import upcoming_relevant  # noqa: E402

import per_asset_backtest as pab  # fetch_binance_klines, fetch_yfinance, atr, donchian, rsi  # noqa: E402
from macross import detect_cross  # noqa: E402


MAPPING_PATH = HERE / "fot_strategy_mapping.json"

# Universo fotmarkets (mirror de config.md assets_universe)
UNIVERSE = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "NAS100", "SPX500", "BTCUSD", "ETHUSD"]

# Override consciente 2026-05-31 (ver config.md phase_1.allowed_assets).
# Mirror de config.md — fuente de verdad humana en config.md, esta es la del router.
PHASE_ALLOWED = {
    1: ["EURUSD", "XAUUSD", "BTCUSD", "ETHUSD"],
    2: ["EURUSD", "USDJPY", "XAUUSD", "NAS100", "BTCUSD", "ETHUSD"],
    3: "ALL",
}

# Risk % y TP R-multiple por fase (mirror config.md)
PHASE_RISK_PCT = {1: 1.0, 2: 2.0, 3: 2.0}
PHASE_TP_R = {1: 2.0, 2: 2.0, 3: 2.5}

# SL floor por activo (mirror config.md strategy.min_sl_pips), en "pips" del activo
MIN_SL_PIPS = {
    "EURUSD": 8, "GBPUSD": 10, "USDJPY": 10, "XAUUSD": 20,
    "NAS100": 25, "SPX500": 4, "BTCUSD": 50, "ETHUSD": 40,
}

# Tamaño de "pip" en unidades de precio (para convertir distancia → pips)
PIP_SIZE = {
    "EURUSD": 0.0001, "GBPUSD": 0.0001, "USDJPY": 0.01, "XAUUSD": 0.1,
    "NAS100": 1.0, "SPX500": 1.0, "BTCUSD": 1.0, "ETHUSD": 0.1,
}

# Valor USD por pip por 0.01 lote — APROXIMADO, validar en MT5 Specification del broker.
PIP_VALUE_PER_001_LOT = {
    "EURUSD": 0.10, "GBPUSD": 0.10, "USDJPY": 0.10, "XAUUSD": 0.10,
    "NAS100": 0.01, "SPX500": 0.01, "BTCUSD": 0.01, "ETHUSD": 0.01,
}

# Símbolos TV (OANDA/Binance) para que el agente refine el quote live
TV_SYMBOL = {
    "EURUSD": "OANDA:EURUSD", "GBPUSD": "OANDA:GBPUSD", "USDJPY": "OANDA:USDJPY",
    "XAUUSD": "OANDA:XAUUSD", "NAS100": "OANDA:NAS100USD", "SPX500": "OANDA:SPX500USD",
    "BTCUSD": "BINANCE:BTCUSDT", "ETHUSD": "BINANCE:ETHUSDT",
}

# Divisas que mueven cada activo (para filtrar noticias FF relevantes).
ASSET_CURRENCIES = {
    "EURUSD": ("EUR", "USD"), "GBPUSD": ("GBP", "USD"), "USDJPY": ("USD", "JPY"),
    "XAUUSD": ("USD",), "NAS100": ("USD",), "SPX500": ("USD",),
    "BTCUSD": ("USD",), "ETHUSD": ("USD",),
}

GOAL_USD = 500.0

# Activos con data real-time (Binance) vs delayed ~15min (yfinance)
_REALTIME = {"BTCUSD", "ETHUSD"}


# ── Data layer ──────────────────────────────────────────────────────────────

def fetch_bars(asset: str, interval: str, n: int) -> list[dict]:
    """Pull OHLCV en formato o/h/l/c/v (estilo per_asset_backtest).

    Binance para BTC/ETH (real-time), yfinance para el resto (delayed ~15min).
    """
    if asset == "BTCUSD":
        return pab.fetch_binance_klines("BTCUSDT", interval, n)
    if asset == "ETHUSD":
        return pab.fetch_binance_klines("ETHUSDT", interval, n)
    return pab.fetch_yfinance(asset, interval, n)


def _to_wally(bars: list[dict]) -> list[dict]:
    """Remap o/h/l/c/v → open/high/low/close/volume (lo que esperan wally_core fns)."""
    return [
        {
            "open": float(b["o"]), "high": float(b["h"]), "low": float(b["l"]),
            "close": float(b["c"]), "volume": float(b.get("v", 0) or 0),
        }
        for b in bars
    ]


# ── Regime ──────────────────────────────────────────────────────────────────

def detect_volatile(bars5m: list[dict], atr_len: int = 14, lookback: int = 50,
                    mult: float = 2.0) -> bool:
    """Overlay VOLATILE (strategy.md hard-stop #1): ATR actual > mult × media de las
    últimas `lookback` ATR → régimen volátil, no operar. Local al router para no tocar
    el wally_core.regime compartido."""
    atrs = [a for a in pab.atr(bars5m, atr_len) if a is not None]
    if len(atrs) < lookback + 1:
        return False
    last = atrs[-1]
    mean_prev = sum(atrs[-(lookback + 1):-1]) / lookback
    return mean_prev > 0 and last > mult * mean_prev


def detect_regime(bars1h: list[dict], bars5m: list[dict]) -> str:
    """Régimen del activo: ADX(1h) + overlay VOLATILE de ATR(5m)."""
    if detect_volatile(bars5m):
        return RegimeLabel.VOLATILE.value
    w1h = _to_wally(bars1h)
    adx = compute_adx(w1h, 14)  # raises if <28 bars
    return label_regime(adx["adx"], adx["plus_di"], adx["minus_di"]).value


# ── Scoring ───────────────────────────────────────────────────────────────────

def _rsi_last(bars: list[dict], length: int = 14) -> float:
    vals = pab.rsi([float(b["c"]) for b in bars], length)
    for v in reversed(vals):
        if v is not None:
            return float(v)
    return 50.0


def _score_mr(asset: str, bars5m: list[dict], bars15m: list[dict], mapping: dict) -> int:
    """Score 0-100 para un trigger Mean Reversion (apropiado a reversión, no a momentum)."""
    score = 60  # base por un trigger MR de 4 filtros válido
    rsi = _rsi_last(bars5m)
    if rsi < 30 or rsi > 70:
        score += 15
    elif rsi < 33 or rsi > 67:
        score += 8
    # Calidad por multifactor (volatilidad: calmo suma, chop resta)
    try:
        card = score_asset(asset, _to_wally(bars15m), RegimeLabel.RANGE_CHOP.value)
        score += round((card.volatility - 50) * 0.2)
    except ValueError:
        pass
    edge = mapping.get("per_asset_edge", {}).get(asset, {}).get("RANGE_CHOP", {})
    if edge.get("expectancy_R", 0) >= 0.30:
        score += 10
    if edge.get("oos") == "WARN":
        score -= mapping.get("oos_warn_penalty", 10)
    elif edge.get("oos") == "FAIL":
        score -= mapping.get("oos_warn_penalty", 10) * 2
    return max(0, min(100, score))


def _score_trend(asset: str, bars15m: list[dict], mapping: dict) -> int:
    """Score 0-100 para setup de tendencia (solo display — capado a TENTATIVE)."""
    try:
        base = composite_score(asset, _to_wally(bars15m))
    except ValueError:
        base = 50
    return max(0, min(100, base - mapping.get("trend_penalty", 15)))


# ── Sizing / setup ─────────────────────────────────────────────────────────────

def _sl_distance(asset: str, bars5m: list[dict], atr_len: int = 14, mult: float = 1.2) -> float:
    """SL distance en precio: max(ATR×mult, floor por activo)."""
    atrs = [a for a in pab.atr(bars5m, atr_len) if a is not None]
    atr_val = atrs[-1] if atrs else 0.0
    floor_price = MIN_SL_PIPS[asset] * PIP_SIZE[asset]
    return max(atr_val * mult, floor_price)


def _size_lots(asset: str, capital: float, phase: int, sl_dist: float) -> float:
    """Lotaje phase-aware (floored a 0.01). APROXIMADO — validar pip value en MT5."""
    risk_usd = capital * PHASE_RISK_PCT[phase] / 100.0
    sl_pips = sl_dist / PIP_SIZE[asset]
    pip_val = PIP_VALUE_PER_001_LOT[asset]
    if sl_pips <= 0 or pip_val <= 0:
        return 0.0
    lots_001_units = risk_usd / (sl_pips * pip_val)  # en unidades de 0.01 lote
    lots = lots_001_units * 0.01
    return math.floor(lots * 100) / 100.0


def _goal_progress(capital: float, phase: int) -> dict:
    next_threshold = {1: 100, 2: 300, 3: None}[phase]
    return {
        "capital": round(capital, 2),
        "goal": GOAL_USD,
        "pct": round(capital / GOAL_USD * 100, 1),
        "phase": phase,
        "next_threshold": next_threshold,
        "to_next": round(next_threshold - capital, 2) if next_threshold else None,
    }


# ── Evaluación por activo ──────────────────────────────────────────────────────

def evaluate_asset(asset: str, mapping: dict, phase: int, capital: float,
                   bars5m: list[dict], bars15m: list[dict], bars1h: list[dict],
                   experimental_trend: bool = False) -> dict:
    """Evalúa un activo y devuelve un candidate dict con status + (si aplica) setup."""
    allowed = PHASE_ALLOWED[phase]
    unlocked = (allowed == "ALL") or (asset in allowed)
    base = {"asset": asset, "tv_symbol": TV_SYMBOL.get(asset, asset), "unlocked": unlocked,
            "data_realtime": asset in _REALTIME}

    # Data suficiente?
    min_bars = max(28, 21, 30)  # ADX(28), validate_setup(21), score_asset(30)
    if len(bars5m) < min_bars or len(bars15m) < 30 or len(bars1h) < 28:
        return {**base, "status": "INSUFFICIENT_DATA",
                "reason": f"bars 5m={len(bars5m)} 15m={len(bars15m)} 1h={len(bars1h)}"}

    try:
        regime = detect_regime(bars1h, bars5m)
    except ValueError as e:
        return {**base, "status": "INSUFFICIENT_DATA", "reason": str(e)}
    base["regime"] = regime

    cell = mapping["regime_strategy"].get(regime, {"strategy": "stand_aside", "edge": "NONE",
                                                   "max_status": "STAND_ASIDE"})
    strat, edge = cell["strategy"], cell["edge"]
    base["strategy"] = strat
    base["edge"] = edge

    if strat == "stand_aside":
        return {**base, "status": "STAND_ASIDE",
                "reason": f"régimen {regime} sin estrategia con edge (backtest)"}

    # Eval del setup según estrategia
    wally5m = _to_wally(bars5m)
    side = None
    if strat == "mean_reversion":
        res_long = validate_setup(wally5m, Side.LONG, 15)
        res_short = validate_setup(wally5m, Side.SHORT, 15)
        if res_long.go:
            side = "LONG"
        elif res_short.go:
            side = "SHORT"
        if side is None:
            return {**base, "status": "NO_SETUP",
                    "reason": "MR sin trigger (4 filtros no alineados)"}
        score = _score_mr(asset, bars5m, bars15m, mapping)
    elif strat == "ma_cross":
        sig = detect_cross([float(b["c"]) for b in bars15m], 9, 21)
        if sig["signal"] not in ("LONG", "SHORT"):
            return {**base, "status": "NO_SETUP", "reason": f"ma_cross: {sig['signal']}"}
        side = sig["signal"]
        score = _score_trend(asset, bars15m, mapping)
    elif strat == "donchian_breakout":
        hi, lo = pab.donchian(bars15m, 20)
        last = bars15m[-1]
        if hi[-1] is not None and last["c"] > hi[-1] * 0.999:
            side = "LONG"
        elif lo[-1] is not None and last["c"] < lo[-1] * 1.001:
            side = "SHORT"
        if side is None:
            return {**base, "status": "NO_SETUP", "reason": "sin ruptura Donchian(20)"}
        score = _score_trend(asset, bars15m, mapping)
    else:
        return {**base, "status": "NO_SETUP", "reason": f"estrategia desconocida {strat}"}

    base["side"] = side
    base["score"] = score

    # Construcción del setup (entry/SL/TP/sizing)
    entry = float(bars5m[-1]["c"])
    sl_dist = _sl_distance(asset, bars5m)
    tp_r = PHASE_TP_R[phase]
    if side == "LONG":
        sl = entry - sl_dist
        tp = entry + sl_dist * tp_r
    else:
        sl = entry + sl_dist
        tp = entry - sl_dist * tp_r
    lots = _size_lots(asset, capital, phase, sl_dist)
    setup = {
        "entry": round(entry, 5), "sl": round(sl, 5), "tp": round(tp, 5),
        "rr": tp_r, "sl_distance": round(sl_dist, 5),
        "sl_pips": round(sl_dist / PIP_SIZE[asset], 1),
        "lots": lots, "risk_usd": round(capital * PHASE_RISK_PCT[phase] / 100.0, 2),
        "risk_pct": PHASE_RISK_PCT[phase],
        "sizing_caveat": "lots APROXIMADO — validar pip value en MT5 Specification",
    }
    base["setup"] = setup

    if lots < 0.01:
        return {**base, "status": "UNTRADEABLE_SIZE",
                "reason": f"lots {lots} < 0.01 min (risk ${setup['risk_usd']} muy chico para el SL)"}

    # Edge-gate honesto
    threshold = mapping.get("global_threshold", 70)
    oos = mapping.get("per_asset_edge", {}).get(asset, {}).get(regime, {}).get("oos")
    if oos:
        base["oos"] = oos

    if edge == "VALIDATED":
        if score >= threshold:
            base["status"] = "APPROVED" if unlocked else "OVERRIDE_LOCKED"
            if not unlocked:
                base["reason"] = f"setup válido pero {asset} bloqueado en fase {phase}"
        else:
            base["status"] = "BELOW_THRESHOLD"
            base["reason"] = f"score {score} < umbral {threshold}"
    else:  # WEAK / NONE → nunca APPROVED
        base["status"] = "TENTATIVE"
        base["label"] = "⚠️ edge no validado (backtest PF ~0.9-1.07, muere al spread)"
        if not experimental_trend:
            base["reason"] = "estrategia de tendencia sin edge validado — solo informativo"
    return base


# ── Scan completo ──────────────────────────────────────────────────────────────

def load_mapping(path: Path | str = MAPPING_PATH) -> dict:
    with open(path) as f:
        return json.load(f)


def scan(mapping: dict, phase: int, capital: float, *, fetch=fetch_bars,
         assets: list[str] | None = None, experimental_trend: bool = False,
         news_fn=upcoming_relevant) -> dict:
    """Escanea el universo y devuelve el resultado estructurado."""
    assets = assets or UNIVERSE
    experimental_trend = experimental_trend or mapping.get("experimental_trend", False)
    candidates: list[dict] = []
    for asset in assets:
        try:
            b5 = fetch(asset, "5m", 120)
            b15 = fetch(asset, "15m", 120)
            b1h = fetch(asset, "1h", 80)
        except Exception as e:  # noqa: BLE001 — un fetch que falla no debe romper el scan
            candidates.append({"asset": asset, "status": "FETCH_ERROR", "reason": str(e)})
            continue
        candidates.append(
            evaluate_asset(asset, mapping, phase, capital, b5, b15, b1h, experimental_trend)
        )

    def _bucket(s):
        return [c for c in candidates if c.get("status") == s]

    approved = sorted(_bucket("APPROVED"),
                      key=lambda c: (c["score"],
                                     mapping.get("per_asset_edge", {})
                                     .get(c["asset"], {}).get(c.get("regime", ""), {})
                                     .get("expectancy_R", 0)),
                      reverse=True)
    override = sorted(_bucket("OVERRIDE_LOCKED"), key=lambda c: c["score"], reverse=True)
    tentative = sorted(_bucket("TENTATIVE"), key=lambda c: c.get("score", 0), reverse=True)

    status = "APPROVED" if approved else ("OVERRIDE_AVAILABLE" if override else "WAIT")

    # Noticias FF relevantes: divisas de los activos DESBLOQUEADOS que se escanean.
    allowed = PHASE_ALLOWED[phase]
    ccys: set[str] = set()
    for a in assets:
        if allowed == "ALL" or a in allowed:
            ccys.update(ASSET_CURRENCIES.get(a, ("USD",)))
    if not ccys:
        ccys = {"USD"}  # USD mueve todo el universo (oro/índices/cripto/EURUSD)
    news = news_fn(ccys, hours=48)

    return {
        "status": status,
        "phase": phase,
        "capital": capital,
        "goal_progress": _goal_progress(capital, phase),
        "news": news,
        "mapping_version": mapping.get("version"),
        "approved": approved,
        "override_candidates": override,
        "tentative_trend": tentative,
        "below_threshold": _bucket("BELOW_THRESHOLD"),
        "no_setup": _bucket("NO_SETUP"),
        "stand_aside": _bucket("STAND_ASIDE"),
        "untradeable": _bucket("UNTRADEABLE_SIZE"),
        "insufficient_data": _bucket("INSUFFICIENT_DATA") + _bucket("FETCH_ERROR"),
    }


# ── CLI ─────────────────────────────────────────────────────────────────────

def _maybe_reexec_venv():
    venv_python = HERE / ".venv" / "bin" / "python"
    if (venv_python.exists()
            and Path(sys.executable).resolve() != venv_python.resolve()
            and not os.environ.get("WALLY_VENV_REEXEC")):
        os.environ["WALLY_VENV_REEXEC"] = "1"
        os.execv(str(venv_python), [str(venv_python), __file__, *sys.argv[1:]])


def _read_phase_capital() -> tuple[int, float]:
    """Lee fase + capital de fotmarkets_phase.py (subprocess, como fotmarkets_guard)."""
    import subprocess
    py = sys.executable
    phase = int(subprocess.check_output([py, str(HERE / "fotmarkets_phase.py"), "phase"]).strip())
    cap = float(subprocess.check_output([py, str(HERE / "fotmarkets_phase.py"), "capital"]).strip())
    return phase, cap


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="Output JSON crudo")
    ap.add_argument("--show-all", action="store_true", help="Incluye buckets WAIT/STAND_ASIDE")
    ap.add_argument("--asset", help="Escanear un solo activo")
    ap.add_argument("--experimental-trend", action="store_true",
                    help="Sube setups de tendencia a TENTATIVE explícito (sin edge validado)")
    ap.add_argument("--phase", type=int, help="Override fase (test)")
    ap.add_argument("--capital", type=float, help="Override capital (test)")
    args = ap.parse_args()

    mapping = load_mapping()
    if args.phase and args.capital:
        phase, capital = args.phase, args.capital
    else:
        try:
            phase, capital = _read_phase_capital()
        except Exception as e:  # noqa: BLE001
            print(f"ERROR leyendo fase/capital: {e}", file=sys.stderr)
            return 3

    assets = [args.asset] if args.asset else UNIVERSE
    result = scan(mapping, phase, capital, assets=assets,
                  experimental_trend=args.experimental_trend)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0

    # Resumen humano
    gp = result["goal_progress"]
    print(f"📈 ${gp['capital']} / ${gp['goal']} ({gp['pct']}%) — Fase {gp['phase']}"
          + (f", faltan ${gp['to_next']} para fase {gp['phase']+1}" if gp["to_next"] else ""))
    print(f"Status: {result['status']}\n")
    if result["approved"]:
        for c in result["approved"]:
            s = c["setup"]
            print(f"🟢 {c['side']} {c['asset']} (regime {c['regime']}, MR, score {c['score']})")
            print(f"   Entry {s['entry']} | SL {s['sl']} ({s['sl_pips']} pips) | "
                  f"TP {s['tp']} (R:R {s['rr']}) | lots {s['lots']} | risk ${s['risk_usd']}")
    elif result["override_candidates"]:
        print("🔒 Candidatos válidos pero bloqueados en esta fase (requieren override):")
        for c in result["override_candidates"]:
            print(f"   {c['side']} {c['asset']} score {c['score']} — {c.get('reason','')}")
    else:
        print("⏳ WAIT — sin setup con edge validado ahora.")

    if args.show_all:
        for bucket in ("tentative_trend", "below_threshold", "no_setup", "stand_aside",
                       "untradeable", "insufficient_data"):
            for c in result[bucket]:
                tag = c.get("label", c.get("reason", ""))
                print(f"   · [{c['status']}] {c['asset']} {c.get('regime','')} — {tag}")
    return 0


if __name__ == "__main__":
    _maybe_reexec_venv()
    sys.exit(main())
