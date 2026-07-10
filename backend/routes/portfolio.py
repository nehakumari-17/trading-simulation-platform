from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models import User, Portfolio, Position
from backend.schemas.portfolio import PortfolioOut, PositionOut, TradeOut
from backend.utils.security import get_current_user
from backend.services import analytics

router = APIRouter()


# GET /api/portfolio/
#the main portfolio page — shows cash, total value, all positions, P&L
  @router.get("/", response_model=PortfolioOut)
async def get_portfolio(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),

):
    """
    Returns the full portfolio for the logged-in user.
    Includes cash balance, total account value, realized and
    unrealized P&L, and a list of all stocks currently held.
    """
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()

    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found."
        )

    return portfolio


#gET /api/portfolio/positions
# Just the list of stocks the user currently holds
  @router.get("/positions", response_model=list[PositionOut])
async def get_positions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns all open positions — stocks the user currently holds.
    Each position shows the symbol, quantity, average buy price,
    current price, and unrealized P&L.
    """
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()

     if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found."
        )

    pos_result = await db.execute(
        select(Position).where(Position.portfolio_id == portfolio.id)
    )
    positions = pos_result.scalars().all()

    return positions


#GET /api/portfolio/summary
# Quick numbers for the dashboard header cards
    @router.get("/summary")
     async def get_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns a lightweight summary with just the key numbers:
    cash balance, holdings value, total value, and P&L.
    Used for the top stat cards on the dashboard.
    """
    summary = await analytics.get_portfolio_summary(
        user_id=current_user.id,
        db=db
    )
    return summary


# GET/api/portfolio/trades
#Full trade history — every buy and sell the user has made
@router.get("/trades", response_model=list[TradeOut])
async def get_trades(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the complete trade history for the user.
    A trade is only created when an order actually gets filled.
    Shows fill price, slippage, transaction cost, and P&L per trade.
    """
    trades = await analytics.get_trade_history(
        user_id=current_user.id,
        db=db
    )
    return trades


# GET /api/portfolio/performance
#Performance analytics — Sharpe ratio, win rate, drawdown etc.
@router.get("/performance")
     async def get_performance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns performance metrics calculated from the user's trade history.
    This is what goes on the analytics/performance page:
      - Total return
      - Win rate
      - Max drawdown
      - Sharpe ratio
      - Profit factor
      - Average P&L per trade
    """
    metrics = await analytics.get_performance_metrics(
        user_id=current_user.id,
        db=db
    )
    return metrics
