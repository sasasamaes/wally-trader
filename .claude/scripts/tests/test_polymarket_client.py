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
