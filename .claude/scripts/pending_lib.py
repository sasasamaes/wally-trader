"""CRUD + invalidation + whitelist for pending orders JSON files.

File layout (per profile):
  .claude/profiles/<profile>/memory/pending_orders.json
  {
    "pending": [<order>, ...],
    "meta": {...}
  }
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PROFILES = ("retail", "retail-bingx", "ftmo", "fotmarkets")


def _repo_root() -> Path:
    """Allow tests to override with WALLY_REPO_ROOT."""
    env = os.environ.get("WALLY_REPO_ROOT")
    if env:
        return Path(env)
    # Default: walk up from this file to find wally-trader root
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "CLAUDE.md").exists() and (parent / ".claude").is_dir():
            return parent
    raise RuntimeError("Could not locate wally-trader repo root")


def _pending_path(profile: str) -> Path:
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile: {profile}. Valid: {PROFILES}")
    return _repo_root() / ".claude" / "profiles" / profile / "memory" / "pending_orders.json"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _load_file(profile: str) -> dict:
    path = _pending_path(profile)
    if not path.exists():
        return {"pending": [], "meta": {}}
    with path.open() as f:
        return json.load(f)


def _save_file(profile: str, payload: dict) -> None:
    """Atomic write: temp file + os.replace."""
    path = _pending_path(profile)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        delete=False,
        prefix=".pending_",
        suffix=".tmp",
    ) as tf:
        json.dump(payload, tf, indent=2)
        tmp_name = tf.name
    os.replace(tmp_name, path)


def load_pendings(profile: str) -> list[dict]:
    """Return list of pending orders for a profile."""
    return _load_file(profile).get("pending", [])


def save_pendings(profile: str, pendings: list[dict], meta: Optional[dict] = None) -> None:
    """Overwrite the pending list for a profile. meta is merged with existing."""
    payload = _load_file(profile)
    payload["pending"] = pendings
    if meta:
        payload.setdefault("meta", {}).update(meta)
    _save_file(profile, payload)


def append_pending(profile: str, order: dict) -> dict:
    """Append a new order. Initializes status_history if missing."""
    order = dict(order)  # don't mutate caller
    if "status_history" not in order:
        order["status_history"] = [
            {
                "at": _now_iso(),
                "status": order.get("status", "pending"),
                "note": "created via append_pending",
            }
        ]
    pendings = load_pendings(profile)
    pendings.append(order)
    save_pendings(profile, pendings)
    return order


def update_status(profile: str, order_id: str, new_status: str, note: str = "") -> dict:
    """Mutate status + append to status_history. Raises KeyError if id not found."""
    pendings = load_pendings(profile)
    for order in pendings:
        if order["id"] == order_id:
            order["status"] = new_status
            history = order.setdefault("status_history", [])
            history.append({"at": _now_iso(), "status": new_status, "note": note})
            save_pendings(profile, pendings)
            return order
    raise KeyError(f"No pending order with id={order_id!r} in profile {profile!r}")


def find_by_id(order_id: str) -> Optional[tuple[str, dict]]:
    """Search all profiles for an order. Returns (profile, order) or None."""
    for profile in PROFILES:
        for order in load_pendings(profile):
            if order["id"] == order_id:
                return profile, order
    return None


def load_all_pendings() -> dict[str, list[dict]]:
    """Return {profile: [pendings, ...]} for all profiles."""
    return {profile: load_pendings(profile) for profile in PROFILES}


from dataclasses import dataclass
from dateutil import parser as _dateutil_parser


@dataclass
class InvalidationResult:
    invalidated: bool
    new_status: Optional[str] = None
    reason: Optional[str] = None


def _parse_iso(s: str) -> datetime:
    """Parse ISO8601 preserving tz info; assume local if naive."""
    dt = _dateutil_parser.isoparse(s)
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return dt


def evaluate_invalidation(
    order: dict,
    current_price: float,
    stopday_profiles: set,
) -> InvalidationResult:
    """Return whether a pending order should be invalidated and why.

    Checked in priority order (first match wins):
      1. Stop-day (2 SLs already hit today in that profile)
      2. Force-exit time reached (regla "no dormir con trade abierto")
      3. TTL expired
      4. Price crossed invalidation threshold
    """
    now_utc = datetime.now(timezone.utc)

    # 1. Stop-day
    if order.get("profile") in stopday_profiles:
        return InvalidationResult(
            True, "invalidated_stopday", "2 SLs hit today → STOP día regla"
        )

    # 2. Force-exit time
    force_exit_s = order.get("force_exit_mx")
    if force_exit_s:
        force_exit_dt = _parse_iso(force_exit_s)
        if now_utc >= force_exit_dt.astimezone(timezone.utc):
            return InvalidationResult(
                True, "expired_force_exit", f"force_exit {force_exit_s} reached"
            )

    # 3. TTL
    expires_s = order.get("expires_at")
    if expires_s:
        expires_dt = _parse_iso(expires_s)
        if now_utc >= expires_dt.astimezone(timezone.utc):
            return InvalidationResult(
                True, "expired_ttl", f"TTL {expires_s} reached"
            )

    # 4. Price
    invalidation_price = order.get("invalidation_price")
    invalidation_side = order.get("invalidation_side", "below")
    if invalidation_price and invalidation_price > 0:
        if invalidation_side == "below" and current_price < invalidation_price:
            return InvalidationResult(
                True,
                "invalidated_price",
                f"price {current_price} < invalidation {invalidation_price}",
            )
        if invalidation_side == "above" and current_price > invalidation_price:
            return InvalidationResult(
                True,
                "invalidated_price",
                f"price {current_price} > invalidation {invalidation_price}",
            )

    return InvalidationResult(False)


def count_sls_today(profile: str) -> int:
    """Parse trading_log.md of profile; count SL trades dated today (MX tz).

    Relaxed parser: any line containing 'SL' or 'stop loss' AND today's date
    in YYYY-MM-DD format. Good enough for stop-day rule.
    """
    log_path = (
        _repo_root() / ".claude" / "profiles" / profile / "memory" / "trading_log.md"
    )
    if not log_path.exists():
        return 0
    # today in MX tz (UTC-6)
    from datetime import timedelta as _td
    mx_now = datetime.now(timezone.utc) - _td(hours=6)
    today_str = mx_now.strftime("%Y-%m-%d")
    content = log_path.read_text().lower()
    count = 0
    for line in content.splitlines():
        if today_str in line and ("sl" in line or "stop loss" in line):
            count += 1
    return count


def stopday_triggered_profiles() -> set:
    """Return set of profiles where today's SL count >= 2."""
    triggered = set()
    for profile in PROFILES:
        if count_sls_today(profile) >= 2:
            triggered.add(profile)
    return triggered


import yaml

TERMINAL_STATUSES = {
    "filled",
    "expired_ttl",
    "expired_force_exit",
    "invalidated_price",
    "invalidated_regime",
    "invalidated_stopday",
    "canceled_manual",
}


def _default_matrix_path() -> Path:
    """Return the whitelist_matrix.yaml path.

    Strategy (approach b):
    1. Try WALLY_REPO_ROOT env var (used by tests) — if matrix exists there, use it.
    2. Fall back to the real repo root found by walking up from __file__.
    This ensures tests that monkeypatch WALLY_REPO_ROOT to tmp still load the
    real matrix (since tmp has no whitelist_matrix.yaml).
    """
    env = os.environ.get("WALLY_REPO_ROOT")
    if env:
        candidate = Path(env) / ".claude" / "watcher" / "whitelist_matrix.yaml"
        if candidate.exists():
            return candidate
    # Fall back to real repo path (from __file__ location)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "CLAUDE.md").exists() and (parent / ".claude").is_dir():
            return parent / ".claude" / "watcher" / "whitelist_matrix.yaml"
    # Last resort: use env path even if it doesn't exist
    if env:
        return Path(env) / ".claude" / "watcher" / "whitelist_matrix.yaml"
    raise RuntimeError("Could not locate whitelist_matrix.yaml")


def _load_matrix(matrix_path: Optional[Path]) -> dict:
    path = Path(matrix_path) if matrix_path else _default_matrix_path()
    if not path.exists():
        # Degrade gracefully: allow-all
        return {"asset_families": {}, "rules": [{"id": "allow_default",
                                                  "match": {}, "action": "allow"}]}
    with path.open() as f:
        return yaml.safe_load(f)


def _asset_family_of(profile: str, asset: str, families: dict) -> Optional[str]:
    key = f"{profile}:{asset}"
    for family, members in families.items():
        if key in members:
            return family
    return None


def _rule_matches(rule_match: dict, pair: tuple, families: dict) -> bool:
    o1, o2 = pair
    # profiles_in + count_gte
    if "profiles_in" in rule_match:
        allowed = set(rule_match["profiles_in"])
        count = sum(1 for o in (o1, o2) if o["profile"] in allowed)
        if count < rule_match.get("count_gte", 2):
            return False
    # same_asset_family
    if "same_asset_family" in rule_match:
        f1 = _asset_family_of(o1["profile"], o1["asset"], families)
        f2 = _asset_family_of(o2["profile"], o2["asset"], families)
        same = f1 is not None and f1 == f2
        if rule_match["same_asset_family"] != same:
            return False
    # same_side
    if "same_side" in rule_match:
        same = o1.get("side") == o2.get("side")
        if rule_match["same_side"] != same:
            return False
    return True


def apply_whitelist_matrix(
    pendings_by_profile: dict,
    matrix_path: Optional[Path] = None,
) -> tuple:
    """Partition all pending orders into (active, suspended_policy).

    Order is iterated chronologically by created_at. For each pair of
    non-terminal orders, the first matching rule decides.
    """
    matrix = _load_matrix(matrix_path)
    families = matrix.get("asset_families", {})
    rules = matrix.get("rules", [])

    # Flatten + filter terminal + sort by created_at
    flat = []
    for profile, orders in pendings_by_profile.items():
        for o in orders:
            if o.get("status") not in TERMINAL_STATUSES:
                flat.append(o)
    flat.sort(key=lambda o: o.get("created_at", ""))

    active: list = []
    suspended: list = []

    for candidate in flat:
        decision = "allow"
        for existing in active:
            for rule in rules:
                if _rule_matches(rule.get("match", {}), (existing, candidate), families):
                    decision = rule.get("action", "allow")
                    break
            if decision != "allow":
                break
        if decision == "suspend_newest":
            suspended.append(candidate)
        else:
            # allow or allow_with_warning both keep it active
            active.append(candidate)

    return active, suspended
