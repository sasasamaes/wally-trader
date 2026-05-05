#!/usr/bin/env python3
"""
strategy_vwap_mtf.py — Estrategia A ganadora del backtest hourly.

VWAP Reversion + Multi-Timeframe Trend Filter

Lógica:
1. **MTF macro filter (1h):** EMA(50) sobre cierres 1h determina trend macro
   - Precio > EMA50 1h → trend macro UP (solo buscar LONGS contra-trend que reviertan a VWAP)
   - Precio < EMA50 1h → trend macro DOWN (solo buscar SHORTS)
2. **Setup trigger (15m):** precio se aleja >0.8×ATR del VWAP en dirección CONTRA-trend macro
3. **Confirmación RSI:** RSI(14) en extremo (>65 SHORT, <35 LONG)
4. **Targets adaptativos:**
   - SL: 0.5×ATR más allá del extremo
   - TP1: vuelta al VWAP (típico 0.3-0.8% movimiento)
   - TP2: VWAP + 0.5×ATR (continuación)
5. **R:R gate:** TP1/SL ≥ 1.0 (sino no abrir)

Performance backtest (15 días, 9 assets):
- WR 57.1% | Profit Factor 3.31 | Avg duration 34 min
- 7 trades en 15 días = 0.47 trades/día/universo
- En sample backtest fue la única rentable (vs BB Squeeze y ADX Pullback que perdieron)

Filosofía: SELECTIVIDAD > frecuencia. Mejor 4-5 trades/día A-grade que 12 trades B-grade.
"""

import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def fetch_klines(symbol, interval, limit):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={min(limit, 1500)}"
    try:
        data = json.loads(urllib.request.urlopen(url, timeout=15).read())
        return [{"t": int(b[0]), "o": float(b[1]), "h": float(b[2]),
                 "l": float(b[3]), "c": float(b[4]), "v": float(b[5])} for b in data]
    except Exception as e:
        print(f"WARN fetch {symbol}: {e}", file=sys.stderr)
        return []


def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains = [max(0, closes[i] - closes[i - 1]) for i in range(-period, 0)]
    losses = [max(0, closes[i - 1] - closes[i]) for i in range(-period, 0)]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period if losses else 0.0001
    rs = avg_gain / (avg_loss if avg_loss > 0 else 0.0001)
    return 100 - (100 / (1 + rs))


def calc_atr(bars, period=14):
    if len(bars) < period + 1:
        return 0
    trs = []
    for i in range(-period, 0):
        tr = max(
            bars[i]["h"] - bars[i]["l"],
            abs(bars[i]["h"] - bars[i - 1]["c"]),
            abs(bars[i]["l"] - bars[i - 1]["c"]),
        )
        trs.append(tr)
    return sum(trs) / period


def calc_vwap(bars):
    """VWAP rolling — todos los bars del input (simplificado, sin session reset)."""
    cum_pv = 0
    cum_v = 0
    for b in bars:
        typical = (b["h"] + b["l"] + b["c"]) / 3
        cum_pv += typical * b["v"]
        cum_v += b["v"]
    return cum_pv / cum_v if cum_v > 0 else bars[-1]["c"]


def calc_ema(values, period):
    if len(values) < period:
        return None
    sma = sum(values[:period]) / period
    multiplier = 2 / (period + 1)
    ema = sma
    for v in values[period:]:
        ema = (v - ema) * multiplier + ema
    return ema


def evaluate_vwap_mtf(symbol):
    """Evalúa setup actual para 1 asset. Returns dict con setup completo o None."""
    bars_15m = fetch_klines(symbol, "15m", 100)
    bars_1h = fetch_klines(symbol, "1h", 80)

    if len(bars_15m) < 50 or len(bars_1h) < 50:
        return {"asset": symbol, "side": None, "reason": "insufficient_data"}

    closes_15m = [b["c"] for b in bars_15m]
    closes_1h = [b["c"] for b in bars_1h]
    last = bars_15m[-1]
    entry = last["c"]
    atr = calc_atr(bars_15m)
    if atr == 0:
        return {"asset": symbol, "side": None, "reason": "zero_atr"}

    rsi = calc_rsi(closes_15m)
    vwap = calc_vwap(bars_15m[-96:])  # ~24h VWAP
    distance_from_vwap_atr = (entry - vwap) / atr

    # MTF filter
    ema50_1h = calc_ema(closes_1h, 50)
    if ema50_1h is None:
        return {"asset": symbol, "side": None, "reason": "ema_unavailable"}
    macro_trend_up = closes_1h[-1] > ema50_1h

    # Setup detection
    setup = {
        "asset": symbol,
        "entry": entry,
        "atr": round(atr, 4),
        "atr_pct": round(atr / entry * 100, 3),
        "rsi": round(rsi, 1),
        "vwap": round(vwap, 4),
        "distance_from_vwap_atr": round(distance_from_vwap_atr, 2),
        "macro_trend_up": macro_trend_up,
    }

    if macro_trend_up and distance_from_vwap_atr < -0.8 and rsi < 35:
        side = "LONG"
        sl = round(entry - 0.5 * atr, 4)
        tp1 = round(vwap, 4)
        tp2 = round(vwap + 0.5 * atr, 4)
    elif not macro_trend_up and distance_from_vwap_atr > 0.8 and rsi > 65:
        side = "SHORT"
        sl = round(entry + 0.5 * atr, 4)
        tp1 = round(vwap, 4)
        tp2 = round(vwap - 0.5 * atr, 4)
    else:
        setup["side"] = None
        setup["reason"] = "no_setup"
        return setup

    rr_tp1 = abs(tp1 - entry) / abs(sl - entry) if sl != entry else 0
    if rr_tp1 < 1.0:
        setup["side"] = None
        setup["reason"] = f"rr_too_low_{rr_tp1:.2f}"
        return setup

    rr_tp2 = abs(tp2 - entry) / abs(sl - entry)
    setup.update({
        "side": side,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "rr_tp1": round(rr_tp1, 2),
        "rr_tp2": round(rr_tp2, 2),
        "sl_distance_pct": round(abs(sl - entry) / entry * 100, 3),
        "tp1_distance_pct": round(abs(tp1 - entry) / entry * 100, 3),
        "tp2_distance_pct": round(abs(tp2 - entry) / entry * 100, 3),
        "expected_duration_min": "30-45 (median backtest 34min)",
    })
    return setup


def main():
    import argparse
    p = argparse.ArgumentParser(description="VWAP Reversion + MTF Trend Filter scanner")
    p.add_argument("--symbol", help="Single asset (e.g. BTCUSDT). Si omitido, scanea watchlist.")
    p.add_argument("--json", action="store_true")
    p.add_argument("--show-all", action="store_true", help="Mostrar también setups que NO triggean")
    args = p.parse_args()

    if args.symbol:
        result = evaluate_vwap_mtf(args.symbol)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print_setup(result)
        return

    # Scan watchlist
    watchlist = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "MSTRUSDT", "AVAXUSDT",
                 "INJUSDT", "DOGEUSDT", "WIFUSDT", "XLMUSDT"]
    setups = []
    for sym in watchlist:
        s = evaluate_vwap_mtf(sym)
        setups.append(s)

    valid = [s for s in setups if s.get("side")]
    invalid = [s for s in setups if not s.get("side")]

    if args.json:
        print(json.dumps({"valid": valid, "invalid": invalid}, indent=2))
        return

    print(f"\n{'='*70}")
    print(f"VWAP-MTF SCAN — {datetime.now().strftime('%H:%M CR')} — {len(watchlist)} assets")
    print(f"{'='*70}")
    if valid:
        print(f"\n✅ {len(valid)} SETUP(S) VÁLIDO(S):\n")
        for s in valid:
            print_setup(s)
    else:
        print(f"\n⏳ NO hay setups VWAP-MTF válidos ahora ({len(invalid)} assets evaluados sin trigger)")

    if args.show_all:
        print(f"\n{'─'*70}\nAssets sin setup (rejected):\n{'─'*70}")
        for s in invalid:
            print(f"  {s['asset']:14s} reason: {s.get('reason', 'unknown'):30s} "
                  f"RSI {s.get('rsi','-')} | dist VWAP {s.get('distance_from_vwap_atr','-')}σ")


def print_setup(s):
    if not s.get("side"):
        print(f"\n❌ {s['asset']}: {s.get('reason', 'no_setup')}")
        return
    arrow = "🟢 LONG" if s["side"] == "LONG" else "🔴 SHORT"
    print(f"\n{arrow} {s['asset']}")
    print(f"  Entry: {s['entry']} | RSI: {s['rsi']} | distance VWAP: {s['distance_from_vwap_atr']}σ")
    print(f"  SL:  {s['sl']} ({s['sl_distance_pct']}%)")
    print(f"  TP1: {s['tp1']} ({s['tp1_distance_pct']}%) — R:R {s['rr_tp1']}")
    print(f"  TP2: {s['tp2']} ({s['tp2_distance_pct']}%) — R:R {s['rr_tp2']}")
    print(f"  Macro trend (1h EMA50): {'UP' if s['macro_trend_up'] else 'DOWN'} (contra-trend setup)")


if __name__ == "__main__":
    main()
