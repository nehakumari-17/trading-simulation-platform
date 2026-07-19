"""
simulation/order_book.py

Generates a synthetic limit order book snapshot from historical OHLCV data.

This is purely visual — it populates the market depth panel in the frontend
(5 bid levels + 5 ask levels). It does NOT affect order execution.
Actual fills use matching.py which works directly from OHLCV candles.

How it works:
  1. Take the current mid-price (close of latest candle)
  2. Calculate the bid-ask spread from the stock's recent volatility
     (volatile stocks have wider spreads)
  3. Generate 5 price levels on each side at equal spacing
  4. Assign realistic quantities — more volume further from mid-price
     because that's how real order books look (thin at top, deep further out)

This approach is described in standard market microstructure literature
as a reasonable approximation when full LOB (Level 2) data is unavailable.
"""

import random
import math
from backend.simulation.slippage import calculate_volatility


# number of bid and ask levels to generate
DEPTH_LEVELS = 5

# how many ticks between each price level
# we calculate this dynamically from volatility but set a floor
MIN_TICK_SPACING = 0.05   # minimum ₹0.05 between levels


def _calculate_spread(price: float, volatility: float) -> float:
    """
    Estimates a realistic bid-ask spread.

    Higher volatility = wider spread (market makers charge more
    for taking on risk in a volatile stock).

    Typical spreads on NSE:
      Low  volatility (ITC, HINDUNILVR) → ~0.05% of price
      High volatility (BAJFINANCE)      → ~0.15% of price
    """
    # spread is proportional to daily volatility
    # roughly 10% of daily vol is a reasonable intraday spread estimate
    spread_pct = max(0.0005, volatility * 0.10)
    spread     = round(price * spread_pct, 2)
    return max(spread, MIN_TICK_SPACING)


def _generate_quantities(base_qty: int, level: int) -> int:
    """
    Generates quantity at a given order book level.

    Level 1 (closest to mid) has the least quantity — tight spreads
    are usually thin. Deeper levels have more — resting orders accumulate.

    Adds a small random variation so it looks natural, not mechanical.
    """
    # quantity grows as you go deeper into the book
    multiplier = 1 + (level * 0.6)
    qty        = int(base_qty * multiplier)

    # add ±20% randomness so consecutive snapshots look different
    variation  = random.uniform(0.80, 1.20)
    return max(1, int(qty * variation))


def generate_order_book(symbol: str, current_price: float) -> dict:
    """
    Generates a full order book snapshot for a symbol.

    Args:
        symbol:        stock symbol e.g. "RELIANCE"
        current_price: current market price (from latest candle close)

    Returns:
        {
          "symbol":    "RELIANCE",
          "bids": [{"price": 1292.50, "quantity": 200}, ...],  # 5 levels
          "asks": [{"price": 1293.50, "quantity": 150}, ...],  # 5 levels
          "spread":    1.00,
          "mid_price": 1293.00,
        }
    """
    volatility = calculate_volatility(symbol)
    spread     = _calculate_spread(current_price, volatility)

    # tick spacing between levels — scales with price and volatility
    # bigger, more volatile stocks have larger gaps between levels
    tick_spacing = max(MIN_TICK_SPACING, round(current_price * volatility * 0.5, 2))

    # base quantity — rough estimate of typical order size for this stock
    # scales inversely with price (cheaper stocks trade in bigger lots)
    if current_price > 5000:
        base_qty = 10
    elif current_price > 1000:
        base_qty = 50
    elif current_price > 200:
        base_qty = 200
    else:
        base_qty = 500

    bids = []
    asks = []

    for level in range(DEPTH_LEVELS):
        # bids go downward from mid-price minus half spread
        bid_price = round(current_price - (spread / 2) - (level * tick_spacing), 2)

        # asks go upward from mid-price plus half spread
        ask_price = round(current_price + (spread / 2) + (level * tick_spacing), 2)

        bids.append({
            "price":    bid_price,
            "quantity": _generate_quantities(base_qty, level),
        })
        asks.append({
            "price":    ask_price,
            "quantity": _generate_quantities(base_qty, level),
        })

    # bids should be sorted highest first (best bid at top)
    # asks should be sorted lowest first (best ask at top)
    bids.sort(key=lambda x: x["price"], reverse=True)
    asks.sort(key=lambda x: x["price"])

    return {
        "symbol":    symbol,
        "bids":      bids,
        "asks":      asks,
        "spread":    round(spread, 2),
        "mid_price": round(current_price, 2),
    }


def get_best_bid_ask(symbol: str, current_price: float) -> dict:
    """
    Returns just the best bid and best ask (top of book).
    Used when you only need the spread, not the full depth.
    """
    book = generate_order_book(symbol, current_price)
    return {
        "best_bid": book["bids"][0]["price"] if book["bids"] else None,
        "best_ask": book["asks"][0]["price"] if book["asks"] else None,
        "spread":   book["spread"],
    }
