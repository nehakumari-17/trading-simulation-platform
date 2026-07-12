from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models import User, StrategyRun, StrategyName
from backend.utils.security import get_current_user
from backend.services import strategy as strategy_service

router = APIRouter()


# POST /api/strategy/run
# Runs one of the three strategies and saves the result
@router.post("/run")
async def run_strategy(
    symbol:        str = Query(...),
    strategy_name: str = Query(..., description="ma_crossover | rsi | vwap"),
    start_date:    str = Query(..., description="YYYY-MM-DD"),
    end_date:      str = Query(..., description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Runs a backtest for the selected strategy over a date range.
    Returns trade-by-trade results and summary metrics.

    Saves the result to the strategy_runs table so you can
    view it again later in history.
    """
    strategy_name = strategy_name.lower().strip()

    # run the right strategy based on what the user picked
    if strategy_name == "ma_crossover":
        result = strategy_service.run_ma_crossover(symbol, start_date, end_date)
    elif strategy_name == "rsi":
        result = strategy_service.run_rsi_strategy(symbol, start_date, end_date)
    elif strategy_name == "vwap":
        result = strategy_service.run_vwap_strategy(symbol, start_date, end_date)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown strategy '{strategy_name}'. Choose from: ma_crossover, rsi, vwap"
        )

    # map string to enum for the DB
    strategy_enum_map = {
        "ma_crossover": StrategyName.MA_CROSSOVER,
        "rsi":          StrategyName.RSI,
        "vwap":         StrategyName.VWAP,
    }

    # save the run and its results to the database
    run = StrategyRun(
        user_id       = current_user.id,
        strategy_name = strategy_enum_map[strategy_name],
        symbol        = symbol.upper(),
        start_date    = start_date,
        end_date      = end_date,
        total_return  = result.get("total_return"),
        sharpe_ratio  = result.get("sharpe_ratio"),
        max_drawdown  = result.get("max_drawdown"),
        win_rate      = result.get("win_rate"),
        profit_factor = result.get("profit_factor"),
        total_trades  = result.get("total_trades"),
    )
    db.add(run)

    return result


# GET /api/strategy/history
# Returns all strategy runs the user has done before
@router.get("/history")
async def get_strategy_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns all past strategy runs for the logged-in user.
    Shown in the strategy history table on the UI.
    """
    result = await db.execute(
        select(StrategyRun)
        .where(StrategyRun.user_id == current_user.id)
        .order_by(StrategyRun.created_at.desc())
    )
    runs = result.scalars().all()
    return runs
