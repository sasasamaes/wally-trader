#!/usr/bin/env python3
"""strategy_distill.py — Extract trading strategy from external content.

Inspired by "Cloud Code + TradingView" YT video where the host imports
Murad's memecoin criteria + Leopold's 165-page thesis into Claude to
distill into actionable rules.

This script extracts text from the source (YouTube URL via yt-dlp / file path
/ raw text) and saves it to a normalized location for Claude to consume.
The actual rule-distillation is done by Claude itself in the next step
(via the /strategy-import slash command).

Usage:
  python3 strategy_distill.py --youtube https://youtube.com/watch?v=XXX
  python3 strategy_distill.py --file /path/to/thesis.pdf
  python3 strategy_distill.py --file /path/to/notes.txt
  python3 strategy_distill.py --text "RSI<30 + price below VWAP"

Output:
  - JSON to stdout with extracted text + metadata
  - Saves text to .claude/strategy_imports/raw/<slug>.txt
  - Returns slug for the next step (Claude reads the raw text and produces
    rules JSON at .claude/strategy_imports/rules/<slug>.json)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = ROOT / ".claude" / "strategy_imports" / "raw"
RULES_DIR = ROOT / ".claude" / "strategy_imports" / "rules"


def slugify(name: str, max_len: int = 50) -> str:
    """Convert string to filename-safe slug."""
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s[:max_len] if s else f"strategy_{int(datetime.now().timestamp())}"


def extract_youtube(url: str) -> dict[str, Any]:
    """Use yt-dlp to download auto-subs and convert to plain text."""
    # Extract video ID from URL
    match = re.search(r"(?:v=|youtu\.be/|/shorts/)([a-zA-Z0-9_-]{11})", url)
    if not match:
        raise ValueError(f"Could not extract video ID from URL: {url}")
    video_id = match.group(1)

    # yt-dlp lives in shared/wally_core/.venv from earlier setup
    yt_dlp = ROOT / "shared/wally_core/.venv/bin/python"
    if not yt_dlp.exists():
        raise RuntimeError("python with yt_dlp not found in shared/wally_core/.venv")

    out_dir = ROOT / ".claude" / "cache" / "yt_subtitles"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(out_dir / f"%(id)s.%(ext)s")

    cmd = [
        str(yt_dlp), "-m", "yt_dlp",
        "--write-auto-sub", "--skip-download",
        "--sub-lang", "en", "--sub-format", "vtt",
        "--output", out_template,
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr[-500:]}")

    vtt_path = out_dir / f"{video_id}.en.vtt"
    if not vtt_path.exists():
        raise FileNotFoundError(f"Subtitles not generated at {vtt_path}")

    # Clean VTT to plain text
    raw = vtt_path.read_text()
    text_lines = []
    seen = set()
    for line in raw.split("\n"):
        line = line.strip()
        if not line or line.startswith(("WEBVTT", "NOTE", "Kind:", "Language:")):
            continue
        if "-->" in line:
            continue
        line = re.sub(r"<[^>]+>", "", line).strip()
        if line and line not in seen:
            text_lines.append(line)
            seen.add(line)

    text = re.sub(r"\s+", " ", " ".join(text_lines))

    return {
        "source_type": "youtube",
        "source_url": url,
        "video_id": video_id,
        "text": text,
        "char_count": len(text),
        "word_count": len(text.split()),
    }


def extract_pdf(path: Path) -> dict[str, Any]:
    """Extract text from a PDF using pdftotext (Poppler)."""
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    # Try pdftotext first (faster, no Python deps)
    try:
        result = subprocess.run(
            ["pdftotext", str(path), "-"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            text = re.sub(r"\s+", " ", result.stdout)
            return {
                "source_type": "pdf",
                "source_path": str(path),
                "text": text,
                "char_count": len(text),
                "word_count": len(text.split()),
                "extractor": "pdftotext",
            }
    except FileNotFoundError:
        pass

    # Fallback: try PyPDF2 if installed in venv
    try:
        py = ROOT / "shared/wally_core/.venv/bin/python"
        result = subprocess.run(
            [
                str(py), "-c",
                f"import PyPDF2; r=PyPDF2.PdfReader('{path}'); "
                f"print(' '.join(p.extract_text() for p in r.pages))",
            ],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0 and result.stdout.strip():
            text = re.sub(r"\s+", " ", result.stdout)
            return {
                "source_type": "pdf",
                "source_path": str(path),
                "text": text,
                "char_count": len(text),
                "word_count": len(text.split()),
                "extractor": "PyPDF2",
            }
    except Exception:
        pass

    raise RuntimeError(
        "PDF extraction failed. Install: brew install poppler  OR "
        f"{ROOT}/shared/wally_core/.venv/bin/python -m pip install PyPDF2"
    )


def extract_file(path: Path) -> dict[str, Any]:
    """Extract text from a generic text file."""
    if path.suffix.lower() == ".pdf":
        return extract_pdf(path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    text = path.read_text(errors="ignore")
    text = re.sub(r"\s+", " ", text)
    return {
        "source_type": "file",
        "source_path": str(path),
        "text": text,
        "char_count": len(text),
        "word_count": len(text.split()),
    }


def extract_url(url: str) -> dict[str, Any]:
    """Fetch and extract text from a generic web URL."""
    req = urllib.request.Request(url, headers={"User-Agent": "wally-trader/1.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        html = r.read().decode("utf-8", errors="ignore")

    # Strip HTML tags (very basic; for serious cases use BeautifulSoup)
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return {
        "source_type": "url",
        "source_url": url,
        "text": text,
        "char_count": len(text),
        "word_count": len(text.split()),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Extract trading strategy content from external source")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--youtube", help="YouTube URL (uses yt-dlp auto-subs)")
    src.add_argument("--file", help="Path to .txt/.md/.pdf")
    src.add_argument("--url", help="Generic web URL (HTML)")
    src.add_argument("--text", help="Raw text directly")
    p.add_argument("--name", help="Strategy name (default: auto from source)")
    p.add_argument("--quiet", action="store_true", help="Skip stderr summary")
    args = p.parse_args()

    try:
        if args.youtube:
            data = extract_youtube(args.youtube)
            default_name = f"yt_{data['video_id']}"
        elif args.file:
            data = extract_file(Path(args.file))
            default_name = Path(args.file).stem
        elif args.url:
            data = extract_url(args.url)
            default_name = re.sub(r"https?://(www\.)?", "", args.url)[:30]
        else:
            text = re.sub(r"\s+", " ", args.text)
            data = {
                "source_type": "raw_text",
                "text": text,
                "char_count": len(text),
                "word_count": len(text.split()),
            }
            default_name = "raw_input"
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stdout)
        return 1

    name = args.name or default_name
    slug = slugify(name)

    # Save raw text
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    RULES_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / f"{slug}.txt"
    raw_path.write_text(data["text"])

    result = {
        "slug": slug,
        "raw_path": str(raw_path),
        "rules_path_target": str(RULES_DIR / f"{slug}.json"),
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        **{k: v for k, v in data.items() if k != "text"},  # exclude text from JSON output
        "preview": data["text"][:500] + ("..." if len(data["text"]) > 500 else ""),
    }

    if not args.quiet:
        print(
            f"[strategy-distill] Extracted {data['word_count']} words from {data['source_type']}.",
            f"Saved to {raw_path}.",
            f"Next: Claude reads raw text + writes rules JSON to {result['rules_path_target']}",
            sep="\n", file=sys.stderr,
        )

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
