"""Tests for notify_hub — all side effects mocked."""
from unittest.mock import patch, MagicMock
import pytest
from pathlib import Path

from notify_hub import (
    Urgency,
    notify,
    macos_notify,
    telegram_send,
    email_send,
    format_event,
)


def test_urgency_ordering():
    assert Urgency.HEARTBEAT < Urgency.INFO < Urgency.WARN < Urgency.CRITICAL


def test_format_event_triggered_go():
    title, body = format_event(
        "triggered_go",
        {
            "order_id": "ord_x",
            "profile": "retail",
            "asset": "BTCUSDT.P",
            "side": "LONG",
            "entry": 77521,
            "sl": 77101,
            "tp1": 78571,
            "current_price": 77522,
            "filters_passed": 4,
            "filters_total": 4,
        },
    )
    assert "TRIGGER GO" in title
    assert "retail" in title
    assert "77521" in body


def test_format_event_unknown_fallback():
    title, body = format_event("mystery_event", {"order_id": "x"})
    assert "mystery_event" in title or "mystery_event" in body


@patch("notify_hub.subprocess.run")
def test_macos_notify_calls_osascript(mock_run):
    macos_notify("Title", "Body", sound="Glass")
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "osascript"
    joined = " ".join(cmd)
    assert "Title" in joined
    assert "Body" in joined


@patch.dict("os.environ", {}, clear=True)
def test_telegram_noop_without_token():
    # should not raise, should return False silently
    assert telegram_send("Title", "Body") is False


@patch.dict("os.environ", {}, clear=True)
def test_email_noop_without_key():
    assert email_send("Title", "Body") is False


@patch("notify_hub.macos_notify")
@patch("notify_hub.telegram_send")
@patch("notify_hub.email_send")
@patch("notify_hub.write_to_dashboard")
@patch("notify_hub.append_to_log")
def test_notify_critical_fires_all_channels(
    mock_log, mock_dash, mock_email, mock_tg, mock_macos
):
    notify(Urgency.CRITICAL, "triggered_go", {"order_id": "x", "profile": "retail"})
    mock_log.assert_called_once()
    mock_dash.assert_called_once()
    mock_macos.assert_called_once()
    mock_tg.assert_called_once()
    mock_email.assert_called_once()


@patch("notify_hub.macos_notify")
@patch("notify_hub.telegram_send")
@patch("notify_hub.email_send")
@patch("notify_hub.write_to_dashboard")
@patch("notify_hub.append_to_log")
def test_notify_info_only_fires_macos(
    mock_log, mock_dash, mock_email, mock_tg, mock_macos
):
    notify(Urgency.INFO, "order_created", {"order_id": "x", "profile": "retail"})
    mock_log.assert_called_once()
    mock_dash.assert_called_once()
    mock_macos.assert_called_once()
    mock_tg.assert_not_called()
    mock_email.assert_not_called()


@patch("notify_hub.macos_notify")
@patch("notify_hub.write_to_dashboard")
@patch("notify_hub.append_to_log")
def test_notify_heartbeat_only_writes(mock_log, mock_dash, mock_macos):
    notify(Urgency.HEARTBEAT, "heartbeat", {"order_id": "x"})
    mock_log.assert_called_once()
    mock_dash.assert_called_once()
    mock_macos.assert_not_called()
