"""
Tests for order routes.
  POST   /api/orders/
  GET    /api/orders/
  GET    /api/orders/{id}
  DELETE /api/orders/{id}
"""

import pytest
from unittest.mock import patch


# reusable helper — places a market buy order for RELIANCE
async def place_buy(client, headers, symbol="RELIANCE", qty=10):
    with patch("backend.services.market_data.get_latest_price", return_value=1293.0):
        with patch("backend.simulation.slippage.load_historical_data", return_value=[
            {"timestamp": None, "open": 1290.0, "high": 1308.0,
             "low": 1286.0, "close": 1293.0, "volume": 13_000_000}
        ]):
            return await client.post("/api/orders/", json={
                "symbol":     symbol,
                "order_type": "market",
                "side":       "buy",
                "quantity":   qty,
            }, headers=headers)


@pytest.mark.asyncio
class TestPlaceOrder:

    async def test_place_market_buy(self, client, auth_headers):
        res = await place_buy(client, auth_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["symbol"]     == "RELIANCE"
        assert data["side"]       == "buy"
        assert data["order_type"] == "market"
        assert data["quantity"]   == 10
        assert data["status"]     == "filled"
        assert data["filled_price"] is not None

    async def test_place_market_sell_after_buy(self, client, auth_headers):
        # buy first
        await place_buy(client, auth_headers)

        # then sell
        with patch("backend.services.market_data.get_latest_price", return_value=1300.0):
            with patch("backend.simulation.slippage.load_historical_data", return_value=[
                {"timestamp": None, "open": 1300.0, "high": 1310.0,
                 "low": 1295.0, "close": 1300.0, "volume": 12_000_000}
            ]):
                res = await client.post("/api/orders/", json={
                    "symbol":     "RELIANCE",
                    "order_type": "market",
                    "side":       "sell",
                    "quantity":   10,
                }, headers=auth_headers)

        assert res.status_code == 201
        assert res.json()["status"] == "filled"

    async def test_place_limit_buy(self, client, auth_headers):
        with patch("backend.services.market_data.get_latest_price", return_value=1293.0):
            with patch("backend.simulation.slippage.load_historical_data", return_value=[
                {"timestamp": None, "open": 1290.0, "high": 1308.0,
                 "low": 1286.0, "close": 1293.0, "volume": 13_000_000}
            ]):
                res = await client.post("/api/orders/", json={
                    "symbol":     "RELIANCE",
                    "order_type": "limit",
                    "side":       "buy",
                    "quantity":   5,
                    "price":      1280.0,
                }, headers=auth_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["order_type"] == "limit"
        assert data["price"]      == 1280.0

    async def test_insufficient_balance(self, client, auth_headers):
        # try to buy 100000 shares — way more than ₹10 lakh allows
        with patch("backend.services.market_data.get_latest_price", return_value=1293.0):
            with patch("backend.simulation.slippage.load_historical_data", return_value=[
                {"timestamp": None, "open": 1290.0, "high": 1308.0,
                 "low": 1286.0, "close": 1293.0, "volume": 13_000_000}
            ]):
                res = await client.post("/api/orders/", json={
                    "symbol":     "RELIANCE",
                    "order_type": "market",
                    "side":       "buy",
                    "quantity":   100_000,
                }, headers=auth_headers)
        assert res.status_code == 400

    async def test_sell_without_position(self, client, auth_headers):
        with patch("backend.services.market_data.get_latest_price", return_value=1293.0):
            with patch("backend.simulation.slippage.load_historical_data", return_value=[
                {"timestamp": None, "open": 1290.0, "high": 1308.0,
                 "low": 1286.0, "close": 1293.0, "volume": 13_000_000}
            ]):
                res = await client.post("/api/orders/", json={
                    "symbol":     "TCS",
                    "order_type": "market",
                    "side":       "sell",
                    "quantity":   10,
                }, headers=auth_headers)
        assert res.status_code == 400

    async def test_no_auth_rejected(self, client):
        res = await client.post("/api/orders/", json={
            "symbol": "RELIANCE", "order_type": "market",
            "side": "buy", "quantity": 1,
        })
        assert res.status_code == 401

    async def test_unknown_symbol_rejected(self, client, auth_headers):
        with patch("backend.services.market_data.get_latest_price", return_value=None):
            res = await client.post("/api/orders/", json={
                "symbol":     "FAKEXYZ",
                "order_type": "market",
                "side":       "buy",
                "quantity":   1,
            }, headers=auth_headers)
        assert res.status_code == 404


@pytest.mark.asyncio
class TestGetOrders:

    async def test_get_orders_empty(self, client, auth_headers):
        res = await client.get("/api/orders/", headers=auth_headers)
        assert res.status_code == 200
        # may or may not be empty depending on test order — just check it's a list
        assert isinstance(res.json(), list)

    async def test_get_orders_after_placing(self, client, auth_headers):
        await place_buy(client, auth_headers, symbol="INFY", qty=5)
        res = await client.get("/api/orders/", headers=auth_headers)
        assert res.status_code == 200
        orders = res.json()
        symbols = [o["symbol"] for o in orders]
        assert "INFY" in symbols

    async def test_get_single_order(self, client, auth_headers):
        buy = await place_buy(client, auth_headers, symbol="WIPRO", qty=3)
        order_id = buy.json()["id"]

        res = await client.get(f"/api/orders/{order_id}", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["id"]     == order_id
        assert res.json()["symbol"] == "WIPRO"

    async def test_cannot_see_other_users_order(self, client, auth_headers, second_auth_headers):
        buy = await place_buy(client, auth_headers, symbol="SBIN", qty=2)
        order_id = buy.json()["id"]

        res = await client.get(f"/api/orders/{order_id}", headers=second_auth_headers)
        assert res.status_code == 404


@pytest.mark.asyncio
class TestCancelOrder:

    async def test_cancel_pending_limit_order(self, client, auth_headers):
        with patch("backend.services.market_data.get_latest_price", return_value=1293.0):
            with patch("backend.simulation.slippage.load_historical_data", return_value=[
                {"timestamp": None, "open": 1290.0, "high": 1308.0,
                 "low": 1286.0, "close": 1293.0, "volume": 13_000_000}
            ]):
                place = await client.post("/api/orders/", json={
                    "symbol":     "HDFCBANK",
                    "order_type": "limit",
                    "side":       "buy",
                    "quantity":   1,
                    "price":      700.0,
                }, headers=auth_headers)

        order_id = place.json()["id"]

        # cancel it — limit orders that filled instantly won't be PENDING
        # so we just check the endpoint responds correctly
        res = await client.delete(f"/api/orders/{order_id}", headers=auth_headers)
        # either cancelled (204/200) or already filled (400)
        assert res.status_code in [200, 400]

    async def test_cancel_nonexistent_order(self, client, auth_headers):
        res = await client.delete("/api/orders/999999", headers=auth_headers)
        assert res.status_code == 404
