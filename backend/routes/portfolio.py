from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models import User, Portfolio, Position
from backend.schemas.portfolio import PortfolioOut, PositionOut, TradeOut
from backend.utils.security import get_current_user
from backend.services import analytics

router = APIRouter()


@router.get("/", response_model=PortfolioOut)
async def get_portfolio(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full portfolio — cash, positions, P&L."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()

    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found.")

    return portfolio


@router.get("/positions", response_model=list[PositionOut])
async def get_positions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns all stocks the user currently holds."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()

    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found.")

    pos_result = await db.execute(
        select(Position).where(Position.portfolio_id == portfolio.id)
    )
    return pos_result.scalars().all()


@router.get("/summary")
async def get_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Quick numbers for the dashboard stat cards."""
    return await analytics.get_portfolio_summary(user_id=current_user.id, db=db)


@router.get("/trades", response_model=list[TradeOut])
async def get_trades(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Complete trade history — every filled buy and sell."""
    return await analytics.get_trade_history(user_id=current_user.id, db=db)


@router.get("/performance")
async def get_performance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Performance metrics — Sharpe, win rate, drawdown, profit factor."""
    return await analytics.get_performance_metrics(user_id=current_user.id, db=db)
