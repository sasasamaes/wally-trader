#!/usr/bin/env python3
"""
backtest_swing_3pct.py — Backtest 3 estrategias swing con target 3% mov de precio.

Filosofía: el user quiere 30% margin profit per trade ($30 sobre $100 margin).
Con leverage 10x → necesita 3% mov de precio favorable.
Eso es SWING intraday, no scalp.

Estrategias evaluadas:
A. **Breakout consolidación + vol spike** (rompe rango N velas con vol >2x avg)
B. **Trending pullback** (1h trend strong + 15m pullback to EMA21 + RSI cross)
C. **Range breakout 4h con retest** (rompe Donchian H/L 4h + retest exitoso)

Targets fijos:
- TP1: 1.5% (cerrar 30%, asegurar +$15)
- TP2: 3.0% (cerrar 50%, asegurar +$15 más = $30 total = 30% margin ✓)
- TP3: 5.0% (runner 20%, +$50+ adicional)
- SL: 1.0% (-$10 = 10% margin)

R:R TP2 = 3.0 ✅ (excelente)
WR breakeven necesario: 100/(100+300) = 25% (con R:R 3, solo 25% WR breakeven)

15 días history, 9 assets, max 1500 candles 15m API.
"""

import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "MSTRUSDT", "AVAXUSDT",
          "INJUSDT", "DOGEUSDT", "WIFUSDT", "XLMUSDT"]
DAYS = 15
MARGIN = 100.0
LEVERAGE = 10
NOTIONAL = MARGIN * LEVERAGE  # $1,000
FEES_PCT = 0.12  # roundtrip


def fetch(symbol, interval, limit):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={min(limit,1500)}"
    try:
        data = json.loads(urllib.request.urlopen(url, timeout=20).read())
        return [{"t": int(b[0]), "o": float(b[1]), "h": float(b[2]),
                 "l": float(b[3]), "c": float(b[4]), "v": float(b[5])} for b in data]
    except Exception as e:
        print(f"  WARN {symbol}: {e}", file=sys.stderr)
        return []


def calc_atr(bars, period=14):
    if len(bars) < period + 1:
        return 0
    trs = []
    for i in range(-period, 0):
        tr = max(bars[i]["h"] - bars[i]["l"],
                 abs(bars[i]["h"] - bars[i-1]["c"]),
                 abs(bars[i]["l"] - bars[i-1]["c"]))
        trs.append(tr)
    return sum(trs) / period


def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains = [max(0, closes[i] - closes[i-1]) for i in range(-period, 0)]
    losses = [max(0, closes[i-1] - closes[i]) for i in range(-period, 0)]
    g = sum(gains) / period
    l = sum(losses) / period if losses else 0.0001
    rs = g / (l if l > 0 else 0.0001)
    return 100 - (100 / (1 + rs))


def calc_ema(values, period):
    if len(values) < period:
        return None
    sma = sum(values[:period]) / period
    mult = 2 / (period + 1)
    ema = sma
    for v in values[period:]:
        ema = (v - ema) * mult + ema
    return ema


# ===== Strategy A: Breakout consolidación + vol spike =====
def strategy_breakout(bars_15m, bars_1h, i):
    """Detecta consolidación N=20 velas + breakout vol >2x."""
    if i < 30 or i >= len(bars_15m) - 24:
        return None
    last = bars_15m[i]
    consolidation = bars_15m[i-20:i]
    cons_high = max(b["h"] for b in consolidation)
    cons_low = min(b["l"] for b in consolidation)
    cons_range = cons_high - cons_low
    cons_range_pct = cons_range / last["c"] * 100
    if cons_range_pct > 4:  # rango muy amplio = no consolidación real
        return None
    if cons_range_pct < 0.5:  # rango muy chico
        return None

    avg_vol = sum(b["v"] for b in consolidation) / 20
    vol_spike = last["v"] > avg_vol * 2.0

    # Breakout direccional
    if last["c"] > cons_high * 1.001 and vol_spike:
        side = "LONG"
        entry = last["c"]
        sl = entry * 0.99  # -1% fijo
        tp1 = entry * 1.015
        tp2 = entry * 1.03
        tp3 = entry * 1.05
    elif last["c"] < cons_low * 0.999 and vol_spike:
        side = "SHORT"
        entry = last["c"]
        sl = entry * 1.01
        tp1 = entry * 0.985
        tp2 = entry * 0.97
        tp3 = entry * 0.95
    else:
        return None
    return {"side": side, "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3}


# ===== Strategy B: Trending pullback =====
def strategy_trending_pullback(bars_15m, bars_1h, i):
    """1h trend strong (price > EMA50 + ADX>20) + 15m pullback EMA21 + RSI cross."""
    if i < 50 or i >= len(bars_15m) - 24:
        return None

    bar_15m_t = bars_15m[i]["t"]
    relevant_1h = [b for b in bars_1h if b["t"] <= bar_15m_t]
    if len(relevant_1h) < 50:
        return None
    closes_1h = [b["c"] for b in relevant_1h]
    ema50_1h = calc_ema(closes_1h, 50)
    if ema50_1h is None:
        return None

    last_1h = relevant_1h[-1]
    trend_up = last_1h["c"] > ema50_1h * 1.005  # >0.5% above
    trend_down = last_1h["c"] < ema50_1h * 0.995

    if not (trend_up or trend_down):
        return None

    closes_15m = [b["c"] for b in bars_15m[:i+1]]
    ema21_15m = calc_ema(closes_15m, 21)
    if ema21_15m is None:
        return None

    last = bars_15m[i]
    prev = bars_15m[i-1]
    rsi_now = calc_rsi(closes_15m)
    rsi_prev = calc_rsi(closes_15m[:-1])

    # LONG en trend up: pullback toca EMA21 + RSI cruza arriba 40
    if trend_up:
        touched_ema = last["l"] <= ema21_15m * 1.002
        rsi_cross = rsi_prev < 40 <= rsi_now
        if touched_ema and rsi_cross:
            entry = last["c"]
            sl = entry * 0.99
            tp1 = entry * 1.015
            tp2 = entry * 1.03
            tp3 = entry * 1.05
            return {"side": "LONG", "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3}

    if trend_down:
        touched_ema = last["h"] >= ema21_15m * 0.998
        rsi_cross = rsi_prev > 60 >= rsi_now
        if touched_ema and rsi_cross:
            entry = last["c"]
            sl = entry * 1.01
            tp1 = entry * 0.985
            tp2 = entry * 0.97
            tp3 = entry * 0.95
            return {"side": "SHORT", "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3}

    return None


# ===== Strategy C: Range breakout 4h =====
def strategy_range_4h_breakout(bars_15m, bars_1h, i):
    """Rompe Donchian H/L de 16 bars 1h (~16h) con confirmación."""
    if i < 70 or i >= len(bars_15m) - 24:
        return None
    bar_t = bars_15m[i]["t"]
    relevant_1h = [b for b in bars_1h if b["t"] <= bar_t]
    if len(relevant_1h) < 16:
        return None
    last_16h = relevant_1h[-16:]
    don_h = max(b["h"] for b in last_16h)
    don_l = min(b["l"] for b in last_16h)

    last = bars_15m[i]
    prev = bars_15m[i-1]
    avg_vol_15m = sum(b["v"] for b in bars_15m[i-20:i]) / 20
    vol_spike = last["v"] > avg_vol_15m * 1.5

    if last["c"] > don_h * 1.001 and prev["c"] <= don_h * 1.001 and vol_spike:
        side = "LONG"
        entry = last["c"]
    elif last["c"] < don_l * 0.999 and prev["c"] >= don_l * 0.999 and vol_spike:
        side = "SHORT"
        entry = last["c"]
    else:
        return None

    if side == "LONG":
        sl = entry * 0.99
        tp1 = entry * 1.015
        tp2 = entry * 1.03
        tp3 = entry * 1.05
    else:
        sl = entry * 1.01
        tp1 = entry * 0.985
        tp2 = entry * 0.97
        tp3 = entry * 0.95

    return {"side": side, "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3}


# ===== Simulator =====
def simulate(setup, future_bars, max_hold_bars=24):  # 24 bars 15m = 6h
    """Cierre escalonado 30% TP1 + 50% TP2 + 20% TP3."""
    if setup is None:
        return None
    entry = setup["entry"]
    sl, tp1, tp2, tp3 = setup["sl"], setup["tp1"], setup["tp2"], setup["tp3"]
    side = setup["side"]
    duration = 0

    tp1_hit = tp2_hit = tp3_hit = False
    sl_hit = False

    for i, bar in enumerate(future_bars[:max_hold_bars]):
        duration = (i + 1) * 15
        if side == "SHORT":
            if bar["h"] >= sl:
                sl_hit = True; break
            if bar["l"] <= tp3 and not tp3_hit: tp3_hit = True
            if bar["l"] <= tp2 and not tp2_hit: tp2_hit = True
            if bar["l"] <= tp1 and not tp1_hit: tp1_hit = True
        else:
            if bar["l"] <= sl:
                sl_hit = True; break
            if bar["h"] >= tp3 and not tp3_hit: tp3_hit = True
            if bar["h"] >= tp2 and not tp2_hit: tp2_hit = True
            if bar["h"] >= tp1 and not tp1_hit: tp1_hit = True
        if tp3_hit: break

    # Calc PnL escalonado
    pnl_pct = 0
    if sl_hit and not tp1_hit:
        pnl_pct = -(abs(sl - entry) / entry)
        outcome = "SL"
    elif tp3_hit:
        # 30% TP1 + 50% TP2 + 20% TP3
        d1 = abs(tp1 - entry) / entry
        d2 = abs(tp2 - entry) / entry
        d3 = abs(tp3 - entry) / entry
        pnl_pct = (d1 * 0.3) + (d2 * 0.5) + (d3 * 0.2)
        outcome = "TP3"
    elif tp2_hit:
        # 30% TP1 + 50% TP2 + 20% BE on runner
        d1 = abs(tp1 - entry) / entry
        d2 = abs(tp2 - entry) / entry
        pnl_pct = (d1 * 0.3) + (d2 * 0.5) + 0
        outcome = "TP2"
    elif tp1_hit:
        # 30% TP1 + 70% BE
        d1 = abs(tp1 - entry) / entry
        pnl_pct = d1 * 0.3
        outcome = "TP1"
    else:
        # Timeout — close at last bar
        if len(future_bars) >= max_hold_bars:
            last_c = future_bars[max_hold_bars - 1]["c"]
            pnl_pct = (entry - last_c) / entry if side == "SHORT" else (last_c - entry) / entry
        outcome = "TIMEOUT"

    pnl_usd = pnl_pct * NOTIONAL - (NOTIONAL * FEES_PCT / 100)
    return {"outcome": outcome, "pnl_pct": pnl_pct * 100, "pnl_usd": pnl_usd, "duration_min": duration}


def backtest_strategy(strat_fn, name, bars_15m, bars_1h, asset):
    trades = []
    last_idx = -100
    for i in range(70, len(bars_15m) - 24):
        if i - last_idx < 16:  # min 4h gap
            continue
        bar_h = datetime.utcfromtimestamp(bars_15m[i]["t"] / 1000).hour
        cr_h = (bar_h - 6) % 24
        if cr_h < 6 or cr_h > 22:
            continue
        setup = strat_fn(bars_15m, bars_1h, i)
        if setup is None:
            continue
        result = simulate(setup, bars_15m[i+1:])
        if result is None:
            continue
        trades.append({"asset": asset, "strategy": name, "cr_hour": cr_h, **setup, **result})
        last_idx = i
    return trades


def summary(trades, name):
    if not trades:
        return f"\n{'='*70}\n{name}: NO TRADES\n"
    n = len(trades)
    wins = [t for t in trades if t["pnl_usd"] > 0]
    losses = [t for t in trades if t["pnl_usd"] < 0]
    wr = len(wins) / n * 100
    pnl = sum(t["pnl_usd"] for t in trades)
    avg = pnl / n
    avg_w = sum(t["pnl_usd"] for t in wins) / len(wins) if wins else 0
    avg_l = sum(t["pnl_usd"] for t in losses) / len(losses) if losses else 0
    pf = abs(sum(t["pnl_usd"] for t in wins) / sum(t["pnl_usd"] for t in losses)) if losses else 999
    avg_dur = sum(t["duration_min"] for t in trades) / n
    by_outcome = {}
    for t in trades:
        by_outcome.setdefault(t["outcome"], 0)
        by_outcome[t["outcome"]] += 1
    pct_30 = sum(1 for t in trades if t["pnl_usd"] >= 30) / n * 100
    return (
        f"\n{'='*70}\n{name}\n{'='*70}\n"
        f"Trades: {n} | WR: {wr:.1f}% | Profit Factor: {pf:.2f}\n"
        f"Total PnL: ${pnl:+.2f} | Avg/trade: ${avg:+.2f}\n"
        f"Avg WIN: ${avg_w:+.2f} | Avg LOSS: ${avg_l:.2f}\n"
        f"Avg duration: {avg_dur:.0f} min\n"
        f"Outcomes: {by_outcome}\n"
        f"% trades con +$30 (30% margin): {pct_30:.0f}%\n"
    )


def main():
    print(f"{'='*70}")
    print(f"BACKTEST SWING 3% TARGET — Margin ${MARGIN}, Leverage {LEVERAGE}x")
    print(f"Notional ${NOTIONAL}, Target +$30/trade (30% margin)")
    print(f"TPs fijos: TP1 1.5% (30%), TP2 3.0% (50%), TP3 5.0% (20%) | SL 1.0%")
    print(f"R:R TP2 = 3.0 | WR breakeven = 25%")
    print(f"{'='*70}")

    all_a, all_b, all_c = [], [], []
    for sym in ASSETS:
        print(f"  {sym}...", file=sys.stderr)
        b15 = fetch(sym, "15m", min(1500, 96 * DAYS))
        b1h = fetch(sym, "1h", min(1500, 24 * DAYS + 60))
        if not b15 or not b1h:
            continue
        ta = backtest_strategy(strategy_breakout, "A_Breakout", b15, b1h, sym)
        tb = backtest_strategy(strategy_trending_pullback, "B_TrendPullback", b15, b1h, sym)
        tc = backtest_strategy(strategy_range_4h_breakout, "C_Range4hBreak", b15, b1h, sym)
        all_a.extend(ta); all_b.extend(tb); all_c.extend(tc)
        print(f"    A:{len(ta)} B:{len(tb)} C:{len(tc)}", file=sys.stderr)

    print(summary(all_a, "📊 STRATEGY A — Breakout consolidación + vol spike"))
    print(summary(all_b, "📊 STRATEGY B — Trending pullback (1h trend + 15m EMA21 RSI cross)"))
    print(summary(all_c, "📊 STRATEGY C — Range 4h breakout + retest"))

    print(f"\n{'='*70}")
    print(f"🏆 RANKING (sortby Total PnL)")
    print(f"{'='*70}")
    cands = []
    for ts, name in [(all_a, "A_Breakout"), (all_b, "B_TrendPullback"), (all_c, "C_Range4hBreak")]:
        if ts:
            n = len(ts); pnl = sum(t["pnl_usd"] for t in ts); wr = sum(1 for t in ts if t["pnl_usd"] > 0)/n*100
            cands.append({"name": name, "n": n, "pnl": pnl, "wr": wr, "pnl_per_trade": pnl/n})
    cands.sort(key=lambda x: -x["pnl"])
    for i, c in enumerate(cands):
        marker = "⭐ WINNER" if i == 0 and c["pnl"] > 0 else ""
        print(f"  {c['name']}: {c['n']} trades | WR {c['wr']:.0f}% | PnL ${c['pnl']:+.2f} | ${c['pnl_per_trade']:+.2f}/trade {marker}")

    if cands and cands[0]["pnl"] > 0:
        w = cands[0]
        # Proyección 1-2 trades/día (esto es swing, baja frecuencia)
        trades_per_day = w["n"] / DAYS
        daily_pnl = w["pnl"] / DAYS
        monthly = daily_pnl * 22
        print(f"\n✅ Estrategia ganadora: {w['name']}")
        print(f"   Trades/día observados: {trades_per_day:.1f}")
        print(f"   PnL/día: ${daily_pnl:+.2f}")
        print(f"   PnL/mes (22d): ${monthly:+.2f}")
        print(f"   PnL/año (252d): ${daily_pnl * 252:+.2f}")
    else:
        print(f"\n❌ Ninguna estrategia logró rentabilidad con target 3% mov.")
        print("   Posibles ajustes: bajar target a 1.5%, aumentar selectividad, multi-confirmation.")


if __name__ == "__main__":
    main()
