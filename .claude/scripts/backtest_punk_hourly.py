#!/usr/bin/env python3
"""
backtest_punk_hourly.py — Simulación honesta de filosofía bitunix "1 trade/hora rotativo".

Objetivo: estimar profitability realista de:
- Cadencia A: 5 trades/día (cada ~3h ventana operativa CR 06:00-23:00)
- Cadencia B: 6 trades/día (1 a CR 06-08 + cada 2h después → 06, 08, 10, 12, 14, 16)
- Margin fijo: $50 por trade (25% capital $200 — conservador vs cap 35%)
- Leverage: 10x (cap regla #5 sagrada — NO 20x como hizo en trade real)
- TPs/SL adaptativos basados en context_multiplier helper
- Scoring simplificado (sin Neptune, usa proxies: RSI extremo + Donchian touch + BB ext + Hyper Wave proxy)

Datos: Binance Futures klines 15m últimos 7 días (free API, sin rate limit fuerte).
Universo: 9 tradeables Bitunix más líquidos (BTC, ETH, SOL, MSTR, AVAX, INJ, DOGE, WIF, XLM)

Honesty disclaimers:
- Scoring sin Neptune Hyper Wave numérico = aproximación. Real puede tener WR ±10pp distinto.
- Slippage + fees: 0.06% per side × 2 = 0.12% round-trip (típico Bitunix Taker).
- Survivorship/data quality: 7 días es muestra pequeña. Resultados orientativos, no garantizados.
- No incluye macro events ni catalysts (assume ocurrieron uniformemente).
"""

import json
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

# Añadir scripts/ al path para importar context_multiplier
sys.path.insert(0, str(Path(__file__).parent))
from context_multiplier import calc_context_multiplier, calc_adaptive_levels

# ===== Config =====
ASSETS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "MSTRUSDT",
    "AVAXUSDT",
    "INJUSDT",
    "DOGEUSDT",
    "WIFUSDT",
    "XLMUSDT",
]

DAYS_HISTORY = 7
MARGIN_PER_TRADE = 50.0  # USD
LEVERAGE = 10
FEES_ROUNDTRIP_PCT = 0.12  # 0.06% per side × 2
INITIAL_CAPITAL = 200.0


# ===== Helpers de indicadores =====
def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = closes[-i] - closes[-i - 1]
        if diff > 0:
            gains.append(diff)
        else:
            losses.append(-diff)
    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0.0001
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calc_atr(bars, period=14):
    if len(bars) < period + 1:
        return 0
    trs = []
    for i in range(1, len(bars)):
        h = bars[i]["h"]
        l = bars[i]["l"]
        prev_c = bars[i - 1]["c"]
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        trs.append(tr)
    return sum(trs[-period:]) / period


def calc_donchian(bars, period=15):
    last_n = bars[-period:]
    return max(b["h"] for b in last_n), min(b["l"] for b in last_n)


def calc_bb(bars, period=20, std_mult=2):
    if len(bars) < period:
        return None, None, None
    closes = [b["c"] for b in bars[-period:]]
    mean = sum(closes) / period
    var = sum((c - mean) ** 2 for c in closes) / period
    std = var ** 0.5
    return mean + std_mult * std, mean - std_mult * std, mean


def calc_hyperwave_proxy(bars, period=14):
    """Aproximación del Hyper Wave (Stochastic-like 0-100 normalizado)."""
    if len(bars) < period:
        return 50
    last_n = bars[-period:]
    high = max(b["h"] for b in last_n)
    low = min(b["l"] for b in last_n)
    close = bars[-1]["c"]
    if high == low:
        return 50
    return ((close - low) / (high - low)) * 100


# ===== Pull data =====
def fetch_klines(symbol, interval="15m", limit=None):
    """Pull klines from Binance Futures (free API)."""
    if limit is None:
        # 15m × 96 candles/day × 7 days = 672 candles
        limit = 96 * DAYS_HISTORY
    if limit > 1500:
        limit = 1500
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        data = json.loads(urllib.request.urlopen(url, timeout=15).read())
        return [
            {
                "t": int(b[0]),
                "o": float(b[1]),
                "h": float(b[2]),
                "l": float(b[3]),
                "c": float(b[4]),
                "v": float(b[5]),
            }
            for b in data
        ]
    except Exception as e:
        print(f"  WARN: failed {symbol}: {e}", file=sys.stderr)
        return []


# ===== Scoring simplificado =====
def evaluate_setup(bars_15m, target_hold_min=60):
    """Devuelve {score, side, entry, atr_pct, atr, regime, ls_smart_proxy} or None."""
    if len(bars_15m) < 30:
        return None
    last = bars_15m[-1]
    entry = last["c"]
    atr = calc_atr(bars_15m, 14)
    atr_pct = (atr / entry) * 100
    rsi = calc_rsi([b["c"] for b in bars_15m], 14)
    don_h, don_l = calc_donchian(bars_15m, 15)
    bb_up, bb_dn, bb_mid = calc_bb(bars_15m, 20, 2)
    hyper = calc_hyperwave_proxy(bars_15m, 14)

    # Determinar side candidato
    dist_to_low = (entry - don_l) / entry if don_l else 1
    dist_to_high = (don_h - entry) / entry if don_h else 1

    if rsi < 35 and dist_to_low < 0.005 and hyper < 20:
        side = "LONG"
    elif rsi > 65 and dist_to_high < 0.005 and hyper > 80:
        side = "SHORT"
    else:
        return None

    # Score simplificado (sin Neptune real)
    # Componente 1 — Hyper Wave proxy (40 pts)
    if side == "SHORT":
        hw_pts = 40 if hyper > 90 else (25 if hyper > 80 else 15)
    else:
        hw_pts = 40 if hyper < 10 else (25 if hyper < 20 else 15)

    # Componente 2 — Reversal Band proxy (BB touch) (25 pts)
    if side == "SHORT":
        rb_pts = 25 if last["h"] >= bb_up else (12 if entry > bb_up * 0.998 else 0)
    else:
        rb_pts = 25 if last["l"] <= bb_dn else (12 if entry < bb_dn * 1.002 else 0)

    # Componente 3 — Estructura (Donchian touch) (20 pts)
    if side == "SHORT":
        struct_pts = 20 if last["h"] >= don_h * 0.998 else 5
    else:
        struct_pts = 20 if last["l"] <= don_l * 1.002 else 5

    # Componente 4 — Vela direccional (15 pts)
    candle_dir = (last["c"] - last["o"]) / last["o"] if last["o"] else 0
    if (side == "SHORT" and candle_dir < 0) or (side == "LONG" and candle_dir > 0):
        candle_pts = 15
    else:
        candle_pts = 5

    score = hw_pts + rb_pts + struct_pts + candle_pts

    # Régimen aproximado
    range_pct = (don_h - don_l) / entry * 100
    if range_pct > 3 and atr_pct > 1.5:
        regime = "VOLATILE"
    elif range_pct < 1.5:
        regime = "RANGING"
    else:
        regime = "TRENDING_UP" if entry > bb_mid else "TRENDING_DOWN"

    return {
        "score": score,
        "side": side,
        "entry": entry,
        "atr": atr,
        "atr_pct": atr_pct,
        "regime": regime,
    }


# ===== Simular trade single =====
def simulate_trade(setup, future_bars, target_hold_min=60):
    """Simula trade con TPs/SL adaptativos. Returns dict con outcome.

    Usa context_multiplier helper para calcular niveles.
    Time-out a 90 min (filosofía bitunix).
    """
    # Smart money proxy: como no tenemos data histórica, asumimos neutral 1.0
    ls_smart_proxy = 0.95 if setup["side"] == "SHORT" else 1.05

    ctx = calc_context_multiplier(
        side=setup["side"],
        atr_pct=setup["atr_pct"],
        market_regime=setup["regime"],
        ls_ratio_smart=ls_smart_proxy,
        target_hold_minutes=target_hold_min,
    )

    levels = calc_adaptive_levels(
        entry=setup["entry"],
        side=setup["side"],
        atr=setup["atr"],
        context_mult=ctx["multiplier"],
        atr_pct=setup["atr_pct"],
    )

    sl = levels["sl"]
    tp1 = levels["tp1"]
    tp2 = levels["tp2"]
    tp3 = levels["tp3"]

    # Time-Achievability Gate: si TP1 distance > 4 × ATR/2 = 2*ATR (movimiento esperado 1h)
    expected_1h_move = 2 * setup["atr"]
    tp1_distance = abs(setup["entry"] - tp1)
    if tp1_distance > expected_1h_move * 1.2:
        return {"outcome": "REJECTED_TIME_GATE", "pnl_pct": 0, "duration_min": 0}

    # Simular hasta tocar SL/TP/timeout (max 6 velas 15m = 90 min)
    notional = MARGIN_PER_TRADE * LEVERAGE  # $500
    qty = notional / setup["entry"]

    pnl_pct_price = 0  # cuanto se movió el precio (para calc PnL USD)
    duration_min = 0
    outcome = "TIMEOUT"

    for i, bar in enumerate(future_bars[:6]):  # max 90 min
        duration_min = (i + 1) * 15

        if setup["side"] == "SHORT":
            # SL hit (precio sube y toca SL)
            if bar["h"] >= sl:
                pnl_pct_price = -(sl - setup["entry"]) / setup["entry"]
                outcome = "SL"
                break
            # TPs hit (precio baja)
            if bar["l"] <= tp3:
                pnl_pct_price = (setup["entry"] - tp3) / setup["entry"]
                outcome = "TP3"
                break
            elif bar["l"] <= tp2:
                pnl_pct_price = (setup["entry"] - tp2) / setup["entry"]
                outcome = "TP2"
                break
            elif bar["l"] <= tp1:
                pnl_pct_price = (setup["entry"] - tp1) / setup["entry"]
                outcome = "TP1"
                break
        else:  # LONG
            if bar["l"] <= sl:
                pnl_pct_price = (sl - setup["entry"]) / setup["entry"]
                outcome = "SL"
                break
            if bar["h"] >= tp3:
                pnl_pct_price = (tp3 - setup["entry"]) / setup["entry"]
                outcome = "TP3"
                break
            elif bar["h"] >= tp2:
                pnl_pct_price = (tp2 - setup["entry"]) / setup["entry"]
                outcome = "TP2"
                break
            elif bar["h"] >= tp1:
                pnl_pct_price = (tp1 - setup["entry"]) / setup["entry"]
                outcome = "TP1"
                break

    # Si timeout, cerrar a precio último bar
    if outcome == "TIMEOUT" and len(future_bars) >= 6:
        last_close = future_bars[5]["c"]
        if setup["side"] == "SHORT":
            pnl_pct_price = (setup["entry"] - last_close) / setup["entry"]
        else:
            pnl_pct_price = (last_close - setup["entry"]) / setup["entry"]

    # PnL USD = pnl_pct_price × notional (porque leverage amplifica)
    pnl_usd = pnl_pct_price * notional - (notional * FEES_ROUNDTRIP_PCT / 100)

    # Outcome final con TP1/TP2/TP3 escalonado (cierra 40/40/20%)
    if outcome == "TP1":
        # Cerró 40% a TP1, 60% sigue. Asumimos 60% restante toca SL eventualmente (peor caso).
        # Mejor: ese 60% promedia entre TP1 y BE
        # Conservador: 40% × TP1 + 60% × 0 (BE)
        pnl_pct_price = pnl_pct_price * 0.4
        pnl_usd = pnl_pct_price * notional - (notional * FEES_ROUNDTRIP_PCT / 100)
    elif outcome == "TP2":
        # Cerró 40% TP1 + 40% TP2 + 20% BE
        tp1_dist = abs(setup["entry"] - tp1) / setup["entry"]
        pnl_pct_price = (tp1_dist * 0.4) + (pnl_pct_price * 0.4)
        pnl_usd = pnl_pct_price * notional - (notional * FEES_ROUNDTRIP_PCT / 100)
    elif outcome == "TP3":
        # Full hit
        tp1_dist = abs(setup["entry"] - tp1) / setup["entry"]
        tp2_dist = abs(setup["entry"] - tp2) / setup["entry"]
        pnl_pct_price = (tp1_dist * 0.4) + (tp2_dist * 0.4) + (pnl_pct_price * 0.2)
        pnl_usd = pnl_pct_price * notional - (notional * FEES_ROUNDTRIP_PCT / 100)

    return {
        "outcome": outcome,
        "pnl_pct_price": round(pnl_pct_price * 100, 4),
        "pnl_usd": round(pnl_usd, 2),
        "duration_min": duration_min,
        "context_mult": ctx["multiplier"],
    }


# ===== Run backtest =====
def backtest_asset(symbol, bars):
    """Para cada hora elegible (bar=4 velas 15m) intenta abrir trade."""
    trades = []
    if len(bars) < 36:
        return trades

    # Iterar cada 4 velas (1 hora) — empezando bar 30 para tener history
    for i in range(30, len(bars) - 6, 4):
        window = bars[: i + 1]
        future = bars[i + 1 : i + 7]
        if len(future) < 6:
            break

        setup = evaluate_setup(window, target_hold_min=60)
        if setup is None or setup["score"] < 70:
            continue

        # Cross-profile conflict: skip si ya hay trade en este asset las últimas 4h
        recent_trades_same_asset = [
            t for t in trades if t["bar_idx"] >= i - 16 and t["symbol"] == symbol
        ]
        if recent_trades_same_asset:
            continue

        # Ventana operativa CR 06:00-23:00 (asumiendo UTC bars, CR=UTC-6, asi UTC 12:00-05:00)
        bar_hour_utc = datetime.utcfromtimestamp(window[-1]["t"] / 1000).hour
        cr_hour = (bar_hour_utc - 6) % 24
        if cr_hour < 6 or cr_hour > 22:
            continue  # fuera de ventana operativa

        result = simulate_trade(setup, future, target_hold_min=60)
        if result["outcome"] == "REJECTED_TIME_GATE":
            continue

        trades.append(
            {
                "symbol": symbol,
                "bar_idx": i,
                "cr_hour": cr_hour,
                "side": setup["side"],
                "score": setup["score"],
                "regime": setup["regime"],
                "atr_pct": round(setup["atr_pct"], 3),
                **result,
            }
        )
    return trades


def main():
    print("=" * 70)
    print(f"BACKTEST PUNK-HUNT HOURLY — {DAYS_HISTORY} días history")
    print(f"Margin: ${MARGIN_PER_TRADE} | Leverage: {LEVERAGE}x | Capital: ${INITIAL_CAPITAL}")
    print(f"Universo: {len(ASSETS)} assets tradeables Bitunix")
    print("=" * 70)

    all_trades = []
    for sym in ASSETS:
        print(f"  Pulling {sym}...", file=sys.stderr)
        bars = fetch_klines(sym, "15m")
        if not bars:
            continue
        trades = backtest_asset(sym, bars)
        all_trades.extend(trades)
        print(f"    {len(trades)} trades simulados", file=sys.stderr)

    if not all_trades:
        print("\n❌ No se generaron trades — ajustar parámetros del scoring")
        return

    # Métricas globales
    n_total = len(all_trades)
    wins = [t for t in all_trades if t["pnl_usd"] > 0]
    losses = [t for t in all_trades if t["pnl_usd"] < 0]
    n_wins = len(wins)
    n_losses = len(losses)
    wr = n_wins / n_total * 100 if n_total else 0

    total_pnl = sum(t["pnl_usd"] for t in all_trades)
    avg_win = sum(t["pnl_usd"] for t in wins) / n_wins if n_wins else 0
    avg_loss = sum(t["pnl_usd"] for t in losses) / n_losses if n_losses else 0
    total_days = DAYS_HISTORY

    avg_trades_per_day = n_total / total_days
    avg_pnl_per_day = total_pnl / total_days
    avg_pnl_per_trade = total_pnl / n_total

    # Distribución por outcome
    by_outcome = {}
    for t in all_trades:
        by_outcome.setdefault(t["outcome"], 0)
        by_outcome[t["outcome"]] += 1

    print(f"\n{'─' * 70}")
    print(f"📊 MÉTRICAS GLOBALES (período {DAYS_HISTORY} días)")
    print(f"{'─' * 70}")
    print(f"Total trades: {n_total}")
    print(f"Wins:    {n_wins} ({wr:.1f}%)")
    print(f"Losses:  {n_losses} ({100-wr:.1f}%)")
    print(f"Total PnL: ${total_pnl:.2f}")
    print(f"Avg PnL per trade: ${avg_pnl_per_trade:.2f}")
    print(f"Avg WIN: ${avg_win:.2f} | Avg LOSS: ${avg_loss:.2f}")
    print(f"Trades/día (avg): {avg_trades_per_day:.1f}")
    print(f"PnL/día (avg): ${avg_pnl_per_day:.2f}")
    print(f"\nDistribución outcomes: {by_outcome}")

    # Por asset
    print(f"\n{'─' * 70}")
    print(f"📊 PnL POR ASSET")
    print(f"{'─' * 70}")
    by_asset = {}
    for t in all_trades:
        by_asset.setdefault(t["symbol"], []).append(t)
    for sym, ts in sorted(by_asset.items(), key=lambda x: -sum(t["pnl_usd"] for t in x[1])):
        n = len(ts)
        w = sum(1 for t in ts if t["pnl_usd"] > 0)
        pnl = sum(t["pnl_usd"] for t in ts)
        print(f"  {sym:14s} {n:3d} trades | WR {w/n*100:.0f}% | PnL ${pnl:+.2f}")

    # Proyección 5 trades/día y 6 trades/día
    print(f"\n{'─' * 70}")
    print(f"📈 PROYECCIONES (capital ${INITIAL_CAPITAL}, margin ${MARGIN_PER_TRADE}/trade)")
    print(f"{'─' * 70}")
    for trades_per_day in [5, 6]:
        # Asume PnL per trade promedio se mantiene
        daily_pnl = avg_pnl_per_trade * trades_per_day
        weekly_pnl = daily_pnl * 5  # 5 trading days
        monthly_pnl = daily_pnl * 22  # 22 trading days
        yearly_pnl = daily_pnl * 252
        # Crecimiento compounded mensual (asumimos reinvertimos cada $50 capital extra)
        # Simplificación: fixed margin, no compounding
        print(f"\nCadencia {trades_per_day} trades/día @ ${MARGIN_PER_TRADE} margin:")
        print(f"  Día:  ${daily_pnl:+.2f} ({daily_pnl/INITIAL_CAPITAL*100:+.2f}% capital)")
        print(f"  Sem:  ${weekly_pnl:+.2f} ({weekly_pnl/INITIAL_CAPITAL*100:+.2f}%)")
        print(f"  Mes:  ${monthly_pnl:+.2f} ({monthly_pnl/INITIAL_CAPITAL*100:+.2f}%)")
        print(f"  Año:  ${yearly_pnl:+.2f} ({yearly_pnl/INITIAL_CAPITAL*100:+.2f}%)")

    # Para 5 wins/día específicamente (no 5 trades — vincula al objetivo del user)
    if wr >= 60:
        # Hace falta más trades para 5 wins. Ej WR 65% → 5/0.65 = 7.7 trades
        trades_needed_for_5wins = 5 / (wr / 100)
        pnl_for_5wins = avg_pnl_per_trade * trades_needed_for_5wins
        print(f"\n📌 Para garantizar 5 WINS/día (con WR backtest {wr:.1f}%):")
        print(f"   Necesitás ~{trades_needed_for_5wins:.1f} trades/día")
        print(f"   PnL esperado: ${pnl_for_5wins:+.2f}/día")

    # Crecimiento compounded (si reinvertís el profit)
    print(f"\n{'─' * 70}")
    print(f"🚀 CRECIMIENTO COMPOUNDED (6 trades/día, reinvirtiendo profits)")
    print(f"{'─' * 70}")
    capital = INITIAL_CAPITAL
    daily_return_pct = (avg_pnl_per_trade * 6) / INITIAL_CAPITAL
    for label, days in [("1 mes", 22), ("3 meses", 66), ("6 meses", 132), ("1 año", 252)]:
        # Capital si reinvertimos pero margin queda fijo en $50
        # Realmente: si capital sube, margin podría subir proporcionalmente (mantener 25% capital)
        # Simplificamos: profits acumulados sin compounding sobre el margin
        accumulated = capital * ((1 + daily_return_pct) ** days)
        print(f"  {label:8s} ({days:3d}d): ${accumulated:.2f} ({(accumulated/INITIAL_CAPITAL-1)*100:+.1f}%)")

    print(f"\n{'─' * 70}")
    print("⚠️  DISCLAIMERS:")
    print("─" * 70)
    print(f"- Scoring sin Neptune real (proxies): WR puede diferir ±10pp en producción")
    print(f"- Sample {DAYS_HISTORY} días = NO statistical significance fuerte (necesitas 30+ días)")
    print(f"- No incluye macro events, gaps inusuales, manipulación")
    print(f"- Fees asume taker 0.06% × 2 = 0.12% — Bitunix puede ser distinto (verificar)")
    print(f"- Slippage real puede ser +0.05-0.15% extra en alts low-liq")
    print(f"- Past performance != future. Este es framework, no promesa.")


if __name__ == "__main__":
    main()
