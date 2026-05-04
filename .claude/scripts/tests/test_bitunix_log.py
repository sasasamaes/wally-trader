import csv
import os
import shutil
import subprocess
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "bitunix"
SCRIPT = Path(__file__).parent.parent / "bitunix_log.py"


def run_log(args, cwd, env=None, stdin=None):
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(
        ["python3", str(SCRIPT), *args],
        capture_output=True, text=True, cwd=cwd, env=full_env, input=stdin
    )


def setup_bitunix_profile(tmp_path: Path) -> Path:
    """Create a minimal bitunix profile structure under tmp_path."""
    p = tmp_path / ".claude" / "profiles" / "bitunix" / "memory"
    p.mkdir(parents=True)
    (p / "signals_received.md").write_text("# Bitunix — Signals received\n\n## Histórico\n\n")
    (p / "signals_received.csv").write_text(
        "date,time,symbol,side,entry,sl,tp,leverage_signal,"
        "day_of_week,filters_4,multifactor,ml_score,chainlink_delta,"
        "regime,pillars_4_count,saturday,verdict,decision,size_pct,"
        "executed,exit_price,exit_reason,pnl_usd,duration_h,"
        "hypothetical_outcome,learning\n"
    )
    return tmp_path


def test_append_signal_no_op_on_non_bitunix_profile(tmp_path):
    setup_bitunix_profile(tmp_path)
    canonical = (FIXTURES / "signal_report_canonical.md").read_text()
    r = run_log(["append-signal", "--stdin"], cwd=tmp_path,
                env={"WALLY_PROFILE": "retail"}, stdin=canonical)
    assert r.returncode == 0
    md = (tmp_path / ".claude/profiles/bitunix/memory/signals_received.md").read_text()
    assert "## 2026" not in md  # no new entry


def test_append_signal_parses_canonical_report(tmp_path):
    setup_bitunix_profile(tmp_path)
    canonical = (FIXTURES / "signal_report_canonical.md").read_text()
    r = run_log(["append-signal", "--stdin"], cwd=tmp_path,
                env={"WALLY_PROFILE": "bitunix"}, stdin=canonical)
    assert r.returncode == 0, r.stderr
    md = (tmp_path / ".claude/profiles/bitunix/memory/signals_received.md").read_text()
    assert "BTCUSDT" in md
    assert "Validation Score:** 78/100" in md
    assert "APPROVE_FULL" in md

    csv_path = tmp_path / ".claude/profiles/bitunix/memory/signals_received.csv"
    rows = list(csv.DictReader(csv_path.open()))
    assert len(rows) == 1
    row = rows[0]
    assert row["symbol"] == "BTCUSDT"
    assert row["side"] == "LONG"
    assert row["entry"] == "67000"
    assert row["sl"] == "66500"
    assert row["tp"] == "68000"
    assert row["leverage_signal"] == "20"
    assert row["day_of_week"] == "Mon"
    assert row["filters_4"] == "4"
    assert row["multifactor"] == "+62"
    assert row["ml_score"] == "71"
    assert row["regime"] == "RANGE"
    assert row["pillars_4_count"] == "4"
    assert row["saturday"] == "N"
    assert row["verdict"] == "APPROVE_FULL"
    assert row["decision"] == "EJECUTADO full size 2%"
    assert row["size_pct"] == "2"
    assert row["executed"] == "yes"


def test_append_signal_malformed_input(tmp_path):
    setup_bitunix_profile(tmp_path)
    r = run_log(["append-signal", "--stdin"], cwd=tmp_path,
                env={"WALLY_PROFILE": "bitunix"},
                stdin="this is not a valid signal report")
    assert r.returncode != 0
    err_log = tmp_path / ".claude/cache/bitunix_log_errors.log"
    assert err_log.exists()
    assert "parse failed" in err_log.read_text().lower()
    md = (tmp_path / ".claude/profiles/bitunix/memory/signals_received.md").read_text()
    assert "## 2026" not in md
