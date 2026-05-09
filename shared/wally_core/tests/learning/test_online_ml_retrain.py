"""Tests for L7 — online_ml_retrain."""
import csv
import json
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from wally_core.learning.online_ml_retrain import (
    should_retrain,
    retrain_and_validate,
    _load_outcomes_count,
    _get_last_train_n,
)


def _write_outcomes_csv(path: Path, n_trades: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["pnl_usd", "symbol"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(n_trades):
            writer.writerow({"pnl_usd": "5.0" if i % 2 == 0 else "-2.0", "symbol": "BTC"})


def test_load_outcomes_count(tmp_path):
    path = tmp_path / "bitunix" / "memory" / "outcomes_v2.csv"
    _write_outcomes_csv(path, 30)
    count = _load_outcomes_count("bitunix", profiles_dir=str(tmp_path))
    assert count == 30


def test_load_outcomes_count_empty(tmp_path):
    count = _load_outcomes_count("bitunix", profiles_dir=str(tmp_path))
    assert count == 0


def test_should_retrain_false_insufficient(tmp_path):
    path = tmp_path / "bitunix" / "memory" / "outcomes_v2.csv"
    _write_outcomes_csv(path, 10)
    result = should_retrain("bitunix", new_trade_threshold=25, last_train_n=0, profiles_dir=str(tmp_path))
    assert result is False


def test_should_retrain_true(tmp_path):
    path = tmp_path / "bitunix" / "memory" / "outcomes_v2.csv"
    _write_outcomes_csv(path, 30)
    result = should_retrain("bitunix", new_trade_threshold=25, last_train_n=0, profiles_dir=str(tmp_path))
    assert result is True


def test_should_retrain_accounts_for_last_train(tmp_path):
    path = tmp_path / "bitunix" / "memory" / "outcomes_v2.csv"
    _write_outcomes_csv(path, 30)
    # If we already trained at n=20, only 10 new trades → below threshold 25
    result = should_retrain("bitunix", new_trade_threshold=25, last_train_n=20, profiles_dir=str(tmp_path))
    assert result is False


def test_retrain_scaffold_no_script(tmp_path):
    """When train.py doesn't exist, should return scaffold_no_script."""
    path = tmp_path / "bitunix" / "memory" / "outcomes_v2.csv"
    _write_outcomes_csv(path, 30)
    fake_script = tmp_path / "nonexistent_train.py"
    result = retrain_and_validate(
        "bitunix",
        profiles_dir=str(tmp_path),
        train_script=fake_script,
    )
    assert result["status"] == "scaffold_no_script"
    assert result["promoted"] is False
    assert "TODO" in result["message"]


def test_retrain_logs_scaffold(tmp_path):
    path = tmp_path / "bitunix" / "memory" / "outcomes_v2.csv"
    _write_outcomes_csv(path, 10)
    fake_script = tmp_path / "nonexistent.py"
    retrain_and_validate("bitunix", profiles_dir=str(tmp_path), train_script=fake_script)

    log_path = tmp_path / "bitunix" / "memory" / "learning" / "ml_retrain_log.jsonl"
    assert log_path.exists()
    content = log_path.read_text()
    assert "retrain_skipped_no_script" in content


def test_get_last_train_n_empty(tmp_path):
    n = _get_last_train_n("bitunix", profiles_dir=str(tmp_path))
    assert n == 0


def test_get_last_train_n_from_log(tmp_path):
    log_path = tmp_path / "bitunix" / "memory" / "learning" / "ml_retrain_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps({
        "timestamp": "2026-01-01T00:00:00+00:00",
        "event": "retrain_promoted",
        "profile": "bitunix",
        "n_trades": 42,
    }) + "\n")
    n = _get_last_train_n("bitunix", profiles_dir=str(tmp_path))
    assert n == 42
