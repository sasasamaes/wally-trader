#!/usr/bin/env python3
"""
Rule Significance Test (RST) — ¿la regla de ENTRADA tiene edge o es ruido?

Destilado del video "Opus 4.8 + Claude Code + MCP = Algo Trading on Autopilot"
(Algo-trading with Saleh, framework Jesse). La idea central que el video martilla:
una estrategia rentable NO prueba que su entrada tenga poder predictivo — en un bull
year un "always long" gana plata sin edge alguno. El RST separa las dos preguntas:

    1. ¿La regla de entrada tiene edge?   ← ESTE test (antes del backtest)
    2. ¿La estrategia completa es rentable? ← backtest + OOS + Monte Carlo (después)

Método (igual al video — "bate a las 2,000 variantes de entrada aleatoria"):
  - Mide la métrica real de los trades que la estrategia abrió en SUS barras de entrada.
  - Genera N permutaciones con el MISMO número de entradas en barras ALEATORIAS
    (dentro del mismo span temporal) aplicando la MISMA regla de salida (exit_fn).
  - p_value = fracción de variantes aleatorias que igualan o superan la real.
  - PASS si p < alpha (0.05 default): la entrada bate al azar → tiene edge.

Uso programático (importable — para el script /tmp/backtest_*.py del agente):
    from rule_significance import significance_test, make_donchian_atr_exit

    exit_fn = make_donchian_atr_exit(don_len=20, atr_len=14, sl_mult=2.0, max_hold=48)
    res = significance_test(bars, entry_indices, exit_fn, side="long", n_permutations=2000)
    print(res["verdict"], res["p_value"])

Uso CLI (estrategia built-in donchian_ema, la del video):
    python3 rule_significance.py --symbol BTCUSDT --tf 30m --days 365 \\
                                 --strategy donchian_ema --side long --n 2000 --json

Exit codes: 0 = PASS (edge), 2 = FAIL/INSUFFICIENT (sin edge o muestra ínfima), 3 = error.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

FEE = 0.0005  # 0.05% per side (round-trip 0.1%), igual que el resto del sistema
ALPHA = 0.05


def _maybe_reexec_venv():
    """Re-ejecutar con el venv python si binary modules (numpy) requieren versión exacta.
    Solo desde __main__ — nunca durante imports."""
    venv_python = HERE / ".venv" / "bin" / "python"
    if (
        venv_python.exists()
        and Path(sys.executable).resolve() != venv_python.resolve()
        and not os.environ.get("WALLY_VENV_REEXEC")
    ):
        os.environ["WALLY_VENV_REEXEC"] = "1"
        os.execv(str(venv_python), [str(venv_python), __file__, *sys.argv[1:]])


# ───────────────────────── core: significance test ─────────────────────────

def _aggregate(returns: list[float] | np.ndarray, metric: str) -> float:
    arr = np.asarray(returns, dtype=float)
    if arr.size == 0:
        return 0.0
    if metric == "total_return":
        return float(arr.sum())
    if metric == "mean_return":
        return float(arr.mean())
    if metric == "sharpe":
        sd = arr.std(ddof=1) if arr.size > 1 else 0.0
        return float(arr.mean() / sd) if sd > 1e-12 else 0.0
    raise ValueError(f"métrica desconocida: {metric}")


def significance_test(
    bars: list[dict],
    entry_indices: list[int],
    exit_fn,
    side: str = "long",
    n_permutations: int = 2000,
    metric: str = "mean_return",
    seed: int = 7,
    valid_pool: list[int] | None = None,
) -> dict:
    """
    RST por permutación de timing de entrada.

    Args:
        bars: OHLCV [{'t','o','h','l','c','v'}, ...]
        entry_indices: barras donde la estrategia REAL abrió posición
        exit_fn: (bars, entry_i, side) -> pnl_pct (float, siempre resuelve)
        side: "long" | "short"
        n_permutations: # de variantes aleatorias (video usa ~2000)
        metric: "mean_return" | "total_return" | "sharpe"
        seed: determinismo (reproducible)
        valid_pool: índices candidatos para entradas aleatorias.
                    Default = span [min(entries), max(entries)] (mismo régimen).

    Returns dict con: verdict, p_value, real_metric, null_mean, null_p95,
    percentile, n_beaten, n_permutations, n_entries, metric, side.
    """
    n_entries = len(entry_indices)
    if n_entries < 3:
        return {
            "verdict": "INSUFFICIENT",
            "reason": f"solo {n_entries} entradas (<3) — muestra ínfima para RST",
            "n_entries": n_entries,
            "p_value": None,
            "real_metric": None,
        }

    real_returns = [exit_fn(bars, int(i), side) for i in entry_indices]
    real_metric = _aggregate(real_returns, metric)

    if valid_pool is None:
        lo, hi = min(entry_indices), max(entry_indices)
        valid_pool = list(range(lo, hi + 1))
    pool = np.asarray(valid_pool, dtype=int)
    if pool.size == 0:
        return {
            "verdict": "INSUFFICIENT",
            "reason": "pool de barras candidatas vacío",
            "n_entries": n_entries,
            "p_value": None,
            "real_metric": real_metric,
        }
    replace = pool.size < n_entries

    rng = np.random.default_rng(seed)
    null_metrics = np.empty(n_permutations, dtype=float)
    for k in range(n_permutations):
        idx = rng.choice(pool, size=n_entries, replace=replace)
        rets = [exit_fn(bars, int(i), side) for i in idx]
        null_metrics[k] = _aggregate(rets, metric)

    n_beaten = int(np.count_nonzero(null_metrics >= real_metric))
    # +1 / +1 = estimador conservador (Davison & Hinkley), evita p=0 exacto
    p_value = (n_beaten + 1) / (n_permutations + 1)
    percentile = float((null_metrics < real_metric).mean() * 100.0)
    verdict = "PASS" if p_value < ALPHA else "FAIL"

    return {
        "verdict": verdict,
        "p_value": round(p_value, 5),
        "alpha": ALPHA,
        "real_metric": round(real_metric, 6),
        "null_mean": round(float(null_metrics.mean()), 6),
        "null_p95": round(float(np.percentile(null_metrics, 95)), 6),
        "percentile": round(percentile, 2),
        "n_beaten": n_beaten,
        "n_permutations": n_permutations,
        "n_entries": n_entries,
        "metric": metric,
        "side": side,
    }


# ───────────────────────── exit functions (factories) ──────────────────────

def make_fixed_horizon_exit(horizon_bars: int = 24, fee: float = FEE):
    """Salida simple: cierra `horizon_bars` después de la entrada (o EOD)."""
    def _exit(bars: list[dict], entry_i: int, side: str) -> float:
        if entry_i >= len(bars) - 1:
            return 0.0
        entry = bars[entry_i]["c"]
        exit_i = min(entry_i + horizon_bars, len(bars) - 1)
        px = bars[exit_i]["c"]
        r = (px - entry) / entry if side == "long" else (entry - px) / entry
        return r - 2 * fee
    return _exit


def make_donchian_atr_exit(
    don_len: int = 20, atr_len: int = 14, sl_mult: float = 2.0,
    max_hold: int = 48, fee: float = FEE,
):
    """
    Salida tipo video: SL = entry ∓ sl_mult·ATR; exit estructural cuando close cruza
    la banda Donchian opuesta; timeout a max_hold barras (cierra a close).
    Devuelve pnl_pct neto de fees.
    """
    def _exit(bars: list[dict], entry_i: int, side: str) -> float:
        n = len(bars)
        if entry_i >= n - 1:
            return 0.0
        entry = bars[entry_i]["c"]
        atr_v = _atr_at(bars, entry_i, atr_len)
        if atr_v is None or atr_v <= 0:
            atr_v = entry * 0.01
        sl = entry - sl_mult * atr_v if side == "long" else entry + sl_mult * atr_v
        last = min(entry_i + max_hold, n - 1)
        for j in range(entry_i + 1, last + 1):
            b = bars[j]
            if side == "long":
                if b["l"] <= sl:
                    return (sl - entry) / entry - 2 * fee
                lo = _donchian_low_at(bars, j, don_len)
                if lo is not None and b["c"] < lo:
                    return (b["c"] - entry) / entry - 2 * fee
            else:
                if b["h"] >= sl:
                    return (entry - sl) / entry - 2 * fee
                hi = _donchian_high_at(bars, j, don_len)
                if hi is not None and b["c"] > hi:
                    return (entry - b["c"]) / entry - 2 * fee
        px = bars[last]["c"]
        r = (px - entry) / entry if side == "long" else (entry - px) / entry
        return r - 2 * fee
    return _exit


# ───────────────────────── indicadores (autocontenidos) ────────────────────

def _ema(values: list[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if len(values) < period:
        return out
    k = 2.0 / (period + 1)
    sma = sum(values[:period]) / period
    out[period - 1] = sma
    prev = sma
    for i in range(period, len(values)):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def _atr_at(bars: list[dict], i: int, period: int) -> float | None:
    if i < period:
        return None
    trs = []
    for j in range(i - period + 1, i + 1):
        h, l, pc = bars[j]["h"], bars[j]["l"], bars[j - 1]["c"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs) / period


def _donchian_high_at(bars: list[dict], i: int, length: int) -> float | None:
    if i + 1 < length:
        return None
    # high del periodo PREVIO (excluye la barra actual — breakout real)
    s = max(0, i - length)
    if s >= i:
        return None
    return max(b["h"] for b in bars[s:i])


def _donchian_low_at(bars: list[dict], i: int, length: int) -> float | None:
    if i + 1 < length:
        return None
    s = max(0, i - length)
    if s >= i:
        return None
    return min(b["l"] for b in bars[s:i])


def donchian_ema_entries(
    bars: list[dict], side: str = "long",
    don_len: int = 20, ema_len: int = 200,
) -> list[int]:
    """
    Estrategia del video: Donchian breakout + filtro de tendencia EMA.
      LONG  = close > Donchian-High(prev) AND close > EMA(ema_len)
      SHORT = close < Donchian-Low(prev)  AND close < EMA(ema_len)
    Devuelve los índices de barra donde dispara (1 entrada por cruce, sin re-pyramiding).
    """
    closes = [b["c"] for b in bars]
    ema = _ema(closes, ema_len)
    warmup = max(don_len, ema_len) + 1
    entries: list[int] = []
    armed = True  # evita disparar cada barra mientras siga roto
    for i in range(warmup, len(bars) - 1):
        if ema[i] is None:
            continue
        c = closes[i]
        if side == "long":
            don = _donchian_high_at(bars, i, don_len)
            sig = don is not None and c > don and c > ema[i]
        else:
            don = _donchian_low_at(bars, i, don_len)
            sig = don is not None and c < don and c < ema[i]
        if sig and armed:
            entries.append(i)
            armed = False
        elif not sig:
            armed = True
    return entries


# ───────────────────────── data fetch (paginado) ───────────────────────────

_BARS_PER_DAY = {"5m": 288, "15m": 96, "30m": 48, "1h": 24, "2h": 12, "4h": 6, "1d": 1}


def fetch_paginated(symbol: str, interval: str, days: int) -> list[dict]:
    """Pagina Binance Futures klines (cap 1500/llamada) hasta `days` hacia atrás."""
    bars_per_day = _BARS_PER_DAY.get(interval, 96)
    target = bars_per_day * days
    seen: dict[int, dict] = {}
    end_ts = None
    while len(seen) < target:
        url = (f"https://fapi.binance.com/fapi/v1/klines"
               f"?symbol={symbol}&interval={interval}&limit=1500")
        if end_ts is not None:
            url += f"&endTime={end_ts}"
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:
                page = json.loads(resp.read())
        except Exception as e:
            print(f"  WARN paginated {symbol}: {e}", file=sys.stderr)
            break
        if not page:
            break
        for b in page:
            t = int(b[0])
            seen[t] = {"t": t, "o": float(b[1]), "h": float(b[2]),
                       "l": float(b[3]), "c": float(b[4]), "v": float(b[5])}
        oldest = min(int(b[0]) for b in page)
        end_ts = oldest - 1
        time.sleep(0.1)
        if len(page) < 1500:
            break
    bars = sorted(seen.values(), key=lambda b: b["t"])
    return bars[-target:] if len(bars) > target else bars


# ───────────────────────── CLI ─────────────────────────────────────────────

def _render(res: dict, symbol: str, tf: str, side: str, strategy: str) -> str:
    if res["verdict"] == "INSUFFICIENT":
        return (f"## Rule Significance Test — {symbol} {tf} {side} ({strategy})\n\n"
                f"⚠️ **INSUFFICIENT** — {res.get('reason')}\n")
    icon = "✅" if res["verdict"] == "PASS" else "❌"
    lines = [
        f"## Rule Significance Test — {symbol} {tf} {side} ({strategy})",
        "",
        f"| Campo | Valor |",
        f"|---|---|",
        f"| Entradas reales | {res['n_entries']} |",
        f"| Permutaciones | {res['n_permutations']} |",
        f"| Métrica | {res['metric']} |",
        f"| Real | {res['real_metric']} |",
        f"| Null (media) | {res['null_mean']} |",
        f"| Null p95 | {res['null_p95']} |",
        f"| Percentil real | {res['percentile']}% |",
        f"| Aleatorias que igualan/baten | {res['n_beaten']}/{res['n_permutations']} |",
        f"| **p-value** | **{res['p_value']}** (α={res['alpha']}) |",
        "",
    ]
    if res["verdict"] == "PASS":
        lines.append(f"{icon} **PASS** — la regla de entrada bate al azar "
                     f"(p={res['p_value']} < {res['alpha']}). Tiene edge → continuar a backtest.")
    else:
        lines.append(f"{icon} **FAIL** — la entrada NO se distingue del azar "
                     f"(p={res['p_value']} ≥ {res['alpha']}). Puede ser suerte, no edge. "
                     f"Itera las reglas de entrada antes de backtestear.")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Rule Significance Test (RST)")
    ap.add_argument("--symbol", default="BTCUSDT", help="Símbolo Binance Futures")
    ap.add_argument("--tf", default="30m", help="Timeframe (5m/15m/30m/1h/4h/1d)")
    ap.add_argument("--days", type=int, default=365, help="Días de historia a paginar")
    ap.add_argument("--strategy", default="donchian_ema",
                    choices=["donchian_ema"], help="Estrategia de entrada built-in")
    ap.add_argument("--side", default="long", choices=["long", "short"])
    ap.add_argument("--n", type=int, default=2000, help="# permutaciones")
    ap.add_argument("--don-len", type=int, default=20)
    ap.add_argument("--ema-len", type=int, default=200)
    ap.add_argument("--sl-mult", type=float, default=2.0)
    ap.add_argument("--max-hold", type=int, default=48)
    ap.add_argument("--metric", default="mean_return",
                    choices=["mean_return", "total_return", "sharpe"])
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--bars-file", help="JSON OHLCV en vez de fetch (lista de dicts)")
    ap.add_argument("--json", action="store_true", help="Output JSON")
    args = ap.parse_args()

    try:
        if args.bars_file:
            with open(args.bars_file) as f:
                bars = json.load(f)
        else:
            print(f"[Binance] Paginando {args.symbol} {args.tf} ({args.days}d)...",
                  file=sys.stderr)
            bars = fetch_paginated(args.symbol, args.tf, args.days)
    except Exception as e:
        print(f"ERROR fetching/loading bars: {e}", file=sys.stderr)
        return 3

    if len(bars) < 250:
        print(f"ERROR: solo {len(bars)} barras, insuficiente para warmup EMA/Donchian.",
              file=sys.stderr)
        return 3

    entries = donchian_ema_entries(bars, side=args.side,
                                   don_len=args.don_len, ema_len=args.ema_len)
    exit_fn = make_donchian_atr_exit(don_len=args.don_len, sl_mult=args.sl_mult,
                                     max_hold=args.max_hold)
    res = significance_test(bars, entries, exit_fn, side=args.side,
                            n_permutations=args.n, metric=args.metric, seed=args.seed)

    if args.json:
        print(json.dumps({**res, "symbol": args.symbol, "tf": args.tf,
                          "bars": len(bars)}, indent=2))
    else:
        print(_render(res, args.symbol, args.tf, args.side, args.strategy))

    if res["verdict"] == "PASS":
        return 0
    return 2  # FAIL o INSUFFICIENT


if __name__ == "__main__":
    _maybe_reexec_venv()
    sys.exit(main())
