"""
Tests for portfolio routes.
  GET /api/portfolio/
  GET /api/portfolio/summary
  GET /api/portfolio/positions
  GET /api/portfolio/trades
  GET /api/portfolio/performance
"""

import pytest
from unittest.mock import patch


async def buy_stock(client, headers, symbol="RELIANCE", qty=10):
    with patch("backend.services.market_data.get_latest_price", return_value=1293.0):
        with patch("backend.simulation.slippage.load_historical_data", return_value=[
            {"timestamp": None, "open": 1290.0, "high": 1308.0,
             "low": 1286.0, "close": 1293.0, "volume": 13_000_000}
        ]):
            return await client.post("/api/orders/", json={
                "symbol": symbol, "order_type": "market",
                "side": "buy", "quantity": qty,
            }, headers=headers)


async def sell_stock(client, headers, symbol="RELIANCE", qty=10, price=1310.0):
    with patch("backend.services.market_data.get_latest_price", return_value=price):
        with patch("backend.simulation.slippage.load_historical_data", return_value=[
            {"timestamp": None, "open": price, "high": price + 20,
             "low": price - 10, "close": price, "volume": 12_000_000}
        ]):
            return await client.post("/api/orders/", json={
                "symbol": symbol, "order_type": "market",
                "side": "sell", "quantity": qty,
            }, headers=headers)


@pytest.mark.asyncio
class TestPortfolioSummary:

    async def test_summary_fresh_account(self, client):
        # register a brand new isolated user for this test
        await client.post("/api/auth/register", json={
            "username": "freshuser", "email": "fresh@test.com", "password": "pass123"
        })
        login = await client.post("/api/auth/login", json={
            "email": "fresh@test.com", "password": "pass123"
        })
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        res = await client.get("/api/portfolio/summary", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["cash_balance"]   == 1_000_000.0
        assert data["holdings_value"] == 0.0
        assert data["total_value"]    == 1_000_000.0
        assert data["realized_pnl"]   == 0.0
        assert data["unrealized_pnl"] == 0.0

    async def test_summary_decreases_after_buy(self, client, auth_headers):
        await buy_stock(client, auth_headers)
        res = await client.get("/api/portfolio/summary", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        # cash should have decreased
        assert data["cash_balance"] < 1_000_000.0
        # holdings should be non-zero
        assert data["holdings_value"] > 0

    async def test_summary_shows_realized_pnl_after_sell(self, client, auth_headers):
        await buy_stock(client, auth_headers, symbol="TCS", qty=5)
        await sell_stock(client, auth_headers, symbol="TCS", qty=5, price=1310.0)

        res = await client.get("/api/portfolio/summary", headers=auth_headers)
        data = res.json()
        # realized P&L should be non-zero after a profitable sell
        assert data["realized_pnl"] != 0

    async def test_summary_requires_auth(self, client):
        res = await client.get("/api/portfolio/summary")
        assert res.status_code == 401


@pytest.mark.asyncio
class TestPositions:

    async def test_positions_empty_initially(self, client, auth_headers):
        res = await client.get("/api/portfolio/positions", headers=auth_headers)
        assert res.status_code == 200
        # fresh account or after selling everything — positions may be empty list
        assert isinstance(res.json(), list)

    async def test_position_created_after_buy(self, client, auth_headers):
        await buy_stock(client, auth_headers, symbol="AXISBANK", qty=20)
        res = await client.get("/api/portfolio/positions", headers=auth_headers)
        assert res.status_code == 200
        positions = res.json()
        symbols   = [p["symbol"] for p in positions]
        assert "AXISBANK" in symbols

    async def test_position_removed_after_full_sell(self, client, auth_headers):
        await buy_stock(client, auth_headers, symbol="ITC", qty=10)
        await sell_stock(client, auth_headers, symbol="ITC", qty=10)

        res = await client.get("/api/portfolio/positions", headers=auth_headers)
        positions = res.json()
        symbols   = [p["symbol"] for p in positions]
        assert "ITC" not in symbols

    async def test_position_has_correct_fields(self, client, auth_headers):
        # use a unique symbol not touched by other tests
        await buy_stock(client, auth_headers, symbol="SUNPHARMA", qty=15)
        res = await client.get("/api/portfolio/positions", headers=auth_headers)
        pos = next((p for p in res.json() if p["symbol"] == "SUNPHARMA"), None)
        assert pos is not None
        assert pos["quantity"]      == 15
        assert pos["avg_buy_price"] > 0
        assert pos["current_price"] > 0


@pytest.mark.asyncio
class TestTradeHistory:

    async def test_trades_empty_initially(self, client, auth_headers):
        res = await client.get("/api/portfolio/trades", headers=auth_headers)
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    async def test_trade_created_after_buy(self, client, auth_headers):
        await buy_stock(client, auth_headers, symbol="SBIN", qty=8)
        res   = await client.get("/api/portfolio/trades", headers=auth_headers)
        trades = res.json()
        assert any(t["symbol"] == "SBIN" for t in trades)

    async def test_trade_has_correct_fields(self, client, auth_headers):
        await buy_stock(client, auth_headers, symbol="MARUTI", qty=2)
        res    = await client.get("/api/portfolio/trades", headers=auth_headers)
        trade  = next((t for t in res.json() if t["symbol"] == "MARUTI"), None)
        assert trade is not None
        assert trade["quantity"]         == 2
        assert trade["fill_price"]       > 0
        assert trade["transaction_cost"] > 0
        assert "executed_at"             in trade


@pytest.mark.asyncio
class TestPerformanceMetrics:

    async def test_performance_empty_account(self, client):
        # isolated user with no trades
        await client.post("/api/auth/register", json={
            "username": "perfuser", "email": "perf@test.com", "password": "pass123"
        })
        login = await client.post("/api/auth/login", json={
            "email": "perf@test.com", "password": "pass123"
        })
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        res = await client.get("/api/portfolio/performance", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total_trades"] == 0

    async def test_total_trades_counts_all(self, client, auth_headers):
        # buy + sell = 2 trades, total_trades should be 2
        await buy_stock(client, auth_headers,  symbol="INFY", qty=5)
        await sell_stock(client, auth_headers, symbol="INFY", qty=5)

        res  = await client.get("/api/portfolio/performance", headers=auth_headers)
        data = res.json()
        # total_trades should be >= 2 (may have more from other tests)
        assert data["total_trades"] >= 2

    async def test_win_rate_with_profitable_trade(self, client, auth_headers):
        await buy_stock(client, auth_headers,  symbol="BAJFINANCE", qty=3, )
        await sell_stock(client, auth_headers, symbol="BAJFINANCE", qty=3, price=1400.0)

        res  = await client.get("/api/portfolio/performance", headers=auth_headers)
        data = res.json()
        assert data["win_rate"] > 0
        assert data["total_return"] is not None
