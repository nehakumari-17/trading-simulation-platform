"""
Tests for simulation modules.
  simulation/slippage.py
  simulation/matching.py
  simulation/order_book.py
  simulation/market_models.py
"""

import pytest
from unittest.mock import patch
from datetime import datetime


# ── Shared sample data ────────────────────────────────────────────

SAMPLE_CANDLE = {
    "timestamp": datetime(2024, 7, 14),
    "open":   1290.0,
    "high":   1308.0,
    "low":    1286.9,
    "close":  1293.0,
    "volume": 13_500_000,
}

NEXT_CANDLE = {
    "timestamp": datetime(2024, 7, 15),
    "open":   1295.0,
    "high":   1315.0,
    "low":    1290.0,
    "close":  1305.0,
    "volume": 11_000_000,
}

# 25 minimal candles for volatility calculation
CANDLES_25 = [
    {"timestamp": datetime(2024, 1, i + 1), "open": 1200 + i,
     "high": 1220 + i, "low": 1190 + i,
     "close": 1210 + i, "volume": 10_000_000}
    for i in range(25)
]


# ── Slippage tests ─────────────────────────────────────────────────

class TestSlippage:

    def test_buy_slippage_is_above_mid(self):
        from backend.simulation.slippage import calculate_slippage
        with patch("backend.simulation.slippage.load_historical_data",
                   return_value=CANDLES_25):
            result = calculate_slippage(
                symbol="RELIANCE", order_quantity=10,
                current_price=1293.0, side="buy", candle=SAMPLE_CANDLE,
            )
        # buy fills above mid-price
        assert result["fill_price"] >= 1293.0
        assert result["slippage_amount"] >= 0

    def test_sell_slippage_is_below_mid(self):
        from backend.simulation.slippage import calculate_slippage
        with patch("backend.simulation.slippage.load_historical_data",
                   return_value=CANDLES_25):
            result = calculate_slippage(
                symbol="RELIANCE", order_quantity=10,
                current_price=1293.0, side="sell", candle=SAMPLE_CANDLE,
            )
        # sell fills below mid-price
        assert result["fill_price"] <= 1293.0

    def test_large_order_has_more_slippage_than_small(self):
        from backend.simulation.slippage import calculate_slippage
        with patch("backend.simulation.slippage.load_historical_data",
                   return_value=CANDLES_25):
            small = calculate_slippage("RELIANCE", 10,   1293.0, "buy", SAMPLE_CANDLE)
            large = calculate_slippage("RELIANCE", 5000, 1293.0, "buy", SAMPLE_CANDLE)
        assert large["slippage_amount"] >= small["slippage_amount"]

    def test_slippage_within_bounds(self):
        from backend.simulation.slippage import calculate_slippage, MIN_SLIPPAGE_PCT, MAX_SLIPPAGE_PCT
        with patch("backend.simulation.slippage.load_historical_data",
                   return_value=CANDLES_25):
            result = calculate_slippage("RELIANCE", 100, 1293.0, "buy", SAMPLE_CANDLE)
        # slippage % should always be between MIN and MAX
        assert result["slippage_pct"] >= MIN_SLIPPAGE_PCT * 100
        assert result["slippage_pct"] <= MAX_SLIPPAGE_PCT * 100

    def test_volatility_calculation(self):
        from backend.simulation.slippage import calculate_volatility
        with patch("backend.simulation.slippage.load_historical_data",
                   return_value=CANDLES_25):
            vol = calculate_volatility("RELIANCE")
        assert vol > 0
        assert vol < 0.5   # daily vol above 50% would be absurd


# ── Matching tests ─────────────────────────────────────────────────

class TestMatching:

    def test_market_order_fills_at_next_candle_open(self):
        from backend.simulation.matching import match_order
        with patch("backend.simulation.slippage.load_historical_data",
                   return_value=CANDLES_25):
            result = match_order(
                symbol="RELIANCE", order_type="market",
                side="buy", quantity=10, limit_price=None,
                current_candle=SAMPLE_CANDLE, next_candle=NEXT_CANDLE,
            )
        assert result is not None
        assert result["filled"]    is True
        assert result["fill_type"] == "market"
        # fill price should be around the next candle open
        assert abs(result["fill_price"] - NEXT_CANDLE["open"]) < 5.0

    def test_market_order_no_next_candle_returns_none(self):
        from backend.simulation.matching import match_order
        result = match_order(
            symbol="RELIANCE", order_type="market",
            side="buy", quantity=10, limit_price=None,
            current_candle=SAMPLE_CANDLE, next_candle=None,
        )
        assert result is None

    def test_limit_buy_fills_when_price_hits_low(self):
        from backend.simulation.matching import match_order
        with patch("backend.simulation.slippage.load_historical_data",
                   return_value=CANDLES_25):
            result = match_order(
                symbol="RELIANCE", order_type="limit",
                side="buy", quantity=10,
                limit_price=SAMPLE_CANDLE["low"],   # exactly at the low
                current_candle=SAMPLE_CANDLE, next_candle=None,
            )
        assert result is not None
        assert result["filled"] is True

    def test_limit_buy_does_not_fill_below_low(self):
        from backend.simulation.matching import match_order
        result = match_order(
            symbol="RELIANCE", order_type="limit",
            side="buy", quantity=10,
            limit_price=SAMPLE_CANDLE["low"] * 0.95,  # below the low
            current_candle=SAMPLE_CANDLE, next_candle=None,
        )
        assert result is None

    def test_limit_sell_fills_when_price_hits_high(self):
        from backend.simulation.matching import match_order
        with patch("backend.simulation.slippage.load_historical_data",
                   return_value=CANDLES_25):
            result = match_order(
                symbol="RELIANCE", order_type="limit",
                side="sell", quantity=10,
                limit_price=SAMPLE_CANDLE["high"],   # exactly at the high
                current_candle=SAMPLE_CANDLE, next_candle=None,
            )
        assert result is not None
        assert result["filled"] is True

    def test_limit_sell_does_not_fill_above_high(self):
        from backend.simulation.matching import match_order
        result = match_order(
            symbol="RELIANCE", order_type="limit",
            side="sell", quantity=10,
            limit_price=SAMPLE_CANDLE["high"] * 1.05,  # above the high
            current_candle=SAMPLE_CANDLE, next_candle=None,
        )
        assert result is None


# ── Order book tests ───────────────────────────────────────────────

class TestOrderBook:

    def test_order_book_has_five_levels(self):
        from backend.simulation.order_book import generate_order_book
        with patch("backend.simulation.order_book.calculate_volatility",
                   return_value=0.011):
            book = generate_order_book("RELIANCE", 1293.0)
        assert len(book["bids"]) == 5
        assert len(book["asks"]) == 5

    def test_bids_below_mid_asks_above_mid(self):
        from backend.simulation.order_book import generate_order_book
        with patch("backend.simulation.order_book.calculate_volatility",
                   return_value=0.011):
            book = generate_order_book("RELIANCE", 1293.0)
        mid = book["mid_price"]
        for bid in book["bids"]:
            assert bid["price"] < mid
        for ask in book["asks"]:
            assert ask["price"] > mid

    def test_bids_sorted_highest_first(self):
        from backend.simulation.order_book import generate_order_book
        with patch("backend.simulation.order_book.calculate_volatility",
                   return_value=0.011):
            book  = generate_order_book("RELIANCE", 1293.0)
        prices = [b["price"] for b in book["bids"]]
        assert prices == sorted(prices, reverse=True)

    def test_asks_sorted_lowest_first(self):
        from backend.simulation.order_book import generate_order_book
        with patch("backend.simulation.order_book.calculate_volatility",
                   return_value=0.011):
            book   = generate_order_book("RELIANCE", 1293.0)
        prices = [a["price"] for a in book["asks"]]
        assert prices == sorted(prices)

    def test_all_quantities_positive(self):
        from backend.simulation.order_book import generate_order_book
        with patch("backend.simulation.order_book.calculate_volatility",
                   return_value=0.011):
            book = generate_order_book("RELIANCE", 1293.0)
        for level in book["bids"] + book["asks"]:
            assert level["quantity"] > 0

    def test_spread_is_positive(self):
        from backend.simulation.order_book import generate_order_book
        with patch("backend.simulation.order_book.calculate_volatility",
                   return_value=0.011):
            book = generate_order_book("RELIANCE", 1293.0)
        assert book["spread"] > 0


# ── Market models tests ────────────────────────────────────────────

class TestMarketModels:

    def test_initialize_symbol_loads_candles(self):
        from backend.simulation.market_models import initialize_symbol
        with patch("backend.simulation.market_models.load_historical_data",
                   return_value=CANDLES_25):
            state = initialize_symbol("RELIANCE")
        assert state is not None
        assert state.symbol        == "RELIANCE"
        assert len(state.candles)  == 25
        assert state.current_price > 0

    def test_initialize_symbol_no_data_returns_none(self):
        from backend.simulation.market_models import initialize_symbol
        with patch("backend.simulation.market_models.load_historical_data",
                   return_value=[]):
            state = initialize_symbol("FAKESYMBOL")
        assert state is None

    def test_next_tick_advances_price(self):
        from backend.simulation.market_models import initialize_symbol, next_tick
        with patch("backend.simulation.market_models.load_historical_data",
                   return_value=CANDLES_25):
            state = initialize_symbol("RELIANCE")
            tick1 = next_tick(state)
            tick2 = next_tick(state)
        assert "price"  in tick1
        assert "candle" in tick1
        # prices can vary but both should be positive
        assert tick1["price"] > 0
        assert tick2["price"] > 0

    def test_intraday_prices_within_candle_bounds(self):
        from backend.simulation.market_models import (
            initialize_symbol, next_tick, INTRADAY_STEPS
        )
        with patch("backend.simulation.market_models.load_historical_data",
                   return_value=CANDLES_25):
            state = initialize_symbol("RELIANCE")
            first_candle = state.candles[0]

            for _ in range(INTRADAY_STEPS):
                tick = next_tick(state)
                if tick["candle"] == first_candle:
                    # price must stay within candle bounds
                    assert tick["price"] >= first_candle["low"]  - 0.01
                    assert tick["price"] <= first_candle["high"] + 0.01
