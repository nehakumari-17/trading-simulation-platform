from pydantic import BaseModel
from datetime import datetime


# One OHLCV candle — used for candlestick charts
# OHLCV = Open, High, Low, Close, Volume
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
    ltp: float
    open: float
    high: float
    low: float
    close: float
    change: float
    change_pct: float
    volume: float
    timestamp: datetime


# One level in the order book — e.g. "100 shares at ₹2450"
class OrderBookLevel(BaseModel):
    price: float
    quantity: int


# Full order book snapshot — top 5 bids and asks
class OrderBookSnapshot(BaseModel):
    symbol: str
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    timestamp: datetime


# A stock in the search results or watchlist
class InstrumentInfo(BaseModel):
    symbol: str
    name: str
    sector: str
    last_price: float
