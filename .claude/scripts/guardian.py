"""
guardian.py — FTMO rules engine for Claude trading system.

Usage:
    python guardian.py --profile ftmo --action status
    python guardian.py --profile ftmo --action check-entry --asset BTCUSD \
                       --entry 77538 --sl 77238 --size 0.1
    python guardian.py --profile ftmo --action equity-update --value 10247
"""
import argparse
import csv
import json
import re
import sys
from datetime import datetime, date
from pathlib import Path


def load_equity_curve(csv_path):
    """Load equity_curve.csv into list of dicts with parsed timestamps."""
    p = Path(csv_path)
    if not p.exists():
        return []
    rows = []
    with open(p, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "timestamp": datetime.fromisoformat(r["timestamp"]),
                "equity": float(r["equity"]),
                "source": r["source"],
                "note": r.get("note", ""),
            })
    rows.sort(key=lambda x: x["timestamp"])
    return rows


def peak_equity(curve):
    """Highest equity value in the curve. 0.0 if empty."""
    if not curve:
        return 0.0
    return max(r["equity"] for r in curve)


def daily_pnl(curve, target_date):
    """Equity delta for a specific calendar date.
    Returns 0.0 if no data or only one point on the date.
    """
    today_rows = [r for r in curve if r["timestamp"].date() == target_date]
    if len(today_rows) < 2:
        return 0.0
    # Sorted chronologically by load_equity_curve
    return today_rows[-1]["equity"] - today_rows[0]["equity"]


def trailing_dd(curve):
    """Drawdown from the peak equity. Positive value = in drawdown.
    0.0 if empty or at new peak.
    """
    if not curve:
        return 0.0
    peak = peak_equity(curve)
    last = curve[-1]["equity"]
    dd = peak - last
    return max(0.0, dd)


def day_profits(curve):
    """Dict mapping date -> profit for that date (equity end - equity start).
    Only includes dates with 2+ entries.
    """
    by_date = {}
    for row in curve:
        d = row["timestamp"].date()
        by_date.setdefault(d, []).append(row)
    result = {}
    for d, rows in by_date.items():
        if len(rows) < 2:
            continue
        rows.sort(key=lambda x: x["timestamp"])
        result[d] = rows[-1]["equity"] - rows[0]["equity"]
    return result


def best_day_ratio(curve):
    """Returns (best_day_profit, total_positive_profit).
    Only positive days are counted toward total.
    """
    profits = day_profits(curve)
    positive = [p for p in profits.values() if p > 0]
    if not positive:
        return (0.0, 0.0)
    return (max(positive), sum(positive))


def load_profile_config(config_md_path):
    """Parse the YAML block inside config.md. Returns dict."""
    text = Path(config_md_path).read_text()
    # Find first ```yaml ... ``` block
    m = re.search(r"```yaml\s*\n(.*?)\n```", text, re.DOTALL)
    if not m:
        raise ValueError(f"No YAML block in {config_md_path}")
    yaml_text = m.group(1)
    # Simple YAML parse (numeric/string values only, no nesting)
    result = {}
    for line in yaml_text.splitlines():
        line = line.split("#", 1)[0].strip()  # strip inline comments
        if not line:
            continue
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()
        # Try numeric
        try:
            if "." in val:
                result[key] = float(val)
            else:
                result[key] = int(val)
        except ValueError:
            result[key] = val
    return result


def _count_trades_today(curve, target_date):
    """Rows with source == 'trade' dated today."""
    return sum(
        1 for r in curve
        if r["timestamp"].date() == target_date and r["source"] == "trade"
    )


def _consecutive_sl_today(curve, target_date):
    """Count trailing consecutive SL events today (based on 'SL' substring in note)."""
    today_trades = [
        r for r in curve
        if r["timestamp"].date() == target_date and r["source"] == "trade"
    ]
    if not today_trades:
        return 0
    today_trades.sort(key=lambda x: x["timestamp"])
    count = 0
    for r in reversed(today_trades):
        if "SL" in r["note"].upper():
            count += 1
        else:
            break
    return count


def check_entry(cfg, curve, trade, now=None):
    """Evaluates whether the proposed trade respects all rules.

    trade dict must include: asset, entry, sl, loss_if_sl (pre-computed USD at SL).
    Returns dict with: verdict, blocking, reason, warnings, size_adjustment.
    """
    if now is None:
        now = datetime.now()
    today = now.date()
    initial = cfg.get("initial_capital", 10000)
    daily_limit_usd = initial * cfg.get("max_daily_loss_pct", 3) / 100.0
    trailing_limit_usd = initial * cfg.get("max_total_trailing_pct", 10) / 100.0
    trailing_warn_threshold_usd = trailing_limit_usd * 0.8
    best_day_cap_pct = cfg.get("best_day_cap_pct", 50)
    best_day_info_threshold = best_day_cap_pct / 100.0 * 0.9  # 0.45 if cap is 50

    loss_if_sl = trade["loss_if_sl"]
    warnings = []

    # REGLA 4: Max trades/día
    trades_today = _count_trades_today(curve, today)
    if trades_today >= cfg.get("max_trades_per_day", 2):
        return {
            "verdict": "BLOCK_HARD",
            "blocking": True,
            "reason": f"Max trades/día ({trades_today}/{cfg['max_trades_per_day']}) alcanzado.",
            "warnings": [],
            "size_adjustment": None,
        }

    # REGLA 5: 2 SLs consecutivos
    if _consecutive_sl_today(curve, today) >= cfg.get("max_sl_consecutive", 2):
        return {
            "verdict": "BLOCK_HARD",
            "blocking": True,
            "reason": "2 SLs consecutivos hoy. STOP por regla psicológica.",
            "warnings": [],
            "size_adjustment": None,
        }

    # REGLA 1: Daily 3%
    daily = daily_pnl(curve, today)
    daily_after_sl = daily - loss_if_sl
    if daily_after_sl <= -daily_limit_usd:
        # Check if ANY size avoids breach
        margin_remaining = daily_limit_usd + daily  # how much more we can lose today
        if margin_remaining <= 0:
            return {
                "verdict": "BLOCK_HARD",
                "blocking": True,
                "reason": (
                    f"Daily loss ya en ${-daily:.2f} ({-daily/initial*100:.2f}%). "
                    f"Ningún size permitido hoy. Reset mañana 06:00 CR."
                ),
                "warnings": [],
                "size_adjustment": None,
            }
        # Size adjustment
        if loss_if_sl > 0:
            size_adj_factor = margin_remaining / loss_if_sl
            return {
                "verdict": "BLOCK_SIZE",
                "blocking": True,
                "reason": (
                    f"Size propuesto pierde ${loss_if_sl:.2f} si SL. "
                    f"Daily margin restante ${margin_remaining:.2f}. "
                    f"Reduce size a {size_adj_factor:.2%} del propuesto."
                ),
                "warnings": [],
                "size_adjustment": size_adj_factor,
            }

    # REGLA 2: Trailing 10% WARN
    dd = trailing_dd(curve)
    dd_after_sl = dd + loss_if_sl
    if dd_after_sl >= trailing_warn_threshold_usd:
        warnings.append(
            f"Trailing DD iría a ${dd_after_sl:.2f} "
            f"({dd_after_sl/initial*100:.1f}% del capital) — cerca del límite 10%."
        )

    # REGLA 3: Best Day INFO
    best, total = best_day_ratio(curve)
    if total > 0:
        ratio = best / total
        if ratio >= best_day_info_threshold:
            warnings.append(
                f"Best day ratio {ratio*100:.0f}% (cap {best_day_cap_pct}%). "
                "Distribuye más en próximos días."
            )

    verdict = "OK_WITH_WARN" if warnings else "OK"
    return {
        "verdict": verdict,
        "blocking": False,
        "reason": "Todas las reglas OK" if not warnings else "OK con advertencias",
        "warnings": warnings,
        "size_adjustment": None,
    }


def _action_status(cfg, curve):
    """Build status payload for --action status."""
    initial = cfg.get("initial_capital", 10000)
    if not curve:
        return {
            "equity_current": initial,
            "equity_peak": initial,
            "daily_pnl": 0.0,
            "daily_pnl_pct": 0.0,
            "trailing_dd": 0.0,
            "trailing_dd_pct": 0.0,
            "best_day": 0.0,
            "total_profit": 0.0,
            "best_day_ratio": 0.0,
        }
    today = date.today()
    current = curve[-1]["equity"]
    peak = peak_equity(curve)
    daily = daily_pnl(curve, today)
    dd = trailing_dd(curve)
    best, total = best_day_ratio(curve)
    return {
        "equity_current": current,
        "equity_peak": peak,
        "daily_pnl": daily,
        "daily_pnl_pct": (daily / initial) * 100,
        "trailing_dd": dd,
        "trailing_dd_pct": (dd / initial) * 100,
        "best_day": best,
        "total_profit": total,
        "best_day_ratio": (best / total) if total > 0 else 0.0,
    }


def _action_equity_update(curve_path, value, note=""):
    """Append a new row to equity_curve.csv."""
    ts = datetime.utcnow().replace(microsecond=0).isoformat()
    with open(curve_path, "a") as f:
        f.write(f"{ts},{value},manual,{note}\n")


def _action_check_entry(cfg, curve, args):
    trade = {
        "asset": args.asset,
        "entry": float(args.entry),
        "sl": float(args.sl),
        "loss_if_sl": float(args.loss_if_sl),
    }
    return check_entry(cfg, curve, trade)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True, choices=["ftmo", "retail"])
    parser.add_argument("--action", required=True,
                        choices=["status", "check-entry", "equity-update"])
    parser.add_argument("--profile-root",
                        default=str(Path(__file__).parent.parent / "profiles"))
    parser.add_argument("--brief", action="store_true",
                        help="Terse one-line output for statusline")
    # check-entry args
    parser.add_argument("--asset")
    parser.add_argument("--entry")
    parser.add_argument("--sl")
    parser.add_argument("--loss-if-sl", dest="loss_if_sl")
    # equity-update args
    parser.add_argument("--value")
    parser.add_argument("--note", default="")

    args = parser.parse_args()

    profile_root = Path(args.profile_root)
    config_path = profile_root / args.profile / "config.md"
    curve_path = profile_root / args.profile / "memory" / "equity_curve.csv"

    if args.action == "equity-update":
        if args.value is None:
            print("ERROR: --value required", file=sys.stderr)
            sys.exit(2)
        _action_equity_update(str(curve_path), float(args.value), args.note)
        print(json.dumps({"profile": args.profile, "action": "equity-update",
                          "equity": float(args.value), "ok": True}))
        return

    # For status and check-entry, load config and curve
    cfg = load_profile_config(str(config_path))
    curve = load_equity_curve(str(curve_path))

    if args.action == "status":
        payload = _action_status(cfg, curve)
        payload["profile"] = args.profile
        if args.brief:
            # One-line for statusline
            daily = payload["daily_pnl"]
            dd = payload["trailing_dd"]
            print(
                f"Daily: ${daily:+.0f} ({daily/cfg['initial_capital']*100:+.1f}%) "
                f"• DD: ${dd:.0f} ({dd/cfg['initial_capital']*100:.1f}%/10%)"
            )
        else:
            print(json.dumps(payload, indent=2))
        return

    if args.action == "check-entry":
        result = _action_check_entry(cfg, curve, args)
        result["profile"] = args.profile
        print(json.dumps(result, indent=2))
        return


if __name__ == "__main__":
    main()
