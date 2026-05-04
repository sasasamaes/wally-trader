"""HTTP client for Polymarket Gamma API with CLOB fallback.

Pure HTTP. No business logic. Returns typed Market dataclasses.
"""
from __future__ import annotations

import json
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


def _coerce_list(value: Any, default: list) -> list:
    """Polymarket Gamma sometimes returns lists as JSON-encoded strings."""
    if value is None:
        return default
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else default
        except json.JSONDecodeError:
            return default
    return default


def _parse_market(raw: dict[str, Any]) -> Market:
    if raw.get("outcomePrices") is None and raw.get("tokens") is None:
        raise PolymarketError(
            f"Cannot parse market {raw.get('id', '?')}: "
            "neither outcomePrices nor tokens field present"
        )
    prices = _coerce_list(raw.get("outcomePrices"), ["0", "0"])
    prob_yes = float(prices[0]) if prices else 0.0
    tags_raw = _coerce_list(raw.get("tags"), [])
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
