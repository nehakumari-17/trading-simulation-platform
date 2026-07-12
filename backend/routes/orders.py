from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from backend.database import get_db
from backend.models import User, Order, OrderStatus
from backend.schemas.order import OrderCreate, OrderOut
from backend.utils.security import get_current_user
from backend.services.execution import place_order

router = APIRouter()


@router.post("/", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Place a market or limit order."""
    from backend.services.market_data import get_latest_price
    current_price = await get_latest_price(order_data.symbol.upper())

    if current_price is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No market data found for '{order_data.symbol}'. Check the symbol and try again."
        )

    return await place_order(
        order_data=order_data,
        user_id=current_user.id,
        db=db,
        current_price=current_price,
    )


@router.get("/", response_model=list[OrderOut])
async def get_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns all orders for the logged-in user, newest first."""
    result = await db.execute(
        select(Order)
        .where(Order.user_id == current_user.id)
        .order_by(desc(Order.created_at))
    )
    return result.scalars().all()


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns a single order by ID. Users can only see their own orders."""
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")

    return order


@router.delete("/{order_id}", response_model=OrderOut)
async def cancel_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancels a PENDING limit order. Filled orders cannot be cancelled."""
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")

    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel an order with status '{order.status}'. Only PENDING orders can be cancelled."
        )

    order.status = OrderStatus.CANCELLED
    return order
