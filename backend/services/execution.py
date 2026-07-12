from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from backend.models import Order, Trade, Portfolio, Position, OrderStatus, OrderSide, OrderType
from backend.schemas.order import OrderCreate


TRANSACTION_COST_RATE = 0.001   # 0.1% brokerage fee
SLIPPAGE_RATE         = 0.0005  # 0.05% slippage on market orders


async def place_order(
    order_data: OrderCreate,
    user_id: int,
    db: AsyncSession,
    current_price: float,
) -> Order:
    """
    Core function that handles the full order lifecycle:
    validates, calculates fill price, records order + trade, updates portfolio.
    """

    # Step 1: Load portfolio
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id)
    )
    portfolio = result.scalar_one_or_none()

    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found for this user."
        )

    # Step 2: Determine fill price
    if order_data.order_type == OrderType.MARKET:
        if order_data.side == OrderSide.BUY:
            fill_price = round(current_price * (1 + SLIPPAGE_RATE), 2)
        else:
            fill_price = round(current_price * (1 - SLIPPAGE_RATE), 2)
        slippage = round(abs(fill_price - current_price) * order_data.quantity, 2)
    else:
        fill_price = order_data.price
        slippage = 0.0

    # Step 3: Calculate costs
    trade_value      = fill_price * order_data.quantity
    transaction_cost = round(trade_value * TRANSACTION_COST_RATE, 2)
    total_cost       = trade_value + transaction_cost

    # Step 4: Validate
    if order_data.side == OrderSide.BUY:
        if portfolio.cash_balance < total_cost:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient balance. Required: ₹{total_cost:.2f}, Available: ₹{portfolio.cash_balance:.2f}"
            )
    else:
        pos_result = await db.execute(
            select(Position).where(
                Position.portfolio_id == portfolio.id,
                Position.symbol == order_data.symbol
            )
        )
        position = pos_result.scalar_one_or_none()
        held = position.quantity if position else 0
        if held < order_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient shares. Required: {order_data.quantity}, Held: {held}"
            )

    # Step 5: Create Order record
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

    # Step 6: Create Trade record
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

    # Step 7: Update portfolio and position
    if order_data.side == OrderSide.BUY:
        await _process_buy(db, portfolio, order_data.symbol.upper(), order_data.quantity, fill_price, total_cost)
    else:
        realized_pnl = await _process_sell(db, portfolio, order_data.symbol.upper(), order_data.quantity, fill_price, transaction_cost)
        new_trade.pnl = realized_pnl
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

    result = await db.execute(
        select(Position).where(
            Position.portfolio_id == portfolio.id,
            Position.symbol == symbol
        )
    )
    position = result.scalar_one_or_none()

    if position:
        total_qty = position.quantity + quantity
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
    result = await db.execute(
        select(Position).where(
            Position.portfolio_id == portfolio.id,
            Position.symbol == symbol
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
