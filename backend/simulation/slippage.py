"""
simulation/slippage.py

Calculates realistic slippage for simulated order execution using the
volume-proportional market impact model.

Academic basis:
  Almgren & Chriss (2000) — "Optimal Execution of Portfolio Transactions"
  This is the standard model used in both academic backtesting literature
  and industry execution systems.

Core idea:
  Slippage is NOT a flat percentage. It depends on how much of the
  day's liquidity your order consumes. Buying 50 shares of RELIANCE
  (daily volume ~1.2M) barely moves the price. Buying 50,000 shares
  eats through the order book and gets a worse average fill price.

Formula:
  participation_rate = order_quantity / daily_volume
  slippage_pct       = participation_rate × volatility × impact_factor
  fill_price         = mid_price × (1 ± slippage_pct)
"""

import math
from backend.utils.data_loader import load_historical_data


# how aggressively the market moves against your order
# based on empirical studies — typically between 0.5 and 1.0
MARKET_IMPACT_FACTOR = 0.5

# minimum slippage — even tiny orders have some spread cost
# represents half the bid-ask spread
MIN_SLIPPAGE_PCT = 0.0002   # 0.02%

# maximum slippage cap — prevents absurd numbers on illiquid stocks
MAX_SLIPPAGE_PCT = 0.02     # 2.0%


def calculate_volatility(symbol: str, lookback: int = 20) -> float:
    """
    Calculates the stock's recent daily volatility from historical data.

    Uses the standard deviation of daily log returns over the last
    `lookback` candles (default 20 trading days = 1 month).

    This is important because a volatile stock like BAJFINANCE will
    have higher slippage than a stable stock like ITC.
    """
    candles = load_historical_data(symbol)

    if len(candles) < 2:
        return 0.01  # fallback — 1% volatility if no data

    # use last `lookback` candles only
    recent = candles[-lookback:] if len(candles) >= lookback else candles

    # log returns: ln(close_today / close_yesterday)
    log_returns = []
    for i in range(1, len(recent)):
        if recent[i - 1]["close"] > 0:
            ret = math.log(recent[i]["close"] / recent[i - 1]["close"])
            log_returns.append(ret)

    if not log_returns:
        return 0.01

    mean    = sum(log_returns) / len(log_returns)
    variance = sum((r - mean) ** 2 for r in log_returns) / len(log_returns)
    return math.sqrt(variance)


def calculate_slippage(
    symbol: str,
    order_quantity: int,
    current_price: float,
    side: str,           # "buy" or "sell"
    candle: dict | None = None,
) -> dict:
    """
    Main function — calculates the fill price and slippage for an order.

    Args:
        symbol:         stock symbol e.g. "RELIANCE"
        order_quantity: number of shares
        current_price:  current market price (mid price)
        side:           "buy" or "sell"
        candle:         the current historical candle (used for volume)

    Returns a dict with:
        fill_price:     the price the order actually fills at
        slippage_pct:   slippage as a percentage
        slippage_amount: total slippage cost in rupees
        participation:  what % of daily volume this order is
    """
    candles = load_historical_data(symbol)

    # get daily volume — use the current candle if provided,
    # otherwise use the average of the last 20 days
    if candle and candle.get("volume", 0) > 0:
        daily_volume = candle["volume"]
    elif candles:
        recent_volumes = [c["volume"] for c in candles[-20:] if c["volume"] > 0]
        daily_volume   = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 1_000_000
    else:
        daily_volume = 1_000_000  # safe fallback

    # what fraction of today's volume is this order?
    participation_rate = order_quantity / daily_volume

    # get volatility for this stock
    volatility = calculate_volatility(symbol)

    # core Almgren-Chriss formula
    # higher participation + higher volatility = more slippage
    slippage_pct = participation_rate * volatility * MARKET_IMPACT_FACTOR

    # clamp within min/max bounds
    slippage_pct = max(MIN_SLIPPAGE_PCT, min(slippage_pct, MAX_SLIPPAGE_PCT))

    # buy orders fill above mid-price (market moves against you)
    # sell orders fill below mid-price (same reason)
    if side == "buy":
        fill_price = round(current_price * (1 + slippage_pct), 2)
    else:
        fill_price = round(current_price * (1 - slippage_pct), 2)

    slippage_amount = round(abs(fill_price - current_price) * order_quantity, 2)

    return {
        "fill_price":      fill_price,
        "slippage_pct":    round(slippage_pct * 100, 4),   # as percentage e.g. 0.0312%
        "slippage_amount": slippage_amount,
        "participation":   round(participation_rate * 100, 4),  # % of daily volume
        "daily_volume":    daily_volume,
    }
