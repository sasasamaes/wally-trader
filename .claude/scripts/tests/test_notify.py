"""Tests for notify.py canonical."""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import notify as notify_mod


def test_log_notification_creates_file(tmp_path, monkeypatch):
    log = tmp_path / "test_notif.log"
    monkeypatch.setattr(notify_mod, "LOG_FILE", log)

    notify_mod.log_notification("Test Title", "Test message", success=True)
    assert log.exists()
    content = log.read_text()
    assert "Test Title" in content
    assert "Test message" in content
    assert "GUI_FAIL" not in content  # success=True


def test_log_notification_marks_failure(tmp_path, monkeypatch):
    log = tmp_path / "test_notif.log"
    monkeypatch.setattr(notify_mod, "LOG_FILE", log)

    notify_mod.log_notification("Test", "Msg", success=False)
    assert "GUI_FAIL" in log.read_text()


def test_log_notification_appends(tmp_path, monkeypatch):
    log = tmp_path / "test_notif.log"
    monkeypatch.setattr(notify_mod, "LOG_FILE", log)

    notify_mod.log_notification("First", "msg1", True)
    notify_mod.log_notification("Second", "msg2", True)
    content = log.read_text()
    assert "First" in content and "Second" in content


def test_main_uses_correct_backend_macos(monkeypatch, tmp_path):
    """On Darwin, notify_macos is called."""
    monkeypatch.setattr(notify_mod, "LOG_FILE", tmp_path / "log.log")
    monkeypatch.setattr(notify_mod.platform, "system", lambda: "Darwin")
    called = {}
    monkeypatch.setattr(notify_mod, "notify_macos", lambda t, m, s="": called.update({"mac": True}) or True)
    monkeypatch.setattr(notify_mod, "notify_linux", lambda t, m: called.update({"linux": True}) or True)
    monkeypatch.setattr(notify_mod, "notify_windows", lambda t, m: called.update({"win": True}) or True)

    rc = notify_mod.main(["notify.py", "title", "msg"])
    assert rc == 0
    assert called == {"mac": True}


def test_main_uses_correct_backend_linux(monkeypatch, tmp_path):
    monkeypatch.setattr(notify_mod, "LOG_FILE", tmp_path / "log.log")
    monkeypatch.setattr(notify_mod.platform, "system", lambda: "Linux")
    called = {}
    monkeypatch.setattr(notify_mod, "notify_macos", lambda *a, **k: called.update({"mac": True}) or True)
    monkeypatch.setattr(notify_mod, "notify_linux", lambda t, m: called.update({"linux": True}) or True)
    monkeypatch.setattr(notify_mod, "notify_windows", lambda *a, **k: called.update({"win": True}) or True)

    notify_mod.main(["notify.py", "title", "msg"])
    assert called == {"linux": True}


def test_main_uses_correct_backend_windows(monkeypatch, tmp_path):
    monkeypatch.setattr(notify_mod, "LOG_FILE", tmp_path / "log.log")
    monkeypatch.setattr(notify_mod.platform, "system", lambda: "Windows")
    called = {}
    monkeypatch.setattr(notify_mod, "notify_macos", lambda *a, **k: called.update({"mac": True}) or True)
    monkeypatch.setattr(notify_mod, "notify_linux", lambda *a, **k: called.update({"linux": True}) or True)
    monkeypatch.setattr(notify_mod, "notify_windows", lambda t, m: called.update({"win": True}) or True)

    notify_mod.main(["notify.py", "title", "msg"])
    assert called == {"win": True}


def test_main_falls_back_to_stderr_if_backend_fails(monkeypatch, tmp_path, capsys):
    """If GUI fails, stderr fallback prints message."""
    monkeypatch.setattr(notify_mod, "LOG_FILE", tmp_path / "log.log")
    monkeypatch.setattr(notify_mod.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(notify_mod, "notify_macos", lambda *a, **k: False)

    rc = notify_mod.main(["notify.py", "Title", "FailMsg"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "[NOTIFY]" in captured.err
    assert "FailMsg" in captured.err
