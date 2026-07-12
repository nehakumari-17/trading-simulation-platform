from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models import Portfolio, Position, OrderSide
from backend.schemas.order import OrderCreate


MAX_POSITION_SIZE_PCT = 0.30     # single stock can't exceed 30% of portfolio
MAX_ORDER_VALUE       = 500_000.0  # single order capped at ₹5 lakh
MIN_CASH_RESERVE_PCT  = 0.05     # always keep at least 5% as cash


async def check_order(
    order: OrderCreate,
    user_id: int,
    current_price: float,
    db: AsyncSession,
) -> dict:
    """
    Runs safety checks before an order goes to execution.
    Returns: { allowed: bool, reason: str, warnings: list }
    """
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id)
    )
    portfolio = result.scalar_one_or_none()

    if portfolio is None:
        return {"allowed": False, "reason": "Portfolio not found.", "warnings": []}

    warnings    = []
    order_value = current_price * order.quantity

    # Check 1: order value cap
    if order_value > MAX_ORDER_VALUE:
        return {
            "allowed": False,
            "reason":  f"Order value ₹{order_value:,.2f} exceeds the ₹{MAX_ORDER_VALUE:,.2f} per-order limit.",
            "warnings": [],
        }

    if order.side == OrderSide.BUY:
        total_cost = order_value * 1.001

        # Check 2: sufficient cash
        if portfolio.cash_balance < total_cost:
            return {
                "allowed": False,
                "reason":  f"Not enough cash. Need ₹{total_cost:,.2f}, have ₹{portfolio.cash_balance:,.2f}.",
                "warnings": [],
            }

        # Check 3: cash reserve warning
        remaining = portfolio.cash_balance - total_cost
        if remaining < portfolio.total_value * MIN_CASH_RESERVE_PCT:
            warnings.append(
                f"This trade leaves only ₹{remaining:,.2f} cash (below the recommended 5% reserve)."
            )

        # Check 4: concentration warning
        pos_result = await db.execute(
            select(Position).where(
                Position.portfolio_id == portfolio.id,
                Position.symbol == order.symbol.upper()
            )
        )
        existing = pos_result.scalar_one_or_none()
        new_pos_value = order_value + (existing.current_price * existing.quantity if existing else 0)

        if portfolio.total_value > 0:
            concentration = new_pos_value / portfolio.total_value
            if concentration > MAX_POSITION_SIZE_PCT:
                warnings.append(
                    f"{order.symbol.upper()} would be {concentration * 100:.1f}% of your portfolio. "
                    f"Recommended max is {MAX_POSITION_SIZE_PCT * 100:.0f}%."
                )

    if order.side == OrderSide.SELL:
        pos_result = await db.execute(
            select(Position).where(
                Position.portfolio_id == portfolio.id,
                Position.symbol == order.symbol.upper()
            )
        )
        position = pos_result.scalar_one_or_none()
        held = position.quantity if position else 0

        # Check 5: sufficient shares
        if held < order.quantity:
            return {
                "allowed": False,
                "reason":  f"Not enough shares. Holding {held}, trying to sell {order.quantity}.",
                "warnings": [],
            }

    return {"allowed": True, "reason": "", "warnings": warnings}


async def get_risk_summary(user_id: int, db: AsyncSession) -> dict:
    """Returns a snapshot of the user's current risk exposure."""
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

    if not positions:
        return {
            "total_exposure":       0.0,
            "cash_pct":             100.0,
            "largest_position":     None,
            "largest_position_pct": 0.0,
            "num_positions":        0,
        }

    holdings_value = sum(p.current_price * p.quantity for p in positions)
    total_value    = portfolio.cash_balance + holdings_value
    largest        = max(positions, key=lambda p: p.current_price * p.quantity)
    largest_value  = largest.current_price * largest.quantity

    return {
        "total_exposure":       round(holdings_value, 2),
        "cash_pct":             round(portfolio.cash_balance / total_value * 100, 2) if total_value else 0,
        "largest_position":     largest.symbol,
        "largest_position_pct": round(largest_value / total_value * 100, 2) if total_value else 0,
        "num_positions":        len(positions),
    }
