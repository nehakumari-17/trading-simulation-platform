from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from backend.database import get_db
from backend.models import User, Order, OrderStatus
from backend.schemas.order import OrderCreate, OrderOut
from backend.utils.security import get_current_user
from backend.services.execution import place_order

router = APIRouter()


# ─────────────────────────────────────────────
# PLACE ORDER
# POST /api/orders/
# User places a buy or sell order
# ─────────────────────────────────────────────
@router.post("/", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Place a market or limit order.
    - Market order: fills immediately at current price + slippage
    - Limit order:  fills at the price you specify

    Requires: JWT token in Authorization header
    """

    # Get current market price for this symbol from the simulation engine
    # For now we fetch it from our market data service
    # (We will wire this properly when simulation engine is ready)
    from backend.services.market_data import get_latest_price
    current_price = await get_latest_price(order_data.symbol.upper())

    if current_price is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No market data found for symbol '{order_data.symbol}'. Check the symbol and try again."
        )

    # Hand off to the execution service — all the real logic lives there
    order = await place_order(
        order_data    = order_data,
        user_id       = current_user.id,
        db            = db,
        current_price = current_price,
    )

    return order


# ─────────────────────────────────────────────
# GET ALL ORDERS
# GET /api/orders/
# Returns the logged-in user's full order history
# ─────────────────────────────────────────────
@router.get("/", response_model=list[OrderOut])
async def get_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns all orders placed by the logged-in user.
    Most recent orders appear first.
    """
    result = await db.execute(
        select(Order)
        .where(Order.user_id == current_user.id)
        .order_by(desc(Order.created_at))
    )
    orders = result.scalars().all()
    return orders


# ─────────────────────────────────────────────
# GET SINGLE ORDER
# GET /api/orders/{order_id}
# Returns details of one specific order
# ─────────────────────────────────────────────
@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns details of a single order by its ID.
    Users can only see their own orders.
    """
    result = await db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.user_id == current_user.id   # security: can't see other users' orders
        )
    )
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found."
        )

    return order


# ─────────────────────────────────────────────
# CANCEL ORDER
# DELETE /api/orders/{order_id}
# Cancels a pending limit order
# ─────────────────────────────────────────────
@router.delete("/{order_id}", response_model=OrderOut)
async def cancel_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cancels a PENDING limit order.
    Market orders fill instantly so they cannot be cancelled.
    Already filled or cancelled orders cannot be cancelled again.
    """
    result = await db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.user_id == current_user.id
        )
    )
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found."
        )

    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel an order with status '{order.status}'. Only PENDING orders can be cancelled."
        )

    order.status = OrderStatus.CANCELLED
    return order
