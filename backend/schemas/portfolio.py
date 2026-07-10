from pydantic import BaseModel
from datetime import datetime

# A single stock position the user holds

class PositionOut(BaseModel):


    id: int
    symbol: str
    quantity: int
    avg_buy_price: float      #average price paid per share
    current_price: float      #latest market price
    unrealized_pnl: float     #(current_price - avg_buy_price) * quantity
    updated_at: datetime

    model_config = {"from_attributes": True}



# Full portfolio summary that shown on the dashboard

class PortfolioOut(BaseModel):

    id: int
    cash_balance: float       # how much virtual cash is left
    total_value: float        # cash + current value of all positions
    realized_pnl: float       # profit/loss from trades already closed
    unrealized_pnl: float     # profit/loss on currently on open positions
    updated_at: datetime
    positions: list[PositionOut]  # list of all stocks currently held

    model_config = {"from_attributes": True}



# A single trade from the user's trade history

class TradeOut(BaseModel):
    id: int
    symbol: str
    side: str             #buy or sell
    quantity: int
 fill_price: float
    slippage: float
 transaction_cost: float
  pnl: float
    executed_at: datetime

    model_config = {"from_attributes": True}
