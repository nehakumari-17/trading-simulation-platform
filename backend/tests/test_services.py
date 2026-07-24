"""
Tests for service layer.
  services/analytics.py
  services/risk.py
  services/strategy.py
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime


# ── Analytics tests ────────────────────────────────────────────────

class TestAnalytics:

    def test_max_drawdown_flat(self):
        from backend.services.analytics import _calculate_max_drawdown
        # no losses — drawdown should be 0
        assert _calculate_max_drawdown([100, 200, 300]) == 0.0

    def test_max_drawdown_single_loss(self):
        from backend.services.analytics import _calculate_max_drawdown
        # peak at 300, drops to 100 — drawdown = 200
        result = _calculate_max_drawdown([100, 200, -200, 100])
        assert result == 200.0

    def test_max_drawdown_empty(self):
        from backend.services.analytics import _calculate_max_drawdown
        assert _calculate_max_drawdown([]) == 0.0

    def test_sharpe_ratio_positive_returns(self):
        from backend.services.analytics import _calculate_sharpe_ratio
        # consistent positive returns should give positive Sharpe
        result = _calculate_sharpe_ratio([100, 120, 110, 130, 115])
        assert isinstance(result, float)

    def test_sharpe_ratio_needs_two_values(self):
        from backend.services.analytics import _calculate_sharpe_ratio
        # single value — not enough to calculate std deviation
        assert _calculate_sharpe_ratio([100]) == 0.0

    def test_sharpe_ratio_zero_std(self):
        from backend.services.analytics import _calculate_sharpe_ratio
        # identical returns — std dev = 0, Sharpe undefined → return 0
        assert _calculate_sharpe_ratio([100, 100, 100]) == 0.0


# ── Risk service tests ─────────────────────────────────────────────

@pytest.mark.asyncio
class TestRiskService:

    async def _make_mock_db(self, cash=1_000_000.0, has_position=False,
                            position_qty=0, total_value=1_000_000.0):
        """Builds a mock DB session that returns a fake portfolio."""
        from backend.models import Portfolio, Position

        mock_portfolio = MagicMock(spec=Portfolio)
        mock_portfolio.id            = 1
        mock_portfolio.cash_balance  = cash
        mock_portfolio.total_value   = total_value

        mock_position = MagicMock(spec=Position)
        mock_position.quantity      = position_qty
        mock_position.current_price = 1293.0
        mock_position.symbol        = "RELIANCE"

        mock_result_portfolio = MagicMock()
        mock_result_portfolio.scalar_one_or_none.return_value = mock_portfolio

        mock_result_position = MagicMock()
        mock_result_position.scalar_one_or_none.return_value = (
            mock_position if has_position else None
        )

        mock_db = AsyncMock()
        mock_db.execute.side_effect = [
            mock_result_portfolio,
            mock_result_position,
        ]
        return mock_db

    async def test_buy_allowed_with_sufficient_cash(self):
        from backend.services.risk import check_order
        from backend.schemas.order import OrderCreate
        from backend.models import OrderType, OrderSide

        order = OrderCreate(
            symbol="RELIANCE", order_type=OrderType.MARKET,
            side=OrderSide.BUY, quantity=10,
        )
        db = await self._make_mock_db(cash=1_000_000.0)
        result = await check_order(order, 1, 1293.0, db)
        assert result["allowed"] is True

    async def test_buy_blocked_insufficient_cash(self):
        from backend.services.risk import check_order
        from backend.schemas.order import OrderCreate
        from backend.models import OrderType, OrderSide

        order = OrderCreate(
            symbol="RELIANCE", order_type=OrderType.MARKET,
            side=OrderSide.BUY, quantity=10,
        )
        # only ₹100 available but order costs ~₹12930
        db = await self._make_mock_db(cash=100.0)
        result = await check_order(order, 1, 1293.0, db)
        assert result["allowed"] is False
        assert "cash" in result["reason"].lower() or "balance" in result["reason"].lower()

    async def test_sell_blocked_no_position(self):
        from backend.services.risk import check_order
        from backend.schemas.order import OrderCreate
        from backend.models import OrderType, OrderSide

        order = OrderCreate(
            symbol="RELIANCE", order_type=OrderType.MARKET,
            side=OrderSide.SELL, quantity=10,
        )
        db = await self._make_mock_db(has_position=False)
        result = await check_order(order, 1, 1293.0, db)
        assert result["allowed"] is False

    async def test_sell_allowed_with_position(self):
        from backend.services.risk import check_order
        from backend.schemas.order import OrderCreate
        from backend.models import OrderType, OrderSide

        order = OrderCreate(
            symbol="RELIANCE", order_type=OrderType.MARKET,
            side=OrderSide.SELL, quantity=5,
        )
        db = await self._make_mock_db(has_position=True, position_qty=10)
        result = await check_order(order, 1, 1293.0, db)
        assert result["allowed"] is True

    async def test_order_value_cap(self):
        from backend.services.risk import check_order, MAX_ORDER_VALUE
        from backend.schemas.order import OrderCreate
        from backend.models import OrderType, OrderSide

        # order value = 1293 × 1000 = ₹12.93 lakh > ₹5 lakh cap
        order = OrderCreate(
            symbol="RELIANCE", order_type=OrderType.MARKET,
            side=OrderSide.BUY, quantity=1000,
        )
        db = await self._make_mock_db(cash=50_000_000.0)
        result = await check_order(order, 1, 1293.0, db)
        assert result["allowed"] is False


# ── Strategy service tests ─────────────────────────────────────────

class TestStrategyService:

    CANDLES = [
        {"timestamp": datetime(2024, 1, (i % 28) + 1),
         "open":  1200 + i * 2,  "high": 1220 + i * 2,
         "low":   1190 + i * 2,  "close": 1210 + i * 2,
         "volume": 10_000_000}
        for i in range(200)
    ]

    def test_ma_crossover_returns_dict(self):
        from backend.services.strategy import run_ma_crossover
        with patch("backend.services.strategy.get_candles_in_range",
                   return_value=self.CANDLES):
            result = run_ma_crossover(
                "RELIANCE", "2024-01-01", "2024-12-31"
            )
        assert isinstance(result, dict)
        assert "total_trades"  in result
        assert "total_return"  in result
        assert "win_rate"      in result
        assert "sharpe_ratio"  in result
        assert "max_drawdown"  in result
        assert "trades"        in result

    def test_rsi_strategy_returns_dict(self):
        from backend.services.strategy import run_rsi_strategy
        with patch("backend.services.strategy.get_candles_in_range",
                   return_value=self.CANDLES):
            result = run_rsi_strategy(
                "TCS", "2024-01-01", "2024-12-31"
            )
        assert isinstance(result, dict)
        assert "total_trades" in result

    def test_vwap_strategy_returns_dict(self):
        from backend.services.strategy import run_vwap_strategy
        with patch("backend.services.strategy.get_candles_in_range",
                   return_value=self.CANDLES):
            result = run_vwap_strategy(
                "INFY", "2024-01-01", "2024-12-31"
            )
        assert isinstance(result, dict)
        assert "total_trades" in result

    def test_strategy_not_enough_data(self):
        from backend.services.strategy import run_ma_crossover
        with patch("backend.services.strategy.get_candles_in_range",
                   return_value=[]):
            result = run_ma_crossover(
                "RELIANCE", "2024-01-01", "2024-02-01"
            )
        # should return gracefully with a message, not crash
        assert result["total_trades"] == 0
        assert "message" in result or result["total_return"] == 0.0

    def test_strategy_win_rate_between_0_and_100(self):
        from backend.services.strategy import run_vwap_strategy
        with patch("backend.services.strategy.get_candles_in_range",
                   return_value=self.CANDLES):
            result = run_vwap_strategy(
                "RELIANCE", "2024-01-01", "2024-12-31"
            )
        if result["total_trades"] > 0:
            assert 0 <= result["win_rate"] <= 100

    def test_trades_list_has_correct_fields(self):
        from backend.services.strategy import run_ma_crossover
        with patch("backend.services.strategy.get_candles_in_range",
                   return_value=self.CANDLES):
            result = run_ma_crossover(
                "RELIANCE", "2024-01-01", "2024-12-31"
            )
        for trade in result["trades"]:
            assert "entry_date"  in trade
            assert "exit_date"   in trade
            assert "entry_price" in trade
            assert "exit_price"  in trade
            assert "pnl"         in trade
