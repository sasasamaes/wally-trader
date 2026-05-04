"""Tests for polymarket.research.report."""
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from polymarket.research import report


def test_render_h1_section():
    md = report.render_h1({"n": 240, "correlation": 0.18, "p_value": 0.003})
    assert "## H1" in md
    assert "0.18" in md
    assert "0.003" in md
    assert "240" in md


def test_render_h4_section_per_market():
    res = {
        "fed-cut-may": {"n": 240, "ic": 0.31, "flag": "OK"},
        "noise-market": {"n": 18, "ic": -0.04, "flag": "LOW_N"},
    }
    md = report.render_h4(res)
    assert "fed-cut-may" in md
    assert "0.31" in md
    assert "LOW_N" in md
    assert "0.04" in md or "-0.04" in md


def test_render_full_report_has_all_sections():
    payload = {
        "window": "2026-04-01 → 2026-05-02",
        "h1": {"n": 100, "correlation": 0.12, "p_value": 0.04},
        "h2": {"spike_n": 12, "baseline_n": 88, "mean_vol_spike": 0.04, "mean_vol_baseline": 0.012, "spike_threshold": 0.05},
        "h3": {"pre_event": {"n": 30, "correlation": 0.25}, "post_event": {"n": 20, "correlation": 0.05}},
        "h4": {"fed-cut-may": {"n": 100, "ic": 0.20, "flag": "OK"}},
    }
    md = report.render(payload)
    assert "# Polymarket Research Report" in md
    assert "## H1" in md
    assert "## H2" in md
    assert "## H3" in md
    assert "## H4" in md


def test_render_marks_insufficient_n():
    payload = {
        "window": "n/a",
        "h1": {"n": 5, "correlation": 0.5, "p_value": 0.4},
        "h2": {"spike_n": 1, "baseline_n": 1, "mean_vol_spike": 0.0, "mean_vol_baseline": 0.0, "spike_threshold": 0.05},
        "h3": {"pre_event": {"n": 0, "correlation": None}, "post_event": {"n": 0, "correlation": None}},
        "h4": {},
    }
    md = report.render(payload)
    assert "directional only" in md.lower() or "n<200" in md.lower() or "insufficient" in md.lower()
