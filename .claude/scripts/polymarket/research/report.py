"""Render a research report and act as CLI entry for /polymarket-research."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _fmt(v, prec=3):
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return f"{v:.{prec}f}"
    return str(v)


def render_h1(res: dict[str, Any]) -> str:
    return (
        "## H1: Composite predicts BTC return\n\n"
        f"- N: {res.get('n')}\n"
        f"- Correlation: {_fmt(res.get('correlation'))}\n"
        f"- P-value (approx): {_fmt(res.get('p_value'))}\n"
    )


def render_h2(res: dict[str, Any]) -> str:
    return (
        "## H2: Spike predicts volatility\n\n"
        f"- Spike threshold (Δ24h): {_fmt(res.get('spike_threshold'))}\n"
        f"- Spike N / baseline N: {res.get('spike_n')} / {res.get('baseline_n')}\n"
        f"- Mean |BTC return| spike: {_fmt(res.get('mean_vol_spike'))}\n"
        f"- Mean |BTC return| baseline: {_fmt(res.get('mean_vol_baseline'))}\n"
    )


def render_h3(res: dict[str, Any]) -> str:
    pre = res.get("pre_event", {})
    post = res.get("post_event", {})
    return (
        "## H3: Pre-event edge\n\n"
        f"- Pre-event N / corr: {pre.get('n')} / {_fmt(pre.get('correlation'))}\n"
        f"- Post-event N / corr: {post.get('n')} / {_fmt(post.get('correlation'))}\n"
    )


def render_h4(res: dict[str, dict[str, Any]]) -> str:
    lines = ["## H4: Per-market information coefficient", "", "| Market | N | IC | Flag |", "|---|---|---|---|"]
    for slug, m in sorted(res.items()):
        lines.append(f"| {slug} | {m.get('n')} | {_fmt(m.get('ic'))} | {m.get('flag', '')} |")
    return "\n".join(lines) + "\n"


def render(payload: dict[str, Any]) -> str:
    parts = [
        "# Polymarket Research Report",
        "",
        f"**Window:** {payload.get('window', 'n/a')}",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        "",
    ]
    n_total = (payload.get("h1") or {}).get("n", 0) or 0
    if n_total < 200:
        parts.append(
            "> ⚠️ **Caveat:** N<200 — this report is **directional only**, not statistically robust.\n"
        )
    parts += [
        render_h1(payload.get("h1", {})),
        render_h2(payload.get("h2", {})),
        render_h3(payload.get("h3", {})),
        render_h4(payload.get("h4", {})),
    ]
    return "\n".join(parts)


def _build_payload_from_data(args) -> dict[str, Any]:
    """Stub composer: in V1 this is intentionally minimal — invoking
    the research pipeline end-to-end requires real data files. The
    CLI is wired so the user can pass a JSON payload and get markdown
    rendered, OR run the helper script that aggregates real data.
    """
    if args.payload:
        return json.loads(Path(args.payload).read_text())
    return {
        "window": "no data",
        "h1": {"n": 0, "correlation": None, "p_value": None},
        "h2": {"spike_n": 0, "baseline_n": 0, "mean_vol_spike": None, "mean_vol_baseline": None, "spike_threshold": 0.05},
        "h3": {"pre_event": {"n": 0, "correlation": None}, "post_event": {"n": 0, "correlation": None}},
        "h4": {},
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [report] %(message)s")
    parser = argparse.ArgumentParser(description="Render a Polymarket research report.")
    parser.add_argument("--payload", help="Path to a JSON payload to render", default=None)
    parser.add_argument("--out", help="Output markdown path", default=None)
    args = parser.parse_args()
    payload = _build_payload_from_data(args)
    md = render(payload)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(md)
        print(f"Wrote {args.out}")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
