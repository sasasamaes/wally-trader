import os
import pytest
from datetime import datetime, timezone
from wally_core.memory import (
    Signal, Side, SignalDecision, SignalOutcome,
)
from wally_core.memory.local import LocalBackend

@pytest.fixture
def backend(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLY_PROFILES_DIR", str(tmp_path / "profiles"))
    return LocalBackend()

def _sample_signal(profile="bitunix"):
    return Signal(
        ts=datetime.now(timezone.utc),
        profile=profile, source="discord",
        symbol="BTCUSDT", side=Side.LONG,
        entry=68000, sl=67500, tp1=68500, tp2=69000, tp3=70000,
        leverage=10, score=72, decision=SignalDecision.GO,
    )

def test_append_signal_writes_csv_row(backend, tmp_path):
    sig = _sample_signal()
    sid = backend.append_signal("bitunix", sig)
    assert sid == sig.id
    csv_path = tmp_path / "profiles" / "bitunix" / "memory" / "signals_received.csv"
    assert csv_path.exists()
    rows = csv_path.read_text().strip().split("\n")
    assert len(rows) == 2
    assert sig.id in rows[1]

def test_read_signals_returns_appended(backend):
    sig = _sample_signal()
    backend.append_signal("bitunix", sig)
    signals = list(backend.read_signals("bitunix"))
    assert len(signals) == 1
    assert signals[0].id == sig.id

def test_update_signal_outcome_modifies_row(backend):
    sig = _sample_signal()
    backend.append_signal("bitunix", sig)
    backend.update_signal_outcome(sig.id, SignalOutcome.TP1, 68500, 1.5)
    signals = list(backend.read_signals("bitunix"))
    assert signals[0].outcome == SignalOutcome.TP1
    assert signals[0].pnl_usd == pytest.approx(1.5)

def test_profile_isolation(backend):
    sig1 = _sample_signal(profile="bitunix")
    sig2 = _sample_signal(profile="retail")
    backend.append_signal("bitunix", sig1)
    backend.append_signal("retail", sig2)
    assert len(list(backend.read_signals("bitunix"))) == 1
    assert len(list(backend.read_signals("retail"))) == 1

def test_health_check_returns_status(backend):
    h = backend.health_check()
    assert h["backend"] == "local"
    assert h["status"] in ("ok", "warn", "error")
