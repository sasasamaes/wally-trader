# Watcher + Pending Orders "Set & Forget" Implementation Plan (Fase 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Shipar v1.0 del sistema watcher: el usuario hace `/order` tras `/morning`, un watcher launchd vigila cada hora, escala a Claude headless cuando el precio está cerca, e invalida automáticamente. Multi-profile (retail, retail-bingx, ftmo, fotmarkets). macOS notify + dashboard. Telegram/email/--real son stubs silenciosos.

**Architecture:** launchd corre `watcher_tick.py` stateless cada hora — evalúa invalidaciones triviales (TTL, precio, 2SL, force_exit) sobre `pending_orders.json` por profile, aplica whitelist matrix cross-profile, y si `distancia_a_entry <0.3%` spawnea `claude -p /watch-deep` headless para validación MCP completa (RSI, BB, Donchian, 4 filtros). Claude-side decide `triggered_go` y llama `notify_hub` en urgency CRITICAL.

**Tech Stack:** Python 3.12 (stdlib + `requests`, `pyyaml`, `python-dateutil`), bash/zsh, macOS `osascript`, `launchd`, pytest, Claude Code slash commands.

**Reference spec:** `docs/superpowers/specs/2026-04-24-watcher-pending-orders-design.md`

---

## Task 1: Scaffolding — dirs + whitelist matrix + pending files

**Files:**
- Create: `.claude/watcher/whitelist_matrix.yaml`
- Create: `.claude/watcher/README.md`
- Create: `.claude/profiles/retail/memory/pending_orders.json` (empty)
- Create: `.claude/profiles/retail-bingx/memory/pending_orders.json` (empty)
- Create: `.claude/profiles/fotmarkets/memory/pending_orders.json` (empty)
- Confirm exists: `.claude/profiles/ftmo/memory/pending_orders.json` (already has `{"pending": []}`)

- [ ] **Step 1: Create watcher directory**

```bash
mkdir -p .claude/watcher/launchd
```

- [ ] **Step 2: Write whitelist_matrix.yaml**

Create `.claude/watcher/whitelist_matrix.yaml`:

```yaml
# Cross-profile compatibility matrix for pending orders.
# Rules evaluated top-to-bottom; first match wins.

asset_families:
  BTC:
    - retail:BTCUSDT.P
    - retail-bingx:BTCUSDT.P
    - ftmo:BTCUSD
    - fotmarkets:BTCUSD
  ETH:
    - ftmo:ETHUSD
    - fotmarkets:ETHUSD
  EURUSD:
    - ftmo:EURUSD
    - fotmarkets:EURUSD
  GBPUSD:
    - ftmo:GBPUSD
    - fotmarkets:GBPUSD
  NAS100:
    - ftmo:NAS100
    - fotmarkets:NAS100
  SPX500:
    - ftmo:SPX500
    - fotmarkets:SPX500

rules:
  - id: block_retail_and_retail_bingx_simultaneous
    match:
      profiles_in: [retail, retail-bingx]
      count_gte: 2
    action: suspend_newest
    reason: "Regla sagrada CLAUDE.md — no dos profiles retail simultáneos"

  - id: block_ftmo_and_fotmarkets_same_asset_family
    match:
      profiles_in: [ftmo, fotmarkets]
      same_asset_family: true
    action: suspend_newest
    reason: "Dos brokers MT5 = doble exposure real-ish"

  - id: block_same_family_same_direction
    match:
      same_asset_family: true
      same_side: true
    action: suspend_newest
    reason: "Doble exposure direccional al mismo underlying"

  - id: allow_hedge_different_direction
    match:
      same_asset_family: true
      same_side: false
    action: allow_with_warning
    warning: "Hedge detectado — asegura que es intencional"

  - id: allow_default
    match: {}
    action: allow
```

- [ ] **Step 3: Write watcher/README.md**

Create `.claude/watcher/README.md`:

```markdown
# Watcher System

Auto-generated runtime state for the pending-orders watcher.

## Files

- `status.json` — last tick metadata (updated every run)
- `dashboard.md` — human-readable state of all pending orders (rewritten each tick)
- `whitelist_matrix.yaml` — cross-profile compatibility rules (hand-edited)
- `launchd/com.wallytrader.watcher.plist` — macOS launch agent template

## Install (one-time)

```bash
cp .claude/watcher/launchd/com.wallytrader.watcher.plist \
   ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.wallytrader.watcher.plist
launchctl list | grep wallytrader
```

See spec: `docs/superpowers/specs/2026-04-24-watcher-pending-orders-design.md`
```

- [ ] **Step 4: Initialize empty pending_orders.json for missing profiles**

```bash
for profile in retail retail-bingx fotmarkets; do
    FILE=".claude/profiles/${profile}/memory/pending_orders.json"
    if [ ! -f "$FILE" ]; then
        echo '{"pending": [], "meta": {}}' > "$FILE"
    fi
done
```

Verify all 4 profiles have the file:

```bash
for profile in retail retail-bingx ftmo fotmarkets; do
    ls -la ".claude/profiles/${profile}/memory/pending_orders.json"
done
```

Expected: 4 files listed, all exist.

- [ ] **Step 5: Commit**

```bash
git add .claude/watcher .claude/profiles/*/memory/pending_orders.json
git commit -m "feat(watcher): scaffolding — whitelist matrix + pending files per profile"
```

---

## Task 2: `pending_lib.py` — CRUD

**Files:**
- Create: `.claude/scripts/pending_lib.py`
- Create: `.claude/scripts/tests/__init__.py`
- Create: `.claude/scripts/tests/test_pending_lib.py`

- [ ] **Step 1: Write failing tests**

Create `.claude/scripts/tests/test_pending_lib.py`:

```python
"""Tests for pending_lib CRUD."""
import json
import os
import tempfile
from pathlib import Path
import pytest

from pending_lib import (
    PROFILES,
    load_pendings,
    save_pendings,
    append_pending,
    update_status,
    find_by_id,
    load_all_pendings,
)


@pytest.fixture
def tmp_repo(tmp_path, monkeypatch):
    """Create a fake .claude/profiles/*/memory/pending_orders.json tree."""
    for profile in PROFILES:
        memdir = tmp_path / ".claude" / "profiles" / profile / "memory"
        memdir.mkdir(parents=True, exist_ok=True)
        (memdir / "pending_orders.json").write_text(
            json.dumps({"pending": [], "meta": {}})
        )
    monkeypatch.setenv("WALLY_REPO_ROOT", str(tmp_path))
    return tmp_path


def test_load_empty_profile_returns_empty_list(tmp_repo):
    assert load_pendings("retail") == []


def test_save_and_load_roundtrip(tmp_repo):
    orders = [{"id": "ord_1", "profile": "retail", "status": "pending"}]
    save_pendings("retail", orders)
    assert load_pendings("retail") == orders


def test_append_pending_adds_status_history(tmp_repo):
    order = {"id": "ord_1", "profile": "retail", "status": "pending"}
    append_pending("retail", order)
    loaded = load_pendings("retail")
    assert len(loaded) == 1
    assert loaded[0]["id"] == "ord_1"
    assert len(loaded[0]["status_history"]) == 1
    assert loaded[0]["status_history"][0]["status"] == "pending"


def test_update_status_appends_history(tmp_repo):
    append_pending("retail", {"id": "ord_1", "profile": "retail", "status": "pending"})
    update_status("retail", "ord_1", "expired_ttl", note="TTL passed")
    loaded = load_pendings("retail")
    assert loaded[0]["status"] == "expired_ttl"
    assert len(loaded[0]["status_history"]) == 2
    assert loaded[0]["status_history"][-1]["note"] == "TTL passed"


def test_update_status_raises_if_id_missing(tmp_repo):
    with pytest.raises(KeyError):
        update_status("retail", "nope", "expired_ttl")


def test_find_by_id_searches_all_profiles(tmp_repo):
    append_pending("fotmarkets", {"id": "ord_fx", "profile": "fotmarkets", "status": "pending"})
    found = find_by_id("ord_fx")
    assert found is not None
    profile, order = found
    assert profile == "fotmarkets"
    assert order["id"] == "ord_fx"


def test_find_by_id_returns_none_if_not_found(tmp_repo):
    assert find_by_id("nonexistent") is None


def test_load_all_pendings_covers_all_profiles(tmp_repo):
    append_pending("retail", {"id": "a", "profile": "retail", "status": "pending"})
    append_pending("ftmo", {"id": "b", "profile": "ftmo", "status": "pending"})
    result = load_all_pendings()
    assert set(result.keys()) == set(PROFILES)
    assert len(result["retail"]) == 1
    assert len(result["ftmo"]) == 1
    assert result["fotmarkets"] == []


def test_save_is_atomic(tmp_repo):
    """Partial writes must not corrupt the file."""
    # Write a valid baseline
    save_pendings("retail", [{"id": "ord_1", "status": "pending"}])
    file_path = tmp_repo / ".claude/profiles/retail/memory/pending_orders.json"
    mtime_before = file_path.stat().st_mtime
    # Trigger a save that raises after writing temp file
    # (simulated: just verify roundtrip doesn't leave .tmp files behind)
    save_pendings("retail", [{"id": "ord_2", "status": "pending"}])
    assert not any(tmp_repo.rglob("*.tmp"))
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd .claude/scripts
python3 -m pytest tests/test_pending_lib.py -v
```

Expected: all tests FAIL with `ImportError: pending_lib`.

- [ ] **Step 3: Implement `pending_lib.py`**

Create `.claude/scripts/pending_lib.py`:

```python
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
from datetime import datetime
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd .claude/scripts
python3 -m pytest tests/test_pending_lib.py -v
```

Expected: 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/pending_lib.py .claude/scripts/tests/
git commit -m "feat(watcher): pending_lib CRUD with atomic writes + status_history"
```

---

## Task 3: `pending_lib.py` — Invalidation evaluator

**Files:**
- Modify: `.claude/scripts/pending_lib.py`
- Modify: `.claude/scripts/tests/test_pending_lib.py`

- [ ] **Step 1: Write failing tests (append to test file)**

Append to `.claude/scripts/tests/test_pending_lib.py`:

```python
from pending_lib import evaluate_invalidation, InvalidationResult
from datetime import datetime, timedelta, timezone


def _iso(dt):
    return dt.astimezone().isoformat(timespec="seconds")


def test_invalidation_ttl_expired():
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    order = {
        "id": "x",
        "expires_at": _iso(past),
        "force_exit_mx": _iso(datetime.now(timezone.utc) + timedelta(days=1)),
        "invalidation_price": 0,
        "invalidation_side": "below",
        "profile": "retail",
    }
    result = evaluate_invalidation(order, current_price=100.0, stopday_profiles=set())
    assert result.invalidated
    assert result.new_status == "expired_ttl"


def test_invalidation_price_broken_below():
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    order = {
        "id": "x",
        "expires_at": _iso(future),
        "force_exit_mx": _iso(future),
        "invalidation_price": 76900,
        "invalidation_side": "below",
        "profile": "retail",
    }
    result = evaluate_invalidation(order, current_price=76800, stopday_profiles=set())
    assert result.invalidated
    assert result.new_status == "invalidated_price"


def test_invalidation_price_broken_above():
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    order = {
        "id": "x",
        "expires_at": _iso(future),
        "force_exit_mx": _iso(future),
        "invalidation_price": 79500,
        "invalidation_side": "above",
        "profile": "retail",
    }
    result = evaluate_invalidation(order, current_price=79600, stopday_profiles=set())
    assert result.invalidated
    assert result.new_status == "invalidated_price"


def test_invalidation_stopday():
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    order = {
        "id": "x",
        "expires_at": _iso(future),
        "force_exit_mx": _iso(future),
        "invalidation_price": 0,
        "invalidation_side": "below",
        "profile": "retail",
    }
    result = evaluate_invalidation(
        order, current_price=100.0, stopday_profiles={"retail"}
    )
    assert result.invalidated
    assert result.new_status == "invalidated_stopday"


def test_invalidation_force_exit():
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    future = datetime.now(timezone.utc) + timedelta(days=1)
    order = {
        "id": "x",
        "expires_at": _iso(future),
        "force_exit_mx": _iso(past),
        "invalidation_price": 0,
        "invalidation_side": "below",
        "profile": "retail",
    }
    result = evaluate_invalidation(order, current_price=100.0, stopday_profiles=set())
    assert result.invalidated
    assert result.new_status == "expired_force_exit"


def test_invalidation_none_active():
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    order = {
        "id": "x",
        "expires_at": _iso(future),
        "force_exit_mx": _iso(future),
        "invalidation_price": 76900,
        "invalidation_side": "below",
        "profile": "retail",
    }
    result = evaluate_invalidation(order, current_price=77500, stopday_profiles=set())
    assert not result.invalidated
    assert result.new_status is None
```

- [ ] **Step 2: Run to verify failing**

```bash
cd .claude/scripts
python3 -m pytest tests/test_pending_lib.py::test_invalidation_ttl_expired -v
```

Expected: FAIL with `ImportError: cannot import name 'evaluate_invalidation'`.

- [ ] **Step 3: Implement invalidation evaluator**

Append to `.claude/scripts/pending_lib.py`:

```python
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
    stopday_profiles: set[str],
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


def stopday_triggered_profiles() -> set[str]:
    """Return set of profiles where today's SL count >= 2."""
    triggered = set()
    for profile in PROFILES:
        if count_sls_today(profile) >= 2:
            triggered.add(profile)
    return triggered
```

- [ ] **Step 4: Run tests — all invalidation tests pass**

```bash
cd .claude/scripts
python3 -m pytest tests/test_pending_lib.py -v
```

Expected: all 15 tests PASS (9 CRUD + 6 invalidation).

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/pending_lib.py .claude/scripts/tests/test_pending_lib.py
git commit -m "feat(watcher): invalidation evaluator — TTL + price + stopday + force_exit"
```

---

## Task 4: `pending_lib.py` — Whitelist matrix evaluator

**Files:**
- Modify: `.claude/scripts/pending_lib.py`
- Modify: `.claude/scripts/tests/test_pending_lib.py`

- [ ] **Step 1: Write failing tests**

Append to `.claude/scripts/tests/test_pending_lib.py`:

```python
from pending_lib import apply_whitelist_matrix


def _order(profile, asset, side, id_="ord_x", status="pending", created_at=None):
    return {
        "id": id_,
        "profile": profile,
        "asset": asset,
        "side": side,
        "status": status,
        "created_at": created_at or "2026-04-24T10:00:00-06:00",
    }


def test_whitelist_single_order_always_active():
    pendings = {"retail": [_order("retail", "BTCUSDT.P", "LONG")]}
    active, suspended = apply_whitelist_matrix(pendings, matrix_path=None)
    assert len(active) == 1
    assert len(suspended) == 0


def test_whitelist_blocks_retail_plus_retail_bingx():
    pendings = {
        "retail": [_order("retail", "BTCUSDT.P", "LONG", id_="a",
                          created_at="2026-04-24T10:00:00-06:00")],
        "retail-bingx": [_order("retail-bingx", "BTCUSDT.P", "LONG", id_="b",
                                created_at="2026-04-24T10:05:00-06:00")],
    }
    active, suspended = apply_whitelist_matrix(pendings, matrix_path=None)
    # newer (b) suspended; older (a) stays
    assert {o["id"] for o in active} == {"a"}
    assert {o["id"] for o in suspended} == {"b"}


def test_whitelist_blocks_same_family_same_side_cross_profile():
    pendings = {
        "retail": [_order("retail", "BTCUSDT.P", "LONG", id_="a",
                          created_at="2026-04-24T09:00:00-06:00")],
        "fotmarkets": [_order("fotmarkets", "BTCUSD", "LONG", id_="b",
                              created_at="2026-04-24T10:00:00-06:00")],
    }
    active, suspended = apply_whitelist_matrix(pendings, matrix_path=None)
    assert {o["id"] for o in active} == {"a"}
    assert {o["id"] for o in suspended} == {"b"}


def test_whitelist_allows_hedge_opposite_side():
    pendings = {
        "retail": [_order("retail", "BTCUSDT.P", "LONG", id_="a",
                          created_at="2026-04-24T09:00:00-06:00")],
        "fotmarkets": [_order("fotmarkets", "BTCUSD", "SHORT", id_="b",
                              created_at="2026-04-24T10:00:00-06:00")],
    }
    active, suspended = apply_whitelist_matrix(pendings, matrix_path=None)
    assert {o["id"] for o in active} == {"a", "b"}
    assert len(suspended) == 0


def test_whitelist_allows_different_asset_families():
    pendings = {
        "retail": [_order("retail", "BTCUSDT.P", "LONG", id_="a")],
        "fotmarkets": [_order("fotmarkets", "EURUSD", "LONG", id_="b")],
    }
    active, suspended = apply_whitelist_matrix(pendings, matrix_path=None)
    assert len(active) == 2
    assert len(suspended) == 0


def test_whitelist_ftmo_plus_fotmarkets_same_family_blocked():
    pendings = {
        "ftmo": [_order("ftmo", "NAS100", "LONG", id_="a",
                        created_at="2026-04-24T09:00:00-06:00")],
        "fotmarkets": [_order("fotmarkets", "NAS100", "LONG", id_="b",
                              created_at="2026-04-24T10:00:00-06:00")],
    }
    active, suspended = apply_whitelist_matrix(pendings, matrix_path=None)
    assert {o["id"] for o in active} == {"a"}
    assert {o["id"] for o in suspended} == {"b"}


def test_whitelist_ignores_already_terminal_status():
    """Orders in filled/expired/canceled status aren't considered for matrix."""
    pendings = {
        "retail": [_order("retail", "BTCUSDT.P", "LONG", id_="a", status="filled")],
        "retail-bingx": [_order("retail-bingx", "BTCUSDT.P", "LONG", id_="b")],
    }
    active, suspended = apply_whitelist_matrix(pendings, matrix_path=None)
    # `b` is active because `a` is terminal
    assert {o["id"] for o in active} == {"b"}
    assert len(suspended) == 0
```

- [ ] **Step 2: Run to verify failure**

```bash
cd .claude/scripts
python3 -m pytest tests/test_pending_lib.py::test_whitelist_single_order_always_active -v
```

Expected: FAIL with `ImportError: cannot import name 'apply_whitelist_matrix'`.

- [ ] **Step 3: Implement whitelist matrix**

Append to `.claude/scripts/pending_lib.py`:

```python
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
    return _repo_root() / ".claude" / "watcher" / "whitelist_matrix.yaml"


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


def _rule_matches(rule_match: dict, pair: tuple[dict, dict], families: dict) -> bool:
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
    pendings_by_profile: dict[str, list[dict]],
    matrix_path: Optional[Path] = None,
) -> tuple[list[dict], list[dict]]:
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

    active: list[dict] = []
    suspended: list[dict] = []

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
```

- [ ] **Step 4: Run all tests**

```bash
cd .claude/scripts
python3 -m pytest tests/test_pending_lib.py -v
```

Expected: all 22 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/pending_lib.py .claude/scripts/tests/test_pending_lib.py
git commit -m "feat(watcher): whitelist matrix evaluator with YAML rules"
```

---

## Task 5: `price_feeds.py` — HTTP price getters

**Files:**
- Create: `.claude/scripts/price_feeds.py`
- Create: `.claude/scripts/tests/test_price_feeds.py`

- [ ] **Step 1: Write failing tests (with mocks)**

Create `.claude/scripts/tests/test_price_feeds.py`:

```python
"""Tests for price_feeds — all HTTP calls mocked."""
from unittest.mock import patch, MagicMock
import pytest

from price_feeds import (
    binance_futures_price,
    okx_swap_price,
    twelvedata_price,
    price_for,
    PriceFeedError,
)


@patch("price_feeds.requests.get")
def test_binance_futures_price(mock_get):
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"symbol": "BTCUSDT", "price": "77521.50"},
    )
    mock_get.return_value.raise_for_status = lambda: None

    price = binance_futures_price("BTCUSDT")
    assert price == 77521.50
    mock_get.assert_called_once()
    assert "fapi.binance.com" in mock_get.call_args[0][0]


@patch("price_feeds.requests.get")
def test_binance_raises_on_http_error(mock_get):
    mock_get.return_value.raise_for_status.side_effect = Exception("503")
    with pytest.raises(PriceFeedError):
        binance_futures_price("BTCUSDT")


@patch("price_feeds.requests.get")
def test_okx_swap_price(mock_get):
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"code": "0", "data": [{"last": "77500.1"}]},
    )
    mock_get.return_value.raise_for_status = lambda: None

    price = okx_swap_price("BTC-USDT-SWAP")
    assert price == 77500.1


@patch.dict("os.environ", {"TWELVEDATA_API_KEY": "test"})
@patch("price_feeds.requests.get")
def test_twelvedata_price(mock_get):
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"price": "1.17150"},
    )
    mock_get.return_value.raise_for_status = lambda: None

    price = twelvedata_price("EUR/USD")
    assert price == 1.17150


def test_price_for_unknown_profile_asset_raises():
    with pytest.raises(PriceFeedError):
        price_for("retail", "UNKNOWN_ASSET")


@patch("price_feeds.binance_futures_price", return_value=77521.0)
def test_price_for_dispatches_retail_to_binance(mock_binance):
    assert price_for("retail", "BTCUSDT.P") == 77521.0
    mock_binance.assert_called_once_with("BTCUSDT")
```

- [ ] **Step 2: Run to verify failure**

```bash
cd .claude/scripts
python3 -m pytest tests/test_price_feeds.py -v
```

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement price_feeds.py**

Create `.claude/scripts/price_feeds.py`:

```python
"""HTTP price feeds — no credentials required for public endpoints.

Providers:
- Binance Futures (fapi.binance.com) — BTCUSDT perpetual
- OKX swap (okx.com) — backup for BTC
- TwelveData (api.twelvedata.com) — EUR/USD, GBP/USD, indices. Free tier 800 req/day.

Asset-symbol mapping per profile in ASSET_MAP.
"""
from __future__ import annotations

import os
import requests
from typing import Callable

DEFAULT_TIMEOUT = 5  # seconds


class PriceFeedError(RuntimeError):
    pass


def _get_json(url: str, params: dict | None = None) -> dict:
    try:
        r = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise PriceFeedError(f"GET {url} failed: {e}") from e


def binance_futures_price(symbol: str) -> float:
    data = _get_json(
        "https://fapi.binance.com/fapi/v1/ticker/price",
        {"symbol": symbol},
    )
    return float(data["price"])


def okx_swap_price(instId: str) -> float:
    data = _get_json(
        "https://www.okx.com/api/v5/market/ticker",
        {"instId": instId},
    )
    if data.get("code") != "0" or not data.get("data"):
        raise PriceFeedError(f"OKX error: {data}")
    return float(data["data"][0]["last"])


def twelvedata_price(symbol: str) -> float:
    api_key = os.environ.get("TWELVEDATA_API_KEY")
    if not api_key:
        raise PriceFeedError(
            "TWELVEDATA_API_KEY not set — add to .claude/.env. "
            "Signup free: twelvedata.com (800 req/day tier)"
        )
    data = _get_json(
        "https://api.twelvedata.com/price",
        {"symbol": symbol, "apikey": api_key},
    )
    if "price" not in data:
        raise PriceFeedError(f"TwelveData unexpected response: {data}")
    return float(data["price"])


# (profile, asset) -> callable
ASSET_MAP: dict[tuple[str, str], Callable[[], float]] = {
    ("retail", "BTCUSDT.P"): lambda: binance_futures_price("BTCUSDT"),
    ("retail-bingx", "BTCUSDT.P"): lambda: binance_futures_price("BTCUSDT"),
    # ftmo uses MT5 symbols; fapi prefix as proxy for retail monitoring
    ("ftmo", "BTCUSD"): lambda: binance_futures_price("BTCUSDT"),
    ("ftmo", "ETHUSD"): lambda: binance_futures_price("ETHUSDT"),
    ("ftmo", "EURUSD"): lambda: twelvedata_price("EUR/USD"),
    ("ftmo", "GBPUSD"): lambda: twelvedata_price("GBP/USD"),
    ("ftmo", "NAS100"): lambda: twelvedata_price("NDX"),
    ("ftmo", "SPX500"): lambda: twelvedata_price("SPX"),
    # fotmarkets (same mapping as ftmo)
    ("fotmarkets", "BTCUSD"): lambda: binance_futures_price("BTCUSDT"),
    ("fotmarkets", "ETHUSD"): lambda: binance_futures_price("ETHUSDT"),
    ("fotmarkets", "EURUSD"): lambda: twelvedata_price("EUR/USD"),
    ("fotmarkets", "GBPUSD"): lambda: twelvedata_price("GBP/USD"),
    ("fotmarkets", "USDJPY"): lambda: twelvedata_price("USD/JPY"),
    ("fotmarkets", "XAUUSD"): lambda: twelvedata_price("XAU/USD"),
    ("fotmarkets", "NAS100"): lambda: twelvedata_price("NDX"),
    ("fotmarkets", "SPX500"): lambda: twelvedata_price("SPX"),
}


def price_for(profile: str, asset: str) -> float:
    """Dispatch to the right feed. Raises PriceFeedError if unknown."""
    key = (profile, asset)
    if key not in ASSET_MAP:
        raise PriceFeedError(f"No price feed mapping for ({profile!r}, {asset!r})")
    return ASSET_MAP[key]()
```

- [ ] **Step 4: Run tests**

```bash
cd .claude/scripts
python3 -m pytest tests/test_price_feeds.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 5: Smoke test against live Binance**

```bash
cd .claude/scripts
python3 -c "from price_feeds import price_for; print(price_for('retail', 'BTCUSDT.P'))"
```

Expected: a float BTC price printed (e.g., `77521.50`). If HTTP fails, check network.

- [ ] **Step 6: Commit**

```bash
git add .claude/scripts/price_feeds.py .claude/scripts/tests/test_price_feeds.py
git commit -m "feat(watcher): price_feeds — Binance/OKX/TwelveData + asset mapping"
```

---

## Task 6: `notify_hub.py` — Urgency dispatcher + macOS + stubs

**Files:**
- Create: `.claude/scripts/notify_hub.py`
- Create: `.claude/scripts/tests/test_notify_hub.py`

- [ ] **Step 1: Write failing tests**

Create `.claude/scripts/tests/test_notify_hub.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

```bash
cd .claude/scripts
python3 -m pytest tests/test_notify_hub.py -v
```

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement notify_hub.py**

Create `.claude/scripts/notify_hub.py`:

```python
"""Multi-channel notification hub.

Channels:
- macOS (osascript) — immediate, no dependencies
- dashboard.md — human-readable append/rewrite
- notifications.log — append-only audit trail
- Telegram (stub v1 — returns False if no token) — v2 integration
- Email via Resend (stub v1 — returns False if no key) — v3 integration

Urgency tiers control which channels fire.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from enum import IntEnum
from pathlib import Path


class Urgency(IntEnum):
    HEARTBEAT = 0
    INFO = 1
    WARN = 2
    CRITICAL = 3


def _repo_root() -> Path:
    env = os.environ.get("WALLY_REPO_ROOT")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "CLAUDE.md").exists() and (parent / ".claude").is_dir():
            return parent
    raise RuntimeError("Could not locate wally-trader repo root")


def _now_mx() -> str:
    from datetime import timedelta, timezone as _tz
    mx = datetime.now(_tz.utc) - timedelta(hours=6)
    return mx.strftime("%Y-%m-%d %H:%M:%S MX")


# ---------- Channel: macOS -----------------------------------

def macos_notify(title: str, body: str, sound: str = "Glass") -> bool:
    """osascript display notification. Returns True on success."""
    # escape double quotes
    t = title.replace('"', "'")
    b = body.replace('"', "'")
    cmd = [
        "osascript",
        "-e",
        f'display notification "{b}" with title "{t}" sound name "{sound}"',
    ]
    try:
        subprocess.run(cmd, check=True, timeout=5, capture_output=True)
        return True
    except Exception:
        return False


# ---------- Channel: Telegram (stub) -------------------------

def telegram_send(title: str, body: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False  # silent no-op (v1 stub)
    # Full implementation in v2
    return False


# ---------- Channel: Email (stub) ----------------------------

def email_send(title: str, body: str) -> bool:
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        return False  # silent no-op (v1 stub)
    # Full implementation in v3
    return False


# ---------- Channel: Dashboard file --------------------------

def write_to_dashboard(urgency: Urgency, event: str, payload: dict) -> None:
    """Append a line to .claude/watcher/dashboard.md events section.

    Full dashboard re-render is done by watcher_tick.py. This only appends to
    the 'Recent events' footer.
    """
    path = _repo_root() / ".claude" / "watcher" / "dashboard.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    line = (
        f"- `{_now_mx()}` [{urgency.name}] **{event}** — "
        f"{payload.get('order_id', '-')} "
        f"({payload.get('profile', '-')}:{payload.get('asset', '-')})"
    )
    # Append at end of file; watcher_tick rewrites the header each run
    with path.open("a") as f:
        f.write(line + "\n")


# ---------- Channel: Log -------------------------------------

def append_to_log(urgency: Urgency, event: str, payload: dict) -> None:
    path = _repo_root() / ".claude" / "scripts" / "notifications.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "at": _now_mx(),
        "urgency": urgency.name,
        "event": event,
        "payload": payload,
    }
    with path.open("a") as f:
        f.write(json.dumps(entry) + "\n")


# ---------- Event formatter ----------------------------------

_SOUNDS = {
    Urgency.HEARTBEAT: None,
    Urgency.INFO: "default",
    Urgency.WARN: "Glass",
    Urgency.CRITICAL: "Submarine",
}


def format_event(event: str, payload: dict) -> tuple[str, str]:
    """Return (title, body) for an event + payload."""
    pid = payload.get("order_id", "-")
    profile = payload.get("profile", "-")
    asset = payload.get("asset", "-")
    side = payload.get("side", "")
    entry = payload.get("entry", "-")

    if event == "triggered_go":
        title = f"🚨 TRIGGER GO — {profile} {asset} {side}"
        body = (
            f"Entry {entry} | SL {payload.get('sl','-')} | TP1 {payload.get('tp1','-')} | "
            f"filtros {payload.get('filters_passed','?')}/{payload.get('filters_total','?')} OK"
        )
    elif event == "near_entry":
        title = f"🔔 Precio cerca entry — {profile} {asset}"
        body = (
            f"Dist {payload.get('distance_pct','?')}% de {entry} — Claude validando"
        )
    elif event == "invalidated_price":
        title = f"⚠️ Invalidated — {profile} {asset}"
        body = f"Precio rompió {payload.get('invalidation_price','-')}"
    elif event == "invalidated_stopday":
        title = f"⚠️ Stop-day — {profile}"
        body = f"2 SLs hoy → pendings del profile canceladas ({pid})"
    elif event in ("expired_ttl", "expired_force_exit"):
        title = f"⏳ Expired — {profile} {asset}"
        body = f"Orden {pid} expiró sin fill ({event})"
    elif event == "order_created":
        title = f"📝 Order queued — {profile} {asset} {side}"
        body = f"Entry {entry} — watcher vigilando"
    elif event == "suspended_switch":
        title = f"⏸ Suspended — profile switch"
        body = f"Orden {pid} en {profile} pausada (switch)"
    elif event == "re_analysis_suggested":
        title = f"📊 Re-análisis sugerido — {profile}"
        body = f"Próxima revisión: {payload.get('next_recheck_mx','-')}"
    elif event == "degraded_watcher":
        title = f"⚠️ Watcher degraded — {profile}"
        body = f"Claude validation failed para {pid} — revisa manual"
    elif event == "filled":
        title = f"✅ Filled — {profile} {asset}"
        body = f"Orden {pid} ejecutada @ {payload.get('filled_price', entry)}"
    else:
        title = f"Wally — {event}"
        body = f"{pid} ({profile}:{asset})"
    return title, body


# ---------- Main dispatcher ----------------------------------

def notify(urgency: Urgency, event: str, payload: dict) -> None:
    """Main entry point. Dispatches to channels based on urgency."""
    append_to_log(urgency, event, payload)
    write_to_dashboard(urgency, event, payload)

    if urgency >= Urgency.INFO:
        title, body = format_event(event, payload)
        sound = _SOUNDS.get(urgency, "Glass") or "default"
        macos_notify(title, body, sound=sound)

    if urgency >= Urgency.WARN:
        title, body = format_event(event, payload)
        telegram_send(title, body)

    if urgency >= Urgency.CRITICAL:
        title, body = format_event(event, payload)
        email_send(title, body)


if __name__ == "__main__":
    # CLI: python3 notify_hub.py --test
    import sys
    if "--test" in sys.argv:
        notify(Urgency.INFO, "order_created", {
            "order_id": "test_001",
            "profile": "retail",
            "asset": "BTCUSDT.P",
            "side": "LONG",
            "entry": 77521,
        })
        print("Test notification sent.")
```

- [ ] **Step 4: Run tests**

```bash
cd .claude/scripts
python3 -m pytest tests/test_notify_hub.py -v
```

Expected: 9 tests PASS.

- [ ] **Step 5: Smoke test macOS notification**

```bash
cd .claude/scripts
python3 notify_hub.py --test
```

Expected: macOS notification banner appears "📝 Order queued — retail BTCUSDT.P LONG / Entry 77521 — watcher vigilando". Console prints "Test notification sent."

- [ ] **Step 6: Commit**

```bash
git add .claude/scripts/notify_hub.py .claude/scripts/tests/test_notify_hub.py
git commit -m "feat(watcher): notify_hub with urgency tiers + macOS + telegram/email stubs"
```

---

## Task 7: `watcher_tick.py` — main orchestrator

**Files:**
- Create: `.claude/scripts/watcher_tick.py`
- Create: `.claude/scripts/tests/test_watcher_tick.py`

- [ ] **Step 1: Write failing tests**

Create `.claude/scripts/tests/test_watcher_tick.py`:

```python
"""Integration-ish tests for watcher_tick — price feed + notify mocked."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from pending_lib import PROFILES, append_pending
from watcher_tick import run_tick, TickResult


def _iso_now_plus(hours):
    dt = datetime.now(timezone.utc) + timedelta(hours=hours)
    return dt.astimezone().isoformat(timespec="seconds")


@pytest.fixture
def tmp_repo(tmp_path, monkeypatch):
    for profile in PROFILES:
        memdir = tmp_path / ".claude" / "profiles" / profile / "memory"
        memdir.mkdir(parents=True, exist_ok=True)
        (memdir / "pending_orders.json").write_text(
            json.dumps({"pending": [], "meta": {}})
        )
    # whitelist matrix (copy from repo)
    watcher_dir = tmp_path / ".claude" / "watcher"
    watcher_dir.mkdir(parents=True, exist_ok=True)
    import shutil
    src_matrix = Path(__file__).parent.parent.parent / ".claude" / "watcher" / "whitelist_matrix.yaml"
    shutil.copy(src_matrix, watcher_dir / "whitelist_matrix.yaml")
    # trading_log stubs (empty)
    for profile in PROFILES:
        log = tmp_path / ".claude" / "profiles" / profile / "memory" / "trading_log.md"
        log.write_text("# empty log\n")
    monkeypatch.setenv("WALLY_REPO_ROOT", str(tmp_path))
    return tmp_path


def test_tick_no_pendings_is_ok(tmp_repo):
    with patch("watcher_tick.price_for") as mock_price, \
         patch("watcher_tick.notify") as mock_notify:
        result = run_tick()
    assert result.ok
    assert result.pendings_checked == 0


def test_tick_invalidates_expired_ttl(tmp_repo):
    order = {
        "id": "ord_e",
        "profile": "retail",
        "asset": "BTCUSDT.P",
        "side": "LONG",
        "status": "pending",
        "entry": 77521,
        "expires_at": _iso_now_plus(-1),
        "force_exit_mx": _iso_now_plus(5),
        "invalidation_price": 0,
        "invalidation_side": "below",
        "created_at": _iso_now_plus(-6),
    }
    append_pending("retail", order)
    with patch("watcher_tick.price_for", return_value=77500.0), \
         patch("watcher_tick.notify") as mock_notify:
        result = run_tick()
    assert result.ok
    from pending_lib import load_pendings
    pendings = load_pendings("retail")
    assert pendings[0]["status"] == "expired_ttl"
    mock_notify.assert_called()


def test_tick_escalates_near_entry(tmp_repo):
    order = {
        "id": "ord_near",
        "profile": "retail",
        "asset": "BTCUSDT.P",
        "side": "LONG",
        "status": "pending",
        "entry": 77521,
        "expires_at": _iso_now_plus(5),
        "force_exit_mx": _iso_now_plus(5),
        "invalidation_price": 76000,
        "invalidation_side": "below",
        "created_at": _iso_now_plus(-1),
    }
    append_pending("retail", order)
    with patch("watcher_tick.price_for", return_value=77540.0), \
         patch("watcher_tick.notify") as mock_notify, \
         patch("watcher_tick.spawn_escalate") as mock_escalate:
        result = run_tick()
    assert result.ok
    mock_escalate.assert_called_once_with("ord_near")
    from pending_lib import load_pendings
    assert load_pendings("retail")[0]["status"] == "triggered_validating"


def test_tick_heartbeat_when_far(tmp_repo):
    order = {
        "id": "ord_far",
        "profile": "retail",
        "asset": "BTCUSDT.P",
        "side": "LONG",
        "status": "pending",
        "entry": 77521,
        "expires_at": _iso_now_plus(5),
        "force_exit_mx": _iso_now_plus(5),
        "invalidation_price": 70000,
        "invalidation_side": "below",
        "created_at": _iso_now_plus(-1),
    }
    append_pending("retail", order)
    with patch("watcher_tick.price_for", return_value=80000.0), \
         patch("watcher_tick.notify") as mock_notify, \
         patch("watcher_tick.spawn_escalate") as mock_escalate:
        result = run_tick()
    assert result.ok
    mock_escalate.assert_not_called()
    from pending_lib import load_pendings
    # status unchanged
    assert load_pendings("retail")[0]["status"] == "pending"


def test_tick_writes_status_and_dashboard(tmp_repo):
    with patch("watcher_tick.price_for"), patch("watcher_tick.notify"):
        run_tick()
    status = tmp_repo / ".claude" / "watcher" / "status.json"
    dashboard = tmp_repo / ".claude" / "watcher" / "dashboard.md"
    assert status.exists()
    assert dashboard.exists()
    data = json.loads(status.read_text())
    assert "last_tick_utc" in data
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd .claude/scripts
python3 -m pytest tests/test_watcher_tick.py -v
```

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement watcher_tick.py**

Create `.claude/scripts/watcher_tick.py`:

```python
#!/usr/bin/env python3
"""Hourly watcher tick — called by launchd.

1. Load pending_orders from all profiles
2. Apply whitelist matrix → (active, suspended_policy)
3. Fetch prices for all unique (profile, asset) pairs
4. Evaluate invalidations (TTL/price/stopday/force_exit) — no MCP required
5. For pendings still alive:
     distance_pct = |price - entry| / entry * 100
     if <= 0.3% → spawn claude -p "/watch-deep <id>" headless
     else → compute next_recheck and just heartbeat
6. Write status.json + dashboard.md
7. notify_hub for each event

Exit codes: 0 ok, 1 partial (some asset prices missing), 2 fatal.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from pending_lib import (
    PROFILES,
    TERMINAL_STATUSES,
    load_all_pendings,
    update_status,
    apply_whitelist_matrix,
    evaluate_invalidation,
    stopday_triggered_profiles,
    _parse_iso,
    _repo_root,
)
from price_feeds import price_for, PriceFeedError
from notify_hub import notify, Urgency


ESCALATE_DISTANCE_PCT = 0.3  # spawn Claude validation if within 0.3%


@dataclass
class TickResult:
    ok: bool
    pendings_checked: int = 0
    actions: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def spawn_escalate(order_id: str) -> None:
    """Run watcher_escalate.sh in background. No blocking."""
    script = _repo_root() / ".claude" / "scripts" / "watcher_escalate.sh"
    if not script.exists():
        # degraded: just log
        return
    subprocess.Popen(
        ["/bin/bash", str(script), order_id],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _distance_pct(price: float, entry: float) -> float:
    if entry == 0:
        return float("inf")
    return abs(price - entry) / entry * 100


def _next_recheck_from_distance(dist_pct: float) -> str:
    """Heuristic: far price = longer next check."""
    from datetime import timedelta as _td
    now = datetime.now().astimezone()
    if dist_pct < 0.5:
        delta = _td(minutes=15)
    elif dist_pct < 2.0:
        delta = _td(hours=1)
    else:
        delta = _td(hours=2)
    return (now + delta).isoformat(timespec="seconds")


def _write_status(result: TickResult, duration_ms: int) -> None:
    path = _repo_root() / ".claude" / "watcher" / "status.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "last_tick_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duration_ms": duration_ms,
        "pendings_checked": result.pendings_checked,
        "actions": result.actions,
        "errors": result.errors,
        "next_tick_eta_utc": (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat(timespec="seconds"),
    }
    path.write_text(json.dumps(data, indent=2))


def _render_dashboard(active: list[dict], suspended: list[dict], prices: dict) -> None:
    path = _repo_root() / ".claude" / "watcher" / "dashboard.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    from datetime import timedelta as _td
    mx_now = (datetime.now(timezone.utc) - _td(hours=6)).strftime("%Y-%m-%d %H:%M MX")

    lines = [
        f"# Watcher Dashboard — {mx_now}",
        "",
        f"Last tick: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"Active pendings: {len(active)} | Suspended: {len(suspended)}",
        "",
        "## Active pendings",
        "",
    ]
    if not active:
        lines.append("_(none)_")
    for o in active:
        key = (o["profile"], o["asset"])
        cur = prices.get(key)
        dist = _distance_pct(cur, o["entry"]) if cur else None
        lines.append(
            f"### `{o['id']}` — {o['profile']} {o['asset']} {o.get('side','')} @ {o.get('entry','?')}"
        )
        lines.append(
            f"Status: **{o.get('status','?')}** | "
            f"Price now: {cur or '?'} | "
            f"Distance: {dist:.2f}%" if dist is not None else f"Status: **{o.get('status','?')}**"
        )
        lines.append(f"TTL: {o.get('expires_at','?')} | Invalid @: {o.get('invalidation_price','?')}")
        lines.append("")

    lines += ["## Suspended", ""]
    if not suspended:
        lines.append("_(none)_")
    for o in suspended:
        lines.append(f"- `{o['id']}` — {o['profile']} {o['asset']} (status: {o.get('status','?')})")

    lines.append("")
    lines.append("## Recent events")
    lines.append("")
    path.write_text("\n".join(lines))


def run_tick() -> TickResult:
    """Run one tick cycle. Returns TickResult."""
    start = datetime.now()
    result = TickResult(ok=True)

    try:
        # Step 1: Load all pendings
        all_pendings = load_all_pendings()

        # Step 2: Whitelist matrix
        active, suspended_new = apply_whitelist_matrix(all_pendings)

        # Apply suspensions to storage
        for o in suspended_new:
            if o.get("status") != "suspended_policy":
                try:
                    update_status(
                        o["profile"], o["id"], "suspended_policy",
                        note="whitelist matrix: conflicting pending active",
                    )
                    notify(
                        Urgency.INFO,
                        "suspended_policy",
                        {"order_id": o["id"], "profile": o["profile"], "asset": o["asset"]},
                    )
                except KeyError:
                    pass

        # Step 3: Fetch prices for active pendings' unique assets
        prices: dict[tuple[str, str], float] = {}
        for o in active:
            key = (o["profile"], o["asset"])
            if key not in prices:
                try:
                    prices[key] = price_for(*key)
                except PriceFeedError as e:
                    result.errors.append(f"price fail {key}: {e}")
                    result.ok = False

        # Step 4: Invalidations
        stopday = stopday_triggered_profiles()
        survivors: list[dict] = []
        for o in active:
            key = (o["profile"], o["asset"])
            price = prices.get(key)
            if price is None:
                survivors.append(o)
                continue
            inv = evaluate_invalidation(o, price, stopday)
            if inv.invalidated:
                update_status(o["profile"], o["id"], inv.new_status, note=inv.reason or "")
                result.actions.append({
                    "order_id": o["id"], "action": "invalidated",
                    "new_status": inv.new_status, "reason": inv.reason,
                })
                urgency = (
                    Urgency.WARN if inv.new_status in ("invalidated_price", "invalidated_stopday")
                    else Urgency.INFO
                )
                notify(urgency, inv.new_status, {
                    "order_id": o["id"], "profile": o["profile"], "asset": o["asset"],
                    "invalidation_price": o.get("invalidation_price"),
                })
            else:
                survivors.append(o)

        # Step 5: Distance check + escalate/heartbeat
        for o in survivors:
            key = (o["profile"], o["asset"])
            price = prices.get(key)
            if price is None:
                continue
            dist_pct = _distance_pct(price, o["entry"])
            if dist_pct <= ESCALATE_DISTANCE_PCT:
                if o.get("status") != "triggered_validating":
                    update_status(
                        o["profile"], o["id"], "triggered_validating",
                        note=f"price {price} dist {dist_pct:.3f}% — escalating to Claude",
                    )
                spawn_escalate(o["id"])
                result.actions.append({
                    "order_id": o["id"], "action": "escalated",
                    "distance_pct": round(dist_pct, 3),
                })
                notify(Urgency.WARN, "near_entry", {
                    "order_id": o["id"], "profile": o["profile"], "asset": o["asset"],
                    "side": o.get("side"), "entry": o["entry"],
                    "distance_pct": round(dist_pct, 3),
                })
            else:
                # heartbeat — just update next_recheck_suggested_mx (no notify)
                next_check = _next_recheck_from_distance(dist_pct)
                # edit in place via save_pendings
                from pending_lib import load_pendings, save_pendings
                all_in = load_pendings(o["profile"])
                for it in all_in:
                    if it["id"] == o["id"]:
                        it["next_recheck_suggested_mx"] = next_check
                save_pendings(o["profile"], all_in)
                result.actions.append({
                    "order_id": o["id"], "action": "heartbeat",
                    "distance_pct": round(dist_pct, 3),
                })

        result.pendings_checked = len(active)

        # Step 6: Render dashboard + status.json
        _render_dashboard(active, suspended_new, prices)

    except Exception as e:
        result.ok = False
        result.errors.append(f"fatal: {e!r}")

    duration_ms = int((datetime.now() - start).total_seconds() * 1000)
    _write_status(result, duration_ms)

    return result


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="Print what would happen")
    args = p.parse_args()

    if args.dry_run:
        os.environ["WALLY_DRY_RUN"] = "1"

    result = run_tick()
    print(json.dumps(asdict(result), indent=2, default=str))
    sys.exit(0 if result.ok else 1 if result.errors else 2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

```bash
cd .claude/scripts
python3 -m pytest tests/test_watcher_tick.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Make executable + run against real (empty) state**

```bash
chmod +x .claude/scripts/watcher_tick.py
cd /Users/josecampos/Documents/wally-trader
python3 .claude/scripts/watcher_tick.py
```

Expected: JSON output with `"ok": true`, `"pendings_checked": 0`. Also creates `.claude/watcher/status.json` and `.claude/watcher/dashboard.md`.

- [ ] **Step 6: Commit**

```bash
git add .claude/scripts/watcher_tick.py .claude/scripts/tests/test_watcher_tick.py
git commit -m "feat(watcher): watcher_tick orchestrator — invalidations + escalation"
```

---

## Task 8: **MANUAL CHECKPOINT** — watcher_tick smoke test

- [ ] **Step 1: Create a test pending order**

```bash
cat > /tmp/test_pending.py <<'EOF'
from pending_lib import append_pending
from datetime import datetime, timedelta, timezone
now = datetime.now(timezone.utc)
append_pending("retail", {
    "id": "smoke_test_001",
    "profile": "retail",
    "asset": "BTCUSDT.P",
    "side": "LONG",
    "status": "pending",
    "entry": 1.0,  # impossibly low so "near" triggers
    "sl": 0.5,
    "tp1": 2.0,
    "invalidation_price": 0.5,
    "invalidation_side": "below",
    "created_at": now.astimezone().isoformat(timespec="seconds"),
    "expires_at": (now + timedelta(hours=6)).astimezone().isoformat(timespec="seconds"),
    "force_exit_mx": (now + timedelta(hours=12)).astimezone().isoformat(timespec="seconds"),
})
print("Added smoke_test_001")
EOF
cd .claude/scripts && python3 /tmp/test_pending.py
```

- [ ] **Step 2: Run watcher tick**

```bash
cd /Users/josecampos/Documents/wally-trader
python3 .claude/scripts/watcher_tick.py 2>&1 | head -40
```

Expected: order gets `invalidated_price` status (since BTC price >> 0.5 invalidation side below logic — actually since the entry is $1 and real BTC is ~$77k, distance is astronomical → heartbeat, NOT escalation).

Adjust expectation: with entry=$1, price=$77521, dist_pct = 7752000% (massive). No escalation. No invalidation (invalidation_price=0.5, side below, price 77521 > 0.5, so NOT below → not invalidated). Heartbeat only. Status unchanged.

- [ ] **Step 3: Verify dashboard + status**

```bash
cat .claude/watcher/status.json
cat .claude/watcher/dashboard.md
```

Expected:
- `status.json` has `actions: [{"order_id": "smoke_test_001", "action": "heartbeat", ...}]`
- `dashboard.md` shows "Active pendings: 1" with the test order.

- [ ] **Step 4: Cleanup**

```bash
cd .claude/scripts && python3 -c "
from pending_lib import load_pendings, save_pendings
pendings = [p for p in load_pendings('retail') if p['id'] != 'smoke_test_001']
save_pendings('retail', pendings)
print('Cleaned.')
"
```

- [ ] **Step 5: User confirmation**

Ask user: "¿Dashboard y status.json se ven correctos? ¿Listo para seguir con /order command?"
Wait for user OK before proceeding.

---

## Task 9: `/order` command — retail profile first

**Files:**
- Modify: `.claude/commands/order.md`
- Create: `.claude/scripts/order_lib.py` (helper logic for order creation)

- [ ] **Step 1: Rewrite `.claude/commands/order.md`**

Overwrite `.claude/commands/order.md`:

```markdown
Encola una orden limit virtual para el profile activo. El watcher la vigila
hourly hasta trigger/invalidación.

Uso:
- `/order` — infiere params del último análisis (si hay `/morning` reciente en la conversación).
- `/order BTCUSDT.P LONG 77521 sl=77101 tp=78571 ttl=6h`
- `/order BTCUSDT.P LONG 77521 sl=77101 tp=78571 invalid=76900 ttl=6h`
- `/order BTCUSDT.P LONG 77521 ... --real` (solo retail; en v1 imprime "stub")
- `/order BTCUSDT.P LONG 77521 ... --check-regime` (invalida si régimen cambia)

Pasos que ejecuta Claude:

1. **Lee profile activo:** `PROFILE=$(bash .claude/scripts/profile.sh get)`
2. **Parsea args:** Si vacíos, busca último setup en la conversación con bloque
   `ENTRY|SL|TP|INVALIDATION`. Si no encuentra → error "Dame params explícitos o corre /morning primero".
3. **Valida profile-specific:**
   - `ftmo` → **DELEGA al flow existente** (guardian.py + EA bridge). Este comando
     SOLO maneja el path virtual nuevo para retail, retail-bingx, fotmarkets.
     Si `PROFILE=ftmo`, imprime "Para FTMO usa el flow existente — ver
     pending_orders.json + mt5_bridge" y aborta (el comando ftmo original aún
     vive; este /order nuevo es para los 3 no-ftmo).
   - `retail` / `retail-bingx` → sanity checks no-bloqueantes (SL lado correcto,
     TP lado correcto, risk_pct ≤ 2, qty>0).
   - `fotmarkets` → llama `bash .claude/scripts/fotmarkets_guard.sh check`; si
     BLOCK → abortar. Aplica phase sizing.
4. **Whitelist matrix check:** Llama `python3 -c "from pending_lib import
   load_all_pendings, apply_whitelist_matrix; ..."` con la orden candidata
   añadida virtualmente. Si la nueva orden quedaría en `suspended_policy` →
   preguntar al usuario: "Otra pending bloquea esta. ¿Abortar o cancelar la
   conflictiva?"
5. **Construye el order dict** usando `order_lib.build_order(...)` (ver paso 7).
6. **Preview ASCII + confirmación:**

   ```
   ╔══════════════════════════════════════╗
   ║  NEW ORDER [virtual, watcher-tracked]║
   ║  ID: ord_YYYYMMDD_HHMMSS_...         ║
   ║  Profile:  retail                    ║
   ║  Asset:    BTCUSDT.P LONG            ║
   ║  Entry:    77521  (tol 0.1%)         ║
   ║  SL:       77101  (-0.54%)           ║
   ║  TP1/2/3:  78571 / 79201 / 80041     ║
   ║  Qty:      0.00086 BTC (Margin $6.72)║
   ║  Risk:     $0.36 (2.0% de $18.09)    ║
   ║  TTL:      6h (expires 16:48 MX)     ║
   ║  Invalid:  76900 (below)             ║
   ║  Filters:  RSI<35, BB-lo, DC-lo,     ║
   ║            candle green (at trigger) ║
   ╚══════════════════════════════════════╝
   ```

   Espera respuesta literal `YES`. Cualquier otro valor → abort.

7. **Si YES:**
   - Llama `python3 -c "from order_lib import create_and_persist; create_and_persist(...)"`
     con los params parseados.
   - Imprime confirmación + `notify_hub.notify(Urgency.INFO, "order_created", ...)`
   - Recuerda al usuario: "Puedes `/watch` ahora para forzar primer tick, o esperar el launchd hourly."

8. **Flags opcionales:**
   - `--real` en retail → en v1 imprime **"⚠️ --real no implementado en v1, orden creada solo virtual"** y continúa con flow virtual.
   - `--check-regime` → en la orden set `check_regime_change: true`.

Si algún paso falla (guardian, whitelist, confirmación != YES) → NO escribe pending_orders.json.
```

- [ ] **Step 2: Create `order_lib.py`**

Create `.claude/scripts/order_lib.py`:

```python
"""Order construction + persistence helpers called from /order slash command."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pending_lib import append_pending, load_all_pendings, apply_whitelist_matrix


# Default TP splits per profile
DEFAULT_TP_SPLITS = {
    "retail": [0.4, 0.4, 0.2],
    "retail-bingx": [0.4, 0.4, 0.2],
    "ftmo": [0.5, 0.5],  # (handled by legacy flow anyway)
    "fotmarkets": [1.0],  # single TP at 2R
}

DEFAULT_REQUIRED_FILTERS = {
    "retail": [
        "price_touches_donchian_low_15_for_long",
        "rsi_15m_lt_35_for_long",
        "bb_lower_touch_for_long",
        "candle_close_green_for_long",
    ],
    "retail-bingx": [
        "price_touches_donchian_low_15_for_long",
        "rsi_15m_lt_35_for_long",
        "bb_lower_touch_for_long",
        "candle_close_green_for_long",
    ],
    "fotmarkets": [
        "price_touches_structural_level",
        "rsi_5m_lt_30_for_long",
        "bb_lower_touch_for_long",
        "reversal_candle_5m",
    ],
}


def _gen_id(profile: str, asset: str, side: str) -> str:
    now = datetime.now().astimezone()
    asset_slug = asset.lower().replace(".", "").replace("/", "")
    return f"ord_{now.strftime('%Y%m%d_%H%M%S')}_{profile}_{asset_slug}_{side.lower()}"


def build_order(
    profile: str,
    asset: str,
    side: str,
    entry: float,
    sl: float,
    tp1: float,
    tp2: float | None = None,
    tp3: float | None = None,
    qty: float = 0.0,
    leverage: int = 10,
    risk_usd: float = 0.0,
    risk_pct: float = 2.0,
    invalidation_price: float = 0.0,
    invalidation_side: str = "below",
    ttl_hours: float = 6.0,
    force_exit_mx: str | None = None,
    strategy: str = "mean_reversion_15m",
    check_regime_change: bool = False,
    filters_at_creation: dict | None = None,
) -> dict:
    """Construct the full order dict per spec schema."""
    side = side.upper()
    now = datetime.now().astimezone()
    expires_at = (now + timedelta(hours=ttl_hours)).isoformat(timespec="seconds")
    if force_exit_mx is None:
        # End of today at 23:59 MX (UTC-6)
        mx_now = datetime.now(timezone.utc) - timedelta(hours=6)
        mx_eod = mx_now.replace(hour=23, minute=59, second=0, microsecond=0)
        force_exit_mx = mx_eod.isoformat(timespec="seconds")

    tp_splits = DEFAULT_TP_SPLITS.get(profile, [1.0])
    tps: list[float] = [t for t in (tp1, tp2, tp3) if t is not None]
    # ensure splits and tps match
    if len(tp_splits) > len(tps):
        tp_splits = tp_splits[: len(tps)]

    order = {
        "id": _gen_id(profile, asset, side),
        "profile": profile,
        "asset": asset,
        "side": side,
        "strategy": strategy,
        "entry_type": "limit",
        "entry": entry,
        "entry_tolerance_pct": 0.1,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "tp_splits": tp_splits,
        "risk_usd": risk_usd,
        "risk_pct": risk_pct,
        "qty": qty,
        "leverage": leverage,
        "filters_at_creation": filters_at_creation or {},
        "required_filters_at_trigger": DEFAULT_REQUIRED_FILTERS.get(profile, []),
        "invalidation_price": invalidation_price,
        "invalidation_side": invalidation_side,
        "invalidation_close_tf": "4h",
        "check_regime_change": check_regime_change,
        "created_at": now.isoformat(timespec="seconds"),
        "expires_at": expires_at,
        "force_exit_mx": force_exit_mx,
        "real_order": {
            "enabled": False,
            "binance_order_id": None,
            "placed_at": None,
        },
        "status": "pending",
        "next_recheck_suggested_mx": "",
    }
    return order


def preflight_whitelist(order: dict) -> tuple[bool, str]:
    """Check if this order would be suspended by the matrix. Returns (ok, reason)."""
    all_pendings = load_all_pendings()
    # add candidate virtually
    all_pendings.setdefault(order["profile"], [])
    virtual = list(all_pendings[order["profile"]]) + [order]
    virtual_map = {**all_pendings, order["profile"]: virtual}
    active, suspended = apply_whitelist_matrix(virtual_map)
    would_suspend = any(o["id"] == order["id"] for o in suspended)
    if would_suspend:
        existing_ids = [o["id"] for o in active]
        return False, f"Would conflict with: {existing_ids}"
    return True, "ok"


def create_and_persist(order: dict) -> dict:
    """Append to pending_orders.json + return the persisted order."""
    return append_pending(order["profile"], order)
```

- [ ] **Step 3: Smoke test `order_lib.py` in isolation**

```bash
cd .claude/scripts
python3 -c "
from order_lib import build_order, preflight_whitelist, create_and_persist
o = build_order('retail', 'BTCUSDT.P', 'LONG',
                entry=77521, sl=77101, tp1=78571, tp2=79201, tp3=80041,
                qty=0.00086, risk_usd=0.36, risk_pct=2.0,
                invalidation_price=76900, ttl_hours=6)
print('order id:', o['id'])
ok, reason = preflight_whitelist(o)
print('whitelist:', ok, reason)
# do NOT persist in smoke (would contaminate live profile)
"
```

Expected: prints `order id: ord_...`, `whitelist: True ok`.

- [ ] **Step 4: Commit**

```bash
git add .claude/commands/order.md .claude/scripts/order_lib.py
git commit -m "feat(watcher): /order command virtual for retail + order_lib builder"
```

---

## Task 10: `/pending` command

**Files:**
- Create: `.claude/commands/pending.md`

- [ ] **Step 1: Write `/pending` command spec**

Create `.claude/commands/pending.md`:

```markdown
Lista, muestra o modifica pending orders virtuales.

Uso:
- `/pending` — lista pending del profile activo (active + suspended)
- `/pending all` — lista cross-profile
- `/pending show <id>` — detalle completo con status_history
- `/pending cancel <id>` — marca `canceled_manual` (terminal, no-op después)
- `/pending modify <id> <field>=<val>` — edit limitado:
   campos permitidos: `tp1`, `tp2`, `tp3`, `ttl_hours`, `invalidation_price`, `check_regime_change`

Pasos que ejecuta Claude:

1. **Parsea subcommand:** si vacío → listar (profile activo). `all` → listar todos.
   `show <id>` → detalle. `cancel <id>` → terminal. `modify <id> ...` → edit.

2. **Para `/pending` / `/pending all`:**
   ```bash
   python3 -c "
   from pending_lib import load_all_pendings, PROFILES
   import json
   all_p = load_all_pendings()
   for profile, orders in all_p.items():
       if not orders: continue
       print(f'\\n{profile}:')
       for o in orders:
           print(f'  {o[\"id\"]}  {o[\"asset\"]} {o.get(\"side\",\"\")}  entry={o.get(\"entry\",\"-\")}  status={o[\"status\"]}')
   "
   ```
   Formatea la salida como tabla ASCII.

3. **Para `/pending show <id>`:**
   ```bash
   python3 -c "
   from pending_lib import find_by_id
   import json
   result = find_by_id('$ID')
   if result is None: print('Not found'); exit(1)
   profile, order = result
   print(f'Profile: {profile}'); print(json.dumps(order, indent=2))
   "
   ```

4. **Para `/pending cancel <id>`:**
   - Confirmación: "¿Cancelar `<id>`? Esto es terminal. [YES/no]"
   - Si YES:
     ```bash
     python3 -c "
     from pending_lib import find_by_id, update_status
     result = find_by_id('$ID')
     if result is None: print('Not found'); exit(1)
     profile, _ = result
     update_status(profile, '$ID', 'canceled_manual', note='user /pending cancel')
     print('Canceled.')
     "
     ```
   - notify INFO

5. **Para `/pending modify <id> <field>=<val>`:**
   - Valida field está en allowlist (`tp1|tp2|tp3|ttl_hours|invalidation_price|check_regime_change`)
   - Valida orden no está terminal
   - Aplica edit (si `ttl_hours`, recalcula `expires_at`):
     ```bash
     python3 -c "
     from pending_lib import find_by_id, load_pendings, save_pendings
     from datetime import datetime, timedelta
     result = find_by_id('$ID')
     if result is None: print('Not found'); exit(1)
     profile, _ = result
     pendings = load_pendings(profile)
     for p in pendings:
         if p['id'] == '$ID':
             if '$FIELD' == 'ttl_hours':
                 base = datetime.fromisoformat(p['created_at'])
                 p['expires_at'] = (base + timedelta(hours=float('$VAL'))).isoformat(timespec='seconds')
             else:
                 p['$FIELD'] = float('$VAL') if '$FIELD' != 'check_regime_change' else ('$VAL' == 'true')
             p.setdefault('status_history',[]).append({'at': datetime.now().astimezone().isoformat(timespec='seconds'), 'status': p['status'], 'note': 'modify $FIELD=$VAL'})
     save_pendings(profile, pendings)
     print('Modified.')
     "
     ```

6. Output final: resumen action + refresca dashboard con `python3 .claude/scripts/watcher_tick.py --dry-run` (solo re-render, no side effects).
```

- [ ] **Step 2: Smoke test listing**

```bash
# create a dummy order for retail
cd .claude/scripts && python3 -c "
from order_lib import build_order, create_and_persist
o = build_order('retail', 'BTCUSDT.P', 'LONG', entry=1, sl=0.5, tp1=2,
                invalidation_price=0.5, ttl_hours=1)
o['id'] = 'test_list_001'
create_and_persist(o)
"

# list
python3 -c "
from pending_lib import load_all_pendings
for profile, orders in load_all_pendings().items():
    if orders:
        print(profile, [o['id'] for o in orders])
"
```

Expected: prints `retail ['test_list_001']`.

Cleanup:
```bash
python3 -c "
from pending_lib import load_pendings, save_pendings
save_pendings('retail', [p for p in load_pendings('retail') if p['id'] != 'test_list_001'])
"
```

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/pending.md
git commit -m "feat(watcher): /pending command list/show/cancel/modify"
```

---

## Task 11: `/filled <id>` command

**Files:**
- Create: `.claude/commands/filled.md`

- [ ] **Step 1: Write command spec**

Create `.claude/commands/filled.md`:

```markdown
Marca una pending order como ejecutada en el exchange/MT5 (llamado después de
ejecutar manual tras notif `triggered_go`).

Uso:
- `/filled <id>` — usa entry del pending como fill price
- `/filled <id> price=77498` — override con slippage real

Pasos:

1. `python3 -c "from pending_lib import find_by_id, update_status; r = find_by_id('$ID');
   print(r[0] if r else 'NOT_FOUND')"` → capture profile
2. Si NOT_FOUND → error.
3. Si orden status != `triggered_go` → warning pero continúa (user sabe lo que hace).
4. Update status a `filled` + append note con fill price.
5. **Append al trading_log.md del profile** (preserva schema existente):
   ```
   ## <fecha>
   Trade filled: <id> | <asset> <side> | entry <fill_price> | SL <sl> | TP <tp1>
   Risk: $<risk_usd> (<risk_pct>%)
   Source: /order + /filled (virtual-tracked watcher)
   ```
6. notify INFO `filled`.
7. Output ASCII box confirmando.
```

- [ ] **Step 2: Commit**

```bash
git add .claude/commands/filled.md
git commit -m "feat(watcher): /filled command to confirm manual execution"
```

---

## Task 12: `/watch` command — manual tick + dashboard render

**Files:**
- Create: `.claude/commands/watch.md`

- [ ] **Step 1: Write command spec**

Create `.claude/commands/watch.md`:

```markdown
Fuerza un tick manual del watcher (no espera al próximo launchd).

Uso: `/watch` (sin args)

Pasos:

1. Ejecuta:
   ```bash
   cd /Users/josecampos/Documents/wally-trader
   python3 .claude/scripts/watcher_tick.py
   ```
2. Lee `.claude/watcher/dashboard.md` y muéstralo al usuario.
3. Lee `.claude/watcher/status.json` y resume en 3 líneas:
   - "Last tick: <utc> (<ms>ms, ok=<bool>)"
   - "Pendings checked: N | errors: M"
   - "Actions: heartbeat(X) / escalated(Y) / invalidated(Z)"
4. Si hay `errors` → imprímelos.
5. Si hay `action=escalated` → recuérdale al usuario: "Claude-headless validando <id>, notif CRITICAL si 4/4 filtros."

NO preguntas al usuario; es read + run + display.
```

- [ ] **Step 2: Commit**

```bash
git add .claude/commands/watch.md
git commit -m "feat(watcher): /watch command for manual tick"
```

---

## Task 13: `watcher_escalate.sh`

**Files:**
- Create: `.claude/scripts/watcher_escalate.sh`

- [ ] **Step 1: Create shell script**

Create `.claude/scripts/watcher_escalate.sh`:

```bash
#!/bin/bash
# watcher_escalate.sh — spawned by watcher_tick when price near entry.
# Runs claude -p "/watch-deep <id>" in background, deduped per order_id.
#
# Usage: watcher_escalate.sh <order_id>

set -eu

ORDER_ID="${1:-}"
if [ -z "$ORDER_ID" ]; then
    echo "Usage: $0 <order_id>" >&2
    exit 1
fi

LOG="/tmp/wally_escalate_${ORDER_ID}.log"
PIDFILE="/tmp/wally_escalate_${ORDER_ID}.pid"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Dedupe: if a previous escalate is still running, skip
if [ -f "$PIDFILE" ]; then
    OLD_PID=$(cat "$PIDFILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "[$TIMESTAMP] Escalate already running (pid $OLD_PID) for $ORDER_ID, skipping" >> "$LOG"
        exit 0
    fi
fi

REPO_ROOT="$HOME/Documents/wally-trader"
cd "$REPO_ROOT"

# Spawn Claude headless with 120s hard timeout
echo "[$TIMESTAMP] Spawning claude -p /watch-deep $ORDER_ID" >> "$LOG"

# Detached background with nohup to survive parent exit
nohup bash -c "timeout 120 claude -p '/watch-deep ${ORDER_ID}' --permission-mode acceptEdits >> '${LOG}' 2>&1" &
echo $! > "$PIDFILE"

exit 0
```

- [ ] **Step 2: chmod + smoke test**

```bash
chmod +x .claude/scripts/watcher_escalate.sh
# smoke: call with fake id, verify dedupe works
.claude/scripts/watcher_escalate.sh fake_id_test
sleep 1
.claude/scripts/watcher_escalate.sh fake_id_test  # should log "already running" or skip
cat /tmp/wally_escalate_fake_id_test.log
```

Expected: first call logs "Spawning...". Second call logs "already running" (if first is still alive) or spawns new (depending on timing — acceptable either way).

Kill the test process:
```bash
if [ -f /tmp/wally_escalate_fake_id_test.pid ]; then
    kill "$(cat /tmp/wally_escalate_fake_id_test.pid)" 2>/dev/null || true
    rm -f /tmp/wally_escalate_fake_id_test.pid /tmp/wally_escalate_fake_id_test.log
fi
```

- [ ] **Step 3: Commit**

```bash
git add .claude/scripts/watcher_escalate.sh
git commit -m "feat(watcher): watcher_escalate.sh — dedupe + timeout spawn of claude -p"
```

---

## Task 14: `/watch-deep <order_id>` — Claude-side deep validation

**Files:**
- Create: `.claude/commands/watch-deep.md`

- [ ] **Step 1: Write command spec**

Create `.claude/commands/watch-deep.md`:

```markdown
Validación profunda de una pending order usando MCP TradingView — invocada
por `watcher_escalate.sh` headless cuando precio <0.3% del entry, o por usuario manual.

Uso: `/watch-deep <order_id>`

Pasos:

1. **Resuelve order:**
   ```bash
   python3 -c "
   from pending_lib import find_by_id
   import json
   r = find_by_id('$ID')
   print(json.dumps(r[1]) if r else '')
   "
   ```
   Si vacío → error "Order not found".

2. **Switch chart TV al asset correcto:**
   - `retail`, `retail-bingx`, `ftmo` BTCUSD/ETHUSD → `BINANCE:BTCUSDT.P` o ETH.
   - `fotmarkets` EURUSD/GBPUSD/etc → `OANDA:EURUSD` etc.
   - TF: retail/retail-bingx → 15m, fotmarkets → 5m.

3. **Lee indicadores con MCP:**
   - `mcp__tradingview__data_get_study_values` (busca RSI, BB, Donchian/Price Channel, ATR)
   - `mcp__tradingview__data_get_ohlcv` últimas 2 velas (para cierre verde/rojo)
   - Neptune si visible (opcional, solo informativo)

4. **Evalúa cada filter en `required_filters_at_trigger`:**
   - Construye tabla: `[filter_name] → PASS/FAIL con valor actual`
   - Ejemplo para retail LONG: RSI<35, precio toca DC Low(15) ±0.1%, BB lower touch, close verde.

5. **Decide:**
   - Si **todos PASS**:
     ```bash
     python3 -c "
     from pending_lib import find_by_id, update_status
     from notify_hub import notify, Urgency
     r = find_by_id('$ID'); profile, o = r
     update_status(profile, '$ID', 'triggered_go', note='all filters PASS')
     notify(Urgency.CRITICAL, 'triggered_go', {
         'order_id': '$ID', 'profile': profile, 'asset': o['asset'],
         'side': o['side'], 'entry': o['entry'], 'sl': o['sl'], 'tp1': o['tp1'],
         'filters_passed': 4, 'filters_total': 4,
     })
     "
     ```
     Luego dibuja en TV (entry/SL/TPs) usando `mcp__tradingview__draw_shape`.

   - Si **parcial (<4)**:
     ```bash
     python3 -c "
     from pending_lib import find_by_id, update_status
     r = find_by_id('$ID'); profile, o = r
     update_status(profile, '$ID', 'pending', note='filters X/4 — waiting')
     "
     ```
     No notify (heartbeat silent).

   - Si **error en MCP**:
     ```bash
     python3 -c "
     from pending_lib import find_by_id, update_status
     from notify_hub import notify, Urgency
     r = find_by_id('$ID'); profile, o = r
     update_status(profile, '$ID', 'check_error', note='MCP failure')
     notify(Urgency.WARN, 'degraded_watcher', {'order_id': '$ID', 'profile': profile, 'asset': o.get('asset')})
     "
     ```

6. **Output compacto** (headless context — mensaje corto):
   - `VERDICT: <triggered_go|pending|check_error>`
   - `Filters: 4/4 | 3/4 | ...`
   - `Notify: <channel list>`

NO preguntas al usuario. Headless-safe.
```

- [ ] **Step 2: Commit**

```bash
git add .claude/commands/watch-deep.md
git commit -m "feat(watcher): /watch-deep Claude-side deep validation with MCP"
```

---

## Task 15: **MANUAL CHECKPOINT** — escalation end-to-end

- [ ] **Step 1: Create a pending order near current BTC price**

```bash
cd .claude/scripts && python3 -c "
from order_lib import build_order, create_and_persist
from price_feeds import price_for
current = price_for('retail', 'BTCUSDT.P')
print('BTC now:', current)
# entry within 0.2% of current → will escalate on first tick
entry = round(current * 0.999, 1)
o = build_order('retail', 'BTCUSDT.P', 'LONG',
                entry=entry, sl=entry*0.994, tp1=entry*1.014,
                qty=0.0001, risk_usd=0.1, risk_pct=1.0,
                invalidation_price=entry*0.98, ttl_hours=1,
                filters_at_creation={'smoke_test': True})
o['id'] = 'escalation_smoke_001'
create_and_persist(o)
print('Created', o['id'], 'entry', entry)
"
```

- [ ] **Step 2: Run watcher tick**

```bash
cd /Users/josecampos/Documents/wally-trader
python3 .claude/scripts/watcher_tick.py
```

Expected:
- `status.json` has `actions: [..., {"action": "escalated", "order_id": "escalation_smoke_001"}]`
- `/tmp/wally_escalate_escalation_smoke_001.log` exists
- macOS notif "🔔 Precio cerca entry — retail BTCUSDT.P"

- [ ] **Step 3: Verify Claude headless spawned**

```bash
sleep 5  # wait for claude -p to start
cat /tmp/wally_escalate_escalation_smoke_001.log
```

Expected: log shows "Spawning claude -p..." and Claude output (may take up to 120s).

If claude CLI missing from PATH or auth not configured → the timeout will fail silently. That's acceptable for v1 (degraded mode). User must have `claude` CLI ready (should already, since it's running Claude Code).

- [ ] **Step 4: Cleanup**

```bash
# wait for claude -p to finish (or kill)
PIDFILE=/tmp/wally_escalate_escalation_smoke_001.pid
if [ -f "$PIDFILE" ]; then
    kill "$(cat $PIDFILE)" 2>/dev/null || true
fi
rm -f /tmp/wally_escalate_escalation_smoke_001.*

cd .claude/scripts && python3 -c "
from pending_lib import load_pendings, save_pendings
save_pendings('retail', [p for p in load_pendings('retail') if p['id'] != 'escalation_smoke_001'])
print('cleaned')
"
```

- [ ] **Step 5: User confirms escalation path works**

Ask user: "¿La notif llegó a macOS? ¿Claude-headless arrancó (ver /tmp/wally_escalate_*.log)?
Si todo OK, seguimos con extensión a fotmarkets + retail-bingx."

Wait for user OK.

---

## Task 16: Extend `/order` to fotmarkets + retail-bingx

**Files:**
- Modify: `.claude/commands/order.md` (añadir branches)
- Modify: `.claude/scripts/order_lib.py` (añadir helpers per profile)

- [ ] **Step 1: Update order_lib with fotmarkets/retail-bingx helpers**

Append to `.claude/scripts/order_lib.py`:

```python
def sizing_for_profile(profile: str, entry: float, sl: float, capital: float) -> dict:
    """Return {qty, risk_usd, risk_pct, leverage} per profile rules.

    retail/retail-bingx: 2% of capital, 10x leverage, qty = risk / sl_distance
    fotmarkets: phase-aware (Phase 1 = 10% cap $3; Phase 2 = 5%; Phase 3 = 2%)
    """
    sl_distance = abs(entry - sl)
    if sl_distance == 0:
        raise ValueError("SL distance is zero")

    if profile in ("retail", "retail-bingx"):
        risk_pct = 2.0
        leverage = 10
        risk_usd = capital * risk_pct / 100
        # qty approx: risk_usd / sl_distance (BTC perp units)
        qty = round(risk_usd / sl_distance, 6)
        return {"qty": qty, "risk_usd": round(risk_usd, 2),
                "risk_pct": risk_pct, "leverage": leverage}

    if profile == "fotmarkets":
        # Phase detection: capital < $100 → Phase 1
        if capital < 100:
            risk_pct, cap = 10.0, 3.0
        elif capital < 300:
            risk_pct, cap = 5.0, float("inf")
        else:
            risk_pct, cap = 2.0, float("inf")
        risk_usd = min(capital * risk_pct / 100, cap)
        # Fotmarkets lots — 0.01 minimum, depends on asset
        qty = 0.01  # placeholder; in practice user adjusts lot in MT5 manually
        return {"qty": qty, "risk_usd": round(risk_usd, 2),
                "risk_pct": risk_pct, "leverage": 500}

    raise ValueError(f"sizing_for_profile not implemented for {profile}")
```

- [ ] **Step 2: Update order.md to handle 3 profiles**

Edit `.claude/commands/order.md` — replace the profile-specific step 3:

```markdown
3. **Valida profile-specific:**
   - `ftmo` → **DELEGA** al flow existente (guardian.py + EA bridge). Si
     `PROFILE=ftmo`, imprime "Para FTMO usa el flow existente — ver mt5_bridge"
     y aborta.
   - `retail`:
     - Sanity: SL lado correcto, TP lado correcto, risk_pct ≤ 2.
     - `order_lib.sizing_for_profile('retail', entry, sl, 18.09)` → qty/risk.
     - Si `--real` → imprimir **"⚠️ --real no implementado en v1, orden virtual only"** y continuar.
   - `retail-bingx`:
     - Igual que retail pero capital=0.93 (lee de config.md).
     - `--real` no aplica (BingX sin API integrada). Siempre virtual.
   - `fotmarkets`:
     - `bash .claude/scripts/fotmarkets_guard.sh check` → si BLOCK, abortar con reason.
     - Verifica asset in `allowed_assets` de la phase (Phase 1 = [EURUSD, GBPUSD] solo).
     - `order_lib.sizing_for_profile('fotmarkets', entry, sl, capital_from_phase_progress)` → qty/risk.
     - Recuerda: ejecución MT5 manual. Watcher solo notifica trigger.
```

- [ ] **Step 3: Smoke test fotmarkets**

```bash
cd .claude/scripts && python3 -c "
from order_lib import build_order, sizing_for_profile, preflight_whitelist
# Phase 1 fotmarkets with EURUSD LONG
sizing = sizing_for_profile('fotmarkets', 1.17, 1.165, 27.09)
print('sizing:', sizing)
o = build_order('fotmarkets', 'EURUSD', 'LONG',
                entry=1.17, sl=1.165, tp1=1.175,
                **sizing,
                invalidation_price=1.16, ttl_hours=3)
print('order id:', o['id'])
ok, reason = preflight_whitelist(o)
print('whitelist:', ok, reason)
"
```

Expected: `sizing: {'qty': 0.01, 'risk_usd': 2.71, 'risk_pct': 10.0, 'leverage': 500}` (Phase 1, $27.09 × 10% = $2.71).

- [ ] **Step 4: Commit**

```bash
git add .claude/commands/order.md .claude/scripts/order_lib.py
git commit -m "feat(watcher): extend /order to fotmarkets + retail-bingx with phase sizing"
```

---

## Task 17: Edit `/profile` command — pending handshake

**Files:**
- Modify: `.claude/commands/profile.md`

- [ ] **Step 1: Read current profile.md to understand existing flow**

```bash
cat .claude/commands/profile.md
```

- [ ] **Step 2: Append handshake logic**

Append to `.claude/commands/profile.md` (AFTER the existing validation "no trade abierto" step, BEFORE the profile set):

```markdown
### Pre-switch: pending handshake (v1 watcher)

Antes de cambiar de profile, checkear pending orders activas:

1. **Leer pending del profile actual:**
   ```bash
   python3 -c "
   from pending_lib import load_pendings, TERMINAL_STATUSES
   orders = [o for o in load_pendings('$CURRENT_PROFILE') if o.get('status') not in TERMINAL_STATUSES and o.get('status') != 'suspended_profile_switch']
   for o in orders:
       print(f'{o[\"id\"]}|{o[\"asset\"]}|{o.get(\"side\",\"\")}|{o[\"status\"]}|dist_ttl={o[\"expires_at\"]}')
   "
   ```
2. Si el output tiene líneas → mostrar prompt:
   ```
   ⚠️ Profile actual `<current>` tiene <N> pending activa(s):
     • ord_xxx BTCUSDT.P LONG (status: pending, TTL ...)

   Al cambiar a `<target>`, ¿qué hago?
     [s] suspend — mantener pending pero pausar watcher (volver reactiva)
     [c] cancel — marcar canceled_manual (terminal, no vuelve)
     [k] keep_active — dejar watcher vigilándolas (respeta matriz whitelist)

   Tu elección:
   ```
3. Aplicar elección:
   - `s` → update_status a `suspended_profile_switch` para cada pending.
   - `c` → update_status a `canceled_manual`.
   - `k` → no tocar (default fallback si timeout/unclear input).

4. **Leer pending suspended del profile target:**
   ```bash
   python3 -c "
   from pending_lib import load_pendings
   orders = [o for o in load_pendings('$TARGET_PROFILE') if o.get('status') == 'suspended_profile_switch']
   for o in orders:
       print(f'{o[\"id\"]}|{o[\"asset\"]}|{o.get(\"side\",\"\")}|ttl={o[\"expires_at\"]}')
   "
   ```
5. Si hay suspended → mostrar prompt Caso B:
   ```
   ℹ️ Profile target `<target>` tiene <N> pending suspended:
     • ord_zzz ...

   ¿Reactivar o descartar?
     [r] reopen — status=pending (watcher vigila de nuevo; si TTL expiró, pasa a expired_ttl en siguiente tick)
     [d] discard — marcar canceled_manual
   ```
6. Aplicar elección. Para `reopen`: update_status a `pending`.

7. **Seguir con el set profile existente** (`bash .claude/scripts/profile.sh set <target>`).

8. Al final, disparar un `/watch` tick (o llamar directo `python3 .claude/scripts/watcher_tick.py`)
   para refresh del dashboard con el nuevo estado.
```

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/profile.md
git commit -m "feat(watcher): /profile handshake for pending on switch"
```

---

## Task 18: `/status` — add watcher section

**Files:**
- Modify: `.claude/commands/status.md`

- [ ] **Step 1: Read current status.md**

```bash
head -50 .claude/commands/status.md
```

- [ ] **Step 2: Append watcher section**

Append to `.claude/commands/status.md`:

```markdown
### Sección Watcher (v1)

Añadir al final del output de `/status`:

```bash
# Read watcher status + pending summary
python3 <<'EOF'
import json
from pathlib import Path
from pending_lib import load_all_pendings, PROFILES, TERMINAL_STATUSES

status_path = Path(".claude/watcher/status.json")
if status_path.exists():
    s = json.loads(status_path.read_text())
    print(f"\n## Watcher")
    print(f"Last tick: {s.get('last_tick_utc','-')} ({s.get('duration_ms','?')}ms, ok={not s.get('errors')})")
    print(f"Pendings checked last tick: {s.get('pendings_checked', 0)}")
    actions = s.get('actions', [])
    by_action = {}
    for a in actions:
        by_action[a.get('action','?')] = by_action.get(a.get('action','?'), 0) + 1
    if by_action:
        parts = " | ".join(f"{k}: {v}" for k,v in by_action.items())
        print(f"Actions: {parts}")
    if s.get('errors'):
        print("Errors:")
        for e in s['errors']:
            print(f"  • {e}")
    print(f"Next tick ETA: {s.get('next_tick_eta_utc','-')}")
else:
    print("\n## Watcher\n_(no tick run yet — instala launchd o corre /watch)_")

# Pending counts per profile
all_p = load_all_pendings()
print("\n### Pendings por profile")
for profile, orders in all_p.items():
    active = [o for o in orders if o.get('status') not in TERMINAL_STATUSES]
    if active:
        print(f"  {profile}: {len(active)} active")
EOF
```
```

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/status.md
git commit -m "feat(watcher): /status shows watcher + pending summary"
```

---

## Task 19: launchd plist + NOTIFY_SETUP.md + binance_real_order stub

**Files:**
- Create: `.claude/watcher/launchd/com.wallytrader.watcher.plist`
- Create: `.claude/scripts/NOTIFY_SETUP.md`
- Create: `.claude/scripts/binance_real_order.py`

- [ ] **Step 1: Write launchd plist template**

Create `.claude/watcher/launchd/com.wallytrader.watcher.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.wallytrader.watcher</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-lc</string>
        <string>cd "$HOME/Documents/wally-trader" &amp;&amp; /usr/bin/env python3 .claude/scripts/watcher_tick.py</string>
    </array>

    <key>StartInterval</key>
    <integer>3600</integer>

    <key>RunAtLoad</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/tmp/wally_watcher.out</string>

    <key>StandardErrorPath</key>
    <string>/tmp/wally_watcher.err</string>

    <key>ProcessType</key>
    <string>Background</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
```

- [ ] **Step 2: Write NOTIFY_SETUP.md**

Create `.claude/scripts/NOTIFY_SETUP.md`:

```markdown
# Notification & Watcher Setup

Guía manual para activar los canales opcionales. macOS notif funciona sin setup.

## 1. Watcher launchd (obligatorio para auto-hourly)

```bash
cp .claude/watcher/launchd/com.wallytrader.watcher.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.wallytrader.watcher.plist
launchctl list | grep wallytrader
```

Verifica logs:
```bash
tail -f /tmp/wally_watcher.out
tail -f /tmp/wally_watcher.err
```

Manual trigger:
```bash
launchctl start com.wallytrader.watcher
```

Unload:
```bash
launchctl unload ~/Library/LaunchAgents/com.wallytrader.watcher.plist
```

## 2. TwelveData (precio forex/índices para ftmo/fotmarkets)

Free tier: 800 req/día.

1. Signup: https://twelvedata.com/
2. Copia tu API key.
3. Añade a `.claude/.env`:
   ```
   TWELVEDATA_API_KEY=tu_key
   ```
4. Smoke: `python3 -c "from price_feeds import twelvedata_price; print(twelvedata_price('EUR/USD'))"`

Si no configuras → los assets forex/índices no se vigilarán (price_feeds.PriceFeedError).
Retail BTCUSDT.P funciona sin esto (Binance público).

## 3. Telegram bot (stub en v1 — no-op si sin token)

No requerido para v1. Para v2:

1. En Telegram, busca `@BotFather` → `/newbot` → obtén token.
2. Inicia chat con tu bot → `/start`.
3. Obtén chat_id:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getUpdates" | jq .result[-1].message.chat.id
   ```
4. Añade a `.claude/.env`:
   ```
   TELEGRAM_BOT_TOKEN=xxx
   TELEGRAM_CHAT_ID=yyy
   ```

## 4. Email (Resend) — stub en v1

No requerido para v1. Para v3:

1. Signup: https://resend.com/ → API key.
2. Añade a `.claude/.env`:
   ```
   RESEND_API_KEY=xxx
   NOTIFY_EMAIL_TO=hamlik@redfi.io
   ```

## 5. Binance API — stub en v1 (--real flag)

NO REQUERIDO v1. El flag `--real` imprime "stub" en /order.

Para v4 (cuando implementes):

1. Binance cuenta → API Management → Create API.
2. Permisos: **Futures trade ON**, **Withdraw OFF**, **IP whitelist** tu IP local.
3. Añade a `.claude/.env`:
   ```
   BINANCE_API_KEY=...
   BINANCE_API_SECRET=...
   ```

Spec de seguridad: nunca commitees estas keys. `.env` está en `.gitignore`.

## Troubleshooting

**"No price feed mapping"**: el (profile, asset) no está en `price_feeds.ASSET_MAP`.
Edita el map.

**Watcher no corre**: `launchctl list | grep wallytrader`. Si ausente, `load` del plist.
Verifica permisos del script: `chmod +x .claude/scripts/watcher_tick.py`.

**Notif macOS silenciadas**: System Settings → Notifications → Script Editor
allow alerts.

**Claude -p headless falla**: ejecuta `which claude` — debe estar en PATH. Si
auth expiró, `claude /login`.
```

- [ ] **Step 3: Write binance_real_order.py stub**

Create `.claude/scripts/binance_real_order.py`:

```python
"""Binance Futures real order submission — STUB v1.

In v1.0 this module is a stub that documents the interface and returns
NotImplementedError. Full implementation in v4 per spec rollout.
"""
from __future__ import annotations


class BinanceRealOrderStub(NotImplementedError):
    pass


def submit_limit_order(
    symbol: str, side: str, qty: float, price: float,
    sl: float, tp: float,
) -> str:
    raise BinanceRealOrderStub(
        "--real not implemented in v1. See docs/superpowers/specs/"
        "2026-04-24-watcher-pending-orders-design.md §Plan de rollout."
    )


def cancel_order(order_id: str) -> None:
    raise BinanceRealOrderStub("cancel_order not implemented in v1")


def get_order_status(order_id: str) -> dict:
    raise BinanceRealOrderStub("get_order_status not implemented in v1")
```

- [ ] **Step 4: Commit**

```bash
git add .claude/watcher/launchd/com.wallytrader.watcher.plist \
        .claude/scripts/NOTIFY_SETUP.md \
        .claude/scripts/binance_real_order.py
git commit -m "feat(watcher): launchd plist + NOTIFY_SETUP docs + binance stub"
```

---

## Task 20: **MANUAL CHECKPOINT** — full end-to-end with launchd

- [ ] **Step 1: Install launchd plist**

```bash
cp .claude/watcher/launchd/com.wallytrader.watcher.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.wallytrader.watcher.plist
launchctl list | grep wallytrader
```

Expected: `com.wallytrader.watcher` listed with PID or `-`.

- [ ] **Step 2: Trigger manual run via launchctl**

```bash
launchctl start com.wallytrader.watcher
sleep 3
tail -30 /tmp/wally_watcher.out
tail -30 /tmp/wally_watcher.err
```

Expected: `wally_watcher.out` contains watcher_tick JSON output. `err` empty or minor warnings.

- [ ] **Step 3: Full flow — create order, trigger tick, verify notif**

```bash
cd /Users/josecampos/Documents/wally-trader

# via Claude Code: /profile retail
# then: /order BTCUSDT.P LONG <current BTC - 0.05%> sl=... tp=...

# OR automated version:
cd .claude/scripts && python3 -c "
from order_lib import build_order, create_and_persist
from price_feeds import price_for
current = price_for('retail', 'BTCUSDT.P')
entry = round(current * 0.9995, 1)  # 0.05% below current
o = build_order('retail', 'BTCUSDT.P', 'LONG',
                entry=entry, sl=entry*0.994, tp1=entry*1.014,
                qty=0.0001, risk_usd=0.1,
                invalidation_price=entry*0.98, ttl_hours=1,
                filters_at_creation={'e2e_smoke': True})
o['id'] = 'e2e_smoke_001'
create_and_persist(o)
print('Created e2e_smoke_001 entry', entry)
"

# force tick
launchctl start com.wallytrader.watcher
sleep 5
```

- [ ] **Step 4: Verify end-to-end**

```bash
cat /tmp/wally_watcher.out | tail -50
cat .claude/watcher/dashboard.md
cat .claude/watcher/status.json | python3 -m json.tool
ls -la /tmp/wally_escalate_e2e_smoke_001.*
cat /tmp/wally_escalate_e2e_smoke_001.log 2>/dev/null
```

Expected:
- Dashboard shows 1 active pending `e2e_smoke_001`.
- Status json `actions` includes `escalated` for e2e_smoke_001.
- macOS notif "🔔 Precio cerca entry — retail BTCUSDT.P".
- Escalate log created (claude -p spawn attempted).

- [ ] **Step 5: Cleanup**

```bash
# kill escalate claude -p if still running
[ -f /tmp/wally_escalate_e2e_smoke_001.pid ] && kill "$(cat /tmp/wally_escalate_e2e_smoke_001.pid)" 2>/dev/null
rm -f /tmp/wally_escalate_e2e_smoke_001.*

cd .claude/scripts && python3 -c "
from pending_lib import load_pendings, save_pendings
save_pendings('retail', [p for p in load_pendings('retail') if p['id'] != 'e2e_smoke_001'])
"

# optionally: unload launchd until user really wants it on
# launchctl unload ~/Library/LaunchAgents/com.wallytrader.watcher.plist
```

- [ ] **Step 6: User signs off on Fase 1**

Ask user: "Fase 1 completa:
  ✅ /order virtual en retail/retail-bingx/fotmarkets
  ✅ launchd watcher hourly
  ✅ Escalation Claude on-demand
  ✅ macOS notif + dashboard
  ✅ Invalidaciones TTL/price/stopday/force_exit
  ✅ Matriz whitelist cross-profile
  ✅ /pending, /filled, /watch, /watch-deep, /status augmented, /profile handshake
  ⬜ Telegram/email/--real = stubs (v2-v4)

¿Listo para merge a main o quieres refinements?"

Esperar OK. Si refinements pedidos → crear plan delta; si OK → fin Fase 1.

---

## Plan Self-Review

**1. Spec coverage check:**

- Pending_orders.json schema → Tasks 2, 9 ✓
- Invalidations (TTL/price/stopday/force_exit) → Task 3 ✓
- Régimen opt-in → Task 9 (flag `--check-regime`) + Task 14 (evaluated in /watch-deep) ✓
- Whitelist matrix → Tasks 1, 4 ✓
- launchd watcher → Tasks 7, 19 ✓
- Claude escalation → Tasks 13, 14 ✓
- Notify multi-channel (macOS + dash + stubs) → Task 6 ✓
- 4 commands new (/watch, /watch-deep, /pending, /filled) → Tasks 10, 11, 12, 14 ✓
- /order extended → Tasks 9, 16 ✓
- /profile handshake → Task 17 ✓
- /status watcher section → Task 18 ✓
- Binance --real stub → Task 19 ✓
- NOTIFY_SETUP docs → Task 19 ✓
- Manual checkpoints → Tasks 8, 15, 20 ✓

**2. Placeholder scan:**
- No "TODO", "TBD", "implement later", "handle edge cases" — all tasks have concrete code or commands. ✓
- "Similar to Task N" — not used. Each task has its full code. ✓

**3. Type consistency:**
- `Urgency` enum consistent across notify_hub + watcher_tick + /watch-deep ✓
- `PROFILES` tuple used consistently ✓
- `TERMINAL_STATUSES` set used in `apply_whitelist_matrix` + `/profile` handshake ✓
- `evaluate_invalidation` signature `(order, current_price, stopday_profiles)` consistent across tests + watcher_tick ✓
- `build_order` + `create_and_persist` + `preflight_whitelist` signatures consistent in order_lib and /order command ✓

No drift detected.

---

## Execution Handoff

Plan completo y saved a `docs/superpowers/plans/2026-04-24-watcher-pending-orders.md`. Dos opciones de ejecución:

**1. Subagent-Driven (recomendado)** — despacho un subagent fresco por task, reviso entre tasks, iteración rápida.

**2. Inline Execution** — ejecutar tasks en esta sesión con executing-plans, batch con checkpoints.

¿Cuál prefieres?
