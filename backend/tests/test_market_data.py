"""
Tests for market data routes.
  GET /api/market/instruments
  GET /api/market/search
  GET /api/market/quote/{symbol}
  GET /api/market/candles/{symbol}
"""

import pytest
from unittest.mock import patch

# sample candle data used across tests
SAMPLE_CANDLES = [
    {"timestamp": "2024-07-01T00:00:00", "open": 1290.0,
     "high": 1310.0, "low": 1280.0, "close": 1293.0, "volume": 12_000_000},
    {"timestamp": "2024-07-02T00:00:00", "open": 1293.0,
     "high": 1320.0, "low": 1285.0, "close": 1300.0, "volume": 11_000_000},
]

SAMPLE_INSTRUMENTS = [
    {"symbol": "RELIANCE", "name": "Reliance Industries Ltd",
     "sector": "Energy",   "last_price": 1293.0},
    {"symbol": "TCS",      "name": "Tata Consultancy Services Ltd",
     "sector": "IT",       "last_price": 2188.0},
]


@pytest.mark.asyncio
class TestInstruments:

    async def test_instruments_returns_list(self, client, auth_headers):
        with patch("backend.services.market_data.get_all_instruments",
                   return_value=SAMPLE_INSTRUMENTS):
            res = await client.get("/api/market/instruments",
                                   headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) == 2

    async def test_instruments_has_required_fields(self, client, auth_headers):
        with patch("backend.services.market_data.get_all_instruments",
                   return_value=SAMPLE_INSTRUMENTS):
            res  = await client.get("/api/market/instruments",
                                    headers=auth_headers)
        item = res.json()[0]
        assert "symbol"     in item
        assert "name"       in item
        assert "sector"     in item
        assert "last_price" in item


@pytest.mark.asyncio
class TestSearch:

    async def test_search_returns_matches(self, client, auth_headers):
        with patch("backend.services.market_data.search_instruments",
                   return_value=[SAMPLE_INSTRUMENTS[0]]):
            res = await client.get("/api/market/search?q=reliance",
                                   headers=auth_headers)
        assert res.status_code == 200
        assert len(res.json()) >= 1

    async def test_search_no_results(self, client, auth_headers):
        with patch("backend.services.market_data.search_instruments",
                   return_value=[]):
            res = await client.get("/api/market/search?q=XYZNOTEXIST",
                                   headers=auth_headers)
        assert res.status_code == 404

    async def test_search_requires_query(self, client, auth_headers):
        res = await client.get("/api/market/search",
                               headers=auth_headers)
        assert res.status_code == 422


@pytest.mark.asyncio
class TestQuote:

    async def test_quote_returns_data(self, client, auth_headers):
        with patch("backend.services.market_data.get_quote",
                   return_value={
                       "symbol": "RELIANCE", "ltp": 1293.0,
                       "open": 1290.0, "high": 1308.0, "low": 1286.0,
                       "close": 1285.0, "change": 8.0, "change_pct": 0.62,
                       "volume": 12_000_000, "timestamp": "2024-07-14",
                   }):
            res = await client.get("/api/market/quote/RELIANCE",
                                   headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["symbol"] == "RELIANCE"
        assert "ltp"          in data
        assert "change_pct"   in data

    async def test_quote_unknown_symbol(self, client, auth_headers):
        with patch("backend.services.market_data.get_quote",
                   return_value=None):
            res = await client.get("/api/market/quote/FAKESTOCK",
                                   headers=auth_headers)
        assert res.status_code == 404


@pytest.mark.asyncio
class TestCandles:

    async def test_candles_returns_list(self, client, auth_headers):
        with patch("backend.services.market_data.get_candles",
                   return_value=SAMPLE_CANDLES):
            res = await client.get("/api/market/candles/RELIANCE",
                                   headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) == 2

    async def test_candle_has_ohlcv_fields(self, client, auth_headers):
        with patch("backend.services.market_data.get_candles",
                   return_value=SAMPLE_CANDLES):
            res  = await client.get("/api/market/candles/RELIANCE",
                                    headers=auth_headers)
        candle = res.json()[0]
        for field in ["open", "high", "low", "close", "volume"]:
            assert field in candle

    async def test_candles_limit_param(self, client, auth_headers):
        candles_200 = SAMPLE_CANDLES * 100   # 200 candles
        with patch("backend.services.market_data.get_candles",
                   return_value=candles_200[:50]):
            res = await client.get(
                "/api/market/candles/RELIANCE?limit=50",
                headers=auth_headers
            )
        assert res.status_code == 200

    async def test_candles_unknown_symbol(self, client, auth_headers):
        with patch("backend.services.market_data.get_candles",
                   return_value=[]):
            res = await client.get("/api/market/candles/FAKESTOCK",
                                   headers=auth_headers)
        assert res.status_code == 404
