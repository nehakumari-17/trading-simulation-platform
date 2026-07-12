from datetime import datetime
from sqlalchemy import String, Float, Integer, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from backend.database import Base


# Enums are fixed sets of allowed values for certain columns.
# SQLAlchemy stores them as strings in the DB.

class OrderType(str, enum.Enum):
    MARKET = "market"
    LIMIT  = "limit"


class OrderSide(str, enum.Enum):
    BUY  = "buy"
    SELL = "sell"


class OrderStatus(str, enum.Enum):
    PENDING   = "pending"
    FILLED    = "filled"
    CANCELLED = "cancelled"
    REJECTED  = "rejected"


class StrategyName(str, enum.Enum):
    MA_CROSSOVER = "ma_crossover"
    RSI          = "rsi"
    VWAP         = "vwap"


# ── TABLE 1: User ─────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id             : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    username       : Mapped[str]      = mapped_column(String(50), unique=True, nullable=False)
    email          : Mapped[str]      = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str]      = mapped_column(String(255), nullable=False)
    is_active      : Mapped[bool]     = mapped_column(Boolean, default=True)
    created_at     : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    portfolio: Mapped["Portfolio"]  = relationship("Portfolio", back_populates="user", uselist=False)
    orders   : Mapped[list["Order"]] = relationship("Order", back_populates="user")


# ── TABLE 2: Portfolio ────────────────────────────────────────────────────────

class Portfolio(Base):
    __tablename__ = "portfolios"

    id            : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    user_id       : Mapped[int]      = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    cash_balance  : Mapped[float]    = mapped_column(Float, default=1_000_000.0)
    total_value   : Mapped[float]    = mapped_column(Float, default=1_000_000.0)
    realized_pnl  : Mapped[float]    = mapped_column(Float, default=0.0)
    unrealized_pnl: Mapped[float]    = mapped_column(Float, default=0.0)
    updated_at    : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user     : Mapped["User"]           = relationship("User", back_populates="portfolio")
    positions: Mapped[list["Position"]] = relationship("Position", back_populates="portfolio")


# ── TABLE 3: Position ─────────────────────────────────────────────────────────
# One row per stock per user — tracks how many shares they hold

class Position(Base):
    __tablename__ = "positions"

    id            : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id  : Mapped[int]      = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    symbol        : Mapped[str]      = mapped_column(String(20), nullable=False)
    quantity      : Mapped[int]      = mapped_column(Integer, default=0)
    avg_buy_price : Mapped[float]    = mapped_column(Float, default=0.0)
    current_price : Mapped[float]    = mapped_column(Float, default=0.0)
    unrealized_pnl: Mapped[float]    = mapped_column(Float, default=0.0)
    updated_at    : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="positions")


# ── TABLE 4: Order ────────────────────────────────────────────────────────────
# Every order a user places — buy or sell, market or limit

class Order(Base):
    __tablename__ = "orders"

    id           : Mapped[int]              = mapped_column(Integer, primary_key=True, index=True)
    user_id      : Mapped[int]              = mapped_column(ForeignKey("users.id"), nullable=False)
    symbol       : Mapped[str]              = mapped_column(String(20), nullable=False)
    order_type   : Mapped[OrderType]        = mapped_column(Enum(OrderType), nullable=False)
    side         : Mapped[OrderSide]        = mapped_column(Enum(OrderSide), nullable=False)
    quantity     : Mapped[int]              = mapped_column(Integer, nullable=False)
    price        : Mapped[float | None]     = mapped_column(Float, nullable=True)
    filled_price : Mapped[float | None]     = mapped_column(Float, nullable=True)
    slippage     : Mapped[float | None]     = mapped_column(Float, nullable=True)
    status       : Mapped[OrderStatus]      = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING)
    created_at   : Mapped[datetime]         = mapped_column(DateTime, default=datetime.utcnow)
    filled_at    : Mapped[datetime | None]  = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="orders")


# ── TABLE 5: Trade ────────────────────────────────────────────────────────────
# Created only when an order gets filled — the permanent execution record

class Trade(Base):
    __tablename__ = "trades"

    id              : Mapped[int]       = mapped_column(Integer, primary_key=True, index=True)
    user_id         : Mapped[int]       = mapped_column(ForeignKey("users.id"), nullable=False)
    order_id        : Mapped[int]       = mapped_column(ForeignKey("orders.id"), nullable=False)
    symbol          : Mapped[str]       = mapped_column(String(20), nullable=False)
    side            : Mapped[OrderSide] = mapped_column(Enum(OrderSide), nullable=False)
    quantity        : Mapped[int]       = mapped_column(Integer, nullable=False)
    fill_price      : Mapped[float]     = mapped_column(Float, nullable=False)
    slippage        : Mapped[float]     = mapped_column(Float, default=0.0)
    transaction_cost: Mapped[float]     = mapped_column(Float, default=0.0)
    pnl             : Mapped[float]     = mapped_column(Float, default=0.0)
    executed_at     : Mapped[datetime]  = mapped_column(DateTime, default=datetime.utcnow)


# ── TABLE 6: StrategyRun ──────────────────────────────────────────────────────
# Records every time a user runs a backtest strategy

class StrategyRun(Base):
    __tablename__ = "strategy_runs"

    id           : Mapped[int]          = mapped_column(Integer, primary_key=True, index=True)
    user_id      : Mapped[int]          = mapped_column(ForeignKey("users.id"), nullable=False)
    strategy_name: Mapped[StrategyName] = mapped_column(Enum(StrategyName), nullable=False)
    symbol       : Mapped[str]          = mapped_column(String(20), nullable=False)
    start_date   : Mapped[str]          = mapped_column(String(20), nullable=False)
    end_date     : Mapped[str]          = mapped_column(String(20), nullable=False)

    total_return : Mapped[float | None] = mapped_column(Float, nullable=True)
    sharpe_ratio : Mapped[float | None] = mapped_column(Float, nullable=True)
    max_drawdown : Mapped[float | None] = mapped_column(Float, nullable=True)
    win_rate     : Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_trades : Mapped[int | None]   = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
