import math
from sqlalchemy.ext.asyncio import AsyncSession
 from sqlalchemy import select

from backend.models import Trade, Portfolio, Position, OrderSide






async def get_portfolio_summary(user_id: int, db: AsyncSession) -> dict:
    """
    Returns the user's overall account summary.
    This is the main thing shown on the dashboard header.
    """
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id)
    )
    portfolio = result.scalar_one_or_none()

    if portfolio is None:
        return {}

    #grab all open positions for this portfolio
    pos_result = await db.execute(
        select(Position).where(Position.portfolio_id == portfolio.id)
    )
    positions = pos_result.scalars().all()

    # total value of all stocks currently held
    holdings_value = sum(p.current_price * p.quantity for p in positions)

    # recalculate unrealized pnl across all positions
       unrealized_pnl = sum(
        (p.current_price - p.avg_buy_price) * p.quantity
        for p in positions
    )

    total_value = round(portfolio.cash_balance + holdings_value, 2)

    return {
        "cash_balance":    round(portfolio.cash_balance, 2),
     "holdings_value":  round(holdings_value, 2),
        "total_value":     total_value,
        "realized_pnl":    round(portfolio.realized_pnl, 2),
        "unrealized_pnl":  round(unrealized_pnl, 2),
        "total_pnl":       round(portfolio.realized_pnl + unrealized_pnl, 2),
    }


async def get_trade_history(user_id: int, db: AsyncSession) -> list[Trade]:
    """
    Returns all completed trades for the user, newest first.
    Used for the trade history table in the UI.
    """
    result = await db.execute(
        select(Trade)
        .where(Trade.user_id == user_id)
        .order_by(Trade.executed_at.desc())
    )
    return result.scalars().all()


async def get_performance_metrics(user_id: int, db: AsyncSession) -> dict:
    """
    Calculates the standard performance numbers shown in the strategy
    analysis section — same metrics professional traders use.

    Only looks at SELL trades because that's when profit/loss is realized.
    """
    result = await db.execute(
        select(Trade).where(
            Trade.user_id == user_id,
            Trade.side == OrderSide.SELL
        )
    )
    trades = result.scalars().all()

    if not trades:
        return {
            "total_trades":    0,
            "win_rate":        0.0,
            "total_return":    0.0,
            "profit_factor":   0.0,
            "avg_pnl":         0.0,
            "max_drawdown":    0.0,
            "sharpe_ratio":    0.0,
        }

    pnl_list    = [t.pnl for t in trades]
    wins        = [p for p in pnl_list if p > 0]
    losses      = [p for p in pnl_list if p <= 0]

    total_trades  = len(pnl_list)
    win_rate      = round(len(wins) / total_trades * 100, 2)
    total_return  = round(sum(pnl_list), 2)
    avg_pnl       = round(total_return / total_trades, 2)

    # Profit factor = total gains / total losses
    # A value above 1.0 means the strategy makes more than it loses
    gross_profit  = sum(wins)
    gross_loss    = abs(sum(losses)) if losses else 0
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0.0

    # Max drawdown — largest peak to trough loss in the equity curve
    max_drawdown  = _calculate_max_drawdown(pnl_list)

    # Sharpe ratio — return relative to risk (volatility)
    # Higher is better. Above 1.0 is decent, above 2.0 is good.
    sharpe_ratio  = _calculate_sharpe_ratio(pnl_list)

    return {
         "total_trades":  total_trades,
        "win_rate":      win_rate,
        "total_return":  total_return,
        "profit_factor": profit_factor,
        "avg_pnl":       avg_pnl,
        "max_drawdown":  max_drawdown,
        "sharpe_ratio":  sharpe_ratio,
    }


  def _calculate_max_drawdown(pnl_list: list[float]) -> float:
    """
    Walks through the equity curve and finds the biggest drop
    from a peak to the lowest point after it.

    Example: if equity went 100 → 150 → 90, the drawdown is 60.
    """
      if not pnl_list:
        return 0.0

    peak        = 0.0
    max_dd      = 0.0
    running     = 0.0

     for pnl in pnl_list:
        running += pnl
        if running > peak:
            peak = running
        drawdown = peak - running
        if drawdown > max_dd:
            max_dd = drawdown

    return round(max_dd, 2)


def _calculate_sharpe_ratio(pnl_list: list[float], risk_free_rate: float = 0.0) -> float:
    """
    Sharpe ratio = (average return - risk free rate) / std deviation of returns

      We use 0 as the risk-free rate here to keep it simple.
    A ratio above 1 means the strategy is earning more than it risks.
    """
    if len(pnl_list) < 2:
        return 0.0

    n       = len(pnl_list)
    mean    = sum(pnl_list) / n
    variance = sum((x - mean) ** 2 for x in pnl_list) / (n - 1)
    std_dev = math.sqrt(variance)

      if std_dev == 0:
        return 0.0

    return round((mean - risk_free_rate) / std_dev, 2)
