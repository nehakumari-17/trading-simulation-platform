from datetime import datetime
from sqlalchemy import String, Float, Integer, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from backend.database import Base



# ENUMS
# These are fixed sets of allowed values for certain columns


class OrderType(str, enum.Enum):
    MARKET = "market"   
    LIMIT  = "limit"    


class OrderSide(str, enum.Enum):
    BUY  = "buy"
    SELL = "sell"


class OrderStatus(str, enum.Enum):
    PENDING   = "pending"    # order placed, not yet filled
    FILLED    = "filled"     # order fully executed
    CANCELLED = "cancelled"  # order cancelled before execution
    REJECTED  = "rejected"   # order rejected (e.g. not enough balance)


class StrategyName(str, enum.Enum):
    MA_CROSSOVER = "ma_crossover"  # Moving Average Crossover
    RSI          = "rsi"           # RSI-Based Strategy
    VWAP         = "vwap"          # VWAP-Based Strategy



# TABLE 1: User
# Stores every registered user

class User(Base):
    __tablename__ = "users"

    id            : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    username      : Mapped[str]      = mapped_column(String(50), unique=True, nullable=False)
    email         : Mapped[str]      = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str]     = mapped_column(String(255), nullable=False)
    is_active     : Mapped[bool]     = mapped_column(Boolean, default=True)
    created_at    : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # One user has one portfolio
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="user", uselist=False)

    # One user can place many orders
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user")

# TABLE 2: Portfolio
# Tracks the cash balance and overall value for each user


class Portfolio(Base):
    __tablename__ = "portfolios"

    id            : Mapped[int]   = mapped_column(Integer, primary_key=True, index=True)
    user_id       : Mapped[int]   = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    cash_balance  : Mapped[float] = mapped_column(Float, default=1_000_000.0)  # starts with ₹10 lakh
    total_value   : Mapped[float] = mapped_column(Float, default=1_000_000.0)  # cash + holdings value
    realized_pnl  : Mapped[float] = mapped_column(Float, default=0.0)          # profit/loss from closed trades
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)          # profit/loss on open positions
    updated_at    : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user     : Mapped["User"]            = relationship("User", back_populates="portfolio")
    positions: Mapped[list["Position"]]  = relationship("Position", back_populates="portfolio")



# TABLE 3: Position
# A position is how many shares of a stock the user currently holds


class Position(Base):
    __tablename__ = "positions"

    id            : Mapped[int]   = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id  : Mapped[int]   = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    symbol        : Mapped[str]   = mapped_column(String(20), nullable=False)   # e.g. "RELIANCE", "TCS"
    quantity      : Mapped[int]   = mapped_column(Integer, default=0)           # number of shares held
    avg_buy_price : Mapped[float] = mapped_column(Float, default=0.0)           # average price paid per share
    current_price : Mapped[float] = mapped_column(Float, default=0.0)           # latest market price
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)           # (current - avg) * quantity
    updated_at    : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship back to portfolio
      portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="positions")


# TABLE 4: Order
# Every order a user places — buy or sell, market or limit


class Order(Base):
    __tablename__ = "orders"

    id          : Mapped[int]         = mapped_column(Integer, primary_key=True, index=True)
    user_id     : Mapped[int]         = mapped_column(ForeignKey("users.id"), nullable=False)
    symbol      : Mapped[str]         = mapped_column(String(20), nullable=False)
    order_type  : Mapped[OrderType]   = mapped_column(Enum(OrderType), nullable=False)
    side        : Mapped[OrderSide]   = mapped_column(Enum(OrderSide), nullable=False)
    quantity    : Mapped[int]         = mapped_column(Integer, nullable=False)
    price       : Mapped[float | None]= mapped_column(Float, nullable=True)   # only for limit orders
    filled_price: Mapped[float | None]= mapped_column(Float, nullable=True)   # actual price it was filled at
    slippage    : Mapped[float | None]= mapped_column(Float, nullable=True)   # difference due to slippage
    status      : Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING)
    created_at  : Mapped[datetime]    = mapped_column(DateTime, default=datetime.utcnow)
    filled_at   : Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationship back to user
    user: Mapped["User"] = relationship("User", back_populates="orders")



# TABLE 5: Trade
# A trade is created when an order gets filled


class Trade(Base):
    __tablename__ = "trades"

    id          : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    user_id     : Mapped[int]      = mapped_column(ForeignKey("users.id"), nullable=False)
    order_id    : Mapped[int]      = mapped_column(ForeignKey("orders.id"), nullable=False)
    symbol      : Mapped[str]      = mapped_column(String(20), nullable=False)
    side        : Mapped[OrderSide]= mapped_column(Enum(OrderSide), nullable=False)
    quantity    : Mapped[int]      = mapped_column(Integer, nullable=False)
    fill_price  : Mapped[float]    = mapped_column(Float, nullable=False)        # price at which it was executed
    slippage    : Mapped[float]    = mapped_column(Float, default=0.0)           # slippage cost on this trade
    transaction_cost: Mapped[float]= mapped_column(Float, default=0.0)          # brokerage/fees
    pnl         : Mapped[float]    = mapped_column(Float, default=0.0)           # profit or loss on this trade
    executed_at : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)



# TABLE 6: StrategyRun
# Records every time a user runs an algorithmic strategy


class StrategyRun(Base):
    __tablename__ = " strategy_runs "

     id           : Mapped[int]          = mapped_column(Integer, primary_key=True, index=True)
    user_id      : Mapped[int]          = mapped_column(ForeignKey("users.id"), nullable=False)
    strategy_name: Mapped[StrategyName] = mapped_column(Enum(StrategyName), nullable=False)
    symbol       : Mapped[str]          = mapped_column(String(20), nullable=False)
    start_date   : Mapped[str]          = mapped_column(String(20), nullable=False)  # "2024-01-01"
    end_date     : Mapped[str]          = mapped_column(String(20), nullable=False)  # "2024-12-31"

    # Results stored after the strategy finishes running
     total_return  : Mapped[float | None] = mapped_column(Float, nullable=True)
     sharpe_ratio  : Mapped[float | None] = mapped_column(Float, nullable=True)
     max_drawdown  : Mapped[float | None] = mapped_column(Float, nullable=True)
    win_rate      : Mapped[float | None] = mapped_column(Float, nullable=True)
     profit_factor : Mapped[float | None] = mapped_column(Float, nullable=True)
    total_trades  : Mapped[int | None]   = mapped_column(Integer, nullable=True)

     created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
