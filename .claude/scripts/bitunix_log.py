#!/usr/bin/env python3
"""bitunix_log.py — append signals + outcomes to bitunix log files.

Subcommands:
  append-signal --stdin    : parse a /signal markdown report and append entry to MD + CSV
  append-outcome SYMBOL OUTCOME EXIT_PRICE [--id N] [--pnl USD] : close an open entry

Profile gating: only writes when WALLY_PROFILE == "bitunix". Otherwise no-op exit 0.
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CR_OFFSET = timezone(timedelta(hours=-6))
CSV_FIELDS = [
    "date", "time", "symbol", "side", "entry", "sl", "tp", "leverage_signal",
    "day_of_week", "filters_4", "multifactor", "ml_score", "chainlink_delta",
    "regime", "pillars_4_count", "saturday", "verdict", "decision", "size_pct",
    "executed", "exit_price", "exit_reason", "pnl_usd", "duration_h",
    "hypothetical_outcome", "learning",
]


def repo_root() -> Path:
    """Find repo root by walking up from cwd looking for .claude/ dir."""
    cur = Path.cwd()
    while cur != cur.parent:
        if (cur / ".claude").is_dir():
            return cur
        cur = cur.parent
    return Path.cwd()


def bitunix_paths() -> tuple[Path, Path]:
    root = repo_root()
    base = root / ".claude" / "profiles" / "bitunix" / "memory"
    return base / "signals_received.md", base / "signals_received.csv"


def is_bitunix_profile() -> bool:
    return os.environ.get("WALLY_PROFILE", "") == "bitunix"


def log_error(msg: str, body: str = "") -> None:
    err_path = repo_root() / ".claude" / "cache" / "bitunix_log_errors.log"
    err_path.parent.mkdir(parents=True, exist_ok=True)
    with err_path.open("a") as f:
        f.write(f"--- {datetime.now(CR_OFFSET).isoformat()} {msg} ---\n")
        if body:
            f.write(body + "\n")


def parse_signal_report(text: str) -> dict[str, str]:
    """Extract fields from a canonical /signal markdown report.

    Raises ValueError on parse failure (missing required fields).
    """

    def grab(pattern: str, default: str = "", flags: int = 0) -> str:
        m = re.search(pattern, text, flags)
        return m.group(1).strip() if m else default

    fields: dict[str, str] = {
        "symbol": grab(r"\*\*Symbol:\*\*\s*(\S+)"),
        "side": grab(r"\*\*Side:\*\*\s*(LONG|SHORT)"),
        "entry": grab(r"\*\*Entry:\*\*\s*([\d.]+)"),
        "sl": grab(r"\*\*SL:\*\*\s*([\d.]+)"),
        "tp": grab(r"\*\*TP:\*\*\s*([\d.]+)"),
        "leverage_signal": grab(r"\*\*Leverage signal:\*\*\s*([\d.]+)x?"),
        "day_of_week": grab(r"\*\*Day-of-week:\*\*\s*(\w+)"),
        "filters_4": grab(r"4 filtros t[eé]cnicos:\*\*\s*(\d)/4"),
        "multifactor": grab(r"Multi-Factor:\*\*\s*([+\-\d]+)"),
        "ml_score": grab(r"\bML:\*\*\s*([\d.]+)"),
        "chainlink_delta": grab(r"Chainlink delta:\*\*\s*([\d.]+)%"),
        "regime": grab(r"R[eé]gimen:\*\*\s*(RANGE|TRENDING|VOLATILE)"),
        "pillars_4_count": grab(r"4-Pilar Neptune SMC:\*\*\s*(\d)/4"),
        "verdict": grab(r"Veredicto:\*\*\s*(APPROVE_FULL|APPROVE_HALF|REJECT)"),
        "decision": grab(r"Decisi[oó]n:\*\*\s*([^\n]+)"),
        "validation_score": grab(r"Validation Score:\*\*\s*(\d+)/100"),
    }

    # Saturday Protocol: "N" if N/A or absent, "Y" if explicitly active
    sat_line = grab(r"Saturday Protocol:\*\*\s*([^\n]+)")
    fields["saturday"] = "N" if (not sat_line or "N/A" in sat_line) else "Y"

    # size_pct: extract the numeric % from the decision line
    size_m = re.search(r"size\s+(\d+)%", fields["decision"], re.IGNORECASE)
    if not size_m:
        # fallback: look anywhere in document for "full size N%" or "half size N%"
        size_m = re.search(r"(?:full|half)\s+size\s+(\d+)%", text, re.IGNORECASE)
    fields["size_pct"] = size_m.group(1) if size_m else ""

    # executed flag
    decision_lower = fields["decision"].lower()
    if "ejecutado" in decision_lower:
        fields["executed"] = "yes"
    elif "skip" in decision_lower:
        fields["executed"] = "no"
    else:
        fields["executed"] = ""

    # Check required fields
    required = ["symbol", "side", "entry", "sl", "tp", "verdict"]
    missing = [k for k in required if not fields[k]]
    if missing:
        raise ValueError(f"Missing required fields in signal report: {missing}")

    # Timestamp in CR timezone
    now = datetime.now(CR_OFFSET)
    fields["date"] = now.strftime("%Y-%m-%d")
    fields["time"] = now.strftime("%H:%M")

    # Ensure all CSV fields have a value (empty string default)
    for k in ("exit_price", "exit_reason", "pnl_usd", "duration_h",
              "hypothetical_outcome", "learning"):
        fields.setdefault(k, "")

    return fields


def render_md_entry(fields: dict[str, str]) -> str:
    """Render a markdown block for the signals_received.md file."""
    return (
        f"\n## {fields['date']} {fields['time']} — "
        f"{fields['symbol']} {fields['side']} {fields['leverage_signal']}x\n\n"
        f"**Señal recibida:** entry {fields['entry']}, SL {fields['sl']}, "
        f"TP {fields['tp']}, leverage {fields['leverage_signal']}x\n"
        f"**Source:** punkchainer Discord\n"
        f"**Day-of-week:** {fields['day_of_week']}\n\n"
        f"**Pipeline validación (8 steps):**\n"
        f"  1. Parse OK\n"
        f"  2. 4 filtros técnicos: {fields['filters_4']}/4\n"
        f"  3. Multi-Factor: {fields['multifactor']} ({fields['side']}) | ML: {fields['ml_score']}\n"
        f"  4. Chainlink delta: {fields['chainlink_delta']}% (OK)\n"
        f"  5. Régimen: {fields['regime']} — compatible con {fields['side']}? Y\n"
        f"  6. **4-Pilar Neptune SMC: {fields['pillars_4_count']}/4**\n"
        f"  7. Saturday Protocol activo? {fields['saturday']}\n"
        f"  8. Veredicto: {fields['verdict']}\n\n"
        f"**Validation Score:** {fields['validation_score']}/100\n"
        f"**Decisión:** {fields['decision']}\n\n"
        f"**Resultado real:**\n"
        f"  - Outcome: _pendiente_\n"
        f"  - Exit price: _pendiente_\n"
        f"  - PnL: _pendiente_\n"
        f"  - Time to outcome: _pendiente_\n\n"
        f"**Aprendizaje:** _pendiente_\n\n"
        f"---\n"
    )


def append_md(md_path: Path, entry: str) -> None:
    md_path.parent.mkdir(parents=True, exist_ok=True)
    if not md_path.exists():
        md_path.write_text("# Bitunix — Signals received\n\n## Histórico\n\n")
    with md_path.open("a") as f:
        f.write(entry)


def append_csv(csv_path: Path, fields: dict[str, str]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with csv_path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if write_header:
            w.writeheader()
        w.writerow({k: fields.get(k, "") for k in CSV_FIELDS})


def cmd_append_signal(args: argparse.Namespace) -> int:
    if not is_bitunix_profile():
        return 0  # silent no-op

    text = sys.stdin.read()
    try:
        fields = parse_signal_report(text)
    except ValueError as e:
        log_error(f"parse failed: {e}", text)
        print(
            "WARNING: bitunix_log parse failed, see cache/bitunix_log_errors.log",
            file=sys.stderr,
        )
        return 1

    md_path, csv_path = bitunix_paths()
    append_md(md_path, render_md_entry(fields))
    append_csv(csv_path, fields)
    print(f"bitunix_log: appended {fields['symbol']} {fields['side']} to {md_path.name}")
    return 0


def cmd_append_outcome(args: argparse.Namespace) -> int:
    """Implemented in Task 2.2."""
    raise NotImplementedError("append-outcome implemented in Task 2.2")


def main() -> int:
    p = argparse.ArgumentParser(
        description="Bitunix signal log manager",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sig = sub.add_parser("append-signal", help="Append a /signal report to MD + CSV")
    sig.add_argument("--stdin", action="store_true", required=True,
                     help="Read signal report from stdin")
    sig.set_defaults(func=cmd_append_signal)

    out = sub.add_parser("append-outcome", help="Update an open signal with its outcome")
    out.add_argument("symbol")
    out.add_argument("outcome", choices=["TP1", "TP2", "TP3", "SL", "manual"])
    out.add_argument("exit_price", type=float)
    out.add_argument("--id", dest="entry_id", type=int, default=None)
    out.add_argument("--pnl", type=float, default=None)
    out.set_defaults(func=cmd_append_outcome)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
