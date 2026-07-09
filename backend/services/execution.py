from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from backend.models import Order, Trade, Portfolio, Position, OrderStatus, OrderSide, OrderType
from backend.schemas.order import OrderCreate


# ─────────────────────────────────────────────
# CONSTANTS
# Transaction cost = brokerage fee per trade
# In real brokers this is typically 0.1% of trade value
# ─────────────────────────────────────────────
TRANSACTION_COST_RATE = 0.001   # 0.1%
SLIPPAGE_RATE         = 0.0005  # 0.05% — market orders slip a little


# ─────────────────────────────────────────────
# MAIN FUNCTION: place_order
# This is the core of the trading engine.
# It does everything needed when a user places an order:
#   1. Validates the order (enough cash? enough shares?)
#   2. Calculates fill price (with slippage for market orders)
#   3. Calculates transaction cost
#   4. Creates an Order record in the DB
#   5. Creates a Trade record in the DB
#   6. Updates the user's Portfolio (cash balance)
#   7. Updates the user's Position (shares held)
# ─────────────────────────────────────────────
async def place_order(
    order_data: OrderCreate,
    user_id: int,
    db: AsyncSession,
    current_price: float,       # current market price of the stock, fetched before calling this
) -> Order:

    # ── Step 1: Load the user's portfolio ──────────────────────────────
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id)
    )
    portfolio = result.scalar_one_or_none()

    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found for this user."
        )

    # ── Step 2: Determine the fill price ───────────────────────────────
    # Market order  → fills at current price + slippage
    # Limit order   → fills at the limit price the user specified
    if order_data.order_type == OrderType.MARKET:
        if order_data.side == OrderSide.BUY:
            # Buying at market: price goes up slightly due to slippage
            fill_price = round(current_price * (1 + SLIPPAGE_RATE), 2)
        else:
            # Selling at market: price goes down slightly due to slippage
            fill_price = round(current_price * (1 - SLIPPAGE_RATE), 2)
        slippage = round(abs(fill_price - current_price) * order_data.quantity, 2)
    else:
        # Limit order: fill at exactly the price the user requested
        fill_price = order_data.price
        slippage = 0.0

    # ── Step 3: Calculate costs ────────────────────────────────────────
    trade_value       = fill_price * order_data.quantity
    transaction_cost  = round(trade_value * TRANSACTION_COST_RATE, 2)
    total_cost        = trade_value + transaction_cost  # for buy orders

    # ── Step 4: Validate the order ─────────────────────────────────────
    if order_data.side == OrderSide.BUY:
        # User must have enough cash to buy
        if portfolio.cash_balance < total_cost:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient balance. Required: ₹{total_cost:.2f}, Available: ₹{portfolio.cash_balance:.2f}"
            )
    else:
        # User must have enough shares to sell
        pos_result = await db.execute(
            select(Position).where(
                Position.portfolio_id == portfolio.id,
                Position.symbol == order_data.symbol
            )
        )
        position = pos_result.scalar_one_or_none()

        if position is None or position.quantity < order_data.quantity:
            held = position.quantity if position else 0
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient shares. Required: {order_data.quantity}, Held: {held}"
            )

    # ── Step 5: Create the Order record ───────────────────────────────
    new_order = Order(
        user_id     = user_id,
        symbol      = order_data.symbol.upper(),
        order_type  = order_data.order_type,
        side        = order_data.side,
        quantity    = order_data.quantity,
        price       = order_data.price,
        filled_price= fill_price,
        slippage    = slippage,
        status      = OrderStatus.FILLED,
        filled_at   = datetime.utcnow(),
    )
    db.add(new_order)
    await db.flush()  # get new_order.id

    # ── Step 6: Create the Trade record ───────────────────────────────
    pnl = 0.0  # will be calculated properly on SELL orders below

    new_trade = Trade(
        user_id         = user_id,
        order_id        = new_order.id,
        symbol          = order_data.symbol.upper(),
        side            = order_data.side,
        quantity        = order_data.quantity,
        fill_price      = fill_price,
        slippage        = slippage,
        transaction_cost= transaction_cost,
        pnl             = pnl,
        executed_at     = datetime.utcnow(),
    )
    db.add(new_trade)

    # ── Step 7: Update Portfolio and Position ─────────────────────────
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
        new_trade.pnl = realized_pnl
        portfolio.realized_pnl += realized_pnl

    return new_order


# ─────────────────────────────────────────────
# HELPER: process a BUY
# Deducts cash, adds shares to position (or creates new position)
# ─────────────────────────────────────────────
async def _process_buy(
    db: AsyncSession,
    portfolio: Portfolio,
    symbol: str,
    quantity: int,
    fill_price: float,
    total_cost: float,
):
    # Deduct cost from cash balance
    portfolio.cash_balance -= total_cost

    # Check if user already holds this stock
    result = await db.execute(
        select(Position).where(
            Position.portfolio_id == portfolio.id,
            Position.symbol == symbol
        )
    )
    position = result.scalar_one_or_none()

    if position:
        # Already holds this stock — update average buy price
        # Formula: new_avg = (old_qty * old_avg + new_qty * new_price) / total_qty
        total_qty   = position.quantity + quantity
        position.avg_buy_price = round(
            (position.quantity * position.avg_buy_price + quantity * fill_price) / total_qty, 2
        )
        position.quantity      = total_qty
        position.current_price = fill_price
    else:
        # First time buying this stock — create a new position
        new_position = Position(
            portfolio_id  = portfolio.id,
            symbol        = symbol,
            quantity      = quantity,
            avg_buy_price = fill_price,
            current_price = fill_price,
        )
        db.add(new_position)


# ─────────────────────────────────────────────
# HELPER: process a SELL
# Adds cash back, reduces shares, calculates realized P&L
# ─────────────────────────────────────────────
async def _process_sell(
    db: AsyncSession,
    portfolio: Portfolio,
    symbol: str,
    quantity: int,
    fill_price: float,
    transaction_cost: float,
) -> float:
    # Get the position
    result = await db.execute(
        select(Position).where(
            Position.portfolio_id == portfolio.id,
            Position.symbol == symbol
        )
    )
    position = result.scalar_one_or_none()

    # Calculate realized P&L for this sell
    # P&L = (sell price - avg buy price) * quantity - transaction cost
    realized_pnl = round(
        (fill_price - position.avg_buy_price) * quantity - transaction_cost, 2
    )

    # Add proceeds to cash balance
    proceeds = fill_price * quantity - transaction_cost
    portfolio.cash_balance += proceeds

    # Reduce share count
    position.quantity      -= quantity
    position.current_price  = fill_price

    # If all shares sold, remove the position row
    if position.quantity == 0:
        await db.delete(position)

    return realized_pnl
