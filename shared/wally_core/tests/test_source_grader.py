import pytest
import sys
import csv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / ".claude/scripts"))

from source_grader import grade_source


def test_grade_no_data(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    res = grade_source("discord_test", "bitunix")
    assert res["grade"] == "N/A"


def test_grade_insufficient_data(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    csv_path = tmp_path / "profiles" / "bitunix" / "memory" / "signals_received.csv"
    csv_path.parent.mkdir(parents=True)
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["source", "outcome"])
        w.writeheader()
        w.writerow({"source": "discord_test", "outcome": "TP1"})
    res = grade_source("discord_test", "bitunix")
    # Only 1 trade < 5 min
    assert res["grade"] == "N/A"


def test_grade_a(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    csv_path = tmp_path / "profiles" / "bitunix" / "memory" / "signals_received.csv"
    csv_path.parent.mkdir(parents=True)
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["source", "outcome"])
        w.writeheader()
        # 7 wins, 2 losses = 78% WR -> A
        for _ in range(7):
            w.writerow({"source": "discord_test", "outcome": "TP1"})
        for _ in range(2):
            w.writerow({"source": "discord_test", "outcome": "SL"})
    res = grade_source("discord_test", "bitunix")
    assert res["grade"] == "A"
    assert res["wr_pct"] >= 60


def test_grade_f(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    csv_path = tmp_path / "profiles" / "bitunix" / "memory" / "signals_received.csv"
    csv_path.parent.mkdir(parents=True)
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["source", "outcome"])
        w.writeheader()
        for _ in range(2):
            w.writerow({"source": "bad_source", "outcome": "TP1"})
        for _ in range(8):
            w.writerow({"source": "bad_source", "outcome": "SL"})
    res = grade_source("bad_source", "bitunix")
    assert res["grade"] == "F"
