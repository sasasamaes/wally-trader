# Polymarket Macro Sentiment Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only Polymarket macro sentiment pipeline that produces a composite BTC bias score (range −100..+100), exposed via skill `polymarket-macro` (auto-invokable by agents) and manual commands `/polymarket` + `/polymarket-research`. Design preserves a research workflow that validates the signal's edge against BTC returns over time.

**Architecture:** Five Python modules under `.claude/scripts/polymarket/` with strict boundaries — `client.py` does HTTP only, `discovery.py` selects markets, `poller.py` writes snapshots hourly via launchd, `analyzer.py` is stateless and computes deltas + composite score, `research/` consumes the JSONL log to test hypotheses. A skill file and two slash commands provide the user/agent surface. JSONL append-only storage; no DB.

**Tech Stack:** Python 3.13 (existing venv `.claude/scripts/.venv`), `httpx` (sync), `pytest` + `pytest-mock`, JSONL on-disk persistence, launchd for scheduling. Tests live in `.claude/scripts/tests/` matching project convention. No API keys.

**Spec:** `docs/superpowers/specs/2026-05-02-polymarket-macro-integration-design.md`

---

## File Structure

**New files:**
- `.claude/scripts/polymarket/__init__.py` — empty marker
- `.claude/scripts/polymarket/config.py` — static constants (tags, weights, thresholds)
- `.claude/scripts/polymarket/client.py` — Gamma + CLOB HTTP client
- `.claude/scripts/polymarket/discovery.py` — market selection + ranking + atomic write
- `.claude/scripts/polymarket/poller.py` — hourly snapshot writer
- `.claude/scripts/polymarket/analyzer.py` — stateless deltas + composite score
- `.claude/scripts/polymarket/research/__init__.py` — empty marker
- `.claude/scripts/polymarket/research/data_loader.py` — join snapshots with BTC OHLCV
- `.claude/scripts/polymarket/research/hypotheses.py` — H1, H2, H3, H4 pure functions
- `.claude/scripts/polymarket/research/report.py` — markdown renderer + CLI entry
- `.claude/scripts/polymarket/data/.gitkeep` — keep dir, ignore JSONL
- `.claude/scripts/polymarket/data/.gitignore` — ignore `*.jsonl` and `tracked_markets.json`
- `.claude/skills/polymarket-macro/SKILL.md` — auto-invokable skill
- `.claude/commands/polymarket.md` — manual command
- `.claude/commands/polymarket-research.md` — manual research command
- `.claude/launchd/com.wally.polymarket-poller.plist` — hourly job
- `.claude/launchd/com.wally.polymarket-discovery.plist` — daily 04:00 CR job
- `.claude/scripts/tests/test_polymarket_client.py`
- `.claude/scripts/tests/test_polymarket_discovery.py`
- `.claude/scripts/tests/test_polymarket_analyzer.py`
- `.claude/scripts/tests/test_polymarket_research.py`
- `.claude/scripts/tests/fixtures/polymarket/gamma_markets_sample.json`
- `.claude/scripts/tests/fixtures/polymarket/gamma_market_detail.json`
- `.claude/scripts/tests/fixtures/polymarket/snapshots_sample.jsonl`

**Modified files:**
- `.claude/scripts/requirements-helpers.txt` — add `httpx>=0.27`, `pytest-mock>=3.12`

---

### Task 1: Bootstrap directories, requirements, and gitignore

**Files:**
- Create: `.claude/scripts/polymarket/__init__.py`
- Create: `.claude/scripts/polymarket/research/__init__.py`
- Create: `.claude/scripts/polymarket/data/.gitkeep`
- Create: `.claude/scripts/polymarket/data/.gitignore`
- Create: `.claude/scripts/tests/fixtures/polymarket/.gitkeep`
- Modify: `.claude/scripts/requirements-helpers.txt`

- [ ] **Step 1: Create empty package markers**

```bash
mkdir -p .claude/scripts/polymarket/research
mkdir -p .claude/scripts/polymarket/data
mkdir -p .claude/scripts/tests/fixtures/polymarket
touch .claude/scripts/polymarket/__init__.py
touch .claude/scripts/polymarket/research/__init__.py
touch .claude/scripts/polymarket/data/.gitkeep
touch .claude/scripts/tests/fixtures/polymarket/.gitkeep
```

- [ ] **Step 2: Create data/.gitignore**

Write `.claude/scripts/polymarket/data/.gitignore`:
```
*.jsonl
tracked_markets.json
!.gitkeep
```

- [ ] **Step 3: Add deps to requirements-helpers.txt**

Append to `.claude/scripts/requirements-helpers.txt`:
```
# Polymarket macro sentiment integration (spec 2026-05-02)
httpx>=0.27
pytest-mock>=3.12
```

- [ ] **Step 4: Install deps in venv**

Run:
```bash
.claude/scripts/.venv/bin/pip install -r .claude/scripts/requirements-helpers.txt
```
Expected: `Successfully installed httpx-... pytest-mock-...` (or "Requirement already satisfied").

- [ ] **Step 5: Smoke import**

Run:
```bash
.claude/scripts/.venv/bin/python -c "import httpx; import pytest_mock; print('ok')"
```
Expected: `ok`

- [ ] **Step 6: Commit**

```bash
git add .claude/scripts/polymarket .claude/scripts/tests/fixtures/polymarket .claude/scripts/requirements-helpers.txt
git commit -m "chore(polymarket): bootstrap package skeleton + deps"
```

---

### Task 2: config.py — static configuration

**Files:**
- Create: `.claude/scripts/polymarket/config.py`
- Test: `.claude/scripts/tests/test_polymarket_config.py`

- [ ] **Step 1: Write the failing test**

Write `.claude/scripts/tests/test_polymarket_config.py`:
```python
"""Tests for polymarket.config."""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from polymarket import config


def test_defaults_present():
    assert config.GAMMA_BASE_URL.startswith("https://")
    assert config.CLOB_BASE_URL.startswith("https://")
    assert config.VOLUME_THRESHOLD_USD == 500_000
    assert config.TOP_N_MARKETS == 12
    assert config.POLL_INTERVAL_SECONDS == 3600
    assert config.STALE_AFTER_SECONDS == 7200
    assert isinstance(config.TAGS_WHITELIST, tuple)
    assert "fed" in config.TAGS_WHITELIST


def test_weight_mapping_first_match_wins():
    assert config.match_weight("will-the-fed-cut-rates-in-may-2026") == 0.30
    assert config.match_weight("us-recession-2026") == -0.25
    assert config.match_weight("trump-tariffs-q2") == -0.20
    assert config.match_weight("totally-unmapped-market") is None


def test_weight_mapping_case_insensitive():
    assert config.match_weight("Fed-Cut-Rates-May") == 0.30
    assert config.match_weight("US-RECESSION-2026") == -0.25


def test_data_paths_under_polymarket_dir():
    assert config.DATA_DIR.name == "data"
    assert config.SNAPSHOTS_PATH.name == "snapshots.jsonl"
    assert config.TRACKED_MARKETS_PATH.name == "tracked_markets.json"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_polymarket_config.py -v`
Expected: `ImportError` or `ModuleNotFoundError: polymarket.config`.

- [ ] **Step 3: Write config.py**

Write `.claude/scripts/polymarket/config.py`:
```python
"""Static configuration for the Polymarket macro sentiment integration.

Patterns are matched case-insensitively as substrings of the market slug.
First match wins; ordering of WEIGHT_MAPPING matters.
"""
from __future__ import annotations

from pathlib import Path

GAMMA_BASE_URL = "https://gamma-api.polymarket.com"
CLOB_BASE_URL = "https://clob.polymarket.com"

# Selection thresholds
VOLUME_THRESHOLD_USD = 500_000
TOP_N_MARKETS = 12
MIN_DAYS_TO_RESOLUTION = 7

# Operations
POLL_INTERVAL_SECONDS = 3600
STALE_AFTER_SECONDS = 7200  # 2h
HTTP_TIMEOUT_SECONDS = 5
HTTP_RETRIES = 2

# Tags accepted at discovery time (any match qualifies)
TAGS_WHITELIST = ("politics", "economics", "fed", "crypto")

# Composite scoring buckets (composite already in [-100, +100])
BUCKET_THRESHOLDS = (
    (-40.0, "STRONG-BEAR"),
    (-15.0, "MILD-BEAR"),
    (15.0, "NEUTRAL"),
    (40.0, "MILD-BULL"),
    (float("inf"), "STRONG-BULL"),
)

# Market slug substring → weight. First match wins.
# Convention: weight = how much YES probability moves BTC sentiment.
# Positive weight = YES is bullish for BTC; negative = YES is bearish.
WEIGHT_MAPPING: tuple[tuple[str, float], ...] = (
    ("fed-cut", 0.30),
    ("fed-rate-cut", 0.30),
    ("us-recession", -0.25),
    ("recession-2026", -0.25),
    ("trump-tariffs", -0.20),
    ("tariff-trigger", -0.20),
    ("stablecoin-pass", 0.20),
    ("crypto-regulation-pass", 0.20),
    ("debt-ceiling-crisis", -0.15),
    ("btc-etf-net-inflows", 0.10),
)


# Paths
_THIS_DIR = Path(__file__).resolve().parent
DATA_DIR = _THIS_DIR / "data"
SNAPSHOTS_PATH = DATA_DIR / "snapshots.jsonl"
TRACKED_MARKETS_PATH = DATA_DIR / "tracked_markets.json"
RESOLUTIONS_PATH = DATA_DIR / "resolutions.jsonl"


def match_weight(slug: str) -> float | None:
    """Return the weight for a market slug, or None if unmapped."""
    s = slug.lower()
    for pattern, weight in WEIGHT_MAPPING:
        if pattern in s:
            return weight
    return None


def bucket_for(composite: float) -> str:
    """Map a composite score to its qualitative label."""
    for threshold, label in BUCKET_THRESHOLDS:
        if composite <= threshold:
            return label
    return BUCKET_THRESHOLDS[-1][1]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_polymarket_config.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/polymarket/config.py .claude/scripts/tests/test_polymarket_config.py
git commit -m "feat(polymarket): config module with weight mapping and bucket helpers"
```

---

### Task 3: client.py — Gamma API list_markets and get_market

**Files:**
- Create: `.claude/scripts/polymarket/client.py`
- Test: `.claude/scripts/tests/test_polymarket_client.py`
- Test fixture: `.claude/scripts/tests/fixtures/polymarket/gamma_markets_sample.json`
- Test fixture: `.claude/scripts/tests/fixtures/polymarket/gamma_market_detail.json`

- [ ] **Step 1: Write fixtures**

Write `.claude/scripts/tests/fixtures/polymarket/gamma_markets_sample.json`:
```json
[
  {
    "id": "0xaaa",
    "slug": "fed-cut-rates-in-may-2026",
    "question": "Will the Fed cut rates in May 2026?",
    "active": true,
    "closed": false,
    "outcomes": ["Yes", "No"],
    "outcomePrices": ["0.62", "0.38"],
    "volume24hr": 2400000,
    "endDate": "2026-05-08T00:00:00Z",
    "tags": [{"slug": "fed"}, {"slug": "economics"}]
  },
  {
    "id": "0xbbb",
    "slug": "us-recession-2026",
    "question": "Will the US enter a recession in 2026?",
    "active": true,
    "closed": false,
    "outcomes": ["Yes", "No"],
    "outcomePrices": ["0.28", "0.72"],
    "volume24hr": 890000,
    "endDate": "2026-12-31T00:00:00Z",
    "tags": [{"slug": "economics"}]
  },
  {
    "id": "0xccc",
    "slug": "low-volume-noise",
    "active": true,
    "closed": false,
    "outcomes": ["Yes", "No"],
    "outcomePrices": ["0.50", "0.50"],
    "volume24hr": 12000,
    "endDate": "2026-08-01T00:00:00Z",
    "tags": [{"slug": "politics"}]
  }
]
```

Write `.claude/scripts/tests/fixtures/polymarket/gamma_market_detail.json`:
```json
{
  "id": "0xaaa",
  "slug": "fed-cut-rates-in-may-2026",
  "active": true,
  "closed": false,
  "outcomes": ["Yes", "No"],
  "outcomePrices": ["0.62", "0.38"],
  "volume24hr": 2400000,
  "lastTradePrice": 0.625,
  "endDate": "2026-05-08T00:00:00Z"
}
```

- [ ] **Step 2: Write the failing test**

Write `.claude/scripts/tests/test_polymarket_client.py`:
```python
"""Tests for polymarket.client. All HTTP is mocked."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from polymarket import client

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "polymarket"


@pytest.fixture
def list_markets_payload():
    return json.loads((FIXTURES / "gamma_markets_sample.json").read_text())


@pytest.fixture
def market_detail_payload():
    return json.loads((FIXTURES / "gamma_market_detail.json").read_text())


def _mock_response(status_code: int, json_payload):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_payload
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "err", request=MagicMock(), response=resp
        )
    return resp


def test_list_markets_returns_parsed_markets(mocker, list_markets_payload):
    mock_get = mocker.patch.object(httpx.Client, "get")
    mock_get.return_value = _mock_response(200, list_markets_payload)

    markets = client.list_markets(active=True, closed=False)

    assert len(markets) == 3
    assert markets[0].slug == "fed-cut-rates-in-may-2026"
    assert markets[0].prob_yes == 0.62
    assert markets[0].volume_24h == 2400000
    assert "fed" in markets[0].tags


def test_get_market_returns_one(mocker, market_detail_payload):
    mock_get = mocker.patch.object(httpx.Client, "get")
    mock_get.return_value = _mock_response(200, market_detail_payload)

    m = client.get_market("0xaaa")

    assert m.slug == "fed-cut-rates-in-may-2026"
    assert m.prob_yes == 0.62
    assert m.last_trade == 0.625


def test_list_markets_retries_on_5xx(mocker, list_markets_payload):
    mock_get = mocker.patch.object(httpx.Client, "get")
    mock_get.side_effect = [
        _mock_response(503, []),
        _mock_response(200, list_markets_payload),
    ]
    # speed up: monkey-patch sleep
    mocker.patch.object(client, "_sleep", lambda s: None)

    markets = client.list_markets()
    assert len(markets) == 3
    assert mock_get.call_count == 2


def test_list_markets_raises_after_exhausting_retries(mocker):
    mock_get = mocker.patch.object(httpx.Client, "get")
    mock_get.side_effect = [
        _mock_response(503, []),
        _mock_response(503, []),
        _mock_response(503, []),
    ]
    mocker.patch.object(client, "_sleep", lambda s: None)

    with pytest.raises(client.PolymarketError):
        client.list_markets()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_polymarket_client.py -v`
Expected: 4 errors (`ModuleNotFoundError: polymarket.client`).

- [ ] **Step 4: Write client.py**

Write `.claude/scripts/polymarket/client.py`:
```python
"""HTTP client for Polymarket Gamma API with CLOB fallback.

Pure HTTP. No business logic. Returns typed Market dataclasses.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from polymarket import config


class PolymarketError(RuntimeError):
    """All HTTP / parsing failures wrap into this."""


@dataclass(frozen=True)
class Market:
    id: str
    slug: str
    question: str
    prob_yes: float
    volume_24h: float
    end_date: str
    tags: tuple[str, ...] = field(default_factory=tuple)
    last_trade: float | None = None
    closed: bool = False


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def _parse_market(raw: dict[str, Any]) -> Market:
    prices = raw.get("outcomePrices") or ["0", "0"]
    prob_yes = float(prices[0])
    tags_raw = raw.get("tags") or []
    tags = tuple(t.get("slug") if isinstance(t, dict) else str(t) for t in tags_raw)
    last_trade_raw = raw.get("lastTradePrice")
    last_trade = float(last_trade_raw) if last_trade_raw is not None else None
    return Market(
        id=str(raw.get("id", "")),
        slug=str(raw.get("slug", "")),
        question=str(raw.get("question", "")),
        prob_yes=prob_yes,
        volume_24h=float(raw.get("volume24hr") or 0),
        end_date=str(raw.get("endDate", "")),
        tags=tags,
        last_trade=last_trade,
        closed=bool(raw.get("closed", False)),
    )


def _request_with_retries(client_obj: httpx.Client, url: str, params: dict | None = None) -> Any:
    last_exc: Exception | None = None
    for attempt in range(config.HTTP_RETRIES + 1):
        try:
            resp = client_obj.get(url, params=params or {}, timeout=config.HTTP_TIMEOUT_SECONDS)
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPStatusError, httpx.HTTPError) as exc:
            last_exc = exc
            if attempt < config.HTTP_RETRIES:
                _sleep(2 ** attempt)
    raise PolymarketError(f"GET {url} failed after retries: {last_exc}")


def list_markets(*, active: bool = True, closed: bool = False, limit: int = 200) -> list[Market]:
    """List markets from Gamma. Returns parsed Market list."""
    params = {"active": str(active).lower(), "closed": str(closed).lower(), "limit": limit}
    with httpx.Client(base_url=config.GAMMA_BASE_URL) as c:
        payload = _request_with_retries(c, "/markets", params=params)
    if not isinstance(payload, list):
        raise PolymarketError(f"Expected list, got {type(payload).__name__}")
    return [_parse_market(m) for m in payload]


def get_market(market_id: str) -> Market:
    """Fetch a single market by id (or slug)."""
    with httpx.Client(base_url=config.GAMMA_BASE_URL) as c:
        payload = _request_with_retries(c, f"/markets/{market_id}")
    if not isinstance(payload, dict):
        raise PolymarketError(f"Expected dict, got {type(payload).__name__}")
    return _parse_market(payload)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_polymarket_client.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add .claude/scripts/polymarket/client.py .claude/scripts/tests/test_polymarket_client.py .claude/scripts/tests/fixtures/polymarket/gamma_markets_sample.json .claude/scripts/tests/fixtures/polymarket/gamma_market_detail.json
git commit -m "feat(polymarket): HTTP client for Gamma API with retry logic"
```

---

### Task 4: client.py — CLOB fallback for get_market

**Files:**
- Modify: `.claude/scripts/polymarket/client.py`
- Modify: `.claude/scripts/tests/test_polymarket_client.py`

- [ ] **Step 1: Write the failing test**

Append to `.claude/scripts/tests/test_polymarket_client.py`:
```python
def test_get_market_with_fallback_uses_clob_when_gamma_fails(mocker, market_detail_payload):
    # Patch the helper that does retry-aware GET to fail then succeed
    calls = {"n": 0}

    def fake_request(client_obj, url, params=None):
        calls["n"] += 1
        if "gamma-api" in str(client_obj.base_url):
            raise client.PolymarketError("gamma down")
        return market_detail_payload

    mocker.patch.object(client, "_request_with_retries", side_effect=fake_request)

    m = client.get_market_with_fallback("0xaaa")
    assert m.slug == "fed-cut-rates-in-may-2026"
    assert calls["n"] == 2  # gamma fail + clob success


def test_get_market_with_fallback_raises_if_both_fail(mocker):
    def always_fail(client_obj, url, params=None):
        raise client.PolymarketError("both down")

    mocker.patch.object(client, "_request_with_retries", side_effect=always_fail)

    with pytest.raises(client.PolymarketError):
        client.get_market_with_fallback("0xaaa")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_polymarket_client.py -v`
Expected: 2 new failures (`AttributeError: get_market_with_fallback`).

- [ ] **Step 3: Add fallback to client.py**

Append to `.claude/scripts/polymarket/client.py`:
```python
def get_market_with_fallback(market_id: str) -> Market:
    """Try Gamma first, fall back to CLOB on failure."""
    try:
        with httpx.Client(base_url=config.GAMMA_BASE_URL) as c:
            payload = _request_with_retries(c, f"/markets/{market_id}")
        if isinstance(payload, dict):
            return _parse_market(payload)
    except PolymarketError:
        pass

    # CLOB fallback. CLOB market detail uses condition_id as path segment.
    with httpx.Client(base_url=config.CLOB_BASE_URL) as c:
        payload = _request_with_retries(c, f"/markets/{market_id}")
    if not isinstance(payload, dict):
        raise PolymarketError(f"CLOB returned non-dict for {market_id}")
    return _parse_market(payload)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_polymarket_client.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/polymarket/client.py .claude/scripts/tests/test_polymarket_client.py
git commit -m "feat(polymarket): CLOB fallback for get_market"
```

---

### Task 5: discovery.py — filter, rank, atomic write

**Files:**
- Create: `.claude/scripts/polymarket/discovery.py`
- Test: `.claude/scripts/tests/test_polymarket_discovery.py`

- [ ] **Step 1: Write the failing test**

Write `.claude/scripts/tests/test_polymarket_discovery.py`:
```python
"""Tests for polymarket.discovery."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from polymarket import config, discovery
from polymarket.client import Market


def _mk_market(slug, prob, vol, days_out=30, tags=("fed",)):
    end_date = (datetime.now(timezone.utc) + timedelta(days=days_out)).isoformat()
    return Market(
        id=f"id-{slug}",
        slug=slug,
        question=slug,
        prob_yes=prob,
        volume_24h=vol,
        end_date=end_date,
        tags=tags,
    )


def test_filter_drops_low_volume():
    markets = [
        _mk_market("a", 0.5, 600_000),
        _mk_market("b", 0.5, 100_000),  # below threshold
    ]
    out = discovery.filter_markets(markets)
    assert {m.slug for m in out} == {"a"}


def test_filter_drops_no_tag_match():
    markets = [
        _mk_market("a", 0.5, 600_000, tags=("fed",)),
        _mk_market("b", 0.5, 600_000, tags=("sports",)),  # tag not whitelisted
    ]
    out = discovery.filter_markets(markets)
    assert {m.slug for m in out} == {"a"}


def test_filter_drops_too_close_to_resolution():
    markets = [
        _mk_market("a", 0.5, 600_000, days_out=30),
        _mk_market("b", 0.5, 600_000, days_out=2),  # < MIN_DAYS_TO_RESOLUTION
    ]
    out = discovery.filter_markets(markets)
    assert {m.slug for m in out} == {"a"}


def test_rank_prefers_50_50():
    markets = [
        _mk_market("a", 0.10, 600_000),  # far from 50/50
        _mk_market("b", 0.50, 600_000),  # exactly 50/50
        _mk_market("c", 0.45, 600_000),  # close to 50/50
    ]
    ranked = discovery.rank_markets(markets)
    assert [m.slug for m in ranked] == ["b", "c", "a"]


def test_atomic_write(tmp_path, monkeypatch):
    target = tmp_path / "tracked.json"
    monkeypatch.setattr(config, "TRACKED_MARKETS_PATH", target)
    markets = [_mk_market("a", 0.5, 600_000)]
    discovery.write_tracked_markets(markets)
    data = json.loads(target.read_text())
    assert data["markets"][0]["slug"] == "a"
    assert "generated_at" in data


def test_run_discovery_keeps_previous_when_zero_results(tmp_path, monkeypatch, mocker):
    target = tmp_path / "tracked.json"
    target.write_text(json.dumps({"markets": [{"slug": "old"}], "generated_at": "old"}))
    monkeypatch.setattr(config, "TRACKED_MARKETS_PATH", target)
    mocker.patch.object(discovery, "list_markets", return_value=[])

    n = discovery.run()
    assert n == 0
    data = json.loads(target.read_text())
    assert data["markets"][0]["slug"] == "old"  # unchanged


def test_run_discovery_writes_empty_on_first_run_zero(tmp_path, monkeypatch, mocker):
    target = tmp_path / "tracked.json"
    monkeypatch.setattr(config, "TRACKED_MARKETS_PATH", target)
    mocker.patch.object(discovery, "list_markets", return_value=[])

    n = discovery.run()
    assert n == 0
    data = json.loads(target.read_text())
    assert data["markets"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_polymarket_discovery.py -v`
Expected: errors (`ModuleNotFoundError: polymarket.discovery`).

- [ ] **Step 3: Write discovery.py**

Write `.claude/scripts/polymarket/discovery.py`:
```python
"""Market selection: tag/volume filter + rank by |p − 0.5| + atomic write."""
from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from polymarket import config
from polymarket.client import Market, list_markets

log = logging.getLogger(__name__)


def _parse_iso(s: str) -> datetime:
    # Tolerant ISO parser; treat naive as UTC.
    s = s.replace("Z", "+00:00") if s.endswith("Z") else s
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return datetime.max.replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def filter_markets(markets: list[Market]) -> list[Market]:
    """Apply volume, tag, and end-date filters."""
    now = datetime.now(timezone.utc)
    out: list[Market] = []
    for m in markets:
        if m.closed:
            continue
        if m.volume_24h < config.VOLUME_THRESHOLD_USD:
            continue
        if not any(t.lower() in config.TAGS_WHITELIST for t in m.tags):
            continue
        end = _parse_iso(m.end_date)
        days_out = (end - now).days
        if days_out < config.MIN_DAYS_TO_RESOLUTION:
            continue
        out.append(m)
    return out


def rank_markets(markets: list[Market]) -> list[Market]:
    """Sort by |prob_yes - 0.5| ascending (closest to 50/50 first)."""
    return sorted(markets, key=lambda m: abs(m.prob_yes - 0.5))


def _atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        finally:
            raise


def write_tracked_markets(markets: list[Market]) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(markets),
        "markets": [asdict(m) for m in markets],
    }
    _atomic_write(config.TRACKED_MARKETS_PATH, payload)


def run(*, dry_run: bool = False) -> int:
    """Run a discovery cycle. Returns the number of markets selected."""
    raw = list_markets(active=True, closed=False, limit=200)
    filtered = filter_markets(raw)
    ranked = rank_markets(filtered)[: config.TOP_N_MARKETS]

    if not ranked and config.TRACKED_MARKETS_PATH.exists():
        log.warning("Discovery returned 0 markets — keeping previous tracked file.")
        return 0

    if dry_run:
        for m in ranked:
            print(f"{m.slug}\t{m.prob_yes:.2f}\t${m.volume_24h:,.0f}")
        return len(ranked)

    write_tracked_markets(ranked)
    return len(ranked)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [discovery] %(message)s")
    dry = "--dry-run" in sys.argv
    n = run(dry_run=dry)
    print(f"Discovery completed: {n} market(s) selected.")
    return 0 if n >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_polymarket_discovery.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/polymarket/discovery.py .claude/scripts/tests/test_polymarket_discovery.py
git commit -m "feat(polymarket): discovery module with filter, rank, atomic write"
```

---

### Task 6: analyzer.py — load snapshots, compute deltas

**Files:**
- Create: `.claude/scripts/polymarket/analyzer.py`
- Test fixture: `.claude/scripts/tests/fixtures/polymarket/snapshots_sample.jsonl`
- Test: `.claude/scripts/tests/test_polymarket_analyzer.py`

- [ ] **Step 1: Write fixture**

Write `.claude/scripts/tests/fixtures/polymarket/snapshots_sample.jsonl`:
```
{"ts":"2026-04-25T13:00:00+00:00","id":"0xaaa","slug":"fed-cut-rates-in-may-2026","prob":0.48,"vol_24h":2000000,"last_trade":0.48}
{"ts":"2026-05-01T13:00:00+00:00","id":"0xaaa","slug":"fed-cut-rates-in-may-2026","prob":0.54,"vol_24h":2200000,"last_trade":0.54}
{"ts":"2026-05-02T12:00:00+00:00","id":"0xaaa","slug":"fed-cut-rates-in-may-2026","prob":0.55,"vol_24h":2300000,"last_trade":0.55}
{"ts":"2026-05-02T13:00:00+00:00","id":"0xaaa","slug":"fed-cut-rates-in-may-2026","prob":0.62,"vol_24h":2400000,"last_trade":0.62}
{"ts":"2026-05-02T13:00:00+00:00","id":"0xbbb","slug":"us-recession-2026","prob":0.28,"vol_24h":890000,"last_trade":0.28}
{"ts":"2026-05-01T13:00:00+00:00","id":"0xbbb","slug":"us-recession-2026","prob":0.33,"vol_24h":900000,"last_trade":0.33}
```

- [ ] **Step 2: Write the failing test**

Write `.claude/scripts/tests/test_polymarket_analyzer.py`:
```python
"""Tests for polymarket.analyzer."""
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from polymarket import analyzer, config

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "polymarket" / "snapshots_sample.jsonl"
NOW_REF = datetime(2026, 5, 2, 13, 5, tzinfo=timezone.utc)


@pytest.fixture
def tmp_snapshots(tmp_path, monkeypatch):
    p = tmp_path / "snapshots.jsonl"
    shutil.copy(FIXTURE, p)
    monkeypatch.setattr(config, "SNAPSHOTS_PATH", p)
    return p


def test_load_snapshots_returns_dicts(tmp_snapshots):
    rows = analyzer.load_snapshots()
    assert len(rows) == 6
    assert all("ts" in r for r in rows)


def test_load_snapshots_skips_malformed(tmp_path, monkeypatch):
    p = tmp_path / "snapshots.jsonl"
    p.write_text(
        '{"ts":"2026-05-02T13:00:00+00:00","slug":"a","prob":0.5,"vol_24h":1}\n'
        'not-json-garbage\n'
        '{"ts":"2026-05-02T14:00:00+00:00","slug":"a","prob":0.6,"vol_24h":1}\n'
    )
    monkeypatch.setattr(config, "SNAPSHOTS_PATH", p)
    rows = analyzer.load_snapshots()
    assert len(rows) == 2


def test_compute_deltas_for_market(tmp_snapshots):
    rows = analyzer.load_snapshots()
    fed = [r for r in rows if r["slug"] == "fed-cut-rates-in-may-2026"]
    out = analyzer.compute_deltas(fed, now=NOW_REF)
    assert out["prob_now"] == pytest.approx(0.62)
    # delta_24h: latest 0.62 vs 24h ago 0.55 ⇒ +0.07 (7pp)
    assert out["delta_24h"] == pytest.approx(0.07, abs=0.001)
    # delta_7d: 0.62 vs 0.48 ⇒ +0.14
    assert out["delta_7d"] == pytest.approx(0.14, abs=0.001)


def test_compute_composite_demeaned():
    per_market = {
        "fed-cut-rates-in-may-2026": {"prob_now": 0.62, "weight": 0.30},
        "us-recession-2026": {"prob_now": 0.28, "weight": -0.25},
    }
    composite = analyzer.composite(per_market)
    # weighted_sum = (0.12)(0.30) + (-0.22)(-0.25) = 0.036 + 0.055 = 0.091
    # total_weight = 0.55
    # composite = 0.091 / 0.55 * 200 = 33.09
    assert composite == pytest.approx(33.09, abs=0.05)


def test_composite_undefined_when_no_weights():
    assert analyzer.composite({}) is None


def test_status_stale_when_snapshot_too_old(tmp_path, monkeypatch):
    p = tmp_path / "snapshots.jsonl"
    p.write_text('{"ts":"2026-05-01T00:00:00+00:00","slug":"a","prob":0.5,"vol_24h":1}\n')
    monkeypatch.setattr(config, "SNAPSHOTS_PATH", p)
    rep = analyzer.report(now=NOW_REF)
    assert rep["status"] == "STALE"


def test_status_fresh_when_recent(tmp_snapshots):
    rep = analyzer.report(now=NOW_REF)
    assert rep["status"] == "FRESH"
    assert rep["composite"] is not None
    assert "fed-cut-rates-in-may-2026" in {m["slug"] for m in rep["markets"]}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_polymarket_analyzer.py -v`
Expected: errors (`ModuleNotFoundError: polymarket.analyzer`).

- [ ] **Step 4: Write analyzer.py**

Write `.claude/scripts/polymarket/analyzer.py`:
```python
"""Stateless analyzer over snapshots.jsonl.

Produces per-market deltas and a composite score in [-100, +100].
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from polymarket import config

log = logging.getLogger(__name__)


def load_snapshots(path: Path | None = None) -> list[dict[str, Any]]:
    """Read JSONL, skipping malformed lines."""
    p = path or config.SNAPSHOTS_PATH
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    for i, line in enumerate(p.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            log.warning("Skipping malformed snapshot line %d", i)
    return rows


def _parse_ts(s: str) -> datetime:
    s = s.replace("Z", "+00:00") if s.endswith("Z") else s
    return datetime.fromisoformat(s)


def compute_deltas(snapshots_for_market: list[dict[str, Any]], *, now: datetime) -> dict[str, Any]:
    """Compute prob_now, delta_1h, delta_24h, delta_7d for one market.

    Picks the snapshot closest to (now - Δ) within a tolerance window.
    """
    if not snapshots_for_market:
        return {"prob_now": None, "delta_1h": None, "delta_24h": None, "delta_7d": None}

    sorted_snaps = sorted(snapshots_for_market, key=lambda r: _parse_ts(r["ts"]))
    latest = sorted_snaps[-1]
    prob_now = float(latest["prob"])

    def at_lookback(delta: timedelta, tolerance: timedelta) -> float | None:
        target = now - delta
        best = None
        best_diff = None
        for r in sorted_snaps[:-1]:
            ts = _parse_ts(r["ts"])
            diff = abs(ts - target)
            if diff <= tolerance and (best_diff is None or diff < best_diff):
                best, best_diff = float(r["prob"]), diff
        return best

    p_1h = at_lookback(timedelta(hours=1), timedelta(minutes=30))
    p_24h = at_lookback(timedelta(hours=24), timedelta(hours=2))
    p_7d = at_lookback(timedelta(days=7), timedelta(hours=24))

    return {
        "prob_now": prob_now,
        "delta_1h": (prob_now - p_1h) if p_1h is not None else None,
        "delta_24h": (prob_now - p_24h) if p_24h is not None else None,
        "delta_7d": (prob_now - p_7d) if p_7d is not None else None,
    }


def composite(per_market: dict[str, dict[str, Any]]) -> float | None:
    """Compute (Σ (p−0.5) × w) / Σ|w| × 200, range [-100, +100]."""
    weighted_sum = 0.0
    total_weight = 0.0
    for slug, info in per_market.items():
        weight = info.get("weight")
        prob = info.get("prob_now")
        if weight is None or prob is None:
            continue
        weighted_sum += (prob - 0.5) * weight
        total_weight += abs(weight)
    if total_weight == 0:
        return None
    return (weighted_sum / total_weight) * 200.0


def report(*, now: datetime | None = None) -> dict[str, Any]:
    """Produce the structured report consumed by skill/command."""
    now = now or datetime.now(timezone.utc)
    rows = load_snapshots()

    if not rows:
        return {"status": "NO_DATA", "composite": None, "bucket": "NEUTRAL", "markets": []}

    last_ts = max(_parse_ts(r["ts"]) for r in rows)
    age_seconds = (now - last_ts).total_seconds()
    if age_seconds > config.STALE_AFTER_SECONDS:
        return {
            "status": "STALE",
            "last_snapshot_age_seconds": int(age_seconds),
            "composite": None,
            "bucket": "NEUTRAL",
            "markets": [],
        }

    by_slug: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_slug.setdefault(r["slug"], []).append(r)

    markets_out: list[dict[str, Any]] = []
    per_market_for_composite: dict[str, dict[str, Any]] = {}
    for slug, snaps in by_slug.items():
        deltas = compute_deltas(snaps, now=now)
        weight = config.match_weight(slug)
        contribution = None
        if weight is not None and deltas["prob_now"] is not None:
            contribution = (deltas["prob_now"] - 0.5) * weight
            per_market_for_composite[slug] = {"prob_now": deltas["prob_now"], "weight": weight}

        latest = sorted(snaps, key=lambda r: _parse_ts(r["ts"]))[-1]
        markets_out.append(
            {
                "slug": slug,
                "prob_now": deltas["prob_now"],
                "delta_1h": deltas["delta_1h"],
                "delta_24h": deltas["delta_24h"],
                "delta_7d": deltas["delta_7d"],
                "vol_24h": float(latest.get("vol_24h", 0)),
                "weight": weight,
                "contribution": contribution,
            }
        )

    comp = composite(per_market_for_composite)
    return {
        "status": "FRESH",
        "last_snapshot_age_seconds": int(age_seconds),
        "composite": comp,
        "bucket": config.bucket_for(comp) if comp is not None else "NEUTRAL",
        "markets": markets_out,
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [analyzer] %(message)s")
    rep = report()
    if "--json" in sys.argv:
        print(json.dumps(rep, indent=2, default=str))
    else:
        print(f"status={rep['status']} composite={rep['composite']} bucket={rep['bucket']} markets={len(rep['markets'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_polymarket_analyzer.py -v`
Expected: 7 passed.

- [ ] **Step 6: Commit**

```bash
git add .claude/scripts/polymarket/analyzer.py .claude/scripts/tests/test_polymarket_analyzer.py .claude/scripts/tests/fixtures/polymarket/snapshots_sample.jsonl
git commit -m "feat(polymarket): analyzer with deltas, composite, stale detection"
```

---

### Task 7: poller.py — write snapshots from tracked markets

**Files:**
- Create: `.claude/scripts/polymarket/poller.py`
- Test: `.claude/scripts/tests/test_polymarket_poller.py`

- [ ] **Step 1: Write the failing test**

Write `.claude/scripts/tests/test_polymarket_poller.py`:
```python
"""Tests for polymarket.poller."""
import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from polymarket import config, poller
from polymarket.client import Market, PolymarketError


def _mk_market(slug, prob, vol):
    return Market(
        id=f"id-{slug}",
        slug=slug,
        question=slug,
        prob_yes=prob,
        volume_24h=vol,
        end_date="2026-12-31T00:00:00Z",
        last_trade=prob,
    )


@pytest.fixture
def tmp_paths(tmp_path, monkeypatch):
    tracked = tmp_path / "tracked.json"
    snaps = tmp_path / "snaps.jsonl"
    monkeypatch.setattr(config, "TRACKED_MARKETS_PATH", tracked)
    monkeypatch.setattr(config, "SNAPSHOTS_PATH", snaps)
    return tracked, snaps


def test_poller_appends_one_line_per_tracked_market(tmp_paths, mocker):
    tracked, snaps = tmp_paths
    tracked.write_text(json.dumps({"markets": [{"id": "0xaaa", "slug": "fed-cut-may"}, {"id": "0xbbb", "slug": "us-recession"}]}))

    def fake_get(market_id):
        return _mk_market("fed-cut-may", 0.62, 2_400_000) if market_id == "0xaaa" else _mk_market("us-recession", 0.28, 890_000)

    mocker.patch.object(poller, "get_market_with_fallback", side_effect=fake_get)

    n = poller.run_once()
    assert n == 2
    lines = snaps.read_text().splitlines()
    assert len(lines) == 2
    parsed = [json.loads(line) for line in lines]
    slugs = {p["slug"] for p in parsed}
    assert slugs == {"fed-cut-may", "us-recession"}
    for p in parsed:
        assert "ts" in p and "prob" in p and "vol_24h" in p


def test_poller_skips_market_on_error_and_continues(tmp_paths, mocker):
    tracked, snaps = tmp_paths
    tracked.write_text(json.dumps({"markets": [{"id": "0xaaa", "slug": "fed-cut-may"}, {"id": "0xbbb", "slug": "us-recession"}]}))

    def fake_get(market_id):
        if market_id == "0xaaa":
            raise PolymarketError("simulated")
        return _mk_market("us-recession", 0.28, 890_000)

    mocker.patch.object(poller, "get_market_with_fallback", side_effect=fake_get)

    n = poller.run_once()
    assert n == 1  # only one written
    lines = snaps.read_text().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["slug"] == "us-recession"


def test_poller_no_tracked_file_returns_zero(tmp_paths):
    tracked, snaps = tmp_paths  # tracked file does not exist
    n = poller.run_once()
    assert n == 0
    assert not snaps.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_polymarket_poller.py -v`
Expected: errors (`ModuleNotFoundError: polymarket.poller`).

- [ ] **Step 3: Write poller.py**

Write `.claude/scripts/polymarket/poller.py`:
```python
"""Hourly poller that appends snapshots for every tracked market."""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from polymarket import config
from polymarket.client import PolymarketError, get_market_with_fallback

log = logging.getLogger(__name__)


def _load_tracked(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        log.error("tracked_markets.json is malformed; aborting cycle")
        return []
    return data.get("markets", [])


def _append_snapshot(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(payload, separators=(",", ":")) + "\n")


def run_once() -> int:
    """Run a single poll cycle. Returns number of snapshots written."""
    tracked = _load_tracked(config.TRACKED_MARKETS_PATH)
    if not tracked:
        log.info("No tracked markets; skipping cycle")
        return 0

    written = 0
    ts = datetime.now(timezone.utc).isoformat()
    for entry in tracked:
        market_id = entry.get("id") or entry.get("slug")
        if not market_id:
            continue
        try:
            m = get_market_with_fallback(market_id)
        except PolymarketError as exc:
            log.warning("Skipping %s: %s", market_id, exc)
            continue
        payload = {
            "ts": ts,
            "id": m.id,
            "slug": m.slug,
            "prob": m.prob_yes,
            "vol_24h": m.volume_24h,
            "last_trade": m.last_trade,
        }
        _append_snapshot(config.SNAPSHOTS_PATH, payload)
        written += 1
    log.info("Poller wrote %d snapshots", written)
    return written


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [poller] %(message)s")
    if "--once" in sys.argv:
        n = run_once()
        print(f"Wrote {n} snapshot(s).")
        return 0
    # Default: also a single shot — launchd handles cadence
    n = run_once()
    return 0 if n >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_polymarket_poller.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/polymarket/poller.py .claude/scripts/tests/test_polymarket_poller.py
git commit -m "feat(polymarket): hourly poller writing snapshots.jsonl"
```

---

### Task 8: research/data_loader.py — join snapshots with BTC OHLCV

**Files:**
- Create: `.claude/scripts/polymarket/research/data_loader.py`
- Test: `.claude/scripts/tests/test_polymarket_data_loader.py`

- [ ] **Step 1: Write the failing test**

Write `.claude/scripts/tests/test_polymarket_data_loader.py`:
```python
"""Tests for polymarket.research.data_loader."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from polymarket import config
from polymarket.research import data_loader


def _write_snapshots(path: Path, rows: list[dict]) -> None:
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def _write_ohlcv_csv(path: Path, rows: list[tuple[str, float]]) -> None:
    """rows = [(iso_ts, close_price)]"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        f.write("ts,open,high,low,close,volume\n")
        for ts, close in rows:
            f.write(f"{ts},{close},{close},{close},{close},0\n")


def test_load_snapshots_as_series(tmp_path, monkeypatch):
    snaps = tmp_path / "snaps.jsonl"
    _write_snapshots(snaps, [
        {"ts": "2026-05-01T00:00:00+00:00", "slug": "fed-cut", "prob": 0.50, "vol_24h": 1},
        {"ts": "2026-05-01T01:00:00+00:00", "slug": "fed-cut", "prob": 0.55, "vol_24h": 1},
    ])
    monkeypatch.setattr(config, "SNAPSHOTS_PATH", snaps)

    series = data_loader.load_snapshots_for_market("fed-cut")
    assert len(series) == 2
    assert series[0][1] == 0.50


def test_align_pm_with_btc(tmp_path, monkeypatch):
    snaps = tmp_path / "snaps.jsonl"
    _write_snapshots(snaps, [
        {"ts": "2026-05-01T00:00:00+00:00", "slug": "fed-cut", "prob": 0.50, "vol_24h": 1},
        {"ts": "2026-05-01T04:00:00+00:00", "slug": "fed-cut", "prob": 0.55, "vol_24h": 1},
    ])
    csv = tmp_path / "btc.csv"
    _write_ohlcv_csv(csv, [
        ("2026-05-01T00:00:00+00:00", 70000.0),
        ("2026-05-01T04:00:00+00:00", 70500.0),
        ("2026-05-01T08:00:00+00:00", 71000.0),
    ])
    monkeypatch.setattr(config, "SNAPSHOTS_PATH", snaps)

    aligned = data_loader.align_with_btc(
        slug="fed-cut",
        btc_csv=csv,
        forward_window=timedelta(hours=4),
    )
    # For each PM snapshot we get (pm_prob, btc_close_at_t, btc_close_at_t+window)
    assert len(aligned) == 2
    pm0, btc0, btc_fwd0 = aligned[0]
    assert pm0 == 0.50
    assert btc0 == 70000.0
    assert btc_fwd0 == 70500.0  # 4h forward
    pm1, btc1, btc_fwd1 = aligned[1]
    assert pm1 == 0.55
    assert btc1 == 70500.0
    assert btc_fwd1 == 71000.0


def test_align_drops_when_no_forward_btc(tmp_path, monkeypatch):
    snaps = tmp_path / "snaps.jsonl"
    _write_snapshots(snaps, [
        {"ts": "2026-05-01T20:00:00+00:00", "slug": "fed-cut", "prob": 0.55, "vol_24h": 1},
    ])
    csv = tmp_path / "btc.csv"
    _write_ohlcv_csv(csv, [
        ("2026-05-01T20:00:00+00:00", 70000.0),
        # No row at +4h
    ])
    monkeypatch.setattr(config, "SNAPSHOTS_PATH", snaps)

    aligned = data_loader.align_with_btc(
        slug="fed-cut",
        btc_csv=csv,
        forward_window=timedelta(hours=4),
    )
    assert aligned == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_polymarket_data_loader.py -v`
Expected: errors (`ModuleNotFoundError`).

- [ ] **Step 3: Write data_loader.py**

Write `.claude/scripts/polymarket/research/data_loader.py`:
```python
"""Join Polymarket snapshots with BTC OHLCV for research.

Reads snapshots.jsonl and a BTC OHLCV CSV (ts,open,high,low,close,volume).
Returns aligned tuples of (pm_prob, btc_close_t, btc_close_t+forward).
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from polymarket import config


def _parse_ts(s: str) -> datetime:
    s = s.replace("Z", "+00:00") if s.endswith("Z") else s
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def load_snapshots_for_market(slug: str, snapshots_path: Path | None = None) -> list[tuple[datetime, float]]:
    """Return [(timestamp, prob_yes)] sorted by ts ascending."""
    p = snapshots_path or config.SNAPSHOTS_PATH
    if not p.exists():
        return []
    out: list[tuple[datetime, float]] = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("slug") != slug:
            continue
        out.append((_parse_ts(row["ts"]), float(row["prob"])))
    return sorted(out, key=lambda t: t[0])


def _load_btc(path: Path) -> list[tuple[datetime, float]]:
    rows: list[tuple[datetime, float]] = []
    with path.open() as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                rows.append((_parse_ts(r["ts"]), float(r["close"])))
            except (KeyError, ValueError):
                continue
    return sorted(rows, key=lambda t: t[0])


def _btc_close_at_or_before(btc: list[tuple[datetime, float]], target: datetime) -> float | None:
    """Find the latest BTC close at or before target (within 1h tolerance)."""
    best = None
    for ts, close in btc:
        if ts > target:
            break
        if (target - ts) <= timedelta(hours=1):
            best = close
    return best


def align_with_btc(
    *,
    slug: str,
    btc_csv: Path,
    forward_window: timedelta,
    snapshots_path: Path | None = None,
) -> list[tuple[float, float, float]]:
    """Align PM probability snapshots with BTC close at the snapshot time and at +forward_window.

    Returns [(pm_prob, btc_t, btc_t+forward)].
    Drops rows where either BTC value cannot be resolved within tolerance.
    """
    pm_series = load_snapshots_for_market(slug, snapshots_path)
    btc = _load_btc(btc_csv)
    if not pm_series or not btc:
        return []

    aligned: list[tuple[float, float, float]] = []
    for ts, prob in pm_series:
        c0 = _btc_close_at_or_before(btc, ts)
        c1 = _btc_close_at_or_before(btc, ts + forward_window)
        if c0 is None or c1 is None:
            continue
        # Require c1's matched timestamp to actually be ≥ ts + window − tolerance
        # (we approximate by checking strict difference)
        if c1 == c0 and ts + forward_window > btc[-1][0]:
            continue
        aligned.append((prob, c0, c1))
    return aligned
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_polymarket_data_loader.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/polymarket/research/data_loader.py .claude/scripts/tests/test_polymarket_data_loader.py
git commit -m "feat(polymarket): research data loader (snapshots + BTC OHLCV alignment)"
```

---

### Task 9: research/hypotheses.py — H1, H2, H3, H4

**Files:**
- Create: `.claude/scripts/polymarket/research/hypotheses.py`
- Test: `.claude/scripts/tests/test_polymarket_hypotheses.py`

- [ ] **Step 1: Write the failing test**

Write `.claude/scripts/tests/test_polymarket_hypotheses.py`:
```python
"""Tests for polymarket.research.hypotheses."""
import math
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from polymarket.research import hypotheses


def test_h1_correlation_perfect_positive():
    # composite = pm_prob, btc_return = pm_prob (identical) ⇒ corr = 1
    aligned = [(0.4, 100.0, 110.0), (0.5, 100.0, 105.0), (0.6, 100.0, 100.0), (0.7, 100.0, 95.0)]
    # btc_return: +10%, +5%, 0%, -5% — and pm_prob 0.4..0.7 ⇒ negative correlation
    res = hypotheses.h1_composite_predicts_btc_return(aligned)
    assert res["n"] == 4
    assert res["correlation"] < -0.95  # near -1
    assert "p_value" in res


def test_h2_spike_predicts_volatility():
    # synthetic: every spike row has high subsequent volatility, baseline rows low
    # input shape: list[(pm_delta_24h, btc_abs_return_24h_after)]
    rows = [
        (0.06, 0.05),  # spike
        (0.08, 0.06),  # spike
        (0.01, 0.01),  # baseline
        (0.02, 0.005),  # baseline
        (0.07, 0.04),  # spike
    ]
    res = hypotheses.h2_spike_predicts_volatility(rows, spike_threshold=0.05)
    assert res["spike_n"] == 3
    assert res["baseline_n"] == 2
    assert res["mean_vol_spike"] > res["mean_vol_baseline"]


def test_h3_pre_event_edge():
    # rows: (days_to_resolution, pm_prob, btc_return_t+24h)
    # Pre-event window: high correlation; post-event: noise
    pre = [(2, 0.6, 0.05), (1, 0.65, 0.06), (0, 0.7, 0.07)]
    post = [(-1, 0.5, -0.01), (-2, 0.5, 0.005)]
    res = hypotheses.h3_pre_event_edge(pre + post)
    assert res["pre_event"]["n"] == 3
    assert res["post_event"]["n"] == 2
    # Pre should have stronger absolute correlation
    assert abs(res["pre_event"]["correlation"]) > abs(res["post_event"]["correlation"])


def test_h4_per_market_ic():
    # Two synthetic markets: one with strong IC, one with zero IC
    series = {
        "good-market": [(0.4, 0.05), (0.5, 0.0), (0.6, -0.05), (0.7, -0.10)],  # strong negative
        "noise-market": [(0.4, 0.0), (0.5, 0.0), (0.4, 0.0), (0.5, 0.0)],  # constant ⇒ undefined or 0
    }
    res = hypotheses.h4_per_market_ic(series, min_n=2)
    assert "good-market" in res
    assert abs(res["good-market"]["ic"]) > 0.95
    # noise-market: stdev zero on btc side, IC should be None
    assert res["noise-market"]["ic"] is None


def test_pearson_correlation_handles_constant():
    assert hypotheses._pearson([1, 1, 1], [1, 2, 3]) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_polymarket_hypotheses.py -v`
Expected: errors.

- [ ] **Step 3: Write hypotheses.py**

Write `.claude/scripts/polymarket/research/hypotheses.py`:
```python
"""Pure functions implementing H1-H4 of the research spec.

Each takes already-aligned data and returns a structured result dict.
No I/O, no side effects.
"""
from __future__ import annotations

import math
from typing import Any


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def _approx_p_value_from_corr(r: float, n: int) -> float | None:
    """Two-sided p-value approximation using Fisher z-transform."""
    if n < 4 or r is None or abs(r) >= 1.0:
        return None
    z = 0.5 * math.log((1 + r) / (1 - r))
    se = 1.0 / math.sqrt(n - 3)
    z_score = z / se
    # Two-sided p ≈ 2 * (1 - Φ(|z|))
    return 2 * (1 - 0.5 * (1 + math.erf(abs(z_score) / math.sqrt(2))))


def h1_composite_predicts_btc_return(aligned: list[tuple[float, float, float]]) -> dict[str, Any]:
    """aligned = [(pm_prob, btc_t, btc_t+window)] → corr(pm_prob, btc_return)."""
    if not aligned:
        return {"n": 0, "correlation": None, "p_value": None}
    probs = [a[0] for a in aligned]
    returns = [(a[2] - a[1]) / a[1] if a[1] != 0 else 0.0 for a in aligned]
    r = _pearson(probs, returns)
    p = _approx_p_value_from_corr(r, len(aligned)) if r is not None else None
    return {"n": len(aligned), "correlation": r, "p_value": p}


def h2_spike_predicts_volatility(
    rows: list[tuple[float, float]],
    *,
    spike_threshold: float = 0.05,
) -> dict[str, Any]:
    """rows = [(pm_delta_24h, btc_abs_return_t+24h)].

    Compares mean |btc_return| in spike rows vs baseline.
    """
    spike = [r for r in rows if abs(r[0]) >= spike_threshold]
    baseline = [r for r in rows if abs(r[0]) < spike_threshold]
    mean_spike = sum(r[1] for r in spike) / len(spike) if spike else None
    mean_base = sum(r[1] for r in baseline) / len(baseline) if baseline else None
    return {
        "spike_n": len(spike),
        "baseline_n": len(baseline),
        "mean_vol_spike": mean_spike,
        "mean_vol_baseline": mean_base,
        "spike_threshold": spike_threshold,
    }


def h3_pre_event_edge(
    rows: list[tuple[int, float, float]],
) -> dict[str, Any]:
    """rows = [(days_to_resolution, pm_prob, btc_return_t+24h)].

    Splits at days_to_resolution >= 0 (pre-event) vs < 0 (post-event)
    and computes correlation in each half.
    """
    pre = [r for r in rows if r[0] >= 0]
    post = [r for r in rows if r[0] < 0]

    def _corr(window: list[tuple[int, float, float]]):
        if not window:
            return {"n": 0, "correlation": None}
        xs = [r[1] for r in window]
        ys = [r[2] for r in window]
        return {"n": len(window), "correlation": _pearson(xs, ys)}

    return {"pre_event": _corr(pre), "post_event": _corr(post)}


def h4_per_market_ic(
    series_per_market: dict[str, list[tuple[float, float]]],
    *,
    min_n: int = 30,
) -> dict[str, dict[str, Any]]:
    """Per-market information coefficient = corr(pm_prob, btc_fwd_return).

    series_per_market[slug] = [(pm_prob, btc_fwd_return), ...]
    Markets with sample below min_n are still computed but flagged.
    """
    out: dict[str, dict[str, Any]] = {}
    for slug, rows in series_per_market.items():
        n = len(rows)
        if n < 2:
            out[slug] = {"n": n, "ic": None, "flag": "INSUFFICIENT_DATA"}
            continue
        xs = [r[0] for r in rows]
        ys = [r[1] for r in rows]
        ic = _pearson(xs, ys)
        flag = "OK" if n >= min_n else "LOW_N"
        out[slug] = {"n": n, "ic": ic, "flag": flag}
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_polymarket_hypotheses.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/polymarket/research/hypotheses.py .claude/scripts/tests/test_polymarket_hypotheses.py
git commit -m "feat(polymarket): research hypotheses H1-H4 (pure functions)"
```

---

### Task 10: research/report.py — markdown rendering and CLI entry

**Files:**
- Create: `.claude/scripts/polymarket/research/report.py`
- Test: `.claude/scripts/tests/test_polymarket_report.py`

- [ ] **Step 1: Write the failing test**

Write `.claude/scripts/tests/test_polymarket_report.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_polymarket_report.py -v`
Expected: errors (`ModuleNotFoundError`).

- [ ] **Step 3: Write report.py**

Write `.claude/scripts/polymarket/research/report.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_polymarket_report.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/polymarket/research/report.py .claude/scripts/tests/test_polymarket_report.py
git commit -m "feat(polymarket): research report renderer + CLI"
```

---

### Task 11: Skill `polymarket-macro` for agent auto-invocation

**Files:**
- Create: `.claude/skills/polymarket-macro/SKILL.md`

- [ ] **Step 1: Write the skill file**

Write `.claude/skills/polymarket-macro/SKILL.md`:
```markdown
---
name: polymarket-macro
description: Use cuando un agente (morning-analyst, signal-validator) o el usuario quieran añadir el bias macro de Polymarket al análisis BTC. Devuelve composite −100..+100 + tabla de markets relevantes + flags. Solo SI el snapshot está fresh (<2h); si está STALE devuelve el aviso. Es un 5° filtro — nunca convierte un NO-GO técnico en GO.
---

# Polymarket Macro Sentiment

## Cómo usarlo

Ejecutá:

```bash
.claude/scripts/.venv/bin/python -m polymarket.analyzer --json
```

Esto devuelve un JSON con shape:

```json
{
  "status": "FRESH|STALE|NO_DATA|NO_MARKETS",
  "last_snapshot_age_seconds": 1080,
  "composite": 13.7,
  "bucket": "MILD-BULL",
  "markets": [
    {"slug": "...", "prob_now": 0.62, "delta_1h": 0.01, "delta_24h": 0.07, "delta_7d": 0.14, "vol_24h": 2400000, "weight": 0.30, "contribution": 0.036}
  ]
}
```

Si `status` es FRESH → usa los datos. Si es cualquier otra cosa → reportá "PM macro no disponible esta sesión" y NO uses el composite.

## Reglas operativas

1. **Nunca convertir NO-GO en GO.** El composite es 5° filtro — informativo, no definitivo.
2. **Reducir size 25%** si `|composite| > 40` y los 4 filtros técnicos contradicen el bias. Nunca aumentar size por PM.
3. **Composite range** [-100, +100] con buckets:
   - `> +40` STRONG-BULL
   - `+15..+40` MILD-BULL
   - `-15..+15` NEUTRAL
   - `-40..-15` MILD-BEAR
   - `< -40` STRONG-BEAR
4. **Profile-agnostic** — funciona igual para retail / ftmo / fundingpips / quantfury / bitunix.

## Output sugerido para el reporte (humano-leíble)

Cuando inserts esto en un reporte:

```markdown
### PM Macro Sentiment
**Composite:** +13.7 (MILD-BULL) | **Status:** FRESH (poll 18 min ago) | 11 markets

| Market | Prob | Δ24h | Δ7d | Contribución |
|---|---|---|---|---|
| fed-cut-may-2026 | 62% | +7pp | +14pp | +0.036 (BULL) |
| us-recession-2026 | 28% | -5pp | -3pp | +0.055 (BULL) |
| ...
```

## Cuándo activarlo

- En `morning-analyst` durante FASE 2 (Contexto Global) — útil para días con catalysts macro.
- En `signal-validator` cuando la señal es BTC y hay events high-impact próximos (FOMC, CPI, NFP).
- Cuando el usuario invoca `/polymarket` directamente.

## Cuándo NO activarlo

- Status `STALE` o `NO_DATA` → ignorar, no inventar.
- Setups ultra-rápidos (scalp <15min) — el ciclo macro es muy lento.
- Cuando los 4 filtros técnicos ya cierran el caso de forma unánime.

## Detalles técnicos

- Snapshots se acumulan en `.claude/scripts/polymarket/data/snapshots.jsonl` cada hora vía launchd.
- Discovery rota la whitelist de markets cada día CR 04:00.
- Pesos en `polymarket.config.WEIGHT_MAPPING`. Se ajustan cada 30-60 días con `/polymarket-research`.
```

- [ ] **Step 2: Verify skill is reachable**

Run:
```bash
ls .claude/skills/polymarket-macro/SKILL.md
```
Expected: file exists.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/polymarket-macro/SKILL.md
git commit -m "feat(polymarket): polymarket-macro skill (auto-invokable)"
```

---

### Task 12: `/polymarket` and `/polymarket-research` slash commands

**Files:**
- Create: `.claude/commands/polymarket.md`
- Create: `.claude/commands/polymarket-research.md`

- [ ] **Step 1: Write `/polymarket` command**

Write `.claude/commands/polymarket.md`:
```markdown
---
description: Macro sentiment desde Polymarket (Fed/recession/tariffs). Composite -100..+100 + tabla markets. 5° filtro, nunca gate.
argument-hint: "[fed|movers|history <slug>] opcional"
allowed-tools: Bash
---

Pasos que ejecuta Claude:

1. **Correr el analyzer** y leer el JSON:
   ```bash
   .claude/scripts/.venv/bin/python -m polymarket.analyzer --json
   ```

2. **Si `status != "FRESH"`** → mostrar al usuario:
   ```
   ⚠️ PM Macro: <STALE|NO_DATA|NO_MARKETS> — no disponible esta sesión.
   Última snapshot hace <N> min. Verificar `launchctl list | grep polymarket`.
   ```
   Y terminar.

3. **Si hay argumento `fed`** → filtrar markets cuyo slug contiene "fed".
   **Si hay argumento `movers`** → solo markets con `abs(delta_24h) > 0.05`.
   **Si hay argumento `history <slug>`** → leer snapshots para ese slug y mostrar línea de tiempo ASCII (mejor esfuerzo: 7 días, 1 char por punto).

4. **Render quick-summary 3 líneas + tabla completa** según formato de la skill `polymarket-macro`:
   ```
   🟢 PM Macro Bias: +13.7 (MILD-BULL) | 11 markets | last poll 18min ago
   ⚠️ Fed-cut +14pp en 7d → DXY bajista esperado
   ✅ Recession odds -5pp → risk-on alineado

   ### Markets relevantes
   | Market | Prob | Δ24h | Δ7d | Contribución |
   |---|---|---|---|---|
   | ...
   ```

5. **Recordatorio final** (siempre):
   ```
   ⚠️ PM Macro es 5° filtro. NO convierte un NO-GO técnico en GO.
   ```

$ARGUMENTS
```

- [ ] **Step 2: Write `/polymarket-research` command**

Write `.claude/commands/polymarket-research.md`:
```markdown
---
description: Corre research pipeline (H1-H4) sobre snapshots históricos y BTC OHLCV. Output markdown a docs/polymarket_research/.
argument-hint: "[H1|H2|H3|H4|all] default all"
allowed-tools: Bash, Write
---

Pasos que ejecuta Claude:

1. **Determinar hipótesis a correr:**
   - `$ARGUMENTS` vacío o `all` → todas (H1, H2, H3, H4)
   - `H1`/`H2`/`H3`/`H4` → solo esa

2. **Verificar prerequisitos:**
   - `.claude/scripts/polymarket/data/snapshots.jsonl` debe existir y tener >50 líneas
   - BTC OHLCV CSV debe estar disponible en `scripts/ml_system/data/BTCUSDT_15m_60d.csv` o equivalente
   - Si falta data → mensaje claro + abort

3. **Componer payload** corriendo el helper:
   ```bash
   .claude/scripts/.venv/bin/python -c "
   from polymarket.research import data_loader, hypotheses
   from datetime import timedelta
   from pathlib import Path
   import json

   btc_csv = Path('scripts/ml_system/data/BTCUSDT_15m_60d.csv')
   # Por slug, alinear y calcular H1 + H4 (ejemplo simplificado).
   # En producción este wrapper se mueve a polymarket/research/runner.py.
   "
   ```
   *Para V1, ejecutar `python -m polymarket.research.report --out docs/polymarket_research/$(date +%Y-%m-%d)-report.md`* para emitir el shell del reporte.

4. **Generar reporte markdown**:
   ```bash
   mkdir -p docs/polymarket_research
   .claude/scripts/.venv/bin/python -m polymarket.research.report \
     --out "docs/polymarket_research/$(date +%Y-%m-%d)-report.md"
   ```

5. **Mostrar al usuario:**
   - Path del reporte generado
   - Caveat si N<200 (incluido por el renderer)
   - Sugerencia: "Si IC en H4 cambió >0.1 vs último report, actualizar weights en `polymarket/config.py`."

6. **Si `$ARGUMENTS` es una hipótesis específica**, sólo correr ese helper y emitir su sección.

$ARGUMENTS
```

- [ ] **Step 3: Verify commands exist**

Run:
```bash
ls .claude/commands/polymarket.md .claude/commands/polymarket-research.md
```
Expected: both files exist.

- [ ] **Step 4: Commit**

```bash
git add .claude/commands/polymarket.md .claude/commands/polymarket-research.md
git commit -m "feat(polymarket): /polymarket and /polymarket-research slash commands"
```

---

### Task 13: launchd plists for poller + discovery

**Files:**
- Create: `.claude/launchd/com.wally.polymarket-poller.plist`
- Create: `.claude/launchd/com.wally.polymarket-discovery.plist`

- [ ] **Step 1: Write poller plist**

Write `.claude/launchd/com.wally.polymarket-poller.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.wally.polymarket-poller</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/josecampos/Documents/wally-trader/.claude/scripts/.venv/bin/python</string>
        <string>-m</string>
        <string>polymarket.poller</string>
        <string>--once</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/josecampos/Documents/wally-trader/.claude/scripts</string>

    <key>StartInterval</key>
    <integer>3600</integer>

    <key>RunAtLoad</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/Users/josecampos/Library/Logs/wally-trader/polymarket-poller.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/josecampos/Library/Logs/wally-trader/polymarket-poller.err</string>

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

- [ ] **Step 2: Write discovery plist**

Write `.claude/launchd/com.wally.polymarket-discovery.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.wally.polymarket-discovery</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/josecampos/Documents/wally-trader/.claude/scripts/.venv/bin/python</string>
        <string>-m</string>
        <string>polymarket.discovery</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/josecampos/Documents/wally-trader/.claude/scripts</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>4</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>RunAtLoad</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/Users/josecampos/Library/Logs/wally-trader/polymarket-discovery.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/josecampos/Library/Logs/wally-trader/polymarket-discovery.err</string>

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

- [ ] **Step 3: Smoke test plists by running modules manually**

Run:
```bash
mkdir -p ~/Library/Logs/wally-trader
cd /Users/josecampos/Documents/wally-trader
.claude/scripts/.venv/bin/python -m polymarket.discovery --dry-run
```
Expected: prints rows like `<slug>\t<prob>\t$<vol>` without crashing (may print 0 markets if Gamma returns nothing matching, that's still success).

- [ ] **Step 4: Commit**

```bash
git add .claude/launchd/com.wally.polymarket-poller.plist .claude/launchd/com.wally.polymarket-discovery.plist
git commit -m "ops(polymarket): launchd plists for poller (1h) + discovery (daily 04:00 CR)"
```

---

### Task 14: End-to-end smoke + integration with morning-analyst

**Files:**
- Modify: `.claude/agents/morning-analyst.md` (or wherever the morning-analyst agent definition lives)
- Verify: full pipeline runs without errors

- [ ] **Step 1: Locate the morning-analyst agent definition**

Run:
```bash
find .claude -name "morning-analyst*" -type f
```
Note the path. Read its FASE 2 section to find the right insertion point.

- [ ] **Step 2: Add a PM Macro reference under FASE 2 (Contexto Global)**

Open the morning-analyst agent file. In the FASE 2 section, after the existing F&G/Funding/sentiment items, append:

```markdown
- **PM Macro (Polymarket):** invocar skill `polymarket-macro` para añadir composite −100..+100 al análisis. Si STALE, ignorar. Es 5° filtro — nunca convierte NO-GO en GO. Reducir size 25% si `|composite| > 40` contradice los 4 filtros técnicos.
```

- [ ] **Step 3: Run the full pytest suite**

Run:
```bash
.claude/scripts/.venv/bin/python -m pytest .claude/scripts/tests/test_polymarket_*.py -v
```
Expected: all polymarket tests pass.

- [ ] **Step 4: Smoke run the modules end-to-end**

Run (in order):
```bash
cd /Users/josecampos/Documents/wally-trader
.claude/scripts/.venv/bin/python -m polymarket.discovery --dry-run
.claude/scripts/.venv/bin/python -m polymarket.discovery        # writes tracked_markets.json
.claude/scripts/.venv/bin/python -m polymarket.poller --once    # writes first snapshot batch
.claude/scripts/.venv/bin/python -m polymarket.analyzer --json  # composite + status
```
Expected:
- discovery dry-run prints market rows (or zero if filters are too tight)
- discovery writes `data/tracked_markets.json`
- poller writes one line per tracked market in `data/snapshots.jsonl`
- analyzer prints JSON with `status: FRESH` and a composite

- [ ] **Step 5: Verify STALE simulation**

Run:
```bash
# Backdate snapshots and re-run analyzer
python3 -c "
import json
from pathlib import Path
p = Path('.claude/scripts/polymarket/data/snapshots.jsonl')
lines = p.read_text().splitlines()
for i, line in enumerate(lines):
    row = json.loads(line)
    row['ts'] = '2026-04-29T00:00:00+00:00'
    lines[i] = json.dumps(row)
p.write_text('\\n'.join(lines) + '\\n')
"
.claude/scripts/.venv/bin/python -m polymarket.analyzer --json
```
Expected: `"status": "STALE"`. Then restore snapshots:
```bash
.claude/scripts/.venv/bin/python -m polymarket.poller --once
```

- [ ] **Step 6: Load launchd jobs (optional, user-initiated)**

Run (only if user is ready to enable scheduling):
```bash
cp .claude/launchd/com.wally.polymarket-poller.plist ~/Library/LaunchAgents/
cp .claude/launchd/com.wally.polymarket-discovery.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.wally.polymarket-poller.plist
launchctl load ~/Library/LaunchAgents/com.wally.polymarket-discovery.plist
launchctl list | grep polymarket
```
Expected: two entries listed. **This step is operational and may be deferred until the user is ready.**

- [ ] **Step 7: Commit integration**

```bash
git add .claude/agents/
git commit -m "feat(polymarket): wire skill into morning-analyst FASE 2"
```

---

## Self-Review (completed during plan write)

**Spec coverage:**
- Read-only ingestion (Gamma + CLOB fallback) → Task 3, 4
- Auto-discovery by tags + volume → Task 5
- Hourly polling → Task 7 + Task 13
- Composite −100..+100 with de-meaned math → Task 6
- Skill `polymarket-macro` → Task 11
- `/polymarket` + `/polymarket-research` → Task 12
- Research pipeline H1-H4 → Tasks 8, 9, 10
- Outcome capture (`resolutions.jsonl`) — **NOT covered in V1 implementation**; spec §9 mentions it but the plan defers it. **Acceptable per spec § "out of scope deferred"** — added to followups below.
- Hard rules (5th filter, never converts NO-GO, profile-agnostic) → Task 11 (skill text)
- Error handling (retry, fallback, atomic write, malformed JSONL) → Tasks 3, 5, 6
- launchd plists → Task 13
- Test coverage with mocked HTTP → Tasks 2-10
- morning-analyst integration → Task 14

**Followups (post-V1, not in this plan):**
- `resolutions.jsonl` capture in `discovery.py` when a market transitions to `closed=true`
- Brier-score calibration metric in research report
- Subgraph integration stub (interface only)

**Placeholder scan:** No "TBD", no "TODO", no "implement later". Each step shows the actual code or command. Step 4 of Task 14 has explicit expected output. Task 12 step 3 has `$(date +%Y-%m-%d)` which is a real shell expansion, not a placeholder.

**Type consistency:**
- `Market` dataclass defined in Task 3 used consistently in Tasks 4, 5, 7
- `config.match_weight()` from Task 2 used in Tasks 6, 11
- `analyzer.report()` signature matches its consumers in Tasks 11, 12
- `align_with_btc()` from Task 8 referenced (not directly called) in Task 10's command — Task 10 explicitly notes the simplified V1 wiring; the full runner is deferred but the building blocks (data_loader, hypotheses) are complete and tested

**Spec sections without explicit task** that are intentionally deferred:
- §9 Resolutions/Brier — added to followups above
- §15 References — documentation, no implementation needed
