from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional

from backend.models import OrderType, OrderSide, OrderStatus


# ─────────────────────────────────────────────
# What the user sends when PLACING an order
# ─────────────────────────────────────────────
class OrderCreate(BaseModel):
    symbol: str                        # e.g. "RELIANCE", "TCS"
    order_type: OrderType              # market or limit
    side: OrderSide                    # buy or sell
    quantity: int                      # number of shares
    price: Optional[float] = None      # only required for limit orders

    # Validation: limit orders must have a price, market orders must not
    @field_validator("price")
    @classmethod
    def price_required_for_limit(cls, price, info):
        order_type = info.data.get("order_type")
        if order_type == OrderType.LIMIT and price is None:
            raise ValueError("Limit orders must have a price")
        if order_type == OrderType.MARKET and price is not None:
            raise ValueError("Market orders should not have a price")
        return price

    # Validation: quantity must be at least 1
    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, quantity):
        if quantity < 1:
            raise ValueError("Quantity must be at least 1")
        return quantity


# ─────────────────────────────────────────────
# What we send BACK after an order is placed or fetched
# ─────────────────────────────────────────────
class OrderOut(BaseModel):
    id: int
    symbol: str
    order_type: OrderType
    side: OrderSide
    quantity: int
    price: Optional[float]         # target price (limit orders only)
    filled_price: Optional[float]  # actual fill price
    slippage: Optional[float]      # how much slippage occurred
    status: OrderStatus
    created_at: datetime
    filled_at: Optional[datetime]

    model_config = {"from_attributes": True}
