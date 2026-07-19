"""
simulation/matching.py

Order matching logic for historical data replay simulation.

Academic basis:
  "Backtest of Trading Systems on Candle Charts"
  Stachurski & Stachurski (ResearchGate, 2014)

  This is the standard approach for simulating order execution
  when only OHLCV candle data is available (not tick data).

Rules used:
  Market order  → fills at the OPEN of the NEXT candle
                  (simulates execution latency — you placed the order
                  at close of candle N, it executes at open of candle N+1)

  Limit BUY     → fills if candle LOW <= limit price
                  (the price dipped to your level during that candle)

  Limit SELL    → fills if candle HIGH >= limit price
                  (the price rose to your level during that candle)

  Fill price for limit orders:
    We use the limit price itself as the fill — conservative assumption.
    In reality you might get a better fill but we don't assume that.

  Slippage:
    Applied on top of the calculated fill price using simulation/slippage.py
    Market orders have higher slippage (less control over execution)
    Limit orders have lower slippage (you control the price)
"""

from backend.simulation.slippage import calculate_slippage


def check_market_order(
    symbol: str,
    side: str,
    quantity: int,
    next_candle: dict,
) -> dict:
    """
    Market orders fill at the open of the next candle.

    This is realistic — when you hit "buy at market", your order goes
    to the exchange and fills at the current best price. In a daily
    simulation that means the next day's open.

    Args:
        symbol:      stock symbol
        side:        "buy" or "sell"
        quantity:    number of shares
        next_candle: the candle after the order was placed

    Returns fill details or None if no next candle yet.
    """
    if next_candle is None:
        # no next candle available yet — order stays pending
        return None

    base_price = next_candle["open"]

    # calculate realistic slippage based on volume
    slip = calculate_slippage(
        symbol        = symbol,
        order_quantity = quantity,
        current_price  = base_price,
        side           = side,
        candle         = next_candle,
    )

    return {
        "filled":          True,
        "fill_price":      slip["fill_price"],
        "slippage_amount": slip["slippage_amount"],
        "slippage_pct":    slip["slippage_pct"],
        "fill_type":       "market",
        "candle_date":     next_candle["timestamp"],
    }


def check_limit_order(
    symbol: str,
    side: str,
    quantity: int,
    limit_price: float,
    current_candle: dict,
) -> dict | None:
    """
    Limit orders fill only if the candle's price range includes the limit price.

    BUY  limit: fills if candle LOW  <= limit_price
    SELL limit: fills if candle HIGH >= limit_price

    If not triggered, returns None — order stays pending and will be
    checked again on the next candle.

    Args:
        symbol:         stock symbol
        side:           "buy" or "sell"
        quantity:       number of shares
        limit_price:    the price the user specified
        current_candle: the candle being evaluated

    Returns fill details or None if not triggered.
    """
    triggered = False

    if side == "buy":
        # price dipped to or below our limit — we can buy
        triggered = current_candle["low"] <= limit_price
    else:
        # price rose to or above our limit — we can sell
        triggered = current_candle["high"] >= limit_price

    if not triggered:
        return None

    # for limit orders, fill at the limit price (conservative)
    # slippage is much smaller since we control the price
    slip = calculate_slippage(
        symbol         = symbol,
        order_quantity = quantity,
        current_price  = limit_price,
        side           = side,
        candle         = current_candle,
    )

    return {
        "filled":          True,
        "fill_price":      slip["fill_price"],
        "slippage_amount": slip["slippage_amount"],
        "slippage_pct":    slip["slippage_pct"],
        "fill_type":       "limit",
        "candle_date":     current_candle["timestamp"],
    }


def match_order(
    symbol: str,
    order_type: str,        # "market" or "limit"
    side: str,              # "buy" or "sell"
    quantity: int,
    limit_price: float | None,
    current_candle: dict,
    next_candle: dict | None,
) -> dict | None:
    """
    Main entry point — routes to the right matching function
    based on order type.

    Called by the simulation engine on every candle tick for
    all pending orders.

    Returns fill details dict if filled, None if not yet filled.
    """
    if order_type == "market":
        return check_market_order(
            symbol      = symbol,
            side        = side,
            quantity    = quantity,
            next_candle = next_candle,
        )
    else:
        # limit order
        if limit_price is None:
            return None  # shouldn't happen but guard against it

        return check_limit_order(
            symbol          = symbol,
            side            = side,
            quantity        = quantity,
            limit_price     = limit_price,
            current_candle  = current_candle,
        )
