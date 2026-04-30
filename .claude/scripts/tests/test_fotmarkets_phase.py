"""Tests for fotmarkets_phase.py canonical."""
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import fotmarkets_phase as fp


def write_progress(path, capital_str):
    path.write_text(f"# Phase progress\n\ncapital_current: {capital_str}\n")


@pytest.mark.parametrize("cap,expected_phase", [
    (50.0, 1),
    (99.99, 1),
    (100.0, 2),
    (250.0, 2),
    (300.0, 3),
    (1500.0, 3),
])
def test_phase_for_capital(cap, expected_phase):
    """Phase boundaries: <100 = 1, [100,300) = 2, >=300 = 3."""
    assert fp.phase_for_capital(cap) == expected_phase


def test_get_capital_basic(tmp_phase_progress):
    write_progress(tmp_phase_progress, "33.84")
    assert fp.get_capital() == 33.84


def test_get_capital_with_comment(tmp_phase_progress):
    """capital_current with inline comment should still parse."""
    tmp_phase_progress.write_text(
        "capital_current: 250.50  # Equity MT5 al cierre\n"
    )
    assert fp.get_capital() == 250.50


def test_get_capital_missing_file(tmp_phase_progress, capsys):
    """File not exists → exit 1 with error."""
    # tmp_phase_progress doesn't exist yet (fixture only sets path)
    with pytest.raises(SystemExit) as exc:
        fp.get_capital()
    assert exc.value.code == 1


def test_get_capital_missing_field(tmp_phase_progress, capsys):
    tmp_phase_progress.write_text("# only comment\n\nother_field: 100\n")
    with pytest.raises(SystemExit) as exc:
        fp.get_capital()
    assert exc.value.code == 1


def test_main_phase_command(tmp_phase_progress, capsys):
    write_progress(tmp_phase_progress, "150")
    rc = fp.main(["fotmarkets_phase.py", "phase"])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out.strip() == "2"


def test_main_capital_command(tmp_phase_progress, capsys):
    write_progress(tmp_phase_progress, "75.5")
    rc = fp.main(["fotmarkets_phase.py", "capital"])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out.strip() == "75.5"


def test_main_detail_command(tmp_phase_progress, capsys):
    write_progress(tmp_phase_progress, "33.84")
    rc = fp.main(["fotmarkets_phase.py", "detail"])
    captured = capsys.readouterr()
    assert rc == 0
    out = captured.out.strip()
    assert "phase=1" in out and "33.84" in out and "next_threshold=100" in out


def test_main_check_command(capsys):
    """check uses arg, no file needed."""
    rc = fp.main(["fotmarkets_phase.py", "check", "150"])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out.strip() == "2"


def test_main_check_invalid(capsys):
    rc = fp.main(["fotmarkets_phase.py", "check", "not-a-number"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "no numérico" in captured.err
