"""Migrate file-based profile state → PostgreSQL.

Reads `.claude/profiles/<slug>/memory/{signals_received.csv, equity_curve.csv}`
and inserts to the DB under a target user. Idempotent: re-running skips
rows that already exist by (profile_id, opened_at, symbol) for signals
and (profile_id, date) for equity points.

Usage:
    cd api
    uv run python scripts/migrate_local_to_db.py \\
        --user-email jose@example.com \\
        --profile-slug bitunix \\
        --profile-kind bitunix \\
        --capital-initial 200

Add `--all-profiles` to import every directory under `.claude/profiles/`
using each one's `config.md` for capital (when discoverable). Otherwise
runs in single-profile mode.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from datetime import date as _date
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

API_ROOT = Path(__file__).parent.parent
REPO_ROOT = API_ROOT.parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


def _parse_float(value: str) -> float | None:
    if not value or value.strip() in {"", "NONE_CROSS", "PENDING"}:
        return None
    try:
        return float(value.replace(",", "").replace("~", ""))
    except ValueError:
        return None


def _parse_int(value: str) -> int | None:
    if not value or not value.strip():
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def _parse_outcome(row: dict) -> str:
    """Map the legacy `hypothetical_outcome` / `executed` / `exit_reason` to
    one of the SignalOutcome enum values."""
    exit_reason = (row.get("exit_reason") or "").lower()
    if "tp3" in exit_reason or "stretch" in exit_reason:
        return "TP3"
    if "tp2" in exit_reason:
        return "TP2"
    if "tp1" in exit_reason:
        return "TP1"
    if "sl" in exit_reason and "manual" not in exit_reason:
        return "SL"
    if row.get("exit_price"):
        return "MANUAL"
    return "PENDING"


def _parse_side(s: str) -> str:
    s = s.strip().upper()
    return "LONG" if s.startswith("L") else "SHORT"


async def migrate_signals(
    db, profile_id, csv_path: Path, dry_run: bool = False
) -> tuple[int, int]:
    """Returns (inserted, skipped)."""
    from sqlalchemy import select

    from app.models.signal import Signal, SignalOutcome, SignalSide, SignalVerdict

    inserted = 0
    skipped = 0

    with csv_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_str = row.get("date", "").strip()
            time_str = row.get("time", "").strip() or "00:00"
            if not date_str:
                continue
            try:
                opened_at = datetime.fromisoformat(f"{date_str}T{time_str}:00").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                continue

            symbol = (row.get("symbol") or "").strip()
            if not symbol:
                continue

            # Dedupe key
            dup_stmt = select(Signal).where(
                Signal.profile_id == profile_id,
                Signal.symbol == symbol,
                Signal.opened_at == opened_at,
            )
            if (await db.execute(dup_stmt)).scalar_one_or_none() is not None:
                skipped += 1
                continue

            outcome_str = _parse_outcome(row)
            verdict_str = (row.get("verdict") or "").upper().strip() or None
            verdict = None
            if verdict_str:
                # Map legacy strings to enum; unknown → None
                mapping = {
                    "APPROVE_FULL": SignalVerdict.approve_full,
                    "APPROVE_HALF": SignalVerdict.approve_half,
                    "REJECT": SignalVerdict.reject,
                    "NO_GO_BY_SYSTEM": SignalVerdict.no_go_by_system,
                    "SELF_GENERATED": SignalVerdict.self_generated,
                    "SELF_GENERATED_PUNK_HUNT": SignalVerdict.self_generated,
                    "VISUAL_COPY": SignalVerdict.visual_copy,
                    "RETRO_LOGGED": SignalVerdict.self_generated,
                }
                verdict = mapping.get(verdict_str)

            sig = Signal(
                profile_id=profile_id,
                symbol=symbol,
                side=SignalSide(_parse_side(row.get("side", "LONG"))),
                entry=_parse_float(row.get("entry", "0")) or 0.0,
                sl=_parse_float(row.get("sl", "")),
                tp1=_parse_float(row.get("tp", "")),
                leverage=_parse_int(row.get("leverage_signal", "")),
                source=(row.get("decision") or "self_generated").lower()[:64],
                verdict=verdict,
                decision=row.get("decision", "")[:64] or None,
                size_pct=_parse_float(row.get("size_pct", "")),
                multifactor_score=_parse_float(row.get("multifactor", "")),
                ml_score=_parse_float(row.get("ml_score", "")),
                chainlink_delta_pct=_parse_float(row.get("chainlink_delta", "")),
                regime=(row.get("regime") or "").strip()[:48] or None,
                filters_4_count=_parse_int((row.get("filters_4") or "").split("/")[0]),
                pillars_4_count=_parse_int(row.get("pillars_4_count", "")),
                saturday=(row.get("saturday") or "").upper().startswith("Y"),
                outcome=SignalOutcome(outcome_str),
                exit_price=_parse_float(row.get("exit_price", "")),
                exit_reason=(row.get("exit_reason") or "")[:64] or None,
                pnl_usd=Decimal(str(_parse_float(row.get("pnl_usd", "")) or 0)),
                duration_h=_parse_float(row.get("duration_h", "")),
                hypothetical_outcome=(row.get("hypothetical_outcome") or "")[:32]
                or None,
                learning=(row.get("learning") or "") or None,
                tier=(row.get("tier") or "")[:32] or None,
                opened_at=opened_at,
            )
            if not dry_run:
                db.add(sig)
            inserted += 1

    if not dry_run:
        await db.flush()
    return inserted, skipped


async def migrate_equity(
    db, profile_id, csv_path: Path, dry_run: bool = False
) -> tuple[int, int]:
    """Returns (inserted, skipped)."""
    from sqlalchemy import select

    from app.models.equity_point import EquityPoint

    inserted = 0
    skipped = 0
    with csv_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts_raw = (row.get("timestamp") or "").strip()
            if not ts_raw:
                continue
            try:
                d = datetime.fromisoformat(ts_raw).date()
            except ValueError:
                # Pure-date fallback
                try:
                    d = _date.fromisoformat(ts_raw.split("T")[0])
                except ValueError:
                    continue

            equity = _parse_float(row.get("equity_usd", ""))
            if equity is None:
                continue

            dup_stmt = select(EquityPoint).where(
                EquityPoint.profile_id == profile_id, EquityPoint.date == d
            )
            if (await db.execute(dup_stmt)).scalar_one_or_none() is not None:
                skipped += 1
                continue

            ep = EquityPoint(
                profile_id=profile_id,
                date=d,
                equity=equity,
                daily_pnl_pct=_parse_float(row.get("daily_pnl_pct", "")),
                dd_pct=_parse_float(row.get("total_dd_pct", "")),
                trade_count=_parse_int(row.get("trades_today", "")) or 0,
            )
            if not dry_run:
                db.add(ep)
            inserted += 1

    if not dry_run:
        await db.flush()
    return inserted, skipped


async def main(args: argparse.Namespace) -> None:
    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.profile import Profile, ProfileKind
    from app.models.user import User

    async with AsyncSessionLocal() as db:
        # Resolve user
        user_stmt = select(User).where(User.email == args.user_email)
        user = (await db.execute(user_stmt)).scalar_one_or_none()
        if user is None:
            print(f"ERROR: user {args.user_email!r} not found. Create via scripts/create_dev_user.py first.")
            sys.exit(1)

        # Resolve or create profile
        prof_stmt = select(Profile).where(
            Profile.user_id == user.id, Profile.slug == args.profile_slug
        )
        profile = (await db.execute(prof_stmt)).scalar_one_or_none()
        if profile is None:
            try:
                kind = ProfileKind(args.profile_kind)
            except ValueError:
                kind = ProfileKind.custom
            profile = Profile(
                user_id=user.id,
                slug=args.profile_slug,
                name=args.profile_slug.title(),
                kind=kind,
                capital_initial=args.capital_initial,
                capital_current=args.capital_initial,
            )
            db.add(profile)
            await db.flush()
            print(f"→ Created profile {args.profile_slug} ({kind.value})")

        # Source paths
        local_dir = REPO_ROOT / ".claude" / "profiles" / args.profile_slug / "memory"
        signals_csv = local_dir / "signals_received.csv"
        equity_csv = local_dir / "equity_curve.csv"

        total_sig_in = total_sig_skip = total_eq_in = total_eq_skip = 0
        if signals_csv.exists():
            ins, skip = await migrate_signals(
                db, profile.id, signals_csv, dry_run=args.dry_run
            )
            total_sig_in += ins
            total_sig_skip += skip
            print(f"→ Signals: {ins} inserted, {skip} skipped (already in DB)")
        else:
            print(f"  ⚠ No signals_received.csv at {signals_csv}")

        if equity_csv.exists():
            ins, skip = await migrate_equity(
                db, profile.id, equity_csv, dry_run=args.dry_run
            )
            total_eq_in += ins
            total_eq_skip += skip
            print(f"→ Equity points: {ins} inserted, {skip} skipped")
        else:
            print(f"  ⚠ No equity_curve.csv at {equity_csv}")

        if args.dry_run:
            await db.rollback()
            print("DRY RUN — no changes committed.")
        else:
            await db.commit()
            print(
                f"✓ Done. {total_sig_in} signals + {total_eq_in} equity points "
                f"imported for {args.profile_slug}."
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-email", required=True)
    parser.add_argument("--profile-slug", required=True)
    parser.add_argument("--profile-kind", default="bitunix")
    parser.add_argument("--capital-initial", type=float, default=200.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args))
