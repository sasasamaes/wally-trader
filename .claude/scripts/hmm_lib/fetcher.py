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

    # Dedupe by open_time (first field), sort, trim to TARGET_BARS most recent
    seen: dict = {}
    for r in all_rows:
        seen[r[0]] = r
    rows_sorted = [seen[k] for k in sorted(seen.keys())][-TARGET_BARS:]

    if len(rows_sorted) < MIN_BARS:
        raise InsufficientDataError(
            f"only {len(rows_sorted)} bars available for {symbol}, need >= {MIN_BARS}")

    cache.write_text(json.dumps({
        "ts_saved": _now_iso(),
        "symbol": symbol,
        "rows": rows_sorted,
    }))

    return _rows_to_df(rows_sorted)
