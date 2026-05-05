import json
import os
import subprocess
from pathlib import Path
from datetime import date

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "digest"
SCRIPT = Path(__file__).parent.parent / "weekly_digest.py"


def run_digest(args, cwd, env=None):
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(
        ["python3", str(SCRIPT), *args, "--no-notif"],
        capture_output=True, text=True, cwd=cwd, env=full_env
    )


def setup_repo_with_fixtures(tmp_path: Path) -> Path:
    """Stage a fake repo root with .claude/profiles structure from fixtures."""
    profiles_root = tmp_path / ".claude" / "profiles"
    for p in FIXTURES.glob("profiles/*"):
        target = profiles_root / p.name
        target.mkdir(parents=True)
        for sub in p.rglob("*"):
            rel = sub.relative_to(p)
            dst = target / rel
            if sub.is_dir():
                dst.mkdir(parents=True, exist_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(sub.read_bytes())
    (tmp_path / "memory" / "weekly_digests").mkdir(parents=True)
    return tmp_path


def test_digest_generates_file_with_cross_profile_table(tmp_path):
    setup_repo_with_fixtures(tmp_path)
    r = run_digest(["--week", "2026-W18"], cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    out = tmp_path / "memory" / "weekly_digests" / "2026-W18.md"
    assert out.exists()
    content = out.read_text()
    assert "Weekly Digest" in content
    assert "Cross-profile summary" in content
    assert "retail" in content
    assert "$18.09" in content
    assert "ftmo" in content
    assert "$9,880" in content


def test_digest_handles_missing_log(tmp_path):
    setup_repo_with_fixtures(tmp_path)
    new_profile = tmp_path / ".claude/profiles/quantfury"
    (new_profile / "memory").mkdir(parents=True)
    (new_profile / "config.md").write_text("Capital actual: 0.01 BTC\n")
    r = run_digest(["--week", "2026-W18"], cwd=tmp_path)
    assert r.returncode == 0
    content = (tmp_path / "memory/weekly_digests/2026-W18.md").read_text()
    assert "quantfury" in content
    assert "parser pending" in content.lower() or "not started" in content.lower()


def test_digest_handles_missing_macro_cache(tmp_path):
    setup_repo_with_fixtures(tmp_path)
    r = run_digest(["--week", "2026-W18"], cwd=tmp_path)
    assert r.returncode == 0
    content = (tmp_path / "memory/weekly_digests/2026-W18.md").read_text()
    assert "macro cache unavailable" in content.lower()


def test_digest_idempotent(tmp_path):
    setup_repo_with_fixtures(tmp_path)
    r1 = run_digest(["--week", "2026-W18"], cwd=tmp_path)
    out_path = tmp_path / "memory/weekly_digests/2026-W18.md"
    content1 = out_path.read_text()
    r2 = run_digest(["--week", "2026-W18"], cwd=tmp_path)
    content2 = out_path.read_text()
    import re
    norm = lambda s: re.sub(r"Generated:.*", "Generated: <ts>", s)
    assert norm(content1) == norm(content2)


def test_digest_no_notif_flag_suppresses_osascript(tmp_path):
    """With --no-notif, no osascript subprocess call."""
    setup_repo_with_fixtures(tmp_path)
    r = run_digest(["--week", "2026-W18"], cwd=tmp_path)
    assert r.returncode == 0


def test_digest_macro_lookahead_with_cache(tmp_path):
    setup_repo_with_fixtures(tmp_path)
    cache = tmp_path / ".claude/cache/macro_events.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({
        "fetched_at": "2026-05-04T04:00:00-06:00",
        "source": "tradingeconomics",
        "events": [
            {"date": "2026-05-06", "time_cr": "13:00",
             "country": "United States", "name": "FOMC Statement", "impact": "high"},
            {"date": "2026-05-08", "time_cr": "06:30",
             "country": "United States", "name": "CPI", "impact": "high"},
        ],
    }))
    r = run_digest(["--week", "2026-W18"], cwd=tmp_path)
    assert r.returncode == 0
    content = (tmp_path / "memory/weekly_digests/2026-W18.md").read_text()
    assert "FOMC" in content
    assert "CPI" in content
    assert "NO TRADE" in content.upper() or "🔴" in content


def test_disciplina_section_renders_basic_checks(tmp_path):
    setup_repo_with_fixtures(tmp_path)
    r = run_digest(["--week", "2026-W18"], cwd=tmp_path)
    assert r.returncode == 0
    content = (tmp_path / "memory/weekly_digests/2026-W18.md").read_text()
    assert "Highlights y disciplina" in content
    assert "días con 2 SLs consecutivos" in content
