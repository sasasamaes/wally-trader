"""L5 — Auto post-mortem on losing trades."""
from __future__ import annotations

import csv
import json
import os
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class PostMortemReport:
    trade_id: str
    lesson_tags: list[str]
    regime_entry: str
    regime_exit: str
    held_minutes: int
    pnl_usd: float
    system_recommended: list[str]   # what system said
    structural_findings: list[str]  # diagnostic findings


def _auto_lesson_tags(row: dict) -> list[str]:
    """Derive lesson tags from trade row."""
    tags = []
    raw_tags = row.get("lesson_tags", "")
    if raw_tags:
        tags.extend([t.strip() for t in raw_tags.replace("|", ",").split(",") if t.strip()])

    # Add structural tags if not already present
    regime_entry = row.get("regime_at_entry", "")
    side = row.get("side", "")
    hold_raw = row.get("hold_minutes", "0")
    try:
        hold = int(float(hold_raw or 0))
    except (ValueError, TypeError):
        hold = 0

    try:
        pnl = float(row.get("pnl_usd") or 0)
    except (ValueError, TypeError):
        pnl = 0.0

    if pnl < 0:
        if "LOSS" not in tags:
            tags.append("LOSS")

        # Counter-trend in strong trend
        if regime_entry in ("TREND_FUERTE", "TREND_EXTREMO"):
            if "counter_trend" not in tags:
                tags.append("counter_trend")

        # Held too long
        if hold > 240:
            tags.append("held_too_long")

        # Quick loss — could be ignored filter
        if hold < 15:
            tags.append("quick_stop")

    return list(dict.fromkeys(tags))  # deduplicate preserving order


def _structural_findings(row: dict) -> list[str]:
    """Generate structural findings from trade data."""
    findings = []
    regime_entry = row.get("regime_at_entry", "UNKNOWN")
    regime_exit = row.get("regime_at_exit", "UNKNOWN")
    side = row.get("side", "")
    try:
        pnl = float(row.get("pnl_usd") or 0)
    except (ValueError, TypeError):
        pnl = 0.0

    try:
        mfe = float(row.get("max_favorable_excursion") or 0)
        mae = float(row.get("max_adverse_excursion") or 0)
    except (ValueError, TypeError):
        mfe, mae = 0.0, 0.0

    try:
        hold = int(float(row.get("hold_minutes") or 0))
    except (ValueError, TypeError):
        hold = 0

    if regime_entry != regime_exit:
        findings.append(f"Regime changed mid-trade: {regime_entry} → {regime_exit}")

    if pnl < 0 and mfe > abs(pnl) * 0.5 and mfe > 0:
        findings.append(f"MFE was {mfe:.2f} but trade ended at loss — TP1 hit failure or early reversal")

    if pnl < 0 and regime_entry in ("TREND_FUERTE", "TREND_EXTREMO"):
        findings.append(f"Entered {side} in {regime_entry} — counter-trend entry, ADX gate may have been bypassed")

    if hold > 360 and pnl < 0:
        findings.append(f"Held for {hold}min ({hold/60:.1f}h) before stopping — exit discipline issue")

    if not findings:
        findings.append("No anomalies detected — standard stop hit")

    return findings


def auto_postmortem(
    trade_id: str,
    *,
    profile: str = "bitunix",
    profiles_dir: str = ".claude/profiles",
    outcomes_row: Optional[dict] = None,
) -> PostMortemReport:
    """Generate post-mortem for a trade. Looks up trade in outcomes_v2.csv.

    If outcomes_row is provided, uses it directly (for testing).
    """
    row = outcomes_row

    if row is None:
        path = Path(profiles_dir) / profile / "memory" / "outcomes_v2.csv"
        if not path.exists():
            raise FileNotFoundError(f"outcomes_v2.csv not found for profile {profile!r}")

        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                # Match by trade_id field or by row index
                if str(r.get("trade_id") or "") == str(trade_id):
                    row = r
                    break
                # Fallback: match by symbol+open_time as composite ID
                composite = f"{r.get('symbol', '')}:{r.get('open_time_utc', '')}"
                if composite == trade_id:
                    row = r
                    break

    if row is None:
        raise KeyError(f"Trade {trade_id!r} not found in outcomes_v2.csv")

    try:
        pnl = float(row.get("pnl_usd") or 0)
    except (ValueError, TypeError):
        pnl = 0.0

    try:
        hold = int(float(row.get("hold_minutes") or 0))
    except (ValueError, TypeError):
        hold = 0

    lesson_tags = _auto_lesson_tags(row)
    findings = _structural_findings(row)

    return PostMortemReport(
        trade_id=trade_id,
        lesson_tags=lesson_tags,
        regime_entry=row.get("regime_at_entry", "UNKNOWN"),
        regime_exit=row.get("regime_at_exit", "UNKNOWN"),
        held_minutes=hold,
        pnl_usd=pnl,
        system_recommended=[],  # populated from recommendation_log if cross-referenced
        structural_findings=findings,
    )


def aggregate_postmortems(
    profile: str,
    days: int = 30,
    *,
    profiles_dir: str = ".claude/profiles",
) -> dict:
    """Cluster post-mortems by lesson_tags. Output: common patterns in losses."""
    from datetime import timedelta

    path = Path(profiles_dir) / profile / "memory" / "outcomes_v2.csv"
    if not path.exists():
        return {"status": "no_data", "top_loss_tags": [], "n_losses": 0}

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    tag_counter: Counter = Counter()
    n_losses = 0

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Date filter
            close_raw = row.get("close_time_utc", "")
            if close_raw:
                try:
                    close_time = datetime.fromisoformat(close_raw.replace("Z", "+00:00"))
                    if close_time < cutoff:
                        continue
                except ValueError:
                    pass

            try:
                pnl = float(row.get("pnl_usd") or 0)
            except (ValueError, TypeError):
                continue

            if pnl >= 0:
                continue  # only losses

            n_losses += 1
            tags = _auto_lesson_tags(row)
            for tag in tags:
                if tag != "LOSS":
                    tag_counter[tag] += 1

    top_tags = [{"tag": tag, "count": count} for tag, count in tag_counter.most_common(10)]
    return {
        "status": "ok",
        "n_losses": n_losses,
        "top_loss_tags": top_tags,
        "days": days,
    }


def append_to_postmortem_log(
    report: PostMortemReport,
    profile: str,
    *,
    profiles_dir: str = ".claude/profiles",
) -> None:
    """Append post-mortem report to postmortems.md."""
    log_dir = Path(profiles_dir) / profile / "memory" / "learning"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "postmortems.md"

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"\n## {ts} — Trade {report.trade_id}",
        f"- **PnL:** ${report.pnl_usd:.2f}",
        f"- **Held:** {report.held_minutes} min",
        f"- **Regime:** {report.regime_entry} → {report.regime_exit}",
        f"- **Tags:** {', '.join(report.lesson_tags)}",
        "- **Findings:**",
    ]
    for f in report.structural_findings:
        lines.append(f"  - {f}")

    with open(log_path, "a") as fh:
        fh.write("\n".join(lines) + "\n")
