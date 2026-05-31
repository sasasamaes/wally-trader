#!/usr/bin/env python3
"""
Strategy optimization loop — auto-busca configs y se queda con la mejor que SOBREVIVE
los gates anti-overfit.

Destilado del video "I Let Claude AI Opus 4.8 Trade For Me" (Trading with DaviddTech). El
video deja a Claude "loopear cada 5 min por 1 hora" optimizando una estrategia hasta hallar
backtests rentables... pero presume resultados con 27% de max DD y curvas sideways SIN
validación out-of-sample/Monte Carlo — el clásico "optimizar hacia overfit".

Este helper toma la idea del loop pero la hace honesta: cada config ganadora del search
pasa por los gates del proyecto (Bundle 5):
  - RST (la entrada tiene edge, no es ruido)
  - OOS 70/30 (no overfit temporal)
  - Monte Carlo trades (robustez del sizing) + candles (no overfit a la trayectoria)

Solo recomienda una config si pasa los 3. Si ninguna pasa, lo dice (no maquilla un 112%
sideways como "ganador").

Uso programático:
    from optimize_strategy import optimize
    res = optimize("BTCUSDT", "4h", days=365, side="long", iterations=40)

Uso CLI:
    python3 optimize_strategy.py --symbol BTCUSDT --tf 4h --days 365 --side long \\
                                 --iterations 40 --validate-top 3 --export-pine --json

Exit codes: 0 = halló config recomendable, 2 = ninguna pasó los gates, 3 = error.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

from rule_significance import (  # noqa: E402
    donchian_ema_entries,
    fetch_paginated,
    make_donchian_atr_exit,
    significance_test,
)
from monte_carlo import (  # noqa: E402
    max_drawdown,
    monte_carlo_candles,
    monte_carlo_trades,
    sharpe as sharpe_of,
)
from backtest_split import temporal_split, degradation_flag  # noqa: E402


def _maybe_reexec_venv():
    venv_python = HERE / ".venv" / "bin" / "python"
    if (
        venv_python.exists()
        and Path(sys.executable).resolve() != venv_python.resolve()
        and not os.environ.get("WALLY_VENV_REEXEC")
    ):
        os.environ["WALLY_VENV_REEXEC"] = "1"
        os.execv(str(venv_python), [str(venv_python), __file__, *sys.argv[1:]])


# ───────────────────────── espacio de búsqueda ─────────────────────────────

SEARCH_SPACE = {
    "don_len": [10, 15, 20, 30, 40, 55],
    "ema_len": [50, 100, 150, 200],
    "atr_len": [10, 14, 21],
    "sl_mult": [1.5, 2.0, 2.5, 3.0],
    "max_hold": [24, 48, 72],
}


def sample_config(rng: np.random.Generator) -> dict:
    return {k: rng.choice(v).item() for k, v in SEARCH_SPACE.items()}


def config_key(params: dict) -> tuple:
    return tuple(params[k] for k in SEARCH_SPACE)


# ───────────────────────── backtest de una config ─────────────────────────

def compute_metrics(returns) -> dict:
    arr = np.asarray(returns, dtype=float)
    n = int(arr.size)
    if n == 0:
        return {"n": 0, "wr": 0.0, "pf": 0.0, "ret": 0.0, "dd": 0.0, "sharpe": 0.0}
    wins = arr[arr > 0]
    losses = arr[arr < 0]
    wr = len(wins) / n * 100
    gross_win = float(wins.sum())
    gross_loss = float(-losses.sum())
    pf = gross_win / gross_loss if gross_loss > 1e-12 else (999.0 if gross_win > 0 else 0.0)
    ret = float(arr.sum()) * 100
    dd = max_drawdown(np.cumsum(arr)) * 100
    return {
        "n": n,
        "wr": round(wr, 1),
        "pf": round(pf, 2),
        "ret": round(ret, 2),
        "dd": round(dd, 2),
        "sharpe": round(sharpe_of(arr), 3),
    }


def backtest_config(bars: list[dict], params: dict, side: str) -> dict:
    """Corre la estrategia donchian_ema con `params` → entries, returns y métricas."""
    entries = donchian_ema_entries(
        bars, side=side, don_len=params["don_len"], ema_len=params["ema_len"])
    exit_fn = make_donchian_atr_exit(
        don_len=params["don_len"], atr_len=params["atr_len"],
        sl_mult=params["sl_mult"], max_hold=params["max_hold"])
    returns = [exit_fn(bars, i, side) for i in entries]
    return {"entries": entries, "exit_fn": exit_fn, "returns": returns,
            "metrics": compute_metrics(returns)}


def base_score(m: dict, min_trades: int) -> float:
    """Score barato para rankear candidatos ANTES de los gates caros."""
    if m["n"] < min_trades:
        return -1e9
    return (m["wr"] * 0.30
            + min(m["pf"], 3.0) * 20 * 0.30
            + m["ret"] * 0.20
            - m["dd"] * 0.20
            + m["sharpe"] * 10 * 0.10)


# ───────────────────────── gates anti-overfit ─────────────────────────────

def validate_config(bars: list[dict], params: dict, side: str, bt: dict,
                    rst_perms: int, mc_sims: int, seed: int) -> dict:
    """Corre RST + OOS + Monte Carlo sobre una config. Devuelve verdict combinado."""
    entries = bt["entries"]
    exit_fn = bt["exit_fn"]
    returns = bt["returns"]

    # RST — ¿la entrada tiene edge?
    rst = significance_test(bars, entries, exit_fn, side=side,
                            n_permutations=rst_perms, seed=seed)

    # OOS 70/30
    try:
        train_bars, test_bars = temporal_split(bars, 0.7)
        train_m = backtest_config(train_bars, params, side)["metrics"]
        test_m = backtest_config(test_bars, params, side)["metrics"]
        oos_status, oos_reasons = degradation_flag(train_m, test_m)
    except ValueError as e:
        oos_status, oos_reasons = "SKIP", [str(e)]

    # Monte Carlo trades (sizing) + candles (overfit)
    mc_trades = monte_carlo_trades(returns, n_sims=max(200, mc_sims * 5), seed=seed) \
        if len(returns) >= 3 else {"verdict": "INSUFFICIENT"}

    def _strat_sharpe(b):
        m = backtest_config(b, params, side)["metrics"]
        return m["sharpe"] if m["n"] >= 2 else 0.0
    mc_candles = monte_carlo_candles(bars, _strat_sharpe, n_sims=mc_sims, seed=seed)

    # Veredicto combinado (gate del Bundle 5)
    rst_ok = rst.get("verdict") == "PASS"
    oos_ok = oos_status != "FAIL"
    mc_ok = not mc_candles.get("overfit_flag", False)
    recommend = rst_ok and oos_ok and mc_ok

    reasons = []
    if not rst_ok:
        reasons.append(f"RST={rst.get('verdict')} (p={rst.get('p_value')}) — entrada sin edge confirmado")
    if not oos_ok:
        reasons.append(f"OOS=FAIL — {'; '.join(oos_reasons)}")
    if not mc_ok:
        reasons.append(f"MC candles={mc_candles.get('zone')} — overfit a la trayectoria")

    return {
        "recommend": recommend,
        "rst": rst,
        "oos_status": oos_status,
        "oos_reasons": oos_reasons,
        "mc_trades": mc_trades,
        "mc_candles": mc_candles,
        "reasons": reasons or ["✅ pasa RST + OOS + Monte Carlo"],
    }


# ───────────────────────── loop de optimización ───────────────────────────

def optimize(symbol: str = "BTCUSDT", tf: str = "4h", days: int = 365,
             side: str = "long", iterations: int = 40, minutes: float | None = None,
             validate_top: int = 3, min_trades: int = 15, rst_perms: int = 1000,
             mc_sims: int = 60, seed: int = 7, bars: list[dict] | None = None) -> dict:
    """
    Busca `iterations` configs (o hasta `minutes`), rankea por base_score, valida el top-K
    con los gates anti-overfit y devuelve la mejor que SOBREVIVE.
    """
    if bars is None:
        bars = fetch_paginated(symbol, tf, days)
    if len(bars) < 250:
        return {"error": f"solo {len(bars)} barras, insuficiente para optimizar"}

    rng = np.random.default_rng(seed)
    seen: set[tuple] = set()
    candidates: list[dict] = []
    t0 = time.time()
    i = 0
    while True:
        if minutes is not None:
            if (time.time() - t0) / 60.0 >= minutes:
                break
        elif i >= iterations:
            break
        i += 1
        params = sample_config(rng)
        key = config_key(params)
        if key in seen:
            continue
        seen.add(key)
        bt = backtest_config(bars, params, side)
        score = base_score(bt["metrics"], min_trades)
        candidates.append({"params": params, "metrics": bt["metrics"],
                           "score": score, "_bt": bt})

    scored = [c for c in candidates if c["score"] > -1e8]
    scored.sort(key=lambda c: c["score"], reverse=True)

    # Validar top-K con los gates caros
    validated = []
    for c in scored[:validate_top]:
        v = validate_config(bars, c["params"], side, c["_bt"],
                            rst_perms=rst_perms, mc_sims=mc_sims, seed=seed)
        validated.append({"params": c["params"], "metrics": c["metrics"],
                          "score": round(c["score"], 2), "validation": v})

    survivors = [v for v in validated if v["validation"]["recommend"]]
    winner = survivors[0] if survivors else None

    return {
        "symbol": symbol, "tf": tf, "side": side, "bars": len(bars),
        "configs_tried": len(seen), "configs_with_trades": len(scored),
        "leaderboard": [
            {"params": c["params"], "metrics": c["metrics"], "score": round(c["score"], 2)}
            for c in scored[:10]
        ],
        "validated": validated,
        "winner": winner,
        "verdict": "RECOMMEND" if winner else "NONE_SURVIVED",
    }


# ───────────────────────── Pine strategy() export ─────────────────────────

def _slug(symbol: str, tf: str, side: str) -> str:
    return f"opt_donchian_ema_{symbol.lower()}_{tf}_{side}"


def to_pine_strategy(params: dict, symbol: str, tf: str, side: str,
                     metrics: dict | None = None) -> str:
    """
    Genera un Pine Script v6 `strategy()` de la estrategia donchian_ema con `params`,
    importable a TradingView para verificar el backtest visualmente.
    """
    m = metrics or {}
    note = (f"// Backtest (motor Wally): n={m.get('n','?')} WR={m.get('wr','?')}% "
            f"PF={m.get('pf','?')} Ret={m.get('ret','?')}% DD={m.get('dd','?')}% "
            f"Sharpe={m.get('sharpe','?')}") if m else "// (sin métricas)"
    # OJO: en Pine, los statements top-level NO se indentan (la indentación = bloque
    # anidado bajo un `if`). Los `if` van en columna 0, lo de adentro a 4 espacios.
    long_block = (
        "if longCond\n"
        "    strategy.entry(\"Long\", strategy.long)\n"
        "    strategy.exit(\"Long X\", \"Long\", stop=longStop)\n"
        "if strategy.position_size > 0 and close < donLow\n"
        "    strategy.close(\"Long\", comment=\"Donchian exit\")"
    )
    short_block = (
        "if shortCond\n"
        "    strategy.entry(\"Short\", strategy.short)\n"
        "    strategy.exit(\"Short X\", \"Short\", stop=shortStop)\n"
        "if strategy.position_size < 0 and close > donHigh\n"
        "    strategy.close(\"Short\", comment=\"Donchian exit\")"
    )
    body = long_block if side == "long" else short_block
    return f"""//@version=6
// Auto-generado por /optimize (Wally Trader) — estrategia donchian_ema.
// Destilado del video "I Let Claude AI Opus 4.8 Trade For Me" (DaviddTech): el loop optimiza
// y EXPORTA un strategy() Pine importable a TradingView para verificación visual.
// {symbol} {tf} {side.upper()}.
{note}
// ⚠️ DRAFT: valida visualmente + re-backtestea antes de confiar. Métricas Wally usan
//    salida por ATR/Donchian sin pyramiding; el backtester de TV puede diferir levemente.
strategy("Opt Donchian-EMA {side.upper()} ({symbol} {tf})", overlay=true,
     default_qty_type=strategy.percent_of_equity, default_qty_value=10,
     commission_type=strategy.commission.percent, commission_value=0.05,
     pyramiding=0)

donLen   = input.int({params['don_len']}, "Donchian length", minval=2)
emaLen   = input.int({params['ema_len']}, "Trend EMA length", minval=2)
atrLen   = input.int({params['atr_len']}, "ATR length", minval=2)
slMult   = input.float({params['sl_mult']}, "SL ATR mult", minval=0.1, step=0.1)

// Donchian del periodo PREVIO (excluye la barra actual → breakout real)
donHigh = ta.highest(high[1], donLen)
donLow  = ta.lowest(low[1], donLen)
trendEma = ta.ema(close, emaLen)
atrV     = ta.atr(atrLen)

longCond  = close > donHigh and close > trendEma
shortCond = close < donLow  and close < trendEma
longStop  = close - atrV * slMult
shortStop = close + atrV * slMult

plot(donHigh, "Donchian High", color=color.new(color.teal, 40))
plot(donLow,  "Donchian Low",  color=color.new(color.maroon, 40))
plot(trendEma, "Trend EMA", color=color.orange)
{body}
"""


def write_pine(params: dict, symbol: str, tf: str, side: str,
               metrics: dict | None = None, out_dir: str | None = None) -> str:
    code = to_pine_strategy(params, symbol, tf, side, metrics)
    base = Path(out_dir) if out_dir else (HERE.parent.parent / "system" / "pine_library")
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{_slug(symbol, tf, side)}.pine"
    path.write_text(code)
    return str(path)


# ───────────────────────── render + CLI ───────────────────────────────────

def render(res: dict) -> str:
    if "error" in res:
        return f"## /optimize — ERROR\n\n{res['error']}\n"
    lines = [
        f"## Strategy Optimization — {res['symbol']} {res['tf']} {res['side']}",
        "",
        f"Configs probadas: {res['configs_tried']} · con trades: {res['configs_with_trades']} "
        f"· barras: {res['bars']}",
        "",
        "### Leaderboard (top 10 por score, PRE-gates)",
        "| # | don | ema | atr | sl | hold | n | WR% | PF | Ret% | DD% | Sharpe | score |",
        "|---|----|----|----|----|----|---|-----|----|------|-----|--------|-------|",
    ]
    for i, c in enumerate(res["leaderboard"], 1):
        p, m = c["params"], c["metrics"]
        lines.append(
            f"| {i} | {p['don_len']} | {p['ema_len']} | {p['atr_len']} | {p['sl_mult']} "
            f"| {p['max_hold']} | {m['n']} | {m['wr']} | {m['pf']} | {m['ret']} | {m['dd']} "
            f"| {m['sharpe']} | {c['score']} |")
    lines += ["", "### Validación de los top candidatos (gates anti-overfit)"]
    for i, v in enumerate(res["validated"], 1):
        val = v["validation"]
        rst = val["rst"]
        lines.append(
            f"\n**#{i}** don={v['params']['don_len']} ema={v['params']['ema_len']} "
            f"sl={v['params']['sl_mult']} hold={v['params']['max_hold']} → "
            f"{'✅ RECOMMEND' if val['recommend'] else '❌ REJECT'}")
        lines.append(
            f"- RST: {rst.get('verdict')} (p={rst.get('p_value')}) · "
            f"OOS: {val['oos_status']} · "
            f"MC candles: {val['mc_candles'].get('zone')} "
            f"(overfit={val['mc_candles'].get('overfit_flag')}) · "
            f"MC trades DD p95: {val['mc_trades'].get('dd_p95')}")
        for r in val["reasons"]:
            lines.append(f"  - {r}")
    lines += ["", "### Veredicto"]
    if res["winner"]:
        w = res["winner"]
        lines.append(
            f"✅ **RECOMMEND** — config sobrevive los 3 gates: "
            f"don={w['params']['don_len']} ema={w['params']['ema_len']} "
            f"atr={w['params']['atr_len']} sl={w['params']['sl_mult']} hold={w['params']['max_hold']} "
            f"(WR {w['metrics']['wr']}% · PF {w['metrics']['pf']} · DD {w['metrics']['dd']}%).")
    else:
        lines.append(
            "❌ **NONE_SURVIVED** — ninguna config pasó RST + OOS + Monte Carlo. "
            "Honesto: el mejor backtest del leaderboard es probable overfit o suerte de régimen "
            "(justo lo que el video NO valida). No operar.")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Strategy optimization loop con gates anti-overfit")
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--side", default="long", choices=["long", "short"])
    ap.add_argument("--iterations", type=int, default=40, help="# configs a probar")
    ap.add_argument("--minutes", type=float, default=None,
                    help="presupuesto de tiempo (override de --iterations, estilo loop del video)")
    ap.add_argument("--validate-top", type=int, default=3, help="# top configs a validar con gates")
    ap.add_argument("--min-trades", type=int, default=15)
    ap.add_argument("--rst-perms", type=int, default=1000)
    ap.add_argument("--mc-sims", type=int, default=60)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--export-pine", action="store_true",
                    help="exporta el ganador a system/pine_library/<slug>.pine")
    ap.add_argument("--bars-file", help="JSON OHLCV en vez de fetch")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        bars = None
        if args.bars_file:
            with open(args.bars_file) as f:
                bars = json.load(f)
        else:
            print(f"[Binance] Paginando {args.symbol} {args.tf} ({args.days}d)...", file=sys.stderr)
        res = optimize(
            symbol=args.symbol, tf=args.tf, days=args.days, side=args.side,
            iterations=args.iterations, minutes=args.minutes,
            validate_top=args.validate_top, min_trades=args.min_trades,
            rst_perms=args.rst_perms, mc_sims=args.mc_sims, seed=args.seed, bars=bars)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 3

    if "error" in res:
        print(res["error"], file=sys.stderr)
        return 3

    pine_path = None
    if args.export_pine and res["winner"]:
        w = res["winner"]
        pine_path = write_pine(w["params"], args.symbol, args.tf, args.side, w["metrics"])
        res["pine_export"] = pine_path

    if args.json:
        print(json.dumps(res, indent=2, default=str))
    else:
        print(render(res))
        if pine_path:
            print(f"\n📄 Pine strategy exportado: {pine_path}")
        elif args.export_pine:
            print("\n⚠️ --export-pine pedido pero ninguna config sobrevivió; no se exportó.")

    return 0 if res["winner"] else 2


if __name__ == "__main__":
    _maybe_reexec_venv()
    sys.exit(main())
