from pydantic import BaseModel
from datetime import datetime


# A single stock position the user currently holds
class PositionOut(BaseModel):
    id: int
    symbol: str
    quantity: int
    avg_buy_price: float
    current_price: float
    unrealized_pnl: float
    updated_at: datetime

    model_config = {"from_attributes": True}


# Full portfolio summary shown on the dashboard
class PortfolioOut(BaseModel):
    id: int
    cash_balance: float
    total_value: float
    realized_pnl: float
    unrealized_pnl: float
    updated_at: datetime
    positions: list[PositionOut]

    model_config = {"from_attributes": True}


# A single completed trade from the user's history
class TradeOut(BaseModel):
    id: int
    symbol: str
    side: str
    quantity: int
    fill_price: float
    slippage: float
    transaction_cost: float
    pnl: float
    executed_at: datetime

    model_config = {"from_attributes": True}
