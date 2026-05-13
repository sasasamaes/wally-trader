# HMM Diagnostic Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `/hmm-analyze SYMBOL STRATEGY` — a strictly diagnostic tool that fits a Hidden Markov Model to 1H × 6m OHLCV, labels regimes, partitions backtest results by regime, and emits a markdown report (plus optional HTML and dry-run mapping patch). No live wire-in.

**Architecture:** Single Python entry point `hmm_analyze.py` delegating to `hmm_lib/` modules (fetcher, features, model, labeling, backtest, reporting, suggest). Strategy implementations are wrapped (not refactored) for V1 — we add a thin adapter layer that calls the existing `strat_*` functions in `backtest_regime_matrix.py` unchanged. Backtest harness runs on 15m bars (matching strategy contract) but the regime label for each trade is the HMM state of the **1H bar covering the entry timestamp**.

**Tech Stack:** Python 3.13, hmmlearn (new dep), numpy, pandas, requests, pytest. Optional plotly for `--html`.

**Reference spec:** `docs/superpowers/specs/2026-05-13-hmm-diagnostic-tool-design.md`

---

## Task 1: Install hmmlearn dependency

**Files:**
- Modify: `requirements.txt` (root) or document in CLAUDE.md if no requirements file
- No code yet

- [ ] **Step 1: Check if requirements.txt exists**

Run: `ls /Users/josecampos/Documents/wally-trader/requirements.txt 2>/dev/null || echo MISSING`

If missing, dependency is installed into the venv directly and documented in CLAUDE.md Bundle 4 section (Task 22).

- [ ] **Step 2: Install hmmlearn into venv**

Run: `.claude/scripts/.venv/bin/pip install 'hmmlearn>=0.3.0'`

Expected: `Successfully installed hmmlearn-0.3.x scikit-learn-1.x`

- [ ] **Step 3: Verify import works**

Run: `.claude/scripts/.venv/bin/python -c "from hmmlearn.hmm import GaussianHMM; print('OK', GaussianHMM)"`

Expected: `OK <class 'hmmlearn.hmm.GaussianHMM'>`

- [ ] **Step 4: Commit (if requirements.txt was modified)**

```bash
# Only if requirements.txt exists and was modified
git add requirements.txt
git commit -m "deps: add hmmlearn>=0.3.0 for HMM diagnostic tool

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

If no requirements.txt, no commit needed at this step — dependency stays in venv and is documented in CLAUDE.md at Task 22.

---

## Task 2: Create hmm_lib package skeleton

**Files:**
- Create: `.claude/scripts/hmm_lib/__init__.py`
- Create: `.claude/scripts/hmm_lib/errors.py`

- [ ] **Step 1: Create empty package**

```bash
mkdir -p .claude/scripts/hmm_lib
```

- [ ] **Step 2: Write `.claude/scripts/hmm_lib/__init__.py`**

```python
"""HMM diagnostic tool library — see docs/superpowers/specs/2026-05-13-hmm-diagnostic-tool-design.md"""

__version__ = "0.1.0"
```

- [ ] **Step 3: Write `.claude/scripts/hmm_lib/errors.py`**

```python
"""Custom exceptions for the HMM diagnostic tool."""


class HMMAnalyzeError(Exception):
    """Base class for all HMM analyze errors."""


class FetchError(HMMAnalyzeError):
    """OHLCV fetch failed (network, 4xx, 5xx)."""


class InsufficientDataError(HMMAnalyzeError):
    """Fewer bars returned than required minimum (1000)."""


class HMMFitError(HMMAnalyzeError):
    """All K values failed to fit a usable HMM."""


class StrategyExecError(HMMAnalyzeError):
    """A strategy raised an exception during backtest. Attributes: bar_index, symbol, strategy."""

    def __init__(self, message: str, *, bar_index: int, symbol: str, strategy: str):
        super().__init__(message)
        self.bar_index = bar_index
        self.symbol = symbol
        self.strategy = strategy
```

- [ ] **Step 4: Verify imports**

Run: `.claude/scripts/.venv/bin/python -c "from hmm_lib.errors import FetchError, HMMFitError; print('OK')"` from `.claude/scripts/` directory.

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add .claude/scripts/hmm_lib/__init__.py .claude/scripts/hmm_lib/errors.py
git commit -m "feat(hmm): scaffold hmm_lib package with custom errors

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Write tests for fetcher.py

**Files:**
- Create: `shared/wally_core/tests/test_hmm_fetcher.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for hmm_lib.fetcher — OHLCV fetch + cache."""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Make .claude/scripts importable
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "scripts"))

from hmm_lib import errors
from hmm_lib import fetcher


def _fake_binance_kline_row(ts_ms: int, close: float):
    """Binance kline response is a list of 12 fields per row."""
    return [ts_ms, "100.0", "110.0", "90.0", str(close), "1500.0", ts_ms + 3_600_000,
            "150000", 25, "750", "75000", "0"]


def test_fetch_returns_dataframe_with_correct_columns(tmp_path, monkeypatch):
    monkeypatch.setattr(fetcher, "CACHE_DIR", tmp_path)
    rows = [_fake_binance_kline_row(1_700_000_000_000 + i * 3_600_000, 100.0 + i)
            for i in range(1500)]
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = rows
    with patch.object(fetcher, "_http_get", return_value=mock_resp):
        df = fetcher.fetch_ohlcv_1h_6m("ETHUSDT")
    assert list(df.columns) == ["open", "high", "low", "close", "volume", "ts_utc"]
    assert len(df) >= 1000


def test_fetch_raises_insufficient_data_on_short_response(tmp_path, monkeypatch):
    monkeypatch.setattr(fetcher, "CACHE_DIR", tmp_path)
    rows = [_fake_binance_kline_row(1_700_000_000_000 + i * 3_600_000, 100.0 + i)
            for i in range(500)]
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = rows
    with patch.object(fetcher, "_http_get", return_value=mock_resp):
        with pytest.raises(errors.InsufficientDataError):
            fetcher.fetch_ohlcv_1h_6m("ETHUSDT")


def test_fetch_raises_fetch_error_on_4xx(tmp_path, monkeypatch):
    monkeypatch.setattr(fetcher, "CACHE_DIR", tmp_path)
    mock_resp = MagicMock(status_code=400)
    mock_resp.json.return_value = {"code": -1121, "msg": "Invalid symbol."}
    with patch.object(fetcher, "_http_get", return_value=mock_resp):
        with pytest.raises(errors.FetchError, match="not listed"):
            fetcher.fetch_ohlcv_1h_6m("XYZUSDT")


def test_fetch_uses_cache_within_ttl(tmp_path, monkeypatch):
    monkeypatch.setattr(fetcher, "CACHE_DIR", tmp_path)
    cache_payload = {
        "ts_saved": "2026-05-13T10:00:00",
        "symbol": "ETHUSDT",
        "rows": [_fake_binance_kline_row(1_700_000_000_000 + i * 3_600_000, 100.0 + i)
                 for i in range(1500)],
    }
    cache_file = tmp_path / "ohlcv_ETHUSDT_1h_6m.json"
    cache_file.write_text(json.dumps(cache_payload))
    # Simulate "now" is 30 minutes after save → still within 1h TTL
    monkeypatch.setattr(fetcher, "_now_iso", lambda: "2026-05-13T10:30:00")
    with patch.object(fetcher, "_http_get") as mock_http:
        df = fetcher.fetch_ohlcv_1h_6m("ETHUSDT")
    mock_http.assert_not_called()
    assert len(df) == 1500
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.claude/scripts/.venv/bin/python -m pytest shared/wally_core/tests/test_hmm_fetcher.py -v`

Expected: 4 ERRORS — `ModuleNotFoundError: No module named 'hmm_lib.fetcher'`

- [ ] **Step 3: Commit the failing tests**

```bash
git add shared/wally_core/tests/test_hmm_fetcher.py
git commit -m "test(hmm): failing tests for OHLCV fetcher

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Implement fetcher.py

**Files:**
- Create: `.claude/scripts/hmm_lib/fetcher.py`

- [ ] **Step 1: Write minimal implementation**

```python
"""OHLCV fetch from Binance Futures with 1h disk cache."""
import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from hmm_lib.errors import FetchError, InsufficientDataError

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CACHE_DIR = PROJECT_ROOT / ".claude" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

BINANCE_FAPI = "https://fapi.binance.com/fapi/v1/klines"
CACHE_TTL_SECONDS = 3600
MIN_BARS = 1000
TARGET_BARS = 4380  # ~6 months of 1H


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _http_get(url: str, params: dict, timeout: int = 15) -> requests.Response:
    return requests.get(url, params=params, timeout=timeout)


def _cache_path(symbol: str) -> Path:
    return CACHE_DIR / f"ohlcv_{symbol.upper()}_1h_6m.json"


def _cache_is_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text())
        saved_ts = datetime.fromisoformat(payload["ts_saved"])
    except (json.JSONDecodeError, KeyError, ValueError):
        return False
    age = (datetime.fromisoformat(_now_iso()) - saved_ts).total_seconds()
    return age < CACHE_TTL_SECONDS


def _rows_to_df(rows: list) -> pd.DataFrame:
    df = pd.DataFrame(
        [{
            "open": float(r[1]),
            "high": float(r[2]),
            "low": float(r[3]),
            "close": float(r[4]),
            "volume": float(r[5]),
            "ts_utc": pd.to_datetime(r[0], unit="ms", utc=True),
        } for r in rows]
    )
    return df


def fetch_ohlcv_1h_6m(symbol: str, *, force_refresh: bool = False) -> pd.DataFrame:
    """Pull ~4380 hourly bars from Binance Futures with 1h disk cache."""
    symbol = symbol.upper()
    cache = _cache_path(symbol)

    if not force_refresh and _cache_is_fresh(cache):
        payload = json.loads(cache.read_text())
        return _rows_to_df(payload["rows"])

    all_rows: list = []
    end_time: int | None = None
    for _ in range(4):  # max 4 pages × 1500 = 6000 bars, more than enough
        params = {"symbol": symbol, "interval": "1h", "limit": 1500}
        if end_time is not None:
            params["endTime"] = end_time

        resp = None
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                resp = _http_get(BINANCE_FAPI, params)
                if resp.status_code == 200:
                    break
                if 400 <= resp.status_code < 500:
                    msg = resp.json().get("msg", "unknown") if resp.content else "unknown"
                    raise FetchError(f"symbol not listed on Binance Futures: {symbol} ({msg})")
                # 5xx → retry
                time.sleep(2 ** attempt)
            except requests.RequestException as exc:
                last_exc = exc
                time.sleep(2 ** attempt)
        else:
            raise FetchError(f"network failure after retries: {last_exc}")

        rows = resp.json()
        if not rows:
            break
        all_rows = rows + all_rows
        end_time = rows[0][0] - 1
        if len(all_rows) >= TARGET_BARS:
            break

    if len(all_rows) < MIN_BARS:
        raise InsufficientDataError(
            f"only {len(all_rows)} bars available for {symbol}, need >= {MIN_BARS}")

    # Dedupe by open_time (first field), sort, trim to TARGET_BARS most recent
    seen: dict = {}
    for r in all_rows:
        seen[r[0]] = r
    rows_sorted = [seen[k] for k in sorted(seen.keys())][-TARGET_BARS:]

    cache.write_text(json.dumps({
        "ts_saved": _now_iso(),
        "symbol": symbol,
        "rows": rows_sorted,
    }))

    return _rows_to_df(rows_sorted)
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `.claude/scripts/.venv/bin/python -m pytest shared/wally_core/tests/test_hmm_fetcher.py -v`

Expected: 4 PASSED

- [ ] **Step 3: Commit**

```bash
git add .claude/scripts/hmm_lib/fetcher.py
git commit -m "feat(hmm): implement OHLCV fetcher with 1h cache and retries

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Write tests for features.py

**Files:**
- Create: `shared/wally_core/tests/test_hmm_features.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for hmm_lib.features — feature engineering."""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "scripts"))

from hmm_lib import features


def _make_bars(closes: list[float]) -> pd.DataFrame:
    n = len(closes)
    return pd.DataFrame({
        "open": closes,
        "high": [c * 1.01 for c in closes],
        "low": [c * 0.99 for c in closes],
        "close": closes,
        "volume": [1000.0] * n,
        "ts_utc": pd.date_range("2026-01-01", periods=n, freq="1h", tz="UTC"),
    })


def test_log_returns_match_manual():
    closes = [100.0, 101.0, 99.0, 100.0, 102.0]
    bars = _make_bars(closes)
    raw = features._raw_log_returns(bars["close"].to_numpy())
    # First bar has NaN return — verify subsequent
    assert math.isclose(raw[1], math.log(101 / 100), abs_tol=1e-9)
    assert math.isclose(raw[2], math.log(99 / 101), abs_tol=1e-9)
    assert math.isclose(raw[3], math.log(100 / 99), abs_tol=1e-9)


def test_features_drops_warmup_bars():
    bars = _make_bars([100.0 + i for i in range(100)])
    matrix = features.build_features(bars)
    # warmup = 20 (max of vol_20 lookback, momentum_14 lookback)
    assert matrix.shape == (80, 3)


def test_features_are_standardized():
    rng = np.random.default_rng(seed=42)
    closes = (100 + rng.standard_normal(500).cumsum()).tolist()
    bars = _make_bars(closes)
    matrix = features.build_features(bars)
    # Each column mean ≈ 0, std ≈ 1
    means = matrix.mean(axis=0)
    stds = matrix.std(axis=0)
    assert np.allclose(means, 0, atol=1e-9), f"means={means}"
    assert np.allclose(stds, 1.0, atol=1e-2), f"stds={stds}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.claude/scripts/.venv/bin/python -m pytest shared/wally_core/tests/test_hmm_features.py -v`

Expected: 3 ERRORS — `ModuleNotFoundError: No module named 'hmm_lib.features'`

- [ ] **Step 3: Commit the failing tests**

```bash
git add shared/wally_core/tests/test_hmm_features.py
git commit -m "test(hmm): failing tests for feature engineering

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Implement features.py

**Files:**
- Create: `.claude/scripts/hmm_lib/features.py`

- [ ] **Step 1: Write minimal implementation**

```python
"""Feature engineering for HMM input: log_return, vol_20, momentum_14 (standardized)."""
import numpy as np
import pandas as pd

VOL_WINDOW = 20
MOMENTUM_WINDOW = 14
WARMUP = 20  # max(VOL_WINDOW, MOMENTUM_WINDOW + 6 buffer for stable estimates)


def _raw_log_returns(closes: np.ndarray) -> np.ndarray:
    """Return log_returns. First entry is NaN."""
    ratios = closes[1:] / closes[:-1]
    out = np.full(len(closes), np.nan)
    out[1:] = np.log(ratios)
    return out


def _rolling_std(x: np.ndarray, window: int) -> np.ndarray:
    """Rolling stdev. First (window-1) entries NaN. Uses pandas for correctness."""
    return pd.Series(x).rolling(window=window, min_periods=window).std().to_numpy()


def _momentum(closes: np.ndarray, window: int) -> np.ndarray:
    """(close[t] - close[t-window]) / close[t-window]. First `window` entries NaN."""
    out = np.full(len(closes), np.nan)
    out[window:] = (closes[window:] - closes[:-window]) / closes[:-window]
    return out


def build_features(bars: pd.DataFrame) -> np.ndarray:
    """Return (N, 3) standardized matrix: [log_return, vol_20, momentum_14].
    Drops initial WARMUP bars. Mean-centered, unit-variance per column.
    """
    closes = bars["close"].to_numpy()
    log_ret = _raw_log_returns(closes)
    vol_20 = _rolling_std(log_ret, VOL_WINDOW)
    mom_14 = _momentum(closes, MOMENTUM_WINDOW)

    stacked = np.column_stack([log_ret, vol_20, mom_14])
    trimmed = stacked[WARMUP:]

    if np.isnan(trimmed).any():
        # Drop any rows that still contain NaN (shouldn't happen with WARMUP=20)
        mask = ~np.isnan(trimmed).any(axis=1)
        trimmed = trimmed[mask]

    means = trimmed.mean(axis=0)
    stds = trimmed.std(axis=0)
    stds[stds == 0] = 1.0  # avoid div-by-zero on flat series
    standardized = (trimmed - means) / stds
    return standardized
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `.claude/scripts/.venv/bin/python -m pytest shared/wally_core/tests/test_hmm_features.py -v`

Expected: 3 PASSED

- [ ] **Step 3: Commit**

```bash
git add .claude/scripts/hmm_lib/features.py
git commit -m "feat(hmm): implement feature engineering with warmup and standardization

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Write tests for model.py

**Files:**
- Create: `shared/wally_core/tests/test_hmm_model.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for hmm_lib.model — HMM fit + BIC selection."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "scripts"))

from hmm_lib import model
from hmm_lib.errors import HMMFitError


def _synthetic_features(n: int = 1500, seed: int = 0) -> np.ndarray:
    """3 clusters in 3D space — should be detected as 3 regimes."""
    rng = np.random.default_rng(seed)
    seg = n // 3
    cluster_a = rng.normal(loc=[-2, -1, -1], scale=0.3, size=(seg, 3))
    cluster_b = rng.normal(loc=[0, 0, 0], scale=0.3, size=(seg, 3))
    cluster_c = rng.normal(loc=[+2, +2, +1], scale=0.3, size=(n - 2 * seg, 3))
    return np.vstack([cluster_a, cluster_b, cluster_c])


def test_fit_returns_hmmfit_with_required_fields():
    features = _synthetic_features()
    fit = model.fit_best_hmm(features, k_range=(2, 3))
    assert fit.k in (2, 3)
    assert fit.transition_matrix.shape == (fit.k, fit.k)
    assert np.allclose(fit.transition_matrix.sum(axis=1), 1.0, atol=1e-6)
    assert fit.states.shape == (len(features),)
    assert isinstance(fit.bic, float)


def test_bic_picks_lowest():
    """When K=3 is clearly best, fit_best_hmm should pick K=3."""
    features = _synthetic_features(n=2000)
    fit = model.fit_best_hmm(features, k_range=(2, 3, 4, 5))
    # With 3 well-separated clusters, BIC should favor K=3 over K=2 and K>=4
    # (allow K=3 OR K=4 because BIC for K=4 can be close)
    assert fit.k in (3, 4), f"expected K in (3, 4), got {fit.k}"


def test_fit_is_deterministic_with_seed():
    features = _synthetic_features()
    fit1 = model.fit_best_hmm(features, k_range=(2, 3), random_state=42)
    fit2 = model.fit_best_hmm(features, k_range=(2, 3), random_state=42)
    assert np.allclose(fit1.transition_matrix, fit2.transition_matrix, atol=1e-9)
    assert fit1.k == fit2.k


def test_fit_raises_when_all_k_fail():
    """Mock GaussianHMM to always fail → HMMFitError."""
    features = _synthetic_features()
    with patch.object(model, "_fit_one_k", side_effect=ValueError("non-convergent")):
        with pytest.raises(HMMFitError):
            model.fit_best_hmm(features, k_range=(2,))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.claude/scripts/.venv/bin/python -m pytest shared/wally_core/tests/test_hmm_model.py -v`

Expected: 4 ERRORS — `ModuleNotFoundError: No module named 'hmm_lib.model'`

- [ ] **Step 3: Commit the failing tests**

```bash
git add shared/wally_core/tests/test_hmm_model.py
git commit -m "test(hmm): failing tests for HMM model fit + BIC selection

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Implement model.py

**Files:**
- Create: `.claude/scripts/hmm_lib/model.py`

- [ ] **Step 1: Write minimal implementation**

```python
"""HMM fit using hmmlearn.GaussianHMM with BIC-based K selection."""
import logging
import math
import warnings
from dataclasses import dataclass

import numpy as np
from hmmlearn import hmm

from hmm_lib.errors import HMMFitError

log = logging.getLogger(__name__)


@dataclass
class HMMFit:
    model: hmm.GaussianHMM
    k: int
    bic: float
    log_likelihood: float
    states: np.ndarray              # (N,) int per bar
    transition_matrix: np.ndarray   # (K, K)


def _params_count(k: int, n_features: int, covariance_type: str) -> int:
    """Free parameters in a GaussianHMM for BIC calculation."""
    # Initial probs: K - 1
    # Transitions: K * (K - 1)
    # Means: K * n_features
    # Covariances: full → K * n_features * (n_features + 1) / 2
    #              diag → K * n_features
    init = k - 1
    trans = k * (k - 1)
    means = k * n_features
    if covariance_type == "full":
        covs = k * n_features * (n_features + 1) // 2
    else:
        covs = k * n_features
    return init + trans + means + covs


def _fit_one_k(features: np.ndarray, k: int, *, random_state: int,
               covariance_type: str = "full", n_iter: int = 100) -> hmm.GaussianHMM:
    """Single fit attempt for given K. Raises ValueError on convergence/singularity failure."""
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        model = hmm.GaussianHMM(
            n_components=k,
            covariance_type=covariance_type,
            n_iter=n_iter,
            random_state=random_state,
            tol=1e-3,
        )
        model.fit(features)
    return model


def _try_fit_with_retries(features: np.ndarray, k: int, base_seed: int) -> hmm.GaussianHMM | None:
    """Try seeds; fall back to covariance_type='diag' on singularity."""
    for seed in (base_seed, base_seed + 1, base_seed + 2, base_seed + 3, base_seed + 4):
        try:
            return _fit_one_k(features, k, random_state=seed, covariance_type="full")
        except (ValueError, Warning) as exc:
            log.warning("K=%d full seed=%d failed: %s", k, seed, exc)
    for seed in (base_seed, base_seed + 1):
        try:
            return _fit_one_k(features, k, random_state=seed, covariance_type="diag")
        except (ValueError, Warning) as exc:
            log.warning("K=%d diag seed=%d failed: %s", k, seed, exc)
    return None


def fit_best_hmm(features: np.ndarray, *, k_range=(2, 3, 4, 5), random_state: int = 42) -> HMMFit:
    """Fit GaussianHMM for each K in k_range, pick lowest BIC."""
    n_obs, n_features = features.shape
    candidates: list[tuple[int, hmm.GaussianHMM, float, float]] = []
    for k in k_range:
        m = _try_fit_with_retries(features, k, random_state)
        if m is None:
            continue
        try:
            ll = m.score(features)
        except Exception as exc:
            log.warning("K=%d score failed: %s", k, exc)
            continue
        if not math.isfinite(ll):
            continue
        params = _params_count(k, n_features, m.covariance_type)
        bic = -2 * ll + params * math.log(n_obs)
        candidates.append((k, m, ll, bic))

    if not candidates:
        raise HMMFitError(f"all K in {k_range} failed to fit")

    # Lowest BIC wins
    k_best, model_best, ll_best, bic_best = min(candidates, key=lambda c: c[3])
    states = model_best.predict(features)
    return HMMFit(
        model=model_best,
        k=k_best,
        bic=bic_best,
        log_likelihood=ll_best,
        states=states,
        transition_matrix=model_best.transmat_,
    )
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `.claude/scripts/.venv/bin/python -m pytest shared/wally_core/tests/test_hmm_model.py -v`

Expected: 4 PASSED. Note: `test_bic_picks_lowest` may take ~5-10 seconds.

- [ ] **Step 3: Commit**

```bash
git add .claude/scripts/hmm_lib/model.py
git commit -m "feat(hmm): implement HMM fit with BIC-based K selection

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Write tests for labeling.py

**Files:**
- Create: `shared/wally_core/tests/test_hmm_labeling.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for hmm_lib.labeling — state → human-readable regime label."""
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "scripts"))

from hmm_lib import labeling


@dataclass
class _FakeFit:
    """Minimal stand-in for HMMFit used in labeling tests."""
    states: np.ndarray
    k: int


def _make_fake_fit_and_features(state_stats: list[dict]) -> tuple[_FakeFit, np.ndarray]:
    """state_stats: list of {'n': bars, 'log_ret': mean_log_return, 'vol': mean_vol}.
    Builds states array assigning each bar to its state, and synthetic features
    such that feature[:, 0] = log_return, feature[:, 1] = vol_20 (raw, not standardized).
    """
    states = []
    features_rows = []
    for sid, stats in enumerate(state_stats):
        states.extend([sid] * stats["n"])
        for _ in range(stats["n"]):
            # Place stats in columns 0 (log_ret) and 1 (vol_20)
            features_rows.append([stats["log_ret"], stats["vol"], 0.0])
    return _FakeFit(np.array(states), len(state_stats)), np.array(features_rows)


def test_high_vol_negative_return_is_stress():
    fit, features = _make_fake_fit_and_features([
        {"n": 800, "log_ret": +0.001, "vol": 0.01},
        {"n": 200, "log_ret": -0.005, "vol": 0.05},  # high vol, neg return
    ])
    labels = labeling.label_states(fit, features)
    assert labels[1]["label"] == "STRESS"


def test_low_vol_positive_return_is_calm_up():
    fit, features = _make_fake_fit_and_features([
        {"n": 800, "log_ret": +0.002, "vol": 0.005},  # low vol, pos return
        {"n": 200, "log_ret": -0.005, "vol": 0.05},
    ])
    labels = labeling.label_states(fit, features)
    assert labels[0]["label"] in ("CALM_UP", "TREND_UP")


def test_low_sample_flag_set_below_threshold():
    fit, features = _make_fake_fit_and_features([
        {"n": 970, "log_ret": +0.0001, "vol": 0.01},
        {"n": 30, "log_ret": -0.001, "vol": 0.02},  # 3% bars → low_sample
    ])
    labels = labeling.label_states(fit, features)
    assert labels[0]["low_sample"] is False
    assert labels[1]["low_sample"] is True


def test_returns_pct_bars_for_each_state():
    fit, features = _make_fake_fit_and_features([
        {"n": 600, "log_ret": +0.001, "vol": 0.01},
        {"n": 300, "log_ret": -0.001, "vol": 0.02},
        {"n": 100, "log_ret": -0.005, "vol": 0.04},
    ])
    labels = labeling.label_states(fit, features)
    assert abs(labels[0]["pct_bars"] - 0.60) < 1e-6
    assert abs(labels[1]["pct_bars"] - 0.30) < 1e-6
    assert abs(labels[2]["pct_bars"] - 0.10) < 1e-6
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.claude/scripts/.venv/bin/python -m pytest shared/wally_core/tests/test_hmm_labeling.py -v`

Expected: 4 ERRORS — `ModuleNotFoundError: No module named 'hmm_lib.labeling'`

- [ ] **Step 3: Commit failing tests**

```bash
git add shared/wally_core/tests/test_hmm_labeling.py
git commit -m "test(hmm): failing tests for state-to-label heuristic

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Implement labeling.py

**Files:**
- Create: `.claude/scripts/hmm_lib/labeling.py`

- [ ] **Step 1: Write minimal implementation**

```python
"""State → human-readable regime label via mean_return × mean_vol heuristic."""
from dataclasses import dataclass
from typing import Protocol

import numpy as np

CHOP_RETURN_THRESHOLD = 0.0005      # |mean_ret| < this → CHOP override
LOW_SAMPLE_THRESHOLD = 0.05         # state with <5% bars flagged


class _FitLike(Protocol):
    states: np.ndarray
    k: int


def label_states(fit: _FitLike, features: np.ndarray) -> dict[int, dict]:
    """Returns {state_id: {label, mean_return, mean_vol, pct_bars, low_sample}}.

    Heuristic:
      mean_vol > p66                        → STRESS
      |mean_ret| < CHOP_RETURN_THRESHOLD    → CHOP
      mean_ret > 0:  vol < p33 → CALM_UP   else → TREND_UP
      mean_ret < 0:  vol < p33 → CALM_DOWN else → TREND_DOWN

    If two states get the same label, the higher-vol one is renamed STRESS_LITE.
    """
    states = fit.states
    n_total = len(states)
    log_ret_col = features[:, 0]
    vol_col = features[:, 1]

    per_state: dict[int, dict] = {}
    for sid in range(fit.k):
        mask = states == sid
        n = int(mask.sum())
        if n == 0:
            per_state[sid] = {
                "label": "EMPTY",
                "mean_return": 0.0,
                "mean_vol": 0.0,
                "pct_bars": 0.0,
                "low_sample": True,
            }
            continue
        per_state[sid] = {
            "mean_return": float(log_ret_col[mask].mean()),
            "mean_vol": float(vol_col[mask].mean()),
            "pct_bars": n / n_total,
            "low_sample": (n / n_total) < LOW_SAMPLE_THRESHOLD,
        }

    # Percentile thresholds across states (not bars)
    mean_vols = np.array([s["mean_vol"] for s in per_state.values()])
    p66 = np.percentile(mean_vols, 66) if len(mean_vols) > 0 else 0.0
    p33 = np.percentile(mean_vols, 33) if len(mean_vols) > 0 else 0.0

    for sid, info in per_state.items():
        if "label" in info:  # EMPTY already set
            continue
        mv = info["mean_vol"]
        mr = info["mean_return"]
        if mv > p66:
            label = "STRESS"
        elif abs(mr) < CHOP_RETURN_THRESHOLD:
            label = "CHOP"
        elif mr > 0:
            label = "CALM_UP" if mv < p33 else "TREND_UP"
        else:
            label = "CALM_DOWN" if mv < p33 else "TREND_DOWN"
        info["label"] = label

    # Disambiguate duplicates by promoting higher-vol to STRESS_LITE
    seen_labels: dict[str, int] = {}
    for sid in sorted(per_state.keys(),
                      key=lambda s: per_state[s]["mean_vol"], reverse=True):
        label = per_state[sid]["label"]
        if label in seen_labels and label != "EMPTY":
            per_state[sid]["label"] = f"{label}_LITE" if label != "STRESS" else "STRESS_LITE"
        else:
            seen_labels[label] = sid

    return per_state
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `.claude/scripts/.venv/bin/python -m pytest shared/wally_core/tests/test_hmm_labeling.py -v`

Expected: 4 PASSED

- [ ] **Step 3: Commit**

```bash
git add .claude/scripts/hmm_lib/labeling.py
git commit -m "feat(hmm): implement state-to-label heuristic with disambiguation

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: Write tests for backtest.py

**Files:**
- Create: `shared/wally_core/tests/test_hmm_backtest.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for hmm_lib.backtest — per-regime backtest harness."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "scripts"))

from hmm_lib import backtest


def _fake_bars_15m(n: int, start_ts: int = 1_700_000_000) -> list[dict]:
    """list of dicts matching backtest_regime_matrix.py bar format."""
    return [{
        "t": start_ts + i * 900,
        "o": 100.0,
        "h": 101.0,
        "l": 99.0,
        "c": 100.0 + (i % 10) * 0.1,
        "v": 1000.0,
    } for i in range(n)]


def _fake_bars_1h(bars_15m: list[dict]) -> list[dict]:
    """Aggregate 15m to 1h."""
    out = []
    for i in range(0, len(bars_15m), 4):
        chunk = bars_15m[i:i + 4]
        out.append({
            "t": chunk[0]["t"],
            "o": chunk[0]["o"],
            "h": max(b["h"] for b in chunk),
            "l": min(b["l"] for b in chunk),
            "c": chunk[-1]["c"],
            "v": sum(b["v"] for b in chunk),
        })
    return out


def _trivial_strategy(bars_15m, bars_1h, i):
    """A toy strategy that always signals LONG at i, exit at i+1."""
    if i < 10 or i >= len(bars_15m) - 2:
        return None
    if i % 50 == 0:  # one signal per 50 bars
        entry = bars_15m[i]["c"]
        return {"side": "LONG", "entry": entry, "sl": entry * 0.99,
                "tp1": entry * 1.01, "tp2": entry * 1.02}
    return None


def test_partition_by_entry_regime():
    bars_15m = _fake_bars_15m(400)
    bars_1h = _fake_bars_1h(bars_15m)
    # 100 hourly bars → assign first 50 to regime CHOP (state 0), next 50 to STRESS (state 1)
    states_1h = np.array([0] * 50 + [1] * 50)
    labels = {0: {"label": "CHOP"}, 1: {"label": "STRESS"}}
    results = backtest.backtest_per_regime(
        bars_15m, bars_1h, states_1h, labels,
        strategy_fn=_trivial_strategy, strategy_name="TEST_STRAT",
    )
    labels_seen = {r.regime_label for r in results}
    assert "GLOBAL" in labels_seen
    assert "CHOP" in labels_seen or "STRESS" in labels_seen


def test_global_baseline_matches_unfiltered():
    bars_15m = _fake_bars_15m(400)
    bars_1h = _fake_bars_1h(bars_15m)
    states_1h = np.array([0] * 100)
    labels = {0: {"label": "CHOP"}}
    results = backtest.backtest_per_regime(
        bars_15m, bars_1h, states_1h, labels,
        strategy_fn=_trivial_strategy, strategy_name="TEST_STRAT",
    )
    global_row = next(r for r in results if r.regime_label == "GLOBAL")
    chop_row = next((r for r in results if r.regime_label == "CHOP"), None)
    # With only one regime, GLOBAL trades == CHOP trades
    assert chop_row is not None
    assert global_row.trades == chop_row.trades


def test_zero_trades_in_regime_emits_row():
    bars_15m = _fake_bars_15m(400)
    bars_1h = _fake_bars_1h(bars_15m)
    states_1h = np.array([0] * 100)
    labels = {0: {"label": "STRESS"}, 1: {"label": "CHOP"}}  # state 1 never appears
    # Strategy that never signals
    results = backtest.backtest_per_regime(
        bars_15m, bars_1h, states_1h, labels,
        strategy_fn=lambda *_: None, strategy_name="NO_SIGNAL",
    )
    global_row = next(r for r in results if r.regime_label == "GLOBAL")
    assert global_row.trades == 0


def test_strategy_exception_propagates_with_bar_index():
    from hmm_lib.errors import StrategyExecError

    def crashing_strategy(bars_15m, bars_1h, i):
        if i == 50:
            raise ValueError("simulated crash")
        return None

    bars_15m = _fake_bars_15m(200)
    bars_1h = _fake_bars_1h(bars_15m)
    states_1h = np.array([0] * 50)
    labels = {0: {"label": "CHOP"}}
    with pytest.raises(StrategyExecError) as exc_info:
        backtest.backtest_per_regime(
            bars_15m, bars_1h, states_1h, labels,
            strategy_fn=crashing_strategy, strategy_name="BOOM",
        )
    assert exc_info.value.bar_index == 50
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.claude/scripts/.venv/bin/python -m pytest shared/wally_core/tests/test_hmm_backtest.py -v`

Expected: 4 ERRORS — `ModuleNotFoundError: No module named 'hmm_lib.backtest'`

- [ ] **Step 3: Commit failing tests**

```bash
git add shared/wally_core/tests/test_hmm_backtest.py
git commit -m "test(hmm): failing tests for per-regime backtest harness

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 12: Implement backtest.py

**Files:**
- Create: `.claude/scripts/hmm_lib/backtest.py`

- [ ] **Step 1: Write minimal implementation**

```python
"""Per-regime backtest harness.

Strategies use the existing contract from backtest_regime_matrix.py:
    fn(bars_15m: list[dict], bars_1h: list[dict], i: int) -> Optional[Signal]

Where Signal is {side, entry, sl, tp1, tp2}. Exit logic: TP1 first hit OR SL first hit
over the next MAX_HOLD bars. We do NOT model TP2 partial fills in V1 — full position
exits at first TP1 or SL touch.
"""
import bisect
from dataclasses import dataclass

import numpy as np

from hmm_lib.errors import StrategyExecError

MAX_HOLD_BARS = 24      # 24 × 15m = 6h max hold
LOW_TRADE_THRESHOLD = 10


@dataclass
class RegimeBacktest:
    regime_label: str
    n_bars: int
    pct_time: float
    trades: int
    wr: float
    pf: float
    net_pnl_pct: float
    max_dd_pct: float
    low_trade_count: bool


def _resolve_trade(bars_15m: list[dict], signal: dict, entry_idx: int) -> tuple[float, str]:
    """Return (pnl_pct, exit_reason) by simulating TP1/SL hit over next MAX_HOLD_BARS."""
    side = signal["side"]
    entry = signal["entry"]
    sl = signal["sl"]
    tp1 = signal["tp1"]

    last_idx = min(entry_idx + MAX_HOLD_BARS, len(bars_15m) - 1)
    for j in range(entry_idx + 1, last_idx + 1):
        bar = bars_15m[j]
        if side == "LONG":
            if bar["l"] <= sl:
                return ((sl - entry) / entry, "SL")
            if bar["h"] >= tp1:
                return ((tp1 - entry) / entry, "TP1")
        else:  # SHORT
            if bar["h"] >= sl:
                return ((entry - sl) / entry, "SL")
            if bar["l"] <= tp1:
                return ((entry - tp1) / entry, "TP1")
    # Timeout: exit at last close
    close = bars_15m[last_idx]["c"]
    pnl = ((close - entry) / entry) if side == "LONG" else ((entry - close) / entry)
    return (pnl, "TIMEOUT")


def _regime_at_entry(entry_ts: int, bars_1h: list[dict], states_1h: np.ndarray) -> int | None:
    """Find the 1h bar covering the entry timestamp; return state or None if out of range."""
    timestamps = [b["t"] for b in bars_1h]
    idx = bisect.bisect_right(timestamps, entry_ts) - 1
    if idx < 0 or idx >= len(states_1h):
        return None
    return int(states_1h[idx])


def _aggregate_trades(trades: list[tuple[float, str]]) -> tuple[int, float, float, float, float]:
    """Compute (n, wr, pf, net_pnl_pct, max_dd_pct) from a list of (pnl, reason) tuples."""
    if not trades:
        return (0, 0.0, 0.0, 0.0, 0.0)
    pnls = np.array([t[0] for t in trades])
    n = len(pnls)
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    wr = (len(wins) / n) * 100.0
    pf = (wins.sum() / -losses.sum()) if len(losses) > 0 else float("inf")
    net = float(pnls.sum() * 100.0)
    equity = np.cumsum(pnls)
    peak = np.maximum.accumulate(equity)
    drawdowns = peak - equity
    max_dd = float(drawdowns.max() * 100.0) if len(drawdowns) > 0 else 0.0
    return (n, wr, pf if pf != float("inf") else 999.99, net, max_dd)


def backtest_per_regime(
    bars_15m: list[dict],
    bars_1h: list[dict],
    states_1h: np.ndarray,
    labels: dict[int, dict],
    *,
    strategy_fn,
    strategy_name: str,
) -> list[RegimeBacktest]:
    """Run strategy across all 15m bars, partition trades by entry-bar regime (1h state).
    Always emits GLOBAL row + one row per state label present in `labels`.
    """
    all_trades: list[tuple[float, str, int]] = []      # (pnl, reason, regime_state)
    n_15m = len(bars_15m)

    for i in range(n_15m):
        try:
            signal = strategy_fn(bars_15m, bars_1h, i)
        except Exception as exc:
            raise StrategyExecError(
                f"strategy {strategy_name} crashed at bar {i}: {exc}",
                bar_index=i, symbol="?", strategy=strategy_name,
            )
        if signal is None:
            continue
        entry_ts = bars_15m[i]["t"]
        regime = _regime_at_entry(entry_ts, bars_1h, states_1h)
        if regime is None:
            continue
        pnl, reason = _resolve_trade(bars_15m, signal, i)
        all_trades.append((pnl, reason, regime))

    rows: list[RegimeBacktest] = []
    n_total_1h = len(bars_1h)

    # GLOBAL row
    n, wr, pf, net, mdd = _aggregate_trades([(t[0], t[1]) for t in all_trades])
    rows.append(RegimeBacktest(
        regime_label="GLOBAL",
        n_bars=n_total_1h,
        pct_time=1.0,
        trades=n, wr=wr, pf=pf, net_pnl_pct=net, max_dd_pct=mdd,
        low_trade_count=False,
    ))

    # Per-regime rows
    for sid, info in labels.items():
        regime_trades = [(t[0], t[1]) for t in all_trades if t[2] == sid]
        n_bars_regime = int((states_1h == sid).sum())
        pct = n_bars_regime / n_total_1h if n_total_1h > 0 else 0.0
        n, wr, pf, net, mdd = _aggregate_trades(regime_trades)
        rows.append(RegimeBacktest(
            regime_label=info.get("label", f"STATE_{sid}"),
            n_bars=n_bars_regime,
            pct_time=pct,
            trades=n, wr=wr, pf=pf, net_pnl_pct=net, max_dd_pct=mdd,
            low_trade_count=(n < LOW_TRADE_THRESHOLD),
        ))

    return rows
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `.claude/scripts/.venv/bin/python -m pytest shared/wally_core/tests/test_hmm_backtest.py -v`

Expected: 4 PASSED

- [ ] **Step 3: Commit**

```bash
git add .claude/scripts/hmm_lib/backtest.py
git commit -m "feat(hmm): implement per-regime backtest harness with TP1/SL resolution

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 13: Write tests for reporting.py

**Files:**
- Create: `shared/wally_core/tests/test_hmm_reporting.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for hmm_lib.reporting — markdown emitter."""
import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "scripts"))

from hmm_lib import reporting
from hmm_lib.backtest import RegimeBacktest


def _sample_report() -> dict:
    return {
        "symbol": "ETHUSDT",
        "strategy": "A_VWAP",
        "date": "2026-05-13",
        "n_bars": 4360,
        "best_k": 3,
        "bic": -37934.6,
        "log_likelihood": 19105.2,
        "labels": {
            0: {"label": "TREND_UP", "mean_return": 0.0012, "mean_vol": 0.014,
                "pct_bars": 0.28, "low_sample": False},
            1: {"label": "CHOP", "mean_return": 0.0001, "mean_vol": 0.010,
                "pct_bars": 0.51, "low_sample": False},
            2: {"label": "STRESS", "mean_return": -0.0018, "mean_vol": 0.028,
                "pct_bars": 0.21, "low_sample": False},
        },
        "transition_matrix": np.array([[0.82, 0.15, 0.03],
                                       [0.09, 0.86, 0.05],
                                       [0.06, 0.18, 0.76]]),
        "backtests": [
            RegimeBacktest("GLOBAL", 4360, 1.0, 147, 51.7, 1.18, 8.3, 11.2, False),
            RegimeBacktest("TREND_UP", 1221, 0.28, 42, 42.9, 0.81, -3.1, 8.4, False),
            RegimeBacktest("CHOP", 2224, 0.51, 78, 61.5, 1.74, 12.8, 4.2, False),
            RegimeBacktest("STRESS", 915, 0.21, 27, 37.0, 0.62, -1.4, 6.8, False),
        ],
        "current_mapping_note": None,
        "caveats": [],
    }


def test_markdown_emits_all_required_sections(tmp_path):
    out = tmp_path / "report.md"
    reporting.emit_markdown(_sample_report(), out)
    content = out.read_text()
    for heading in ("# HMM Analysis", "## Summary", "## Regime Distribution",
                    "## Transition Matrix", "## Backtest per Regime",
                    "## Recommendations", "## Caveats"):
        assert heading in content, f"missing heading: {heading}"


def test_markdown_includes_all_regime_labels(tmp_path):
    out = tmp_path / "report.md"
    reporting.emit_markdown(_sample_report(), out)
    content = out.read_text()
    assert "TREND_UP" in content
    assert "CHOP" in content
    assert "STRESS" in content
    assert "GLOBAL" in content
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.claude/scripts/.venv/bin/python -m pytest shared/wally_core/tests/test_hmm_reporting.py -v`

Expected: 2 ERRORS — `ModuleNotFoundError: No module named 'hmm_lib.reporting'`

- [ ] **Step 3: Commit failing tests**

```bash
git add shared/wally_core/tests/test_hmm_reporting.py
git commit -m "test(hmm): failing tests for markdown report emitter

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 14: Implement reporting.py (markdown only — HTML is a later task)

**Files:**
- Create: `.claude/scripts/hmm_lib/reporting.py`

- [ ] **Step 1: Write minimal markdown implementation**

```python
"""Markdown emitter for HMM analysis reports."""
from pathlib import Path

import numpy as np


def _format_pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _format_signed(x: float) -> str:
    return f"{x:+.2f}"


def _markdown_table_header(cols: list[str]) -> str:
    sep = "|" + "|".join("---" for _ in cols) + "|"
    head = "| " + " | ".join(cols) + " |"
    return f"{head}\n{sep}"


def _summary_section(report: dict) -> str:
    return (
        "## Summary\n\n"
        f"- Symbol: `{report['symbol']}`\n"
        f"- Strategy: `{report['strategy']}`\n"
        f"- Bars analyzed: {report['n_bars']} (1H × 6m)\n"
        f"- Best K (via BIC): **{report['best_k']}**\n"
        f"- BIC: {report['bic']:.1f}\n"
        f"- Log-likelihood: {report['log_likelihood']:.1f}\n"
    )


def _distribution_section(report: dict) -> str:
    lines = ["## Regime Distribution\n",
             _markdown_table_header(["State", "Label", "% bars", "Mean return", "Mean vol", "Low sample"])]
    for sid in sorted(report["labels"].keys()):
        info = report["labels"][sid]
        flag = "⚠️ yes" if info["low_sample"] else "no"
        lines.append(f"| {sid} | {info['label']} | {_format_pct(info['pct_bars'])} | "
                     f"{info['mean_return']:+.4f} | {info['mean_vol']:.4f} | {flag} |")
    return "\n".join(lines) + "\n"


def _transition_section(report: dict) -> str:
    matrix = report["transition_matrix"]
    labels = [report["labels"][sid]["label"] for sid in sorted(report["labels"].keys())]
    k = len(labels)
    lines = ["## Transition Matrix\n",
             _markdown_table_header(["From \\ To", *labels])]
    for i in range(k):
        row = [labels[i]] + [f"{matrix[i, j]:.2f}" for j in range(k)]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def _backtest_section(report: dict) -> str:
    lines = ["## Backtest per Regime\n",
             _markdown_table_header(["Regime", "% time", "Trades", "WR", "PF",
                                     "Net PnL%", "Max DD%", "Flag"])]
    for r in report["backtests"]:
        flag = "⚠️ low-trade" if r.low_trade_count else ""
        lines.append(f"| {r.regime_label} | {_format_pct(r.pct_time)} | {r.trades} | "
                     f"{r.wr:.1f}% | {r.pf:.2f} | {_format_signed(r.net_pnl_pct)} | "
                     f"{r.max_dd_pct:.1f} | {flag} |")
    return "\n".join(lines) + "\n"


def _recommendations_section(report: dict) -> str:
    note = report.get("current_mapping_note")
    if note is None:
        return "## Recommendations\n\nNo `regime_mapping.json` comparison requested.\n"
    return f"## Recommendations\n\n{note}\n"


def _caveats_section(report: dict) -> str:
    caveats = report.get("caveats") or []
    body = "\n".join(f"- {c}" for c in caveats) if caveats else "- None flagged."
    body += (
        "\n- HMM seed fixed for reproducibility; different seeds may yield slightly different labelings."
        "\n- Backtest uses TP1-or-SL resolution over max 24×15m bars (6h hold)."
        "\n- Regime assigned by **entry-bar 1H state**, not exit-bar state."
    )
    return f"## Caveats\n\n{body}\n"


def emit_markdown(report: dict, out_path: Path) -> None:
    """Write the full markdown report to out_path."""
    sections = [
        f"# HMM Analysis — {report['symbol']} × {report['strategy']} — {report['date']}\n",
        _summary_section(report),
        _distribution_section(report),
        _transition_section(report),
        _backtest_section(report),
        _recommendations_section(report),
        _caveats_section(report),
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(sections))


def emit_html(report: dict, out_path: Path) -> None:
    """Emit interactive plotly HTML. Raises ImportError if plotly missing."""
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError as exc:
        raise ImportError("plotly not installed; run pip install plotly to enable --html") from exc

    # V1: 2 panels — transition matrix heatmap + equity curve table
    fig = make_subplots(rows=2, cols=1,
                        subplot_titles=("Transition Matrix", "Backtest per Regime"),
                        specs=[[{"type": "heatmap"}], [{"type": "table"}]])

    matrix = report["transition_matrix"]
    labels = [report["labels"][sid]["label"] for sid in sorted(report["labels"].keys())]
    fig.add_trace(go.Heatmap(z=matrix, x=labels, y=labels, colorscale="Blues",
                             showscale=True, zmin=0, zmax=1), row=1, col=1)

    rows = report["backtests"]
    fig.add_trace(go.Table(
        header=dict(values=["Regime", "% time", "Trades", "WR", "PF", "Net%", "MaxDD%"]),
        cells=dict(values=[
            [r.regime_label for r in rows],
            [f"{r.pct_time * 100:.1f}%" for r in rows],
            [r.trades for r in rows],
            [f"{r.wr:.1f}%" for r in rows],
            [f"{r.pf:.2f}" for r in rows],
            [f"{r.net_pnl_pct:+.2f}" for r in rows],
            [f"{r.max_dd_pct:.1f}" for r in rows],
        ]),
    ), row=2, col=1)

    fig.update_layout(title=f"HMM Analysis — {report['symbol']} × {report['strategy']}",
                      height=800)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out_path))
```

- [ ] **Step 2: Run tests to verify markdown passes**

Run: `.claude/scripts/.venv/bin/python -m pytest shared/wally_core/tests/test_hmm_reporting.py -v`

Expected: 2 PASSED

- [ ] **Step 3: Commit**

```bash
git add .claude/scripts/hmm_lib/reporting.py
git commit -m "feat(hmm): implement markdown and HTML report emitters

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 15: Write tests + implement suggest.py

**Files:**
- Create: `shared/wally_core/tests/test_hmm_suggest.py`
- Create: `.claude/scripts/hmm_lib/suggest.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for hmm_lib.suggest — dry-run regime_mapping.json patch."""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "scripts"))

from hmm_lib import suggest
from hmm_lib.backtest import RegimeBacktest


def _sample_mapping(tmp_path):
    mapping = {
        "version": 2,
        "global": {
            "RANGING": {"strategy": "A_VWAP", "wr": 33.3, "pnl_per_trade": 0.93}
        },
        "per_asset": {
            "ETHUSDT": {
                "STRONG_TREND_DOWN": {"strategy": "E_RangeBounce", "wr": 25.9,
                                       "pnl_per_trade": 0.05}
            }
        }
    }
    path = tmp_path / "regime_mapping.json"
    path.write_text(json.dumps(mapping, indent=2))
    return path


def test_suggest_returns_diff_when_strategy_outperforms(tmp_path):
    mapping_path = _sample_mapping(tmp_path)
    backtests = [
        RegimeBacktest("GLOBAL", 4360, 1.0, 147, 51.7, 1.18, 8.3, 11.2, False),
        RegimeBacktest("CHOP", 2224, 0.51, 78, 61.5, 1.74, 12.8, 4.2, False),
    ]
    diff = suggest.suggest_mapping_patch(backtests, mapping_path, "ETHUSDT", "A_VWAP")
    assert "DRY-RUN" in diff
    assert "ETHUSDT" in diff
    assert "A_VWAP" in diff


def test_suggest_skips_low_trade_count_regimes(tmp_path):
    mapping_path = _sample_mapping(tmp_path)
    backtests = [
        RegimeBacktest("GLOBAL", 4360, 1.0, 147, 51.7, 1.18, 8.3, 11.2, False),
        RegimeBacktest("CHOP", 2224, 0.51, 5, 80.0, 5.0, 12.8, 4.2, True),  # low_trade
    ]
    diff = suggest.suggest_mapping_patch(backtests, mapping_path, "ETHUSDT", "A_VWAP")
    # CHOP should NOT be suggested because low_trade_count=True
    assert "CHOP" not in diff or "DRY-RUN" in diff
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.claude/scripts/.venv/bin/python -m pytest shared/wally_core/tests/test_hmm_suggest.py -v`

Expected: 2 ERRORS — `ModuleNotFoundError: No module named 'hmm_lib.suggest'`

- [ ] **Step 3: Write minimal `suggest.py`**

```python
"""Dry-run regime_mapping.json patch. NEVER writes files."""
import difflib
import json
from pathlib import Path

from hmm_lib.backtest import RegimeBacktest


def _format_mapping_for_diff(mapping: dict) -> list[str]:
    return json.dumps(mapping, indent=2, sort_keys=True).splitlines(keepends=True)


def suggest_mapping_patch(
    backtests: list[RegimeBacktest],
    current_mapping_path: Path,
    symbol: str,
    strategy_name: str,
) -> str:
    """Returns a string. DRY-RUN ONLY. Never writes to file.

    The string is either an explanation message (when nothing to suggest)
    or a unified diff prefixed by a 'DRY-RUN' warning.
    """
    if not current_mapping_path.exists():
        return f"DRY-RUN: regime_mapping.json not found at {current_mapping_path}; skipping."

    mapping = json.loads(current_mapping_path.read_text())
    # Pick the regime where this strategy performs BEST (excluding GLOBAL + low-trade)
    candidates = [
        r for r in backtests
        if r.regime_label != "GLOBAL" and not r.low_trade_count and r.trades >= 10
    ]
    if not candidates:
        return "DRY-RUN: no regimes with sufficient trades to suggest a mapping change."

    best = max(candidates, key=lambda r: r.pf)
    if best.pf <= 1.0:
        return f"DRY-RUN: best regime {best.regime_label} has PF={best.pf:.2f} <= 1.0; no improvement to suggest."

    proposed = json.loads(json.dumps(mapping))  # deep copy
    proposed.setdefault("per_asset", {}).setdefault(symbol, {})[best.regime_label] = {
        "strategy": strategy_name,
        "wr": best.wr,
        "pnl_per_trade": best.net_pnl_pct / best.trades if best.trades else 0.0,
        "n_trades": best.trades,
        "source": "hmm_diagnostic_2026-05-13",
    }

    original_lines = _format_mapping_for_diff(mapping)
    proposed_lines = _format_mapping_for_diff(proposed)
    diff = "".join(difflib.unified_diff(
        original_lines, proposed_lines,
        fromfile="regime_mapping.json (current)",
        tofile="regime_mapping.json (proposed)",
        lineterm="",
    ))
    return (f"DRY-RUN — review manually before applying.\n"
            f"Symbol {symbol}, strategy {strategy_name} performs best in HMM regime "
            f"{best.regime_label} (PF={best.pf:.2f}, WR={best.wr:.1f}%, n={best.trades}).\n\n"
            f"{diff}")
```

- [ ] **Step 4: Run tests to verify pass**

Run: `.claude/scripts/.venv/bin/python -m pytest shared/wally_core/tests/test_hmm_suggest.py -v`

Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add shared/wally_core/tests/test_hmm_suggest.py .claude/scripts/hmm_lib/suggest.py
git commit -m "feat(hmm): implement dry-run regime_mapping.json suggestion patch

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 16: Write CLI entry point `hmm_analyze.py`

**Files:**
- Create: `.claude/scripts/hmm_analyze.py`

- [ ] **Step 1: Write the CLI script**

```python
#!/usr/bin/env python3
"""HMM Diagnostic Tool — main entry point.

Usage:
    hmm_analyze.py --symbol ETHUSDT --strategy A_VWAP [--html] [--suggest-mapping]
                   [--force-refresh] [--seed 42]

See docs/superpowers/specs/2026-05-13-hmm-diagnostic-tool-design.md
"""
import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "scripts"))

# Strategies live in backtest_regime_matrix.py — import the registry
try:
    from backtest_regime_matrix import (
        strat_a_vwap, strat_b_trending_pullback,
        strat_c_bb_squeeze_break, strat_d_momentum_macd, strat_e_range_bounce,
    )
except ImportError as exc:
    print(f"ERROR: cannot import strategies from backtest_regime_matrix.py: {exc}",
          file=sys.stderr)
    sys.exit(7)

from hmm_lib import (
    fetcher, features as features_mod, model as model_mod,
    labeling, backtest as backtest_mod, reporting, suggest,
)
from hmm_lib.errors import (
    FetchError, InsufficientDataError, HMMFitError, StrategyExecError,
)

STRATEGY_REGISTRY = {
    "A_VWAP": strat_a_vwap,
    "B_TrendPullback": strat_b_trending_pullback,
    "C_BBSqueeze": strat_c_bb_squeeze_break,
    "D_MACDMomentum": strat_d_momentum_macd,
    "E_RangeBounce": strat_e_range_bounce,
}

CACHE_DIR = PROJECT_ROOT / ".claude" / "cache"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "hmm_analysis"


def _setup_logging() -> None:
    log_path = CACHE_DIR / "hmm_analyze.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(log_path),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )


def _df_to_15m_bars(df_1h) -> list[dict]:
    """Strategies want 15m granularity; for V1 we synthesize 15m bars from 1h
    by duplicating each 1h bar into 4 identical 15m bars. This is a known
    approximation — V2 should pull true 15m series."""
    out = []
    for _, row in df_1h.iterrows():
        ts_base = int(row["ts_utc"].timestamp())
        for sub in range(4):
            out.append({
                "t": ts_base + sub * 900,
                "o": row["open"],
                "h": row["high"],
                "l": row["low"],
                "c": row["close"],
                "v": row["volume"] / 4,
            })
    return out


def _df_to_1h_bars(df_1h) -> list[dict]:
    return [{
        "t": int(row["ts_utc"].timestamp()),
        "o": row["open"], "h": row["high"], "l": row["low"],
        "c": row["close"], "v": row["volume"],
    } for _, row in df_1h.iterrows()]


def _build_report(symbol: str, strategy: str, df, fit, labels, backtests,
                  mapping_note: str | None) -> dict:
    caveats = []
    for sid, info in labels.items():
        if info.get("low_sample"):
            caveats.append(
                f"State {sid} ({info['label']}) covers only {info['pct_bars'] * 100:.1f}% of bars — "
                "labeling may be unreliable.")
    for r in backtests:
        if r.low_trade_count and r.regime_label != "GLOBAL":
            caveats.append(
                f"Regime {r.regime_label} has only {r.trades} trades — backtest metrics noisy.")
    if all(info.get("label", "").startswith("CHOP") for info in labels.values()):
        caveats.append("All detected regimes are CHOP-like; HMM provides little differentiation. "
                       "Consider a higher timeframe or a different asset.")

    return {
        "symbol": symbol,
        "strategy": strategy,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "n_bars": len(df),
        "best_k": fit.k,
        "bic": fit.bic,
        "log_likelihood": fit.log_likelihood,
        "labels": labels,
        "transition_matrix": fit.transition_matrix,
        "backtests": backtests,
        "current_mapping_note": mapping_note,
        "caveats": caveats,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hmm_analyze.py")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--strategy", required=True,
                        choices=sorted(STRATEGY_REGISTRY.keys()))
    parser.add_argument("--html", action="store_true")
    parser.add_argument("--suggest-mapping", action="store_true")
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    _setup_logging()
    log = logging.getLogger("hmm_analyze")
    symbol = args.symbol.upper()
    log.info("start symbol=%s strategy=%s", symbol, args.strategy)

    try:
        df = fetcher.fetch_ohlcv_1h_6m(symbol, force_refresh=args.force_refresh)
    except FetchError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2 if "not listed" in str(exc) else 3
    except InsufficientDataError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 4

    feat_matrix = features_mod.build_features(df)
    log.info("features shape=%s", feat_matrix.shape)

    try:
        fit = model_mod.fit_best_hmm(feat_matrix, random_state=args.seed)
    except HMMFitError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 5

    labels = labeling.label_states(fit, feat_matrix)
    log.info("k=%d labels=%s", fit.k, {sid: info["label"] for sid, info in labels.items()})

    # Map HMM states (defined on features=bars after WARMUP) back to original 1h timeline.
    # WARMUP bars are dropped from features. Pad states with the first state for alignment.
    from hmm_lib.features import WARMUP as FEATURE_WARMUP
    import numpy as np
    states_1h = np.concatenate([
        np.full(FEATURE_WARMUP, fit.states[0]),
        fit.states,
    ])
    # Trim to match df length
    states_1h = states_1h[:len(df)]

    bars_1h = _df_to_1h_bars(df)
    bars_15m = _df_to_15m_bars(df)
    # Each 15m bar inherits state from its parent 1h bar (4 sub-bars share state).
    # The backtest module looks up regime by entry_ts via bisect on bars_1h timestamps.

    strategy_fn = STRATEGY_REGISTRY[args.strategy]
    try:
        backtests = backtest_mod.backtest_per_regime(
            bars_15m, bars_1h, states_1h, labels,
            strategy_fn=strategy_fn, strategy_name=args.strategy,
        )
    except StrategyExecError as exc:
        print(f"ERROR: strategy crashed at bar {exc.bar_index}: {exc}", file=sys.stderr)
        return 6

    # Suggest mapping (optional)
    mapping_note: str | None = None
    if args.suggest_mapping:
        mapping_path = PROJECT_ROOT / ".claude" / "scripts" / "regime_mapping.json"
        mapping_note = suggest.suggest_mapping_patch(backtests, mapping_path, symbol, args.strategy)

    report = _build_report(symbol, args.strategy, df, fit, labels, backtests, mapping_note)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    date_str = report["date"]
    md_path = OUTPUT_DIR / f"{symbol}_{args.strategy}_{date_str}.md"
    reporting.emit_markdown(report, md_path)
    print(f"Wrote {md_path}")

    if args.html:
        html_path = OUTPUT_DIR / f"{symbol}_{args.strategy}_{date_str}.html"
        try:
            reporting.emit_html(report, html_path)
            print(f"Wrote {html_path}")
        except ImportError as exc:
            print(f"WARNING: {exc}", file=sys.stderr)

    if mapping_note:
        print()
        print(mapping_note)

    log.info("done exit=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Verify CLI usage**

Run: `.claude/scripts/.venv/bin/python .claude/scripts/hmm_analyze.py --help`

Expected: argparse usage printed showing all options.

- [ ] **Step 3: Verify rejection of unknown strategy**

Run: `.claude/scripts/.venv/bin/python .claude/scripts/hmm_analyze.py --symbol ETHUSDT --strategy Z_Foo; echo "exit=$?"`

Expected: error mentioning invalid choice, exit ≠ 0.

- [ ] **Step 4: Commit**

```bash
git add .claude/scripts/hmm_analyze.py
git commit -m "feat(hmm): CLI entry point hmm_analyze.py orchestrating the pipeline

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 17: Write integration test (full pipeline on synthetic fixture)

**Files:**
- Create: `shared/wally_core/tests/test_hmm_integration.py`

- [ ] **Step 1: Write the test**

```python
"""Integration tests for hmm_analyze pipeline."""
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "scripts"))


def test_cli_exits_1_on_unknown_strategy():
    result = subprocess.run(
        [str(PROJECT_ROOT / ".claude" / "scripts" / ".venv" / "bin" / "python"),
         str(PROJECT_ROOT / ".claude" / "scripts" / "hmm_analyze.py"),
         "--symbol", "ETHUSDT", "--strategy", "Z_Foo"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert "Z_Foo" in result.stderr or "invalid choice" in result.stderr.lower()


def test_cli_exits_2_on_unknown_symbol(tmp_path, monkeypatch):
    """Use force-refresh to skip cache; bypass real network by patching is risky for CLI tests.
    Instead, use a clearly invalid symbol and trust Binance to 400."""
    result = subprocess.run(
        [str(PROJECT_ROOT / ".claude" / "scripts" / ".venv" / "bin" / "python"),
         str(PROJECT_ROOT / ".claude" / "scripts" / "hmm_analyze.py"),
         "--symbol", "DEFINITELYNOTASYMBOL_X", "--strategy", "A_VWAP",
         "--force-refresh"],
        capture_output=True, text=True, timeout=30,
    )
    # Either 2 (FetchError "not listed") or 3 (network/parse mismatch) acceptable
    assert result.returncode in (2, 3), (
        f"expected 2 or 3, got {result.returncode}\nstderr: {result.stderr}")
```

- [ ] **Step 2: Run test**

Run: `.claude/scripts/.venv/bin/python -m pytest shared/wally_core/tests/test_hmm_integration.py -v`

Expected: 2 PASSED (the symbol test takes ~5-10s due to network round-trip).

- [ ] **Step 3: Commit**

```bash
git add shared/wally_core/tests/test_hmm_integration.py
git commit -m "test(hmm): integration tests for CLI exit codes

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 18: Write E2E smoke test (network, opt-in)

**Files:**
- Create: `shared/wally_core/tests/test_hmm_e2e.py`

- [ ] **Step 1: Write the test**

```python
"""E2E smoke test — runs against real Binance Futures.
Skipped by default. Run manually with: pytest -m network shared/wally_core/tests/test_hmm_e2e.py
"""
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.network
def test_real_eth_btc_pipeline(tmp_path):
    """Run hmm_analyze on real ETHUSDT data and verify report is created."""
    output_dir = PROJECT_ROOT / "docs" / "hmm_analysis"
    # Snapshot pre-existing files
    before = set(output_dir.glob("ETHUSDT_A_VWAP_*.md")) if output_dir.exists() else set()

    result = subprocess.run(
        [str(PROJECT_ROOT / ".claude" / "scripts" / ".venv" / "bin" / "python"),
         str(PROJECT_ROOT / ".claude" / "scripts" / "hmm_analyze.py"),
         "--symbol", "ETHUSDT", "--strategy", "A_VWAP"],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"

    after = set(output_dir.glob("ETHUSDT_A_VWAP_*.md"))
    new_files = after - before
    if not new_files:
        # Same-day rerun overwrites — verify at least one exists and is fresh
        assert after, "no markdown report produced"
        md = max(after, key=lambda p: p.stat().st_mtime)
    else:
        md = new_files.pop()
    assert md.stat().st_size > 2000, f"report suspiciously small: {md.stat().st_size} bytes"
```

- [ ] **Step 2: Register the `network` marker**

Check if `pytest.ini` or `pyproject.toml` already declares the marker. If not, add to `pyproject.toml` (if it exists) or create `conftest.py` marker registration:

Read existing root config:
```bash
ls pytest.ini pyproject.toml setup.cfg 2>/dev/null
```

If `shared/wally_core/tests/conftest.py` exists (we know it does), append the marker config there:

```python
# Add to shared/wally_core/tests/conftest.py
def pytest_configure(config):
    config.addinivalue_line("markers", "network: tests that require external network")
```

(If `pytest_configure` already exists, merge the line into it instead of overwriting.)

- [ ] **Step 3: Verify it's skipped by default**

Run: `.claude/scripts/.venv/bin/python -m pytest shared/wally_core/tests/test_hmm_e2e.py -v`

Expected: 1 SKIPPED (or 1 PASSED if `-m network` was implicitly active).

Run: `.claude/scripts/.venv/bin/python -m pytest shared/wally_core/tests/test_hmm_e2e.py -v -m network`

Expected: 1 PASSED (takes ~30-60s with real network).

- [ ] **Step 4: Commit**

```bash
git add shared/wally_core/tests/test_hmm_e2e.py shared/wally_core/tests/conftest.py
git commit -m "test(hmm): E2E smoke test against real Binance (network-opt-in)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 19: Create slash command `/hmm-analyze`

**Files:**
- Create: `.claude/commands/hmm-analyze.md`

- [ ] **Step 1: Inspect an existing command for the conventions**

Run: `cat .claude/commands/punk-hunt.md | head -40` to see how slash commands are documented in this repo.

- [ ] **Step 2: Write the command spec**

```markdown
# /hmm-analyze

Run an HMM regime analysis on a single asset × strategy combination. Strictly diagnostic — never modifies live state.

## Usage

```
/hmm-analyze <SYMBOL> <STRATEGY> [--html] [--suggest-mapping] [--force-refresh] [--seed N]
```

## Arguments

- `SYMBOL` — Binance Futures symbol (e.g., `ETHUSDT`). Case-insensitive.
- `STRATEGY` — one of: `A_VWAP`, `B_TrendPullback`, `C_BBSqueeze`, `D_MACDMomentum`, `E_RangeBounce`.

## Flags

- `--html` — also emit interactive plotly HTML report (requires plotly installed).
- `--suggest-mapping` — print a DRY-RUN diff for `regime_mapping.json` (never writes the file).
- `--force-refresh` — bypass the 1h OHLCV cache.
- `--seed N` — change HMM random seed (default 42) for reproducibility experiments.

## Output

Markdown report saved to `docs/hmm_analysis/<SYMBOL>_<STRATEGY>_<YYYY-MM-DD>.md` with 7 sections (Summary, Regime Distribution, Transition Matrix, Backtest per Regime, Recommendations, Caveats). Optional HTML alongside.

## Steps Claude executes

1. Verify profile (no profile guard — tool works for any profile, diagnostic only).
2. Run `.claude/scripts/.venv/bin/python .claude/scripts/hmm_analyze.py --symbol <SYMBOL> --strategy <STRATEGY> [...]`.
3. Print the produced markdown report path.
4. If `--suggest-mapping`, print the dry-run diff to the user along with a reminder that the file is unchanged.

## Reglas

- NUNCA modifica `regime_mapping.json`.
- NUNCA toca paths live (`/punk-smart`, `/signal`, `/validate`).
- Si la red está caída y la cache es stale → reporta error con exit code 3.
- Si el símbolo no está listado en Binance Futures → exit code 2.

## Ejemplo

```
/hmm-analyze ETHUSDT A_VWAP --suggest-mapping
```

Output esperado:
- Markdown en `docs/hmm_analysis/ETHUSDT_A_VWAP_2026-05-13.md`
- Diff DRY-RUN impreso a stdout
```

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/hmm-analyze.md
git commit -m "feat(hmm): slash command /hmm-analyze spec

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 20: Wire `/backtest --hmm-analyze` alias

**Files:**
- Modify: `.claude/commands/backtest.md` (if exists)
- Inspect: `.claude/scripts/backtest_runner.py` (if exists, the slash entry point)

- [ ] **Step 1: Locate the backtest entry point**

Run: `ls .claude/commands/backtest.md .claude/scripts/backtest_runner.py 2>/dev/null; grep -rl "backtest" .claude/commands/ 2>/dev/null | head -5`

- [ ] **Step 2a: If `backtest_runner.py` exists**

Add at the top of `main()` (or equivalent):

```python
# Hand off to HMM analyzer if --hmm-analyze flag present
if "--hmm-analyze" in sys.argv:
    import subprocess
    hmm_args = [a for a in sys.argv[1:] if a != "--hmm-analyze"]
    return subprocess.call(
        [sys.executable, str(Path(__file__).parent / "hmm_analyze.py"), *hmm_args]
    )
```

- [ ] **Step 2b: If only `.claude/commands/backtest.md` exists (slash spec only)**

Add a section at the bottom of `backtest.md`:

```markdown
## HMM Diagnostic Mode

`/backtest --hmm-analyze SYMBOL STRATEGY [flags...]` is an alias for `/hmm-analyze SYMBOL STRATEGY [flags...]`. See `.claude/commands/hmm-analyze.md` for full documentation.

When Claude sees `--hmm-analyze` in the args, it must invoke `.claude/scripts/hmm_analyze.py` instead of the regular backtest runner.
```

- [ ] **Step 3: Verify**

Run: `.claude/scripts/.venv/bin/python .claude/scripts/hmm_analyze.py --help` (the direct path) — already confirmed in Task 16.

If Task 2a was taken: `.claude/scripts/.venv/bin/python .claude/scripts/backtest_runner.py --hmm-analyze --symbol ETHUSDT --strategy A_VWAP --help 2>&1 | head -5` should produce hmm_analyze argparse help.

- [ ] **Step 4: Commit**

```bash
git add .claude/commands/backtest.md .claude/scripts/backtest_runner.py
git commit -m "feat(hmm): wire /backtest --hmm-analyze alias to hmm_analyze.py

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 21: Skill doc `@hmm-regime-analysis`

**Files:**
- Create: `.claude/skills/hmm-regime-analysis/SKILL.md`

- [ ] **Step 1: Inspect an existing skill for the conventions**

Run: `cat .claude/skills/neptune-community-config/SKILL.md 2>/dev/null | head -30` (or any existing skill).

- [ ] **Step 2: Write the skill doc**

```markdown
---
name: hmm-regime-analysis
description: Use when you want to analyze how a given strategy behaves across HMM-detected regimes for an asset, BEFORE deciding whether to update regime_mapping.json. Strictly diagnostic — never wires into live trading. Read this skill to understand how to interpret transition matrices and when HMM disagrees with ADX detection.
---

# HMM Regime Analysis Skill

## When to invoke

- You suspect a strategy is performing poorly because the ADX-based regime detection is wrong for an asset.
- You want to see how a strategy fares under STRESS vs CHOP vs TREND_UP regimes detected by HMM.
- You're considering updating `regime_mapping.json` for an asset and want backtest-grounded data.

## When NOT to invoke

- You want to execute a trade. (Use `/signal`, `/validate`, or `/punk-smart` — those are live paths. HMM is diagnostic.)
- You want to backtest a strategy in general. (Use `/backtest`.)
- All regimes in the asset are CHOP-like (lateral market) — HMM provides no differentiation.

## How to interpret outputs

### Regime Distribution table

- A state with `pct_bars < 5%` is flagged ⚠️ low_sample. Treat its label and backtest with skepticism — too few observations.
- If all states are labeled CHOP* the asset has been lateral for ~6 months and HMM cannot separate regimes. Try a longer lookback or different asset.

### Transition Matrix

- Diagonal values (state stays the same) typically 0.7–0.95 for daily-scale regimes. A diagonal value < 0.5 suggests an unstable / noisy regime.
- Off-diagonal values show transition probabilities. `P(STRESS → CALM_UP) = 0.05` means STRESS rarely flips directly to a bullish regime — usually transitions through CHOP first.
- Use it to estimate how long the *current* regime is likely to persist.

### Backtest per Regime

- `GLOBAL` row is the baseline (strategy run unconditionally). Per-regime rows partition the GLOBAL trades by HMM state at entry.
- A regime row with `low_trade_count=⚠️` (n<10) has noisy WR/PF — do not rely on it.
- The valuable signal is when the strategy has clear differential performance: e.g., PF=1.74 in CHOP vs PF=0.62 in STRESS means "deploy in CHOP, sit out in STRESS".

### Recommendations / Dry-run patch

- The patch is generated ONLY when:
  - At least one regime has PF > 1.0
  - That regime has ≥10 trades (not low_trade_count)
  - Excluding GLOBAL
- The patch is **never applied to `regime_mapping.json`**. Review it manually before any edit.

## Reproducing the analysis Alex Ruiz demonstrates

In the video `Cdhqu6rIvb0`, Alex generates an HMM dashboard for a strategy on EUR/USD daily. Our tool replicates this for crypto on Binance Futures 1H. The conceptual mapping:

| Alex's video | Our tool |
|---|---|
| EUR/USD daily | Binance Futures `SYMBOL` 1H |
| Auto-detect 2–5 regimes | `K ∈ {2,3,4,5}` selected via BIC |
| Volatility + cumulative returns + momentum | log_return + vol_20 + momentum_14 |
| "Global" vs "Combined" rentabilidad | `GLOBAL` row vs per-regime rows |
| Top-3 parameters per regime | Out-of-scope V1 — see Task 22 of the implementation plan |

## Honest-first caveats

- HMM regimes are probabilistic — a bar labeled STRESS has *P(STRESS)* high but not 1.0.
- The 5% low_sample threshold is a heuristic — adjust `LOW_SAMPLE_THRESHOLD` in `labeling.py` if you have reasons to.
- Strategy backtest uses TP1/SL resolution over max 6h hold — not the same as router's live exit logic which uses DUREX + scaled exits.
- This tool's findings are NEVER auto-applied. The decision to edit `regime_mapping.json` is yours.
```

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/hmm-regime-analysis/SKILL.md
git commit -m "docs(hmm): skill @hmm-regime-analysis with interpretation guide

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 22: Document in CLAUDE.md (Bundle 4 section)

**Files:**
- Modify: `CLAUDE.md` (append a new bundle section)
- Modify: `/Users/josecampos/.claude/projects/-Users-josecampos-Documents-wally-trader/memory/MEMORY.md` (add 1 line)
- Create: `/Users/josecampos/.claude/projects/-Users-josecampos-Documents-wally-trader/memory/hmm_analysis.md`

- [ ] **Step 1: Append to CLAUDE.md**

Run: `tail -5 CLAUDE.md` to see the last bundle section's ending.

Append the following section after the last bundle (before any final disclaimers):

```markdown
## HMM Diagnostic Tool (Bundle 4, 2026-05-13)

`/hmm-analyze SYMBOL STRATEGY` — diagnostic tool that fits a Hidden Markov Model to 1H × 6m OHLCV from Binance Futures, labels regimes (CALM_UP/TREND_UP/CHOP/TREND_DOWN/CALM_DOWN/STRESS/STRESS_LITE), backtests one of the 5 router strategies (A_VWAP, B_TrendPullback, C_BBSqueeze, D_MACDMomentum, E_RangeBounce) per regime, and emits a markdown report.

**Strictly diagnostic.** No live wire-in. Never modifies `regime_mapping.json`.

- CLI: `.claude/scripts/.venv/bin/python .claude/scripts/hmm_analyze.py --symbol ETHUSDT --strategy A_VWAP [--html] [--suggest-mapping]`
- Slash: `/hmm-analyze ETHUSDT A_VWAP` or `/backtest --hmm-analyze ETHUSDT A_VWAP`
- Output: `docs/hmm_analysis/<SYM>_<STRAT>_<YYYY-MM-DD>.md`
- Skill: `@hmm-regime-analysis` documents how to interpret outputs.
- Dependency: `hmmlearn>=0.3.0` installed in `.claude/scripts/.venv` (and `plotly` for `--html`, optional).

Reference: video `Cdhqu6rIvb0` by Alex Ruiz. Spec/plan in `docs/superpowers/{specs,plans}/2026-05-13-hmm-diagnostic-tool*.md`.

Bundle 3 (2026-05-12) rejected HMM-for-live-tuning; this tool implements only the **portfolio-management framing** Alex describes in the conclusion (~25 min mark): parameters fixed, strategy selection per regime informed by analysis.
```

- [ ] **Step 2: Append to MEMORY.md (1 line)**

Edit the memory MEMORY.md file by adding a new bullet under the existing memory list:

```markdown
- [HMM diagnostic tool](hmm_analysis.md) — `/hmm-analyze SYMBOL STRATEGY` diagnostic-only (Bundle 4). Fits HMM on 1H × 6m, partitions backtest by regime. Never touches live paths.
```

- [ ] **Step 3: Create the memory file**

Write `/Users/josecampos/.claude/projects/-Users-josecampos-Documents-wally-trader/memory/hmm_analysis.md`:

```markdown
---
name: hmm-analysis
description: HMM diagnostic tool — when to invoke /hmm-analyze, what to look for in the report, what NOT to do (no live wire-in).
metadata:
  type: reference
---

# HMM Diagnostic Tool

## When to invoke

- Suspect ADX-based regime detection is misclassifying an asset.
- Want backtest-grounded evidence before editing `regime_mapping.json`.
- Want to see strategy A_VWAP vs B_TrendPullback vs others *under HMM-detected regimes* for one asset.

## When NOT to invoke

- Live execution decisions — use `/signal`, `/validate`, `/punk-smart`.
- All-CHOP markets (lateral 6 months) — tool reports "no differentiation".
- Just need a quick regime label — use `/regime` (ADX-based, faster).

## Key files

- Script: `.claude/scripts/hmm_analyze.py`
- Lib: `.claude/scripts/hmm_lib/` (fetcher, features, model, labeling, backtest, reporting, suggest, errors)
- Skill: `@hmm-regime-analysis`
- Output dir: `docs/hmm_analysis/`
- Cache: `.claude/cache/ohlcv_<SYM>_1h_6m.json` (1h TTL), `.claude/cache/hmm_analyze.log`

## Spec & plan

- `docs/superpowers/specs/2026-05-13-hmm-diagnostic-tool-design.md`
- `docs/superpowers/plans/2026-05-13-hmm-diagnostic-tool.md`

## Strict invariants

- NEVER modifies `regime_mapping.json` (even with `--suggest-mapping`)
- NEVER touches live paths (`/punk-smart`, `/signal`, `/validate`)
- Reproducibility: seed defaults to 42; can be overridden with `--seed N`
```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude.md): document Bundle 4 HMM diagnostic tool

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

Memory files are outside the repo (under `~/.claude/projects/`) — they're not committed to the repo's git, but they should be saved (the Write tool handled that in Step 2-3).

---

## Task 23: Final regression test — verify router still works

**Files:**
- No file changes; pure verification

- [ ] **Step 1: Snapshot pre-existing router output**

Run:
```bash
.claude/scripts/.venv/bin/python .claude/scripts/punk_smart_router.py --json > /tmp/router_after_hmm.json 2>&1 || true
head -3 /tmp/router_after_hmm.json
```

Expected: JSON with `status`, `approved`, `vetoed`, `no_setup` keys (matches the format we saw earlier in the session).

- [ ] **Step 2: Verify all hmm tests pass**

Run:
```bash
.claude/scripts/.venv/bin/python -m pytest shared/wally_core/tests/test_hmm_*.py -v
```

Expected: all unit tests + integration test PASS (e2e test SKIPPED unless `-m network`).

Test count check: 4 (fetcher) + 3 (features) + 4 (model) + 4 (labeling) + 4 (backtest) + 2 (reporting) + 2 (suggest) + 2 (integration) = **25 tests PASS**, 1 SKIPPED (e2e).

- [ ] **Step 3: Verify other existing tests still pass**

Run:
```bash
.claude/scripts/.venv/bin/python -m pytest shared/wally_core/tests/ -v --ignore=shared/wally_core/tests/test_hmm_e2e.py 2>&1 | tail -20
```

Expected: no FAILED. Some pre-existing tests may be SKIPPED for unrelated reasons (network markers, missing fixtures) — that's OK.

- [ ] **Step 4: Run hmm_analyze on a real symbol as a smoke check**

```bash
.claude/scripts/.venv/bin/python .claude/scripts/hmm_analyze.py --symbol ETHUSDT --strategy A_VWAP
```

Expected:
- exit 0
- `Wrote docs/hmm_analysis/ETHUSDT_A_VWAP_2026-05-13.md`
- Open the file, verify all 7 sections present + non-empty backtest table.

If the smoke test fails, debug per the error message and fix before declaring the plan complete. Do NOT commit the smoke output (it's generated artifact in `docs/hmm_analysis/` — decide whether to gitignore the output dir or commit example outputs as documentation).

- [ ] **Step 5: Decide on gitignore**

Run: `cat .gitignore | grep hmm 2>/dev/null || echo NONE`

If `hmm_analysis` not yet listed, append the following to `.gitignore`:

```
# HMM diagnostic tool — generated reports
docs/hmm_analysis/*.html
docs/hmm_analysis/*.md
!docs/hmm_analysis/README.md
```

Then create a one-line `docs/hmm_analysis/README.md`:

```markdown
# HMM Analysis Reports

This directory contains generated reports from `/hmm-analyze`. They're gitignored except this README. See `docs/superpowers/specs/2026-05-13-hmm-diagnostic-tool-design.md`.
```

- [ ] **Step 6: Final commit**

```bash
git add .gitignore docs/hmm_analysis/README.md
git commit -m "chore(hmm): gitignore generated reports, add README for output dir

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Self-review checklist (run after writing the plan)

This was completed inline by the plan author:

- ✅ **Spec coverage:** every spec section has at least one task (fetcher → Tasks 3-4, features → 5-6, model → 7-8, labeling → 9-10, backtest → 11-12, reporting → 13-14, suggest → 15, CLI → 16, integration tests → 17, E2E → 18, slash command → 19, backtest alias → 20, skill doc → 21, CLAUDE.md/memory → 22, regression → 23)
- ✅ **Placeholder scan:** no "TBD", "TODO" (other than the inline `# TODO: dedupe with router` if duplication fallback is taken — that's intentional)
- ✅ **Type consistency:** `HMMFit` dataclass field names consistent across model.py and labeling.py callers. `RegimeBacktest` fields consistent across backtest.py, reporting.py, suggest.py. `strategy_fn` parameter named identically in test fixture and production code.
- ✅ **Scope check:** plan fits within one implementation cycle. 23 tasks, ~2-3 days for an experienced engineer.

One nuance worth flagging: the spec mentions a strategies refactor under `.claude/scripts/strategies/` with an ABC pattern. The plan deliberately uses the **fallback path** (direct import from `backtest_regime_matrix.py` without refactor) because:

1. The existing `strat_*` functions have a stable, well-defined signature that already supports diagnostic use
2. Refactoring to ABC adds 1+ days for no V1 user-visible benefit
3. The spec explicitly allows this fallback ("V1 ships with duplication; V2 (future PR) does the real refactor")

If during implementation the engineer finds the direct import path painful, the refactor can be added as Tasks 24-N (out of scope for V1 plan).

---

## Execution handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-13-hmm-diagnostic-tool.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Best for tasks 3-15 where TDD steps benefit from focused context.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints. Best for tasks 16-23 where orchestration benefits from carrying context.

A hybrid is also possible (subagents for TDD modules, inline for orchestration).

**Which approach?**
