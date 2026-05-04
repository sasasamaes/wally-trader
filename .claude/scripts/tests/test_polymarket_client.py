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


def test_parse_market_handles_json_string_outcome_prices():
    """Real Gamma API returns outcomePrices as a JSON-encoded string."""
    raw = {
        "id": "0xreal",
        "slug": "real-market",
        "question": "Will X happen?",
        "outcomes": '["Yes", "No"]',  # JSON string, not list
        "outcomePrices": '["0.62", "0.38"]',  # JSON string, not list
        "volume24hr": 1500000,
        "endDate": "2026-12-31T00:00:00Z",
        "tags": None,  # also seen in real responses
        "active": True,
        "closed": False,
    }
    m = client._parse_market(raw)
    assert m.prob_yes == 0.62
    assert m.tags == ()


def test_parse_market_handles_list_outcome_prices_back_compat():
    """Old fixtures pass lists — must continue to work."""
    raw = {
        "id": "0xold",
        "slug": "old-fixture",
        "outcomes": ["Yes", "No"],
        "outcomePrices": ["0.55", "0.45"],
        "volume24hr": 500_000,
    }
    m = client._parse_market(raw)
    assert m.prob_yes == 0.55


def test_parse_market_raises_when_neither_prices_nor_tokens_field():
    """_parse_market raises PolymarketError when both outcomePrices and tokens are absent."""
    raw = {
        "id": "0xclob",
        "slug": "clob-style-market",
        "question": "Will X happen?",
        "volume24hr": 500_000,
        # Neither outcomePrices nor tokens — CLOB-shaped response
    }
    with pytest.raises(client.PolymarketError, match="neither outcomePrices nor tokens"):
        client._parse_market(raw)
