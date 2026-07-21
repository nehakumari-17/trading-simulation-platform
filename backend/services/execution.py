"""
services/execution.py

Handles order placement for manually triggered orders (from the API).

For market orders placed via the UI, we use the simulation engine's
current price and the realistic slippage model from simulation/slippage.py
instead of the old flat 0.05% rate.

Risk checks are now run before any order is accepted.
"""

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from backend.models import Order, Trade, Portfolio, Position, OrderStatus, OrderSide, OrderType
from backend.schemas.order import OrderCreate
from backend.simulation.slippage import calculate_slippage
from backend.services.risk import check_order


TRANSACTION_COST_RATE = 0.001  # 0.1% brokerage fee


async def place_order(
    order_data: OrderCreate,
    user_id: int,
    db: AsyncSession,
    current_price: float,
) -> Order:
    """
    Handles the full lifecycle of a manually placed order:
      1. Run risk checks (new — wired in step 7)
      2. Calculate realistic fill price using simulation slippage model
      3. Validate cash / share balance
      4. Save Order + Trade records
      5. Update Portfolio + Position
    """

    # Step 1: Risk check — runs before anything else
    risk = await check_order(
        order         = order_data,
        user_id       = user_id,
        current_price = current_price,
        db            = db,
    )

    if not risk["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=risk["reason"]
        )

    # warnings are non-blocking — we include them in the response later
    # for now just log them (frontend sees them via the order response)

    # Step 2: Load portfolio
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id)
    )
    portfolio = result.scalar_one_or_none()

    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found for this user."
        )

    # Step 3: Calculate fill price using real slippage model
    # Market orders go through the full simulation slippage calculation
    # Limit orders fill at the user's specified price (+ small slippage)
    if order_data.order_type == OrderType.MARKET:
        slip = calculate_slippage(
            symbol         = order_data.symbol.upper(),
            order_quantity = order_data.quantity,
            current_price  = current_price,
            side           = order_data.side.value,
        )
        fill_price = slip["fill_price"]
        slippage   = slip["slippage_amount"]
    else:
        # limit order — fill at limit price with minimal slippage
        slip = calculate_slippage(
            symbol         = order_data.symbol.upper(),
            order_quantity = order_data.quantity,
            current_price  = order_data.price,
            side           = order_data.side.value,
        )
        fill_price = slip["fill_price"]
        slippage   = slip["slippage_amount"]

    # Step 4: Calculate total cost
    trade_value      = fill_price * order_data.quantity
    transaction_cost = round(trade_value * TRANSACTION_COST_RATE, 2)
    total_cost       = trade_value + transaction_cost

    # Step 5: Final balance validation
    # (risk.check_order already caught obvious cases, this is a safety net)
    if order_data.side == OrderSide.BUY:
        if portfolio.cash_balance < total_cost:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient balance. Required: {total_cost:.2f}, Available: {portfolio.cash_balance:.2f}"
            )
    else:
        pos_result = await db.execute(
            select(Position).where(
                Position.portfolio_id == portfolio.id,
                Position.symbol       == order_data.symbol.upper()
            )
        )
        position = pos_result.scalar_one_or_none()
        held     = position.quantity if position else 0
        if held < order_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient shares. Required: {order_data.quantity}, Held: {held}"
            )

    # Step 6: Save Order record
    new_order = Order(
        user_id      = user_id,
        symbol       = order_data.symbol.upper(),
        order_type   = order_data.order_type,
        side         = order_data.side,
        quantity     = order_data.quantity,
        price        = order_data.price,
        filled_price = fill_price,
        slippage     = slippage,
        status       = OrderStatus.FILLED,
        filled_at    = datetime.utcnow(),
    )
    db.add(new_order)
    await db.flush()

    # Step 7: Save Trade record
    new_trade = Trade(
        user_id          = user_id,
        order_id         = new_order.id,
        symbol           = order_data.symbol.upper(),
        side             = order_data.side,
        quantity         = order_data.quantity,
        fill_price       = fill_price,
        slippage         = slippage,
        transaction_cost = transaction_cost,
        pnl              = 0.0,
        executed_at      = datetime.utcnow(),
    )
    db.add(new_trade)

    # Step 8: Update Portfolio and Position
    if order_data.side == OrderSide.BUY:
        await _process_buy(
            db, portfolio, order_data.symbol.upper(),
            order_data.quantity, fill_price, total_cost
        )
    else:
        realized_pnl = await _process_sell(
            db, portfolio, order_data.symbol.upper(),
            order_data.quantity, fill_price, transaction_cost
        )
        new_trade.pnl       = realized_pnl
        portfolio.realized_pnl += realized_pnl

    return new_order


async def _process_buy(
    db: AsyncSession,
    portfolio: Portfolio,
    symbol: str,
    quantity: int,
    fill_price: float,
    total_cost: float,
):
    portfolio.cash_balance -= total_cost

    result   = await db.execute(
        select(Position).where(
            Position.portfolio_id == portfolio.id,
            Position.symbol       == symbol
        )
    )
    position = result.scalar_one_or_none()

    if position:
        total_qty              = position.quantity + quantity
        position.avg_buy_price = round(
            (position.quantity * position.avg_buy_price + quantity * fill_price) / total_qty, 2
        )
        position.quantity      = total_qty
        position.current_price = fill_price
    else:
        db.add(Position(
            portfolio_id  = portfolio.id,
            symbol        = symbol,
            quantity      = quantity,
            avg_buy_price = fill_price,
            current_price = fill_price,
        ))


async def _process_sell(
    db: AsyncSession,
    portfolio: Portfolio,
    symbol: str,
    quantity: int,
    fill_price: float,
    transaction_cost: float,
) -> float:
    result   = await db.execute(
        select(Position).where(
            Position.portfolio_id == portfolio.id,
            Position.symbol       == symbol
        )
    )
    position = result.scalar_one_or_none()

    realized_pnl = round(
        (fill_price - position.avg_buy_price) * quantity - transaction_cost, 2
    )

    portfolio.cash_balance += fill_price * quantity - transaction_cost
    position.quantity      -= quantity
    position.current_price  = fill_price

    if position.quantity == 0:
        await db.delete(position)

    return realized_pnl
