#!/usr/bin/env python3
"""
Monte Carlo robustness — ¿el resultado del backtest es robusto o suerte/overfit?

Destilado del video "Opus 4.8 + Claude Code + MCP = Algo Trading on Autopilot"
(Algo-trading with Saleh, framework Jesse). Dos pruebas complementarias, exactamente
como las muestra el dashboard de Jesse:

  1. MONTE CARLO TRADES (reshuffle) — reordena el orden en que ocurrieron los trades
     (mismos trades, distinta secuencia). El retorno final es invariante, pero el max
     drawdown cambia: responde "¿qué hubiera pasado con mi position sizing si las
     pérdidas se hubieran agrupado al inicio?". Output: distribución de max DD.

  2. MONTE CARLO CANDLES (block-bootstrap) — genera data OHLCV sintética a partir de
     la real (preservando geometría de vela y autocorrelación de corto plazo) y corre
     la estrategia en cada path. Stress test de overfit: si el Sharpe original cae
     entre la mediana y el p95 de las sintéticas → robusto razonable; si supera el p95
     → sospecha de overfit (la estrategia "memorizó" la data real).

Uso programático (importable):
    from monte_carlo import monte_carlo_trades, monte_carlo_candles

    mc1 = monte_carlo_trades(trade_returns, n_sims=1000)        # lista de pnl% por trade
    mc2 = monte_carlo_candles(bars, strategy_fn, n_sims=200)    # strategy_fn(bars)->sharpe

Uso CLI:
    # Reshuffle sobre los retornos de trades de un backtest (JSON: lista de floats):
    python3 monte_carlo.py --mode trades --trades-file /tmp/trades.json --json

    # Candles sintéticos sobre la estrategia donchian_ema del video:
    python3 monte_carlo.py --mode candles --symbol BTCUSDT --tf 30m --days 365 --json

Exit codes: 0 = OK (no overfit / DD tolerable), 2 = WARN (overfit_flag o DD inflado), 3 = error.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

# Reusa estrategia + exit + fetch del RST (single source of truth)
from rule_significance import (  # noqa: E402
    donchian_ema_entries,
    fetch_paginated,
    make_donchian_atr_exit,
)


def _maybe_reexec_venv():
    venv_python = HERE / ".venv" / "bin" / "python"
    if (
        venv_python.exists()
        and Path(sys.executable).resolve() != venv_python.resolve()
        and not os.environ.get("WALLY_VENV_REEXEC")
    ):
        os.environ["WALLY_VENV_REEXEC"] = "1"
        os.execv(str(venv_python), [str(venv_python), __file__, *sys.argv[1:]])


# ───────────────────────── métricas base ───────────────────────────────────

def max_drawdown(curve: np.ndarray) -> float:
    """Max drawdown (en unidades de la curva, p.ej. suma acumulada de retornos)."""
    if curve.size == 0:
        return 0.0
    peak = np.maximum.accumulate(curve)
    return float((peak - curve).max())


def sharpe(returns: np.ndarray) -> float:
    """Sharpe per-trade (mean/std). NO anualizado — comparación relativa."""
    arr = np.asarray(returns, dtype=float)
    if arr.size < 2:
        return 0.0
    sd = arr.std(ddof=1)
    return float(arr.mean() / sd) if sd > 1e-12 else 0.0


# ───────────────────────── MC trades (reshuffle) ───────────────────────────

def monte_carlo_trades(
    trade_returns: list[float], n_sims: int = 1000, seed: int = 7,
    method: str = "reshuffle",
) -> dict:
    """
    Args:
        trade_returns: pnl% por trade (en el orden real).
        method: "reshuffle" (permuta orden, retorno final invariante — la del video)
                | "bootstrap" (resample con reemplazo — retorno también varía).

    Returns dict con distribución de max_dd (y de ret si bootstrap) + veredicto.
    """
    arr = np.asarray(trade_returns, dtype=float)
    n = arr.size
    if n < 3:
        return {"verdict": "INSUFFICIENT",
                "reason": f"solo {n} trades (<3)", "n_trades": n}

    orig_curve = np.cumsum(arr)
    orig_dd = max_drawdown(orig_curve)
    orig_ret = float(arr.sum())

    rng = np.random.default_rng(seed)
    dds = np.empty(n_sims, dtype=float)
    rets = np.empty(n_sims, dtype=float)
    for k in range(n_sims):
        if method == "bootstrap":
            sample = rng.choice(arr, size=n, replace=True)
        else:
            sample = rng.permutation(arr)
        c = np.cumsum(sample)
        dds[k] = max_drawdown(c)
        rets[k] = float(sample.sum())

    dd_p95 = float(np.percentile(dds, 95))
    # WARN si el DD original está en el cuartil "afortunado": el peor caso plausible
    # (p95) es notablemente peor que lo observado → el sizing debe soportar dd_p95.
    dd_inflation = (dd_p95 - orig_dd) / orig_dd if orig_dd > 0 else 0.0
    verdict = "WARN" if dd_inflation > 0.5 else "OK"

    out = {
        "verdict": verdict,
        "method": method,
        "n_trades": n,
        "n_sims": n_sims,
        "orig_max_dd": round(orig_dd, 4),
        "dd_p5": round(float(np.percentile(dds, 5)), 4),
        "dd_median": round(float(np.percentile(dds, 50)), 4),
        "dd_p95": round(dd_p95, 4),
        "dd_inflation_pct": round(dd_inflation * 100, 1),
        "orig_ret": round(orig_ret, 4),
    }
    if method == "bootstrap":
        out["ret_p5"] = round(float(np.percentile(rets, 5)), 4)
        out["ret_median"] = round(float(np.percentile(rets, 50)), 4)
        out["ret_p95"] = round(float(np.percentile(rets, 95)), 4)
        out["prob_negative"] = round(float((rets < 0).mean()), 4)
    return out


# ───────────────────────── MC candles (block-bootstrap) ────────────────────

def _candle_factors(bars: list[dict]) -> list[tuple]:
    """
    Descompone cada vela (i>0) en factores multiplicativos relativos al close previo:
      o_f = o_i / c_{i-1}   ;  h_f = h_i / o_i  ;  l_f = l_i / o_i  ;  c_f = c_i / o_i
    Esto preserva la GEOMETRÍA de la vela al re-muestrear.
    """
    factors = []
    for i in range(1, len(bars)):
        pc = bars[i - 1]["c"]
        o = bars[i]["o"]
        if pc <= 0 or o <= 0:
            factors.append((1.0, 1.0, 1.0, 1.0, bars[i].get("v", 0.0)))
            continue
        factors.append((
            o / pc,
            bars[i]["h"] / o,
            bars[i]["l"] / o,
            bars[i]["c"] / o,
            bars[i].get("v", 0.0),
        ))
    return factors


def synthetic_bars(bars: list[dict], rng: np.random.Generator, block: int = 10) -> list[dict]:
    """
    Genera una serie OHLCV sintética por block-bootstrap de factores de vela.
    Bloques contiguos preservan autocorrelación de corto plazo; el remuestreo
    rompe la secuencia macro (rompe overfit a la trayectoria real exacta).
    """
    factors = _candle_factors(bars)
    nf = len(factors)
    if nf == 0:
        return list(bars)
    sampled: list[tuple] = []
    while len(sampled) < nf:
        start = int(rng.integers(0, max(1, nf - block + 1)))
        sampled.extend(factors[start:start + block])
    sampled = sampled[:nf]

    t0 = bars[0].get("t", 0)
    out = [{"t": t0, "o": bars[0]["o"], "h": bars[0]["h"],
            "l": bars[0]["l"], "c": bars[0]["c"], "v": bars[0].get("v", 0.0)}]
    prev_c = bars[0]["c"]
    dt = (bars[1].get("t", 0) - t0) if len(bars) > 1 else 60000
    if dt <= 0:
        dt = 60000
    for k, (o_f, h_f, l_f, c_f, v) in enumerate(sampled, start=1):
        o = prev_c * o_f
        h = o * h_f
        l = o * l_f
        c = o * c_f
        hi = max(o, h, l, c)
        lo = min(o, h, l, c)
        out.append({"t": t0 + k * dt, "o": o, "h": hi, "l": lo, "c": c, "v": v})
        prev_c = c
    return out


def default_strategy_sharpe(side: str = "long", don_len: int = 20,
                            ema_len: int = 200, sl_mult: float = 2.0,
                            max_hold: int = 48):
    """
    Factory: strategy_fn(bars) -> sharpe per-trade de la estrategia donchian_ema.
    Usada por monte_carlo_candles para el caso CLI/video.
    """
    exit_fn = make_donchian_atr_exit(don_len=don_len, sl_mult=sl_mult, max_hold=max_hold)

    def _fn(bars: list[dict]) -> float:
        entries = donchian_ema_entries(bars, side=side, don_len=don_len, ema_len=ema_len)
        if len(entries) < 2:
            return 0.0
        rets = np.array([exit_fn(bars, i, side) for i in entries], dtype=float)
        return sharpe(rets)
    return _fn


def monte_carlo_candles(
    bars: list[dict], strategy_fn, n_sims: int = 100,
    seed: int = 7, block: int = 10,
) -> dict:
    """
    Args:
        bars: OHLCV real.
        strategy_fn: (bars) -> float (Sharpe u otra métrica donde "más alto = mejor").
        n_sims: # de series sintéticas.

    Returns dict con orig_sharpe vs distribución sintética + overfit_flag.
    overfit_flag = orig_sharpe > sharpe_p95 (el real bate a casi toda la data sintética
    → la estrategia se ajustó a la trayectoria específica, no a una estructura robusta).
    """
    orig = float(strategy_fn(bars))
    rng = np.random.default_rng(seed)
    sims = np.empty(n_sims, dtype=float)
    for k in range(n_sims):
        syn = synthetic_bars(bars, rng, block=block)
        sims[k] = float(strategy_fn(syn))

    p5 = float(np.percentile(sims, 5))
    p50 = float(np.percentile(sims, 50))
    p95 = float(np.percentile(sims, 95))
    overfit_flag = orig > p95

    if overfit_flag:
        zone = "OVERFIT_SUSPECT"  # real > p95 sintético
    elif orig >= p50:
        zone = "ROBUST"           # entre mediana y p95: deseable
    elif orig >= p5:
        zone = "FRAGILE"          # bajo la mediana: poco margen
    else:
        zone = "WEAK"             # bajo p5: el real es peor que casi toda la sintética

    return {
        "verdict": "WARN" if overfit_flag else "OK",
        "zone": zone,
        "overfit_flag": bool(overfit_flag),
        "n_sims": n_sims,
        "block": block,
        "orig_sharpe": round(orig, 4),
        "sharpe_p5": round(p5, 4),
        "sharpe_median": round(p50, 4),
        "sharpe_p95": round(p95, 4),
    }


# ───────────────────────── CLI ─────────────────────────────────────────────

def _render_trades(res: dict) -> str:
    if res["verdict"] == "INSUFFICIENT":
        return f"## Monte Carlo (trades)\n\n⚠️ **INSUFFICIENT** — {res.get('reason')}\n"
    icon = "⚠️" if res["verdict"] == "WARN" else "✅"
    lines = [
        f"## Monte Carlo — trades reshuffle ({res['method']})",
        "",
        f"| Campo | Valor |", "|---|---|",
        f"| Trades | {res['n_trades']} |",
        f"| Simulaciones | {res['n_sims']} |",
        f"| Max DD original | {res['orig_max_dd']} |",
        f"| DD p5 (suerte) | {res['dd_p5']} |",
        f"| DD mediana | {res['dd_median']} |",
        f"| DD p95 (peor plausible) | {res['dd_p95']} |",
        f"| Inflación DD vs original | {res['dd_inflation_pct']}% |",
        "",
    ]
    if "ret_p5" in res:
        lines += [f"| Ret p5 | {res['ret_p5']} |",
                  f"| Ret mediana | {res['ret_median']} |",
                  f"| Ret p95 | {res['ret_p95']} |",
                  f"| Prob. retorno negativo | {res['prob_negative']} |", ""]
    if res["verdict"] == "WARN":
        lines.append(f"{icon} **WARN** — el DD p95 ({res['dd_p95']}) supera al original "
                     f"en {res['dd_inflation_pct']}%. Dimensiona el sizing para soportar "
                     f"el p95, no el caso observado.")
    else:
        lines.append(f"{icon} **OK** — DD estable bajo reordenamiento. Sizing tolerante.")
    return "\n".join(lines)


def _render_candles(res: dict) -> str:
    icon = "⚠️" if res["overfit_flag"] else "✅"
    zone_txt = {
        "OVERFIT_SUSPECT": "real > p95 sintético — sospecha de overfit",
        "ROBUST": "entre mediana y p95 — robustez razonable",
        "FRAGILE": "bajo la mediana — poco margen",
        "WEAK": "bajo p5 — el real es peor que casi toda la data sintética",
    }[res["zone"]]
    lines = [
        f"## Monte Carlo — candles sintéticos (block-bootstrap)",
        "",
        f"| Campo | Valor |", "|---|---|",
        f"| Simulaciones | {res['n_sims']} (block={res['block']}) |",
        f"| Sharpe original | {res['orig_sharpe']} |",
        f"| Sharpe p5 | {res['sharpe_p5']} |",
        f"| Sharpe mediana | {res['sharpe_median']} |",
        f"| Sharpe p95 | {res['sharpe_p95']} |",
        f"| Zona | **{res['zone']}** |",
        "",
        f"{icon} {'**WARN**' if res['overfit_flag'] else '**OK**'} — {zone_txt}.",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Monte Carlo robustness (trades + candles)")
    ap.add_argument("--mode", required=True, choices=["trades", "candles"])
    ap.add_argument("--trades-file", help="[trades] JSON: lista de pnl% por trade")
    ap.add_argument("--mc-method", default="reshuffle", choices=["reshuffle", "bootstrap"])
    ap.add_argument("--symbol", default="BTCUSDT", help="[candles] símbolo Binance Futures")
    ap.add_argument("--tf", default="30m", help="[candles] timeframe")
    ap.add_argument("--days", type=int, default=365, help="[candles] días de historia")
    ap.add_argument("--side", default="long", choices=["long", "short"])
    ap.add_argument("--bars-file", help="[candles] JSON OHLCV en vez de fetch")
    ap.add_argument("--n", type=int, default=None, help="# simulaciones (default 1000 trades / 100 candles)")
    ap.add_argument("--block", type=int, default=10, help="[candles] tamaño de bloque bootstrap")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        if args.mode == "trades":
            if not args.trades_file:
                print("ERROR: --trades-file requerido en modo trades", file=sys.stderr)
                return 3
            with open(args.trades_file) as f:
                trade_returns = json.load(f)
            n_sims = args.n or 1000
            res = monte_carlo_trades(trade_returns, n_sims=n_sims,
                                     seed=args.seed, method=args.mc_method)
            print(json.dumps(res, indent=2) if args.json else _render_trades(res))
            return 2 if res.get("verdict") == "WARN" else 0

        # candles
        if args.bars_file:
            with open(args.bars_file) as f:
                bars = json.load(f)
        else:
            print(f"[Binance] Paginando {args.symbol} {args.tf} ({args.days}d)...",
                  file=sys.stderr)
            bars = fetch_paginated(args.symbol, args.tf, args.days)
        if len(bars) < 250:
            print(f"ERROR: solo {len(bars)} barras, insuficiente.", file=sys.stderr)
            return 3
        n_sims = args.n or 100
        strat = default_strategy_sharpe(side=args.side)
        res = monte_carlo_candles(bars, strat, n_sims=n_sims, seed=args.seed, block=args.block)
        print(json.dumps({**res, "symbol": args.symbol, "tf": args.tf}, indent=2)
              if args.json else _render_candles(res))
        return 2 if res.get("overfit_flag") else 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    _maybe_reexec_venv()
    sys.exit(main())
