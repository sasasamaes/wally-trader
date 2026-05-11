"""Unit tests for dragno_track.py."""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import dragno_track as dt


def test_derive_margin_from_win():
    # KITE: +15.48% / +$0.45994 → margin = 0.45994 / 0.1548 ≈ 2.972
    margin = dt.derive_margin(pyg_pct=15.48, pyg_usd=0.45994)
    assert abs(margin - 2.972) < 0.01


def test_derive_margin_from_loss():
    # VIRTUAL: -15.28% / -$0.52676 → margin = 0.52676 / 0.1528 ≈ 3.448
    margin = dt.derive_margin(pyg_pct=-15.28, pyg_usd=-0.52676)
    assert abs(margin - 3.448) < 0.01


def test_derive_margin_returns_zero_if_pct_zero():
    assert dt.derive_margin(pyg_pct=0.0, pyg_usd=0.0) == 0.0
