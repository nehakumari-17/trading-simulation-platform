from pydantic import BaseModel
from datetime import datetime

     # One OHLCV candle — used for candlestick charts
     #OHLCV = Open, High, Low, Close, Volume

  class Candle(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float



  # Current price quote for a stock
  # Shown in the top bar of the trading UI

class Quote(BaseModel):
    symbol: str
    ltp: float          # Last Traded Price
    open: float
    high: float
    low: float
    close: float        # previous day close
    change: float       # ltp - close
    change_pct: float   # percentage change
    volume: float
    timestamp: datetime


# One level in the order book (bid or ask)
# e.g. "100 shares available at ₹2450"

class OrderBookLevel(BaseModel):
    price: float
    quantity: int



# Full order book view

class OrderBookSnapshot(BaseModel):
    symbol: str
    bids: list[OrderBookLevel]   # top 5 buy prices
    asks: list[OrderBookLevel]   # top 5 sell prices
    timestamp: datetime


#A stock in the search results or watchlist

class InstrumentInfo(BaseModel):
    symbol: str
    name: str            # e.g. "Reliance Industries Ltd"
    sector: str          # e.g. "Energy"
    last_price: float
