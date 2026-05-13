#!/usr/bin/env python3
"""autohunt.py — Hourly autonomous best-pick selector for /punk-autohunt.

MVP scope (per user-approved spec):
  - Reuses punk_smart_router.evaluate_asset() as the candidate generator.
  - Fuses confluence via autohunt_score.compute_score().
  - Computes adaptive TP ladder via autohunt_tp.compute_tp_plan().
  - Filters by $10 PnL floor + ATR-extreme gate (Appendix B safety).
  - Picks single best survivor (highest score, then highest expected $).
  - Paper mode writes to a parallel CSV (autohunt_paper_log.csv) to avoid
    touching the live signals_received.csv schema.
  - Skips TV draw (Claude parent agent executes MCP calls based on JSON output).
  - On-chain bias, pump detector, smart-money L/S extraction: NOT WIRED in MVP
    (their score components remain None → graceful redistribution).

Components wired in MVP:
  ✓ backtest_pnl_per_trade (from regime_mapping via evaluate_asset)
  ✓ multifactor_score (from multifactor_score.py local call)
  ✓ rr_tp1 (from evaluate_asset)
  ✓ liq_magnet alignment (placeholder — None for now)
  ✓ fib zone (placeholder — None)
  ✓ obv slope alignment (from volume_divergence)
  ✗ smart_money_ls (skipped — None)
  ✗ pump_score (skipped — None)
  ✓ sentiment_funding_passed (derived from vetos result)
  ✓ usdt_d_bias (from usdtd_tracker via subprocess — BTC/ETH only)
  ✗ on_chain_bias (skipped — None)

Exit codes:
  0  pick emitted or honest "no setup"
  1  pre-flight blocked (profile, kill-switch, macro HARD, session BLOCK,
     daily cap, concurrent slot)
  2  internal error (treated as no-op, not blocking)
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_SHARED = Path(__file__).resolve().parent.parent.parent / "shared/wally_core/src"
if _SHARED.exists() and str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

import autohunt_score as ascore
import autohunt_tp as atp
import punk_smart_state as state
import punk_smart_vetos as vetos
import punk_smart_router as router
import market_context as mctx
from backtest_regime_matrix import fetch as fetch_bars  # for multifactor input

CR_OFFSET = state.CR_OFFSET
SCRIPTS_DIR = Path(__file__).resolve().parent
PROFILES_DIR = SCRIPTS_DIR.parent / "profiles"
BITUNIX_MEMORY = PROFILES_DIR / "bitunix" / "memory"
PAPER_LOG_CSV = BITUNIX_MEMORY / "autohunt_paper_log.csv"
LIVE_AUTOHUNT_LOG_CSV = BITUNIX_MEMORY / "autohunt_signals.csv"
DAILY_CAP = 7
CONCURRENT_CAP = 2
MARGIN_USD_DEFAULT = 50.0
LEVERAGE_DEFAULT = 15

# Slimmed static universe for MVP — covers majors + a few alts.
# Dynamic discovery (--dynamic) deliberately deferred to v2.
UNIVERSE = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "INJUSDT",
    "DOGEUSDT", "WIFUSDT", "TRXUSDT", "TONUSDT", "ADAUSDT",
]

PAPER_CSV_FIELDS = [
    "tick_ts", "origin", "symbol", "side", "entry", "sl",
    "tp1", "tp2", "tp3", "close_pct",
    "score", "tier", "regime", "strategy",
    "expected_move_pct", "atr_pct_15m",
    "tp1_usd", "tp2_usd", "tp3_usd",
    "margin_usd", "leverage", "session_quality",
    "macro_tier", "components_used",
    # outcome columns (left blank at insertion)
    "outcome", "exit_price", "pnl_usd", "duration_h",
]


# ---------------------------------------------------------------------------
# Stage helpers
# ---------------------------------------------------------------------------
def stage0_preflight(now: datetime, args) -> dict:
    """Return {"pass": bool, "reason": str}. profile/kill-switch/caps."""
    profile = os.environ.get("WALLY_PROFILE", "bitunix")
    if profile != "bitunix":
        return {"pass": False, "reason": f"profile != bitunix (got {profile})"}

    active, reason = state.is_kill_switch_active(now)
    if active:
        return {"pass": False, "reason": reason or "kill-switch active"}

    # Daily signal counter (any origin)
    csv_path = BITUNIX_MEMORY / "signals_received.csv"
    today_count = 0
    if csv_path.exists():
        try:
            today_str = now.astimezone(CR_OFFSET).strftime("%Y-%m-%d")
            with csv_path.open() as f:
                for row in csv.DictReader(f):
                    if row.get("date") == today_str:
                        today_count += 1
        except Exception:
            today_count = 0
    if today_count >= DAILY_CAP:
        return {"pass": False, "reason": f"daily cap reached ({today_count}/{DAILY_CAP})"}

    open_pos = state.open_positions()
    if len(open_pos) >= CONCURRENT_CAP:
        return {"pass": False, "reason": f"concurrent slot full ({len(open_pos)}/{CONCURRENT_CAP})"}

    return {
        "pass": True,
        "today_count": today_count,
        "concurrent_open": len(open_pos),
    }


def _sub_json(args_list: list[str], timeout: int = 15) -> dict | None:
    """Run a helper as subprocess, return parsed JSON or None on any failure."""
    venv_py = SCRIPTS_DIR / ".venv" / "bin" / "python"
    py = str(venv_py) if venv_py.exists() else sys.executable
    cmd = [py] + args_list
    try:
        out = subprocess.check_output(cmd, timeout=timeout, stderr=subprocess.DEVNULL)
        return json.loads(out)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            json.JSONDecodeError, FileNotFoundError):
        return None


def stage1_macro_session(symbol_anchor: str = "BTCUSDT") -> dict:
    """Returns dict with macro tier + session quality verdict."""
    macro = _sub_json([str(SCRIPTS_DIR / "macro_gate.py"), "--check-tier"])
    if macro is None:
        # Fallback to --check-now (only HARD/OK signal)
        macro_now = _sub_json([str(SCRIPTS_DIR / "macro_gate.py"), "--check-now"])
        if macro_now and macro_now.get("blocked"):
            macro = {"tier": "HARD", "reason": macro_now.get("reason")}
        else:
            macro = {"tier": "OK", "reason": None}

    macro_tier = (macro.get("tier") or "OK").upper()
    session = _sub_json(
        [str(SCRIPTS_DIR / "session_quality.py"),
         "--symbol", symbol_anchor, "--quick"]
    )
    if session is None:
        session_verdict = "OK"  # if helper unavailable, fail open
    else:
        session_verdict = (session.get("verdict") or "OK").upper()

    return {
        "macro_tier": macro_tier,
        "macro_reason": macro.get("reason"),
        "session_quality": session_verdict,
    }


def stage3_enrich(tentative: dict) -> dict:
    """For a TENTATIVE setup from evaluate_asset, attach confluence components.

    Wired in MVP-v2 (2026-05-12 iter2):
      ✓ backtest_pnl_per_trade, rr_tp1, entry, tp1  (from evaluate_asset)
      ✓ multifactor_score                            (wally_core composite)
      ✓ obv_verdict                                  (volume_divergence)
      ✓ liq_magnet + smart_money_ls + retail_ls      (liq_heatmap subprocess)
      ✓ fib_zone                                     (fib_extension retracement)
      ✗ pump_score (component remains None → graceful skip)
      ✗ on_chain_bias (component remains None → graceful skip)
    """
    symbol = tentative["asset"]
    side = tentative["side"]
    entry = float(tentative["entry"])
    tp1 = float(tentative["tp1"])
    rr_tp1 = float(tentative.get("rr_tp1", 0))
    pnl_per_trade = float(tentative.get("backtest_pnl_per_trade", 0))
    components = {
        "backtest_pnl_per_trade": pnl_per_trade,
        "backtest_n_trades": tentative.get("backtest_n_trades"),
        "rr_tp1": rr_tp1,
        "entry": entry,
        "tp1": tp1,
    }

    # multifactor — needs bars1h
    try:
        bars1h = fetch_bars(symbol, "1h", 100)
        if len(bars1h) >= 50:
            mf = _multifactor_from_bars(bars1h)
            if mf is not None:
                components["multifactor_score"] = mf
    except Exception:
        pass

    # OBV slope verdict — call volume_divergence helper inline
    try:
        from volume_divergence import detect_divergence, fetch_bars as _vd_fetch
        vd_bars = _vd_fetch(symbol, "1h", 50)
        verdict = detect_divergence(vd_bars, direction=side)
        components["obv_verdict"] = verdict.get("verdict", "OK")
    except Exception:
        pass

    # liq_heatmap → magnet on entry side + Smart Money L/S piggybacked
    try:
        liq = _sub_json(
            [str(SCRIPTS_DIR / "liq_heatmap.py"), "--symbol", symbol],
            timeout=20,
        )
        if liq:
            mag = liq.get("magnet")
            if mag and mag.get("price"):
                components["liq_magnet"] = float(mag["price"])
            sm_ls = liq.get("smart_money_ls")
            rt_ls = liq.get("retail_ls")
            if sm_ls is not None:
                components["smart_money_ls"] = float(sm_ls)
            if rt_ls is not None:
                components["retail_ls"] = float(rt_ls)
    except Exception:
        pass

    # fib_extension --mode retracement → derive zone label
    try:
        fib = _sub_json(
            [str(SCRIPTS_DIR / "fib_extension.py"),
             "--symbol", symbol, "--tf", "1h",
             "--mode", "retracement", "--json"],
            timeout=20,
        )
        zone = _fib_zone_from_levels(fib, entry) if fib else None
        if zone:
            components["fib_zone"] = zone
    except Exception:
        pass

    # pump_detector
    try:
        pump = _sub_json(
            [str(SCRIPTS_DIR / "pump_detector.py"), "--symbol", symbol, "--json"],
            timeout=15,
        )
        if pump:
            components["pump_score"] = pump.get("score")
            components["pump_side_bias"] = pump.get("side_bias")
    except Exception:
        pass

    # on-chain bias (BTC/ETH only — cached 1h)
    if symbol.replace(".P", "").upper() in ("BTCUSDT", "ETHUSDT"):
        try:
            oc = _sub_json(
                [str(SCRIPTS_DIR / "btc_onchain.py"),
                 "--symbol", symbol.replace(".P", "")],
                timeout=15,
            )
            if oc and oc.get("bias"):
                components["on_chain_bias"] = oc["bias"]
        except Exception:
            pass

    return components


def _fib_zone_from_levels(fib: dict, price: float) -> str | None:
    """Classify `price` into a fib retracement bucket.

    fib JSON shape: {direction: long|short, swing_high, swing_low,
                     entry_zones: {382, 500, 618}, sl_075, tp_swing}
    """
    try:
        sh = float(fib["swing_high"])
        sl = float(fib["swing_low"])
        direction = (fib.get("direction") or "").lower()
        rng = sh - sl
        if rng <= 0:
            return None
        # Retracement fraction along the rng (0 = no retrace, 1 = full)
        if direction == "long":
            ret = (sh - price) / rng
        else:
            ret = (price - sl) / rng
        if ret < 0.382 or ret > 0.886:
            return "OUT"
        if ret < 0.5:
            return "SHALLOW"
        if ret < 0.618:
            return "GOLDEN"
        if ret < 0.786:
            return "OTE"
        return "DEEP"
    except (KeyError, TypeError, ValueError):
        return None


def _multifactor_from_bars(bars1h: list[dict]) -> float | None:
    """Inline call to wally_core composite_score using the router's bars."""
    try:
        from wally_core.multifactor import composite_score
        normalized = [
            {"open": b["o"], "high": b["h"], "low": b["l"],
             "close": b["c"], "volume": b.get("v", 0)}
            for b in bars1h
        ]
        result = composite_score(normalized)
        # wally_core returns dict {score: -100..100, ...}
        if isinstance(result, dict):
            return float(result.get("score", 0))
        if isinstance(result, (int, float)):
            return float(result)
    except Exception:
        return None
    return None


def _usdt_d_bias() -> str | None:
    """Cached USDT.D bias from usdtd_tracker."""
    out = _sub_json([str(SCRIPTS_DIR / "usdtd_tracker.py"), "--json"])
    if out is None:
        return None
    bias = out.get("btc_inverse_bias")
    return bias.upper() if bias else None


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def _csv_append(path: Path, fields: dict, fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            w.writeheader()
        w.writerow({k: fields.get(k, "") for k in fieldnames})


def log_pick(pick: dict, origin: str) -> Path:
    """Append the pick to the paper or live autohunt log CSV."""
    target = PAPER_LOG_CSV if origin.endswith("paper") else LIVE_AUTOHUNT_LOG_CSV
    components_used = ",".join(
        c["name"] for c in pick.get("score_components", []) if c.get("used")
    )
    row = {
        "tick_ts": pick["tick_ts"],
        "origin": origin,
        "symbol": pick["symbol"],
        "side": pick["side"],
        "entry": pick["entry"],
        "sl": pick["sl"],
        "tp1": pick["tp1"],
        "tp2": pick["tp2"],
        "tp3": pick["tp3"],
        "close_pct": json.dumps(pick["close_pct"]),
        "score": pick["score"],
        "tier": pick["tier"],
        "regime": pick["regime"],
        "strategy": pick.get("strategy", ""),
        "expected_move_pct": pick["expected_move_pct"],
        "atr_pct_15m": pick["atr_pct_15m"],
        "tp1_usd": pick["tp1_usd"],
        "tp2_usd": pick["tp2_usd"],
        "tp3_usd": pick["tp3_usd"],
        "margin_usd": pick["margin_usd"],
        "leverage": pick["leverage"],
        "session_quality": pick.get("session_quality", ""),
        "macro_tier": pick.get("macro_tier", ""),
        "components_used": components_used,
        "outcome": "pending",
        "exit_price": "",
        "pnl_usd": "",
        "duration_h": "",
    }
    _csv_append(target, row, PAPER_CSV_FIELDS)
    return target


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------
def _human_pick(pick: dict, ctx: dict) -> str:
    arrow = "🟢 LONG" if pick["side"] == "LONG" else "🔴 SHORT"
    lines = [
        f"\n{'=' * 72}",
        f"PUNK-AUTOHUNT — hourly tick {ctx['now_str']}  |  pick {ctx['today_count'] + 1}/{DAILY_CAP} today, "
        f"{ctx['concurrent_open']}/{CONCURRENT_CAP} concurrent  |  ORIGIN: {ctx['origin']}",
        "=" * 72,
        "",
        f"ASSET: {pick['symbol']}  SIDE: {arrow}  SCORE: {pick['score']}/100  TIER: {pick['tier']}",
        f"Regime: {pick['regime']} 15m  |  Strategy: {pick.get('strategy','-')}  "
        f"(BT $/trade ${pick.get('backtest_pnl_per_trade', 0):+.2f})",
        "",
        f"  Entry: {pick['entry']}  SL: {pick['sl']}",
        f"  TP1:   {pick['tp1']}  (+{pick['tp1_pct']:.2f}%, +${pick['tp1_usd']:.2f})   close {int(pick['close_pct'][0]*100)}%",
        f"  TP2:   {pick['tp2']}  (+{pick['tp2_pct']:.2f}%, +${pick['tp2_usd']:.2f})   close {int(pick['close_pct'][1]*100)}%",
        f"  TP3:   {pick['tp3']}  (+{pick['tp3_pct']:.2f}%, +${pick['tp3_usd']:.2f})   close {int(pick['close_pct'][2]*100)}%",
        "",
        f"  Expected move: {pick['expected_move_pct']:.2f}%  |  ATR(15m)%: {pick['atr_pct_15m']:.3f}",
        f"  Sizing: ${pick['margin_usd']} margin × {pick['leverage']}x = ${pick['margin_usd']*pick['leverage']:.0f} notional",
        f"  Session: {pick.get('session_quality','OK')}  |  Macro: {pick.get('macro_tier','OK')}",
        f"  Floor status: {pick['floor_status']}",
    ]
    if pick.get("margin_bumped"):
        lines.append(f"  ⚠ Margin bumped from $50 → ${pick['margin_usd']} (A-GRADE floor edge)")
    if pick.get("atr_extreme"):
        lines.append(f"  ⚠ ATR EXTREME — flagged but pick survived (manual override risk)")

    return "\n".join(lines)


def _human_no_pick(reasons: list[dict], ctx: dict) -> str:
    lines = [
        f"\n⏳ PUNK-AUTOHUNT — no A/B-grade setup at {ctx['now_str']}",
        "",
        f"  Evaluated {ctx.get('evaluated', 0)} assets. Top-5 drops:",
    ]
    for r in reasons[:5]:
        lines.append(f"  - {r['symbol']:12s} {r.get('side','--'):5s} reason: {r['reason']}")
    lines.append("")
    lines.append(f"  Slot: {ctx['today_count']}/{DAILY_CAP} today, {ctx['concurrent_open']}/{CONCURRENT_CAP} concurrent")
    lines.append(f"  Next tick: in ~60 min")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Hourly autonomous best-pick selector")
    ap.add_argument("--paper", action="store_true",
                    help="Paper mode — log to autohunt_paper_log.csv (no TV, no live)")
    ap.add_argument("--dry-run", action="store_true",
                    help="No CSV write, no TV draw — just emit the report")
    ap.add_argument("--asset", help="Force a single asset (skips universe build)")
    ap.add_argument("--json", action="store_true", help="JSON output to stdout")
    ap.add_argument("--margin", type=float, default=MARGIN_USD_DEFAULT)
    ap.add_argument("--leverage", type=int, default=LEVERAGE_DEFAULT)
    ap.add_argument("--dynamic", choices=["volume", "movers", "trending"],
                    help="Pull universe dynamically (top-N + Bitunix tradeable). "
                         "Falls back to static universe if discovery fails.")
    ap.add_argument("--top-n", type=int, default=10,
                    help="N for --dynamic (default 10)")
    ap.add_argument("--min-vol-usd", type=float, default=1_000_000,
                    help="Min 24h volume USD for --dynamic filter (default $1M)")
    args = ap.parse_args()

    origin = "autohunt-paper" if args.paper else "autohunt"
    now = datetime.now(CR_OFFSET)
    now_str = now.strftime("%H:%M CR")

    # STAGE 0
    pre = stage0_preflight(now, args)
    if not pre["pass"]:
        msg = f"🚫 PUNK-AUTOHUNT — blocked: {pre['reason']}"
        if args.json:
            print(json.dumps({"status": "BLOCKED", "reason": pre["reason"]}))
        else:
            print(msg)
        return 1

    # STAGE 1
    ms = stage1_macro_session()
    if ms["macro_tier"] == "HARD":
        msg = f"🚫 PUNK-AUTOHUNT — blocked: macro HARD ({ms['macro_reason']})"
        if args.json:
            print(json.dumps({"status": "BLOCKED", "reason": msg}))
        else:
            print(msg)
        return 1
    if ms["session_quality"] == "BLOCK":
        msg = f"🚫 PUNK-AUTOHUNT — blocked: session quality BLOCK (dead session)"
        if args.json:
            print(json.dumps({"status": "BLOCKED", "reason": msg}))
        else:
            print(msg)
        return 1

    # STAGE 2 — universe
    if args.asset:
        targets = [args.asset]
    elif args.dynamic:
        if args.dynamic == "volume":
            raw_disc = mctx.fetch_top_volume_binance(n=args.top_n)
        elif args.dynamic == "movers":
            raw_disc = mctx.fetch_top_movers_binance(n=args.top_n)
        else:
            raw_disc = mctx.fetch_trending_coingecko(n=args.top_n)
        if raw_disc:
            symbols = [r["symbol"] for r in raw_disc]
            tradeable = mctx.filter_tradeable_bitunix(
                symbols, min_vol_usd=args.min_vol_usd)
            targets = [t["symbol"] for t in tradeable] or UNIVERSE
        else:
            targets = UNIVERSE
    else:
        targets = UNIVERSE

    mapping = router.load_mapping()

    # STAGE 3 — per-asset analytics
    enabled_vetos = mapping.get("vetos_enabled",
                                 ["macro", "blacklist", "correlation",
                                  "sentiment", "funding", "time_of_day"])
    raw = []
    for sym in targets:
        try:
            res = router.evaluate_asset(sym, mapping, now)
        except Exception as e:
            raw.append({"asset": sym, "status": "ERROR", "reason": str(e)})
            continue
        raw.append(res)

    usdt_bias = _usdt_d_bias()
    survivors = []
    drops = []

    for r in raw:
        sym = r.get("asset", "?")
        if r.get("status") != "TENTATIVE":
            drops.append({
                "symbol": sym,
                "side": r.get("side", "--"),
                "reason": f"{r.get('status', '?')}: {r.get('reason', '')}",
            })
            continue

        # vetos — re-run identical to router
        ctx = {
            "now": now,
            "memory_dir": None,
            "regime_pnl_per_trade": r.get("backtest_pnl_per_trade", 0.0),
            "enabled": enabled_vetos,
        }
        veto_results = vetos.evaluate({"asset": sym, "side": r["side"]}, ctx)
        all_passed = all(v.passed for v in veto_results)
        sentiment_pass = next(
            (v.passed for v in veto_results if v.name == "sentiment"), True)
        funding_pass = next(
            (v.passed for v in veto_results if v.name == "funding"), True)
        if not all_passed:
            failed = [v.name for v in veto_results if not v.passed]
            drops.append({
                "symbol": sym,
                "side": r["side"],
                "reason": f"VETOED ({','.join(failed)})",
            })
            continue

        # confluence components
        atr_15m = float(r.get("atr_15m", 0)) or float(r.get("_atr_15m", 0) or 0)
        entry = float(r["entry"])
        atr_pct = (atr_15m / entry * 100) if entry > 0 else 0.0

        comps = stage3_enrich(r)
        comps["sentiment_funding_passed"] = sentiment_pass and funding_pass
        if ascore._is_btc_eth(sym):
            comps["usdt_d_bias"] = usdt_bias

        # STAGE 5 — score
        score_out = ascore.compute_score(
            symbol=sym,
            side=r["side"],
            **comps,
        )
        if score_out["tier"] == "DROP":
            drops.append({
                "symbol": sym,
                "side": r["side"],
                "reason": f"score {score_out['score']} < 60 ({score_out['tier']})",
            })
            continue

        # STAGE 6 — TP plan + floor (Appendix B: atr_percentile drives extreme-vol gate)
        tp_plan = atp.compute_tp_plan(
            side=r["side"],
            entry=entry,
            atr_pct_15m=atr_pct,
            regime=r["regime"],
            confluence_score=score_out["score"],
            session_quality=ms["session_quality"],
            margin_usd=args.margin,
            leverage=args.leverage,
            atr_percentile=r.get("atr_percentile"),
        )
        if tp_plan["atr_extreme"]:
            drops.append({
                "symbol": sym,
                "side": r["side"],
                "reason": "ATR_EXTREME (top 5% — too violent)",
            })
            continue
        if not tp_plan["floor_passed"]:
            drops.append({
                "symbol": sym,
                "side": r["side"],
                "reason": f"PnL_FLOOR ({tp_plan['floor_status']}, TP3=${tp_plan['tp3_usd']})",
            })
            continue

        survivors.append({
            "symbol": sym,
            "side": r["side"],
            "entry": entry,
            "sl": float(r["sl"]),
            "tp1": tp_plan["tp1"],
            "tp2": tp_plan["tp2"],
            "tp3": tp_plan["tp3"],
            "tp1_pct": tp_plan["tp1_pct"],
            "tp2_pct": tp_plan["tp2_pct"],
            "tp3_pct": tp_plan["tp3_pct"],
            "tp1_usd": tp_plan["tp1_usd"],
            "tp2_usd": tp_plan["tp2_usd"],
            "tp3_usd": tp_plan["tp3_usd"],
            "close_pct": tp_plan["close_pct"],
            "expected_move_pct": tp_plan["expected_move_pct"],
            "atr_pct_15m": atr_pct,
            "score": score_out["score"],
            "tier": score_out["tier"],
            "score_components": score_out["components"],
            "regime": r["regime"],
            "strategy": r.get("strategy", ""),
            "backtest_pnl_per_trade": r.get("backtest_pnl_per_trade", 0),
            "session_quality": ms["session_quality"],
            "macro_tier": ms["macro_tier"],
            "margin_usd": tp_plan["margin_used_usd"],
            "leverage": tp_plan["leverage"],
            "margin_bumped": tp_plan["margin_bumped"],
            "floor_status": tp_plan["floor_status"],
            "atr_extreme": tp_plan["atr_extreme"],
        })

    # STAGE 7 — single-best-pick selection
    pick = None
    if survivors:
        survivors.sort(key=lambda x: (-x["score"], -x["tp3_usd"]))
        pick = survivors[0]
        pick["tick_ts"] = now.isoformat()

    out_ctx = {
        "now_str": now_str,
        "today_count": pre["today_count"],
        "concurrent_open": pre["concurrent_open"],
        "evaluated": len(raw),
        "origin": origin,
    }

    # STAGE 8 — TV draw: emitted as JSON instruction, Claude parent executes
    draw_instructions = None
    if pick and not args.paper and not args.dry_run:
        draw_instructions = _make_draw_instructions(pick)

    # STAGE 9 — log
    log_path = None
    if pick and not args.dry_run:
        log_path = log_pick(pick, origin=origin)

    # macOS notification on A-GRADE pick (best-effort; silent on failure / non-macOS)
    if pick and pick.get("tier") == "A-GRADE":
        try:
            import subprocess as _sp, shlex as _sh
            arrow = "LONG" if pick["side"] == "LONG" else "SHORT"
            title = f"🎯 Autohunt {pick['tier']} — {pick['symbol']} {arrow}"
            msg = (f"Score {pick['score']}/100  TP3 ${pick['tp3_usd']:.0f}  "
                   f"Regime {pick['regime']}")
            script = (f'display notification {_sh.quote(msg)} '
                      f'with title {_sh.quote(title)} sound name "Glass"')
            _sp.run(["osascript", "-e", script],
                    timeout=5, stderr=_sp.DEVNULL, stdout=_sp.DEVNULL)
        except Exception:
            pass

    # OUTPUT
    if args.json:
        print(json.dumps({
            "status": "PICK" if pick else "NO_PICK",
            "tick_ts": now.isoformat(),
            "origin": origin,
            "pick": pick,
            "drops": drops,
            "session_quality": ms["session_quality"],
            "macro_tier": ms["macro_tier"],
            "log_path": str(log_path) if log_path else None,
            "draw_instructions": draw_instructions,
            "today_count": pre["today_count"],
            "concurrent_open": pre["concurrent_open"],
        }, indent=2, default=str))
        return 0

    if pick:
        print(_human_pick(pick, out_ctx))
        if log_path:
            print(f"\n📤 Logged to {log_path.name}")
        if draw_instructions:
            print(f"🎨 TV draw instructions emitted ({len(draw_instructions)} shapes) — "
                  "parent agent will execute via MCP")
    else:
        print(_human_no_pick(drops, out_ctx))

    return 0


def _make_draw_instructions(pick: dict) -> list[dict]:
    """Emit a list of MCP draw_shape kwargs for the parent Claude to execute."""
    sym = pick["symbol"]
    shapes = [
        {"shape": "horizontal_line", "price": pick["entry"],
         "label": f"autohunt:ENTRY {pick['entry']}", "color": "yellow"},
        {"shape": "horizontal_line", "price": pick["sl"],
         "label": f"autohunt:SL {pick['sl']}", "color": "red"},
        {"shape": "horizontal_line", "price": pick["tp1"],
         "label": f"autohunt:TP1 +${pick['tp1_usd']:.0f}", "color": "lightgreen"},
        {"shape": "horizontal_line", "price": pick["tp2"],
         "label": f"autohunt:TP2 +${pick['tp2_usd']:.0f}", "color": "green"},
        {"shape": "horizontal_line", "price": pick["tp3"],
         "label": f"autohunt:TP3 +${pick['tp3_usd']:.0f}", "color": "darkgreen"},
    ]
    return [{"symbol": f"BITUNIX:{sym}.P", **s} for s in shapes]


if __name__ == "__main__":
    sys.exit(main())
