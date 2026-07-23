import math
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models import Trade, Portfolio, Position, OrderSide


async def get_portfolio_summary(user_id: int, db: AsyncSession) -> dict:
    """Returns the key numbers shown on the dashboard header."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id)
    )
    portfolio = result.scalar_one_or_none()

    if portfolio is None:
        return {}

    pos_result = await db.execute(
        select(Position).where(Position.portfolio_id == portfolio.id)
    )
    positions = pos_result.scalars().all()

    holdings_value = sum(p.current_price * p.quantity for p in positions)
    unrealized_pnl = sum(
        (p.current_price - p.avg_buy_price) * p.quantity for p in positions
    )
    total_value = round(portfolio.cash_balance + holdings_value, 2)

    return {
        "cash_balance":   round(portfolio.cash_balance, 2),
        "holdings_value": round(holdings_value, 2),
        "total_value":    total_value,
        "realized_pnl":   round(portfolio.realized_pnl, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "total_pnl":      round(portfolio.realized_pnl + unrealized_pnl, 2),
    }


async def get_trade_history(user_id: int, db: AsyncSession) -> list[Trade]:
    """Returns all trades for the user, newest first."""
    result = await db.execute(
        select(Trade)
        .where(Trade.user_id == user_id)
        .order_by(Trade.executed_at.desc())
    )
    return result.scalars().all()


async def get_performance_metrics(user_id: int, db: AsyncSession) -> dict:
    """
    Calculates performance metrics from the user's trade history.

    total_trades  = ALL trades (buy + sell) — what the user sees in Trade History
    P&L metrics   = only SELL trades, because P&L is only realised on a sell
    """
    # count all trades for the total_trades number
    all_result = await db.execute(
        select(Trade).where(Trade.user_id == user_id)
    )
    all_trades  = all_result.scalars().all()
    total_trades = len(all_trades)

    # P&L calculations only use sell trades
    sell_result = await db.execute(
        select(Trade).where(
            Trade.user_id == user_id,
            Trade.side    == OrderSide.SELL,
        )
    )
    sell_trades = sell_result.scalars().all()

    if not sell_trades:
        return {
            "total_trades": total_trades,  # still show correct count even with no sells
            "win_rate":     0.0,
            "total_return": 0.0,
            "profit_factor":0.0,
            "avg_pnl":      0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
        }

    pnl_list      = [t.pnl for t in sell_trades]
    wins          = [p for p in pnl_list if p > 0]
    losses        = [p for p in pnl_list if p <= 0]
    total_return  = round(sum(pnl_list), 2)
    win_rate      = round(len(wins) / len(sell_trades) * 100, 2)
    avg_pnl       = round(total_return / len(sell_trades), 2)

    gross_profit  = sum(wins)
    gross_loss    = abs(sum(losses)) if losses else 0
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0.0

    return {
        "total_trades": total_trades,       # all trades — matches Trade History count
        "win_rate":     win_rate,           # % of sell trades that were profitable
        "total_return": total_return,       # total realised P&L from sells
        "profit_factor":profit_factor,
        "avg_pnl":      avg_pnl,
        "max_drawdown": _calculate_max_drawdown(pnl_list),
        "sharpe_ratio": _calculate_sharpe_ratio(pnl_list),
    }


def _calculate_max_drawdown(pnl_list: list[float]) -> float:
    """Finds the biggest peak-to-trough drop in the equity curve."""
    if not pnl_list:
        return 0.0

    peak = running = max_dd = 0.0
    for pnl in pnl_list:
        running += pnl
        if running > peak:
            peak = running
        dd = peak - running
        if dd > max_dd:
            max_dd = dd

    return round(max_dd, 2)


def _calculate_sharpe_ratio(pnl_list: list[float], risk_free_rate: float = 0.0) -> float:
    """
    Sharpe ratio = average return / std deviation of returns.
    Above 1.0 means the strategy earns more than it risks.
    """
    if len(pnl_list) < 2:
        return 0.0

    n        = len(pnl_list)
    mean     = sum(pnl_list) / n
    variance = sum((x - mean) ** 2 for x in pnl_list) / (n - 1)
    std_dev  = math.sqrt(variance)

    if std_dev == 0:
        return 0.0

    return round((mean - risk_free_rate) / std_dev, 2)
