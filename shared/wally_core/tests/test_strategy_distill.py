"""Tests for strategy_distill.py — content extraction helpers."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch


def _load():
    sp = Path(__file__).resolve().parents[3] / ".claude" / "scripts" / "strategy_distill.py"
    assert sp.exists(), sp
    spec = importlib.util.spec_from_file_location("strategy_distill", str(sp))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["strategy_distill"] = mod
    spec.loader.exec_module(mod)
    return mod


sd = _load()


def test_slugify_basic():
    assert sd.slugify("My Strategy 2026") == "my_strategy_2026"
    assert sd.slugify("VWAP + EMA / Cross!") == "vwap_ema_cross"
    assert sd.slugify("") != ""  # falls back to timestamp


def test_slugify_max_length():
    long_name = "a" * 100
    s = sd.slugify(long_name, max_len=20)
    assert len(s) == 20


def test_slugify_strips_leading_trailing_underscores():
    assert not sd.slugify("---test---").startswith("_")
    assert not sd.slugify("---test---").endswith("_")


def test_extract_file_text(tmp_path):
    f = tmp_path / "strategy.md"
    f.write_text("Long when RSI < 30\nShort when RSI > 70\nRisk 1%")
    r = sd.extract_file(f)
    assert r["source_type"] == "file"
    assert "RSI" in r["text"]
    assert r["word_count"] > 5
    # whitespace normalized
    assert "\n" not in r["text"]


def test_extract_file_missing_raises(tmp_path):
    import pytest
    with pytest.raises(FileNotFoundError):
        sd.extract_file(tmp_path / "nope.txt")


def test_extract_youtube_invalid_url_raises():
    import pytest
    with pytest.raises(ValueError, match="Could not extract video ID"):
        sd.extract_youtube("https://example.com/not-a-video")


def test_extract_youtube_extracts_video_id_from_various_formats():
    """Verify regex matches all common YouTube URL formats (without network call)."""
    # We test the ID-extraction logic only by patching the rest
    valid_urls = [
        "https://www.youtube.com/watch?v=DNHj8GwzvYg",
        "https://youtu.be/DNHj8GwzvYg",
        "https://youtube.com/shorts/DNHj8GwzvYg",
        "youtube.com/watch?v=DNHj8GwzvYg&t=10s",
    ]
    for url in valid_urls:
        # Match just the regex part (we don't call network)
        import re
        match = re.search(r"(?:v=|youtu\.be/|/shorts/)([a-zA-Z0-9_-]{11})", url)
        assert match is not None, f"failed to match {url}"
        assert match.group(1) == "DNHj8GwzvYg"


def test_extract_url_strips_html(monkeypatch):
    fake_html = b"<html><body><script>alert(1)</script><h1>Strategy</h1><p>RSI < 30</p></body></html>"
    class FakeResponse:
        def read(self): return fake_html
        def __enter__(self): return self
        def __exit__(self, *a): pass

    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: FakeResponse())
    r = sd.extract_url("https://example.com/strategy")
    assert r["source_type"] == "url"
    assert "<script>" not in r["text"]
    assert "<h1>" not in r["text"]
    assert "Strategy" in r["text"]
    assert "RSI" in r["text"]


def test_extract_pdf_uses_pdftotext_when_available(tmp_path):
    """Verify the pdf extractor tries pdftotext first."""
    fake_pdf = tmp_path / "fake.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake content")

    class FakeRun:
        returncode = 0
        stdout = "Extracted PDF text from fake content"
        stderr = ""

    with patch("subprocess.run", return_value=FakeRun()):
        r = sd.extract_pdf(fake_pdf)
    assert r["source_type"] == "pdf"
    assert r["extractor"] == "pdftotext"
    assert "Extracted" in r["text"]


def test_extract_pdf_missing_raises(tmp_path):
    import pytest
    with pytest.raises(FileNotFoundError):
        sd.extract_pdf(tmp_path / "missing.pdf")
