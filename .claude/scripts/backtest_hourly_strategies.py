#!/usr/bin/env python3
"""
backtest_hourly_strategies.py — Compara 3 estrategias hourly trading en cripto.

Estrategias evaluadas (todas usan SOLO OHLCV de Binance, NO depende de Neptune privado):

A. **VWAP Reversion + MTF Trend Filter** (mi recomendación)
   - 1h EMA(50) determina trend macro
   - 15m: precio se aleja >0.8×ATR de VWAP en dirección CONTRA-trend macro
   - RSI confirma extremo (>70 o <30)
   - TP1: vuelta al VWAP (típico 0.3-0.8%)
   - TP2: 1.5× distance to VWAP
   - SL: 0.5×ATR más allá del extremo

B. **Bollinger Squeeze Breakout**
   - Detect squeeze: BB(20,2) bandwidth < 30% del bandwidth promedio 50 velas
   - Esperar breakout direccional con vol spike >1.5x avg
   - TP1: 2× squeeze height
   - TP2: 3× squeeze height
   - SL: re-entry del squeeze (0.5× squeeze height)

C. **ADX Trend + RSI Pullback**
   - ADX(14) > 25 = trend fuerte (precondición)
   - En trend up (DI+ > DI-): entrar LONG cuando RSI cruza arriba de 40 desde abajo
   - En trend down: entrar SHORT cuando RSI cruza abajo de 60 desde arriba
   - TP1: continuation 1×ATR
   - TP2: 2×ATR
   - SL: 0.7×ATR

Comparativa contra:
- Filosofía bitunix 1trade/h: cierre en 60-90 min max
- Margin $50, leverage 10x = $500 notional
- Fees 0.12% round-trip
- 30 días history Binance Futures
"""

import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ASSETS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "MSTRUSDT", "AVAXUSDT",
    "INJUSDT", "DOGEUSDT", "WIFUSDT", "XLMUSDT",
]

DAYS_HISTORY = 15  # Limitado a 1500 velas 15m API Binance Futures
MARGIN = 50.0
LEVERAGE = 10
FEES_PCT = 0.12  # 0.06% × 2
NOTIONAL = MARGIN * LEVERAGE


# ===== Indicadores =====
def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return [50] * len(closes)
    rsis = [50] * (period)
    gains = [max(0, closes[i] - closes[i - 1]) for i in range(1, period + 1)]
    losses = [max(0, closes[i - 1] - closes[i]) for i in range(1, period + 1)]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    for i in range(period + 1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gain = max(0, diff)
        loss = max(0, -diff)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        rs = avg_gain / (avg_loss if avg_loss > 0 else 0.0001)
        rsis.append(100 - (100 / (1 + rs)))
    return rsis


def calc_ema(values, period):
    if len(values) < period:
        return [None] * len(values)
    ema = [None] * (period - 1)
    sma = sum(values[:period]) / period
    ema.append(sma)
    multiplier = 2 / (period + 1)
    for v in values[period:]:
        ema.append((v - ema[-1]) * multiplier + ema[-1])
    return ema


def calc_atr_series(bars, period=14):
    if len(bars) < period + 1:
        return [0] * len(bars)
    trs = [0]
    for i in range(1, len(bars)):
        tr = max(
            bars[i]["h"] - bars[i]["l"],
            abs(bars[i]["h"] - bars[i - 1]["c"]),
            abs(bars[i]["l"] - bars[i - 1]["c"]),
        )
        trs.append(tr)
    atrs = [0] * period
    atrs.append(sum(trs[1:period + 1]) / period)
    for i in range(period + 1, len(trs)):
        atrs.append((atrs[-1] * (period - 1) + trs[i]) / period)
    return atrs


def calc_vwap_session(bars):
    """VWAP rolling (no session reset, simplificado)."""
    if not bars:
        return []
    vwap = []
    cumulative_pv = 0
    cumulative_v = 0
    for b in bars:
        typical = (b["h"] + b["l"] + b["c"]) / 3
        cumulative_pv += typical * b["v"]
        cumulative_v += b["v"]
        vwap.append(cumulative_pv / cumulative_v if cumulative_v else typical)
    return vwap


def calc_bb_series(closes, period=20, std_mult=2):
    upper, lower, mid = [None] * period, [None] * period, [None] * period
    for i in range(period, len(closes) + 1):
        window = closes[i - period:i]
        m = sum(window) / period
        var = sum((c - m) ** 2 for c in window) / period
        std = var ** 0.5
        upper.append(m + std_mult * std)
        lower.append(m - std_mult * std)
        mid.append(m)
    # Trim to length of closes
    upper = upper[: len(closes)]
    lower = lower[: len(closes)]
    mid = mid[: len(closes)]
    return upper, lower, mid


def calc_adx(bars, period=14):
    """ADX simplificado."""
    if len(bars) < period * 2:
        return [0] * len(bars)
    dms_pos, dms_neg, trs = [], [], []
    for i in range(1, len(bars)):
        up_move = bars[i]["h"] - bars[i - 1]["h"]
        down_move = bars[i - 1]["l"] - bars[i]["l"]
        dms_pos.append(up_move if up_move > down_move and up_move > 0 else 0)
        dms_neg.append(down_move if down_move > up_move and down_move > 0 else 0)
        tr = max(
            bars[i]["h"] - bars[i]["l"],
            abs(bars[i]["h"] - bars[i - 1]["c"]),
            abs(bars[i]["l"] - bars[i - 1]["c"]),
        )
        trs.append(tr)
    # Smoothing
    adx_series = [0]
    di_pos_smooth = sum(dms_pos[:period]) / period
    di_neg_smooth = sum(dms_neg[:period]) / period
    tr_smooth = sum(trs[:period]) / period
    for i in range(period, len(trs)):
        di_pos_smooth = (di_pos_smooth * (period - 1) + dms_pos[i]) / period
        di_neg_smooth = (di_neg_smooth * (period - 1) + dms_neg[i]) / period
        tr_smooth = (tr_smooth * (period - 1) + trs[i]) / period
        di_pos = (di_pos_smooth / tr_smooth) * 100 if tr_smooth else 0
        di_neg = (di_neg_smooth / tr_smooth) * 100 if tr_smooth else 0
        di_sum = di_pos + di_neg
        dx = abs(di_pos - di_neg) / di_sum * 100 if di_sum else 0
        adx_series.append(dx)
    # Pad
    while len(adx_series) < len(bars):
        adx_series.insert(0, 0)
    return adx_series, dms_pos, dms_neg


# ===== Strategies =====
def strategy_a_vwap_reversion(bars_15m, bars_1h, i):
    """A: VWAP Reversion + MTF Trend Filter."""
    if i < 60 or i >= len(bars_15m) - 6:
        return None
    closes = [b["c"] for b in bars_15m[: i + 1]]
    vwap = calc_vwap_session(bars_15m[: i + 1])
    rsis = calc_rsi(closes)
    atrs = calc_atr_series(bars_15m[: i + 1])
    last = bars_15m[i]
    entry = last["c"]
    atr = atrs[-1]
    if atr == 0:
        return None
    vwap_now = vwap[-1]
    distance_from_vwap = (entry - vwap_now) / atr  # in ATR units
    rsi = rsis[-1]

    # MTF filter: 1h EMA(50) trend
    if len(bars_1h) < 60:
        return None
    closes_1h = [b["c"] for b in bars_1h]
    # Find which 1h bar corresponds to i
    bar_15m_time = bars_15m[i]["t"]
    relevant_1h = [b for b in bars_1h if b["t"] <= bar_15m_time]
    if len(relevant_1h) < 50:
        return None
    ema50_1h = calc_ema([b["c"] for b in relevant_1h], 50)
    macro_trend_up = relevant_1h[-1]["c"] > ema50_1h[-1]

    # Setup: precio se alejó >0.8×ATR contra-trend + RSI extremo
    if macro_trend_up and distance_from_vwap < -0.8 and rsi < 35:
        side = "LONG"
        sl = entry - 0.5 * atr
        tp1 = vwap_now
        tp2 = vwap_now + 0.5 * atr
    elif not macro_trend_up and distance_from_vwap > 0.8 and rsi > 65:
        side = "SHORT"
        sl = entry + 0.5 * atr
        tp1 = vwap_now
        tp2 = vwap_now - 0.5 * atr
    else:
        return None

    rr_tp1 = abs(tp1 - entry) / abs(sl - entry)
    if rr_tp1 < 1.0:
        return None

    return {"side": side, "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "atr": atr}


def strategy_b_bb_squeeze(bars_15m, bars_1h, i):
    """B: BB Squeeze Breakout."""
    if i < 70 or i >= len(bars_15m) - 6:
        return None
    closes = [b["c"] for b in bars_15m[: i + 1]]
    upper, lower, mid = calc_bb_series(closes, 20, 2)
    if upper[-1] is None or upper[-50] is None:
        return None
    # Bandwidth actual y promedio
    bw_now = upper[-1] - lower[-1]
    bw_avg = sum(upper[k] - lower[k] for k in range(-50, 0) if upper[k]) / 50
    if bw_avg == 0:
        return None
    squeeze_ratio = bw_now / bw_avg

    if squeeze_ratio > 0.5:  # No squeeze
        return None

    # Detectar breakout direccional últimas 2 velas
    last = bars_15m[i]
    prev = bars_15m[i - 1]
    vol_avg = sum(b["v"] for b in bars_15m[i - 20:i]) / 20
    vol_spike = last["v"] > vol_avg * 1.5

    if last["c"] > upper[-1] and prev["c"] <= upper[-2] and vol_spike:
        side = "LONG"
        squeeze_height = upper[-1] - lower[-1]
        entry = last["c"]
        sl = mid[-1]  # back to middle of squeeze
        tp1 = entry + 2 * squeeze_height
        tp2 = entry + 3 * squeeze_height
    elif last["c"] < lower[-1] and prev["c"] >= lower[-2] and vol_spike:
        side = "SHORT"
        squeeze_height = upper[-1] - lower[-1]
        entry = last["c"]
        sl = mid[-1]
        tp1 = entry - 2 * squeeze_height
        tp2 = entry - 3 * squeeze_height
    else:
        return None

    rr_tp1 = abs(tp1 - entry) / abs(sl - entry)
    if rr_tp1 < 1.5:
        return None

    atrs = calc_atr_series(bars_15m[: i + 1])
    return {"side": side, "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "atr": atrs[-1]}


def strategy_c_adx_pullback(bars_15m, bars_1h, i):
    """C: ADX Trend + RSI Pullback."""
    if i < 50 or i >= len(bars_15m) - 6:
        return None
    bars_window = bars_15m[: i + 1]
    closes = [b["c"] for b in bars_window]
    adx, dm_pos, dm_neg = calc_adx(bars_window)
    rsis = calc_rsi(closes)
    atrs = calc_atr_series(bars_window)

    if adx[-1] < 25:  # No trend fuerte
        return None

    last = bars_15m[i]
    entry = last["c"]
    atr = atrs[-1]
    if atr == 0:
        return None

    # Determinar dirección del trend (DI+ vs DI-)
    if len(dm_pos) >= 14:
        avg_dm_pos = sum(dm_pos[-14:]) / 14
        avg_dm_neg = sum(dm_neg[-14:]) / 14
        trend_up = avg_dm_pos > avg_dm_neg
    else:
        return None

    # Cross detection
    rsi_now = rsis[-1]
    rsi_prev = rsis[-2]

    if trend_up and rsi_prev < 40 <= rsi_now:
        side = "LONG"
        sl = entry - 0.7 * atr
        tp1 = entry + 1.0 * atr
        tp2 = entry + 2.0 * atr
    elif not trend_up and rsi_prev > 60 >= rsi_now:
        side = "SHORT"
        sl = entry + 0.7 * atr
        tp1 = entry - 1.0 * atr
        tp2 = entry - 2.0 * atr
    else:
        return None

    rr_tp1 = abs(tp1 - entry) / abs(sl - entry)
    if rr_tp1 < 1.3:
        return None

    return {"side": side, "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "atr": atr}


# ===== Simular trade =====
def simulate(setup, future_bars, max_hold_bars=6):
    """Simula trade hasta SL/TP/timeout. Cierre escalonado 50/50 en TP1/TP2."""
    if setup is None:
        return None
    entry = setup["entry"]
    sl = setup["sl"]
    tp1 = setup["tp1"]
    tp2 = setup["tp2"]
    side = setup["side"]
    duration = 0
    outcome = "TIMEOUT"
    pnl_pct = 0

    tp1_hit = False
    tp2_hit = False
    for i, bar in enumerate(future_bars[:max_hold_bars]):
        duration = (i + 1) * 15
        if side == "SHORT":
            if bar["h"] >= sl:
                pnl_pct = -(sl - entry) / entry
                outcome = "SL"
                break
            if bar["l"] <= tp2 and not tp2_hit:
                tp2_hit = True
            if bar["l"] <= tp1 and not tp1_hit:
                tp1_hit = True
        else:
            if bar["l"] <= sl:
                pnl_pct = (sl - entry) / entry
                outcome = "SL"
                break
            if bar["h"] >= tp2 and not tp2_hit:
                tp2_hit = True
            if bar["h"] >= tp1 and not tp1_hit:
                tp1_hit = True
        if tp2_hit:
            break
        if tp1_hit:
            outcome = "TP1"

    # Calcular PnL final escalonado
    if outcome == "SL":
        pass  # ya calculado
    elif tp2_hit:
        # 50% TP1 + 50% TP2
        pnl_tp1 = abs(tp1 - entry) / entry
        pnl_tp2 = abs(tp2 - entry) / entry
        pnl_pct = (pnl_tp1 * 0.5) + (pnl_tp2 * 0.5)
        outcome = "TP2"
    elif tp1_hit:
        # 50% TP1 + 50% sigue → asumir BE en runner (DUREX implícito)
        pnl_tp1 = abs(tp1 - entry) / entry
        pnl_pct = pnl_tp1 * 0.5  # +0% on runner = breakeven
        outcome = "TP1"
    else:
        # TIMEOUT — cerrar a precio último bar
        if len(future_bars) >= max_hold_bars:
            last = future_bars[max_hold_bars - 1]["c"]
            if side == "SHORT":
                pnl_pct = (entry - last) / entry
            else:
                pnl_pct = (last - entry) / entry

    pnl_usd = pnl_pct * NOTIONAL - (NOTIONAL * FEES_PCT / 100)
    return {"outcome": outcome, "pnl_pct": pnl_pct * 100, "pnl_usd": pnl_usd, "duration_min": duration}


# ===== Pull data + run =====
def fetch(symbol, interval, limit):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        data = json.loads(urllib.request.urlopen(url, timeout=20).read())
        return [{"t": int(b[0]), "o": float(b[1]), "h": float(b[2]),
                 "l": float(b[3]), "c": float(b[4]), "v": float(b[5])} for b in data]
    except Exception as e:
        print(f"  WARN fetch {symbol}: {e}", file=sys.stderr)
        return []


def backtest_strategy(strat_fn, strat_name, bars_15m, bars_1h, asset):
    trades = []
    last_trade_idx = -100
    for i in range(60, len(bars_15m) - 6):
        # Min 1h gap entre trades
        if i - last_trade_idx < 4:
            continue
        # Ventana operativa CR 06:00-23:00 (UTC = CR + 6)
        bar_hour_utc = datetime.utcfromtimestamp(bars_15m[i]["t"] / 1000).hour
        cr_hour = (bar_hour_utc - 6) % 24
        if cr_hour < 6 or cr_hour > 22:
            continue
        setup = strat_fn(bars_15m, bars_1h, i)
        if setup is None:
            continue
        result = simulate(setup, bars_15m[i + 1:], max_hold_bars=6)
        if result is None:
            continue
        trades.append({"asset": asset, "strategy": strat_name, "cr_hour": cr_hour, **setup, **result})
        last_trade_idx = i
    return trades


def summary(trades, name):
    if not trades:
        return f"{name}: NO trades generated"
    n = len(trades)
    wins = [t for t in trades if t["pnl_usd"] > 0]
    losses = [t for t in trades if t["pnl_usd"] < 0]
    wr = len(wins) / n * 100
    pnl_total = sum(t["pnl_usd"] for t in trades)
    avg_pnl = pnl_total / n
    avg_win = sum(t["pnl_usd"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["pnl_usd"] for t in losses) / len(losses) if losses else 0
    profit_factor = abs(sum(t["pnl_usd"] for t in wins) / sum(t["pnl_usd"] for t in losses)) if losses else 999
    avg_duration = sum(t["duration_min"] for t in trades) / n
    return (
        f"\n{'='*70}\n{name}\n{'='*70}\n"
        f"Total trades: {n} | WR: {wr:.1f}% | Profit factor: {profit_factor:.2f}\n"
        f"Total PnL: ${pnl_total:+.2f} | Avg PnL/trade: ${avg_pnl:+.2f}\n"
        f"Avg WIN: ${avg_win:+.2f} | Avg LOSS: ${avg_loss:.2f}\n"
        f"Avg duration: {avg_duration:.0f} min\n"
    )


def main():
    print(f"=" * 70)
    print(f"BACKTEST 3 ESTRATEGIAS HOURLY — {DAYS_HISTORY} días")
    print(f"Margin ${MARGIN}, Lev {LEVERAGE}x = Notional ${NOTIONAL}")
    print(f"Fees roundtrip {FEES_PCT}% = ${NOTIONAL * FEES_PCT / 100:.2f}/trade")
    print(f"Universo: {len(ASSETS)} assets")
    print(f"=" * 70)

    all_a, all_b, all_c = [], [], []
    for sym in ASSETS:
        print(f"  Pulling {sym}...", file=sys.stderr)
        bars_15m = fetch(sym, "15m", min(1500, 96 * DAYS_HISTORY))
        bars_1h = fetch(sym, "1h", min(1500, 24 * DAYS_HISTORY + 60))
        if not bars_15m or not bars_1h:
            continue
        ta = backtest_strategy(strategy_a_vwap_reversion, "A_VWAP", bars_15m, bars_1h, sym)
        tb = backtest_strategy(strategy_b_bb_squeeze, "B_BBSqueeze", bars_15m, bars_1h, sym)
        tc = backtest_strategy(strategy_c_adx_pullback, "C_ADX_Pullback", bars_15m, bars_1h, sym)
        all_a.extend(ta)
        all_b.extend(tb)
        all_c.extend(tc)
        print(f"    A:{len(ta)} B:{len(tb)} C:{len(tc)}", file=sys.stderr)

    print(summary(all_a, "📊 ESTRATEGIA A — VWAP Reversion + MTF Trend Filter"))
    print(summary(all_b, "📊 ESTRATEGIA B — Bollinger Squeeze Breakout"))
    print(summary(all_c, "📊 ESTRATEGIA C — ADX Trend + RSI Pullback"))

    # Comparar y elegir ganadora
    candidates = []
    for trades, name in [(all_a, "A"), (all_b, "B"), (all_c, "C")]:
        if not trades:
            continue
        n = len(trades)
        pnl = sum(t["pnl_usd"] for t in trades)
        wr = sum(1 for t in trades if t["pnl_usd"] > 0) / n * 100
        candidates.append({"name": name, "trades": n, "pnl": pnl, "wr": wr})

    print(f"\n{'='*70}")
    print(f"🏆 RANKING")
    print(f"{'='*70}")
    candidates.sort(key=lambda x: -x["pnl"])
    for c in candidates:
        marker = "⭐ WINNER" if c == candidates[0] and c["pnl"] > 0 else ""
        print(f"  {c['name']}: {c['trades']} trades, WR {c['wr']:.1f}%, PnL ${c['pnl']:+.2f} {marker}")

    if candidates and candidates[0]["pnl"] > 0:
        winner = candidates[0]
        print(f"\n✅ Estrategia ganadora: {winner['name']}")
        print(f"   Esperado por día (asume 5 trades): ${(winner['pnl']/winner['trades'])*5:.2f}")
        print(f"   Esperado por mes (22 trading days, 5/día): ${(winner['pnl']/winner['trades'])*5*22:.2f}")
    else:
        print(f"\n❌ Ninguna estrategia es rentable en backtest 30d. Necesita re-diseño.")


if __name__ == "__main__":
    main()
