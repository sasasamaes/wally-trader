#!/usr/bin/env python3
"""
Backtest del universo fot-scout — computa el `per_asset_edge` (RANGE_CHOP / Mean Reversion)
para cada uno de los 23 instrumentos curados.

Por qué existe: `per_asset_backtest.py` emite n/WR/PF/Ret/DD pero NO `setups_per_day`
ni `expectancy_R`, que son justo los dos campos que `fot_strategy_mapping.json →
per_asset_edge` usa para el scoring del router (expectancy_R≥0.30 → +10; oos WARN/FAIL →
penaliza) y el flag `edge_backtested`. Este runner los calcula con contabilidad de R
por trade correcta (suma de parciales 40/40/20), reusando los indicadores del engine
pero SIN mutar la sim compartida.

Solo backtestea Mean Reversion (el único edge VALIDATED del mapping asimétrico). Las
estrategias de tendencia son WEAK por diseño y nunca llegan a GO — no se re-validan acá.

Uso:
    .venv/bin/python fot_backtest_universe.py --json          # JSON crudo
    .venv/bin/python fot_backtest_universe.py --md            # reporte markdown
    .venv/bin/python fot_backtest_universe.py --assets EURUSD,XAUUSD   # subset
    .venv/bin/python fot_backtest_universe.py --tf 5m --days 60

Caveat honesto: FEE=0.0005 round-trip (igual que el engine que produjo los 4 edges
originales). El spread real del bonus CFD en exóticos/índices es más ancho → el edge
LIVE es ≤ al de este backtest. yfinance 5m capa a 60d; Binance se pagina a ~días-objetivo.
"""
from __future__ import annotations
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_SHARED = HERE.parent.parent / "shared" / "wally_core" / "src"
if _SHARED.exists() and str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

import per_asset_backtest as pab  # noqa: E402  (rsi/atr/donchian/sma/stdev)
from backtest_split import temporal_split, degradation_flag  # noqa: E402
import fot_scout_router as r  # noqa: E402  (ASSETS table: data_source/data_symbol)
from wally_core.regime import compute_adx, label_regime, RegimeLabel  # noqa: E402

FEE = 0.0005  # round-trip, mismo valor que per_asset_backtest.simulate_mean_reversion

# MR params — espejo del setup que CONSTRUYE el router (evaluate_asset), no del
# cascade 2.5/4/6 de CLAUDE.md. El router usa SL=max(ATR×1.2, floor_pips) y TP único
# a 2R (PHASE_TP_R fase 1). Eso es lo que el per_asset_edge debe representar.
DONCHIAN_LEN = 15
RSI_OS, RSI_OB = 35.0, 65.0
BB_LEN, BB_MULT = 20, 2.0
ATR_LEN = 14
SL_ATR_MULT = 1.2   # _sl_distance del router
TP_R = 2.0          # PHASE_TP_R[1]
RISK_PCT = 0.01     # fase 1 (1%); la expectancy_R es invariante al sizing


# ── Data layer ────────────────────────────────────────────────────────────────

def fetch_binance_paginated(symbol: str, interval: str, days: int) -> list[dict]:
    """Pagina la API pública de Binance hacia atrás hasta cubrir ~`days` (límite 1000/call)."""
    ms_per_bar = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000}[interval]
    end = int(time.time() * 1000)
    start = end - days * 86_400_000
    out: list[dict] = []
    cur = start
    while cur < end:
        qs = urllib.parse.urlencode(
            {"symbol": symbol, "interval": interval, "startTime": cur, "limit": 1000}
        )
        url = f"https://api.binance.com/api/v3/klines?{qs}"
        with urllib.request.urlopen(url, timeout=20) as resp:
            raw = json.loads(resp.read())
        if not raw:
            break
        out.extend(
            {"t": k[0], "o": float(k[1]), "h": float(k[2]),
             "l": float(k[3]), "c": float(k[4]), "v": float(k[5])}
            for k in raw
        )
        last_t = raw[-1][0]
        if last_t <= cur or len(raw) < 1000:
            cur = last_t + ms_per_bar
            if len(raw) < 1000:
                break
        else:
            cur = last_t + ms_per_bar
    return out


def fetch(asset: str, interval: str, days: int) -> list[dict]:
    cfg = r.ASSETS[asset]
    if cfg["data_source"] == "binance":
        return fetch_binance_paginated(cfg["data_symbol"], interval, days)
    # yfinance: pab.fetch_yfinance pulla 60d para 5m y trunca a `bars` — pedimos de sobra
    return pab.fetch_yfinance(cfg["data_symbol"], interval, bars=days * 300)


# ── Regime gate (replica detect_regime del router: MR solo en RANGE_CHOP) ──────

ADX_WINDOW = 80  # mismo nº de barras 1h que usa el router en vivo (fetch "1h", 80)


def regime_series_1h(bars1h: list[dict]) -> list[tuple[int, str]]:
    """Para cada barra 1h (con suficiente historia) calcula el régimen vía ADX rolling.
    Devuelve (close_time_ms, label) ordenado. RANGE_CHOP = ADX<25 (igual que el router)."""
    out: list[tuple[int, str]] = []
    for j in range(len(bars1h)):
        win = bars1h[max(0, j - ADX_WINDOW + 1): j + 1]
        if len(win) < 28:  # compute_adx exige ≥28 barras
            continue
        w = [{"open": b["o"], "high": b["h"], "low": b["l"], "close": b["c"],
              "volume": b.get("v", 0) or 0} for b in win]
        try:
            adx = compute_adx(w, 14)
        except Exception:  # noqa: BLE001
            continue
        label = label_regime(adx["adx"], adx["plus_di"], adx["minus_di"]).value
        close_t = bars1h[j]["t"] + 3_600_000  # open + 1h = cierre
        out.append((close_t, label))
    return out


def _range_lookup(regimes: list[tuple[int, str]]):
    """Closure: dado un timestamp de barra 5m, ¿la última 1h CERRADA era RANGE_CHOP?"""
    times = [t for t, _ in regimes]
    labels = [lab for _, lab in regimes]
    import bisect

    def is_range(t5: int | None) -> bool:
        if t5 is None or not times:
            return False
        idx = bisect.bisect_right(times, t5) - 1  # última 1h cuyo cierre ≤ t5
        return idx >= 0 and labels[idx] == RegimeLabel.RANGE_CHOP.value
    return is_range


# ── Mean Reversion sim con R-accounting por trade ──────────────────────────────

def simulate(bars: list[dict], capital: float = 100.0, is_range=None,
             sl_floor: float = 0.0) -> dict:
    """MR mecánica 4-filtros con el MISMO exit que el router: SL=max(ATR×1.2, floor) y
    TP único a 2R. Outcome binario por trade (TP=+2R / SL=-1R). Si TP y SL caen en la
    misma vela se asume SL primero (conservador).

    `is_range`: callable(t5_ms)->bool. Si se pasa, SOLO entra cuando la última 1h cerrada
    fue RANGE_CHOP (replica el gate de régimen del router — MR no opera en tendencia).
    `sl_floor`: distancia mínima de SL en precio (min_sl_pips × pip_size del activo)."""
    closes = [b["c"] for b in bars]
    rsi_v = pab.rsi(closes, 14)
    bb_mid = pab.sma(closes, BB_LEN)
    bb_sd = pab.stdev(closes, BB_LEN)
    atr_v = pab.atr(bars, ATR_LEN)
    don_hi, don_lo = pab.donchian(bars, DONCHIAN_LEN)

    equity = capital
    peak = equity
    max_dd = 0.0
    trades: list[dict] = []  # cada trade: {pnl, risk, entry_t}
    ot = None
    warmup = max(DONCHIAN_LEN, BB_LEN, ATR_LEN) + 2

    for i in range(warmup, len(bars)):
        bar = bars[i]
        if any(x is None for x in (rsi_v[i], bb_mid[i], bb_sd[i], atr_v[i], don_hi[i], don_lo[i])):
            continue
        bb_up = bb_mid[i] + BB_MULT * bb_sd[i]
        bb_lo = bb_mid[i] - BB_MULT * bb_sd[i]

        if ot:
            hit_sl = (ot["side"] == "long" and bar["l"] <= ot["sl"]) or \
                     (ot["side"] == "short" and bar["h"] >= ot["sl"])
            hit_tp = (ot["side"] == "long" and bar["h"] >= ot["tp"]) or \
                     (ot["side"] == "short" and bar["l"] <= ot["tp"])
            exit_px = None
            if hit_sl:               # SL primero si ambos en la misma vela
                exit_px = ot["sl"]
            elif hit_tp:
                exit_px = ot["tp"]
            if exit_px is not None:
                gross = (exit_px - ot["entry"]) * (1 if ot["side"] == "long" else -1) * ot["size"]
                pnl = gross - abs(ot["entry"]) * ot["size"] * FEE
                equity += pnl
                trades.append({"pnl": pnl, "gross": gross, "risk": ot["risk"],
                               "entry_t": ot["entry_t"]})
                ot = None

        if not ot and (is_range is None or is_range(bar.get("t"))):
            color = "green" if bar["c"] > bar["o"] else "red"
            long_sig = (bar["l"] <= don_lo[i] * 1.001 and rsi_v[i] < RSI_OS
                        and bar["l"] <= bb_lo and color == "green")
            short_sig = (bar["h"] >= don_hi[i] * 0.999 and rsi_v[i] > RSI_OB
                         and bar["h"] >= bb_up and color == "red")
            if long_sig or short_sig:
                side = "long" if long_sig else "short"
                entry = bar["c"]
                sl_dist = max(atr_v[i] * SL_ATR_MULT, sl_floor)
                if sl_dist <= 0:
                    continue
                sign = 1 if side == "long" else -1
                sl = entry - sign * sl_dist
                tp = entry + sign * sl_dist * TP_R
                risk = equity * RISK_PCT
                ot = {"side": side, "entry": entry, "sl": sl, "tp": tp,
                      "size": risk / sl_dist, "risk": risk, "entry_t": bar.get("t")}

        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak * 100)

    if ot:  # mark-to-market al cierre de data
        last = bars[-1]["c"]
        pnl = (last - ot["entry"]) * (1 if ot["side"] == "long" else -1) * ot["size"]
        pnl -= abs(ot["entry"]) * ot["size"] * FEE
        equity += pnl
        trades.append({"pnl": pnl, "gross": pnl, "risk": ot["risk"], "entry_t": ot["entry_t"]})

    n = len(trades)
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    gross_w = sum(t["pnl"] for t in wins)
    gross_l = abs(sum(t["pnl"] for t in losses)) or 1e-9
    r_mults = [t["pnl"] / t["risk"] for t in trades if t["risk"] > 0]
    r_gross = [t["gross"] / t["risk"] for t in trades if t["risk"] > 0]
    expectancy_r = sum(r_mults) / len(r_mults) if r_mults else 0.0
    expectancy_r_gross = sum(r_gross) / len(r_gross) if r_gross else 0.0

    # setups/día sobre días-de-mercado reales (fechas UTC distintas con barras)
    span_days = trading_days = None
    if bars and bars[0].get("t") and bars[-1].get("t"):
        span_days = (bars[-1]["t"] - bars[0]["t"]) / 86_400_000
        dates = {datetime.fromtimestamp(b["t"] / 1000, timezone.utc).date()
                 for b in bars if b.get("t")}
        trading_days = len(dates)
    setups_per_day = (n / trading_days) if trading_days else None

    return {
        "n": n,
        "wr": round(len(wins) / n * 100, 1) if n else 0.0,
        "pf": round(gross_w / gross_l, 2),
        "ret": round((equity - capital) / capital * 100, 2),
        "dd": round(max_dd, 2),
        "expectancy_R": round(expectancy_r, 3),
        "expectancy_R_gross": round(expectancy_r_gross, 3),
        "setups_per_day": round(setups_per_day, 2) if setups_per_day is not None else None,
        "span_days": round(span_days, 1) if span_days is not None else None,
        "trading_days": trading_days,
    }


def backtest_asset(asset: str, tf: str, days: int) -> dict:
    bars = fetch(asset, tf, days)
    bars1h = fetch(asset, "1h", days)
    regimes = regime_series_1h(bars1h)
    is_range = _range_lookup(regimes)
    range_pct = round(
        sum(1 for b in bars if b.get("t") and is_range(b["t"])) / len(bars) * 100, 1
    ) if bars else 0.0
    cfg = r.ASSETS[asset]
    sl_floor = cfg["min_sl_pips"] * cfg["pip_size"]
    full = simulate(bars, is_range=is_range, sl_floor=sl_floor)
    oos = "SKIP"
    if len(bars) >= 100:
        try:
            tr, te = temporal_split(bars, 0.7)
            oos, _ = degradation_flag(
                simulate(tr, is_range=is_range, sl_floor=sl_floor),
                simulate(te, is_range=is_range, sl_floor=sl_floor),
            )
        except ValueError:
            oos = "SKIP"
    return {"asset": asset, "bars_n": len(bars), "range_pct": range_pct,
            "oos": oos, **full}


# ── Edge classification (mirror de la semántica del mapping) ───────────────────

def edge_block(res: dict) -> dict | None:
    """Construye la entrada RANGE_CHOP del per_asset_edge, o None si no hay muestra."""
    if res["n"] == 0 or res["setups_per_day"] is None:
        return None
    return {
        "RANGE_CHOP": {
            "setups_per_day": res["setups_per_day"],
            # GROSS (3×WR−1, sin costo) — el net con fee notional es negativo en todo el
            # universo y sobre-castiga; ver docs/backtest_findings_2026-06-02_fot_universe.md.
            "expectancy_R": round(res["expectancy_R_gross"], 2),
            "oos": res["oos"],
        }
    }


def render_md(results: list[dict]) -> str:
    today = datetime.now(timezone.utc).date().isoformat()
    lines = [
        f"# fot-scout Universe Backtest — Mean Reversion (RANGE_CHOP edge)",
        f"_Generado {today} · TF 5m · FEE {FEE} round-trip · 2% risk/trade_\n",
        "| Asset | n | WR% | PF | expR_gross | expR_net | setups/d | range% | OOS |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for x in sorted(results, key=lambda d: (d.get("expectancy_R_gross") or -99), reverse=True):
        if "error" in x:
            lines.append(f"| {x['asset']} | — | — | — | — | — | — | — | ERR |")
            continue
        lines.append(
            f"| {x['asset']} | {x['n']} | {x['wr']} | {x['pf']} "
            f"| {x['expectancy_R_gross']:+.3f} | {x['expectancy_R']:+.3f} "
            f"| {x['setups_per_day']} | {x.get('range_pct', '—')} | {x['oos']} |"
        )
    lines += [
        "\n_expR_gross = edge puro (3×WR−1, sin costo); expR_net = con FEE notional 0.05% "
        "round-trip del engine. Solo RANGE_CHOP (gate ADX 1h<25). SL=max(ATR×1.2, floor), TP 2R._",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", help="Comma-separated subset (default: 23 del universo)")
    ap.add_argument("--tf", default="5m")
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--md", action="store_true")
    ap.add_argument("--emit-edge", action="store_true",
                    help="Imprime el bloque per_asset_edge listo para pegar al mapping")
    args = ap.parse_args()

    assets = args.assets.split(",") if args.assets else r.UNIVERSE
    results = []
    for a in assets:
        try:
            print(f"[backtest] {a} {args.tf} ~{args.days}d ...", file=sys.stderr)
            results.append(backtest_asset(a, args.tf, args.days))
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {a}: {e}", file=sys.stderr)
            results.append({"asset": a, "error": str(e)})

    if args.json:
        print(json.dumps(results, indent=2))
    if args.md or not (args.json or args.emit_edge):
        print(render_md(results))
    if args.emit_edge:
        edge = {x["asset"]: edge_block(x) for x in results if "error" not in x and edge_block(x)}
        print(json.dumps(edge, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
