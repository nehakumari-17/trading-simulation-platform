"""
simulation/market_models.py

Historical data replay price model.

Instead of generating synthetic prices using GBM (which produces
random, made-up numbers), this module replays real historical OHLCV
candles from our CSV files as if they are happening live.

Within each daily candle, we simulate a small number of intraday
price points that stay within the candle's actual High/Low bounds.
This gives a live price feed that feels realistic because it IS
derived from real market data.

Approach:
  - Load all candles for a symbol from the CSV
  - Keep a pointer to the "current" candle index
  - Each tick, either:
      a. Move within the current candle (intraday simulation)
      b. Advance to the next candle when the intraday steps are done
  - Push the current price to subscribers

Academic basis:
  OHLCV candle replay is the standard historical simulation approach
  described in backtesting literature. The intraday path is simulated
  to stay within [Low, High] bounds, which is consistent with the
  "Backtest of Trading Systems on Candle Charts" methodology.
"""

import math
import random
from dataclasses import dataclass, field
from datetime import datetime

from backend.utils.data_loader import load_historical_data


# how many intraday price points to simulate per daily candle
# lower = faster replay, higher = smoother intraday movement
INTRADAY_STEPS = 8


@dataclass
class SymbolState:
    """
    Tracks the current replay state for one symbol.
    One instance per symbol, held in the engine.
    """
    symbol:          str
    candles:         list       # all historical candles loaded from CSV
    candle_index:    int = 0    # which candle we are currently on
    step_index:      int = 0    # which intraday step within the candle
    current_price:   float = 0.0
    intraday_path:   list = field(default_factory=list)  # pre-computed steps

    # stats calculated from history — used by order book and slippage
    volatility:      float = 0.01
    daily_volume:    float = 1_000_000.0


def _simulate_intraday_path(candle: dict, steps: int) -> list[float]:
    """
    Generates `steps` price points that simulate intraday movement
    within the bounds of a single OHLCV candle.

    Rules:
      - Start at Open
      - End at Close
      - Never go above High or below Low
      - Path has some randomness but looks smooth

    This is a simple linear interpolation with bounded random noise —
    good enough for a simulation platform and academically justified
    as a candle-consistent intraday model.
    """
    o = candle["open"]
    h = candle["high"]
    l = candle["low"]
    c = candle["close"]

    path = [o]

    for i in range(1, steps - 1):
        # interpolate between open and close as the base path
        progress   = i / (steps - 1)
        base_price = o + (c - o) * progress

        # add noise scaled by the candle's range
        candle_range = h - l
        noise        = random.uniform(-0.3, 0.3) * candle_range * 0.2
        price        = base_price + noise

        # clamp within the candle's actual High/Low bounds
        price = max(l, min(h, price))
        path.append(round(price, 2))

    path.append(c)  # always end at close
    return path


def _calculate_volatility(candles: list, lookback: int = 20) -> float:
    """
    Calculates daily volatility from recent log returns.
    Same formula as slippage.py — kept here so market_models
    doesn't need to import from slippage (avoid circular deps).
    """
    if len(candles) < 2:
        return 0.01

    recent = candles[-lookback:] if len(candles) >= lookback else candles
    log_returns = []
    for i in range(1, len(recent)):
        if recent[i - 1]["close"] > 0:
            ret = math.log(recent[i]["close"] / recent[i - 1]["close"])
            log_returns.append(ret)

    if not log_returns:
        return 0.01

    mean     = sum(log_returns) / len(log_returns)
    variance = sum((r - mean) ** 2 for r in log_returns) / len(log_returns)
    return math.sqrt(variance)


def initialize_symbol(symbol: str) -> SymbolState | None:
    """
    Loads historical data for a symbol and sets up the replay state.
    Returns None if no data is available for the symbol.

    Called once per symbol when the engine starts.
    """
    candles = load_historical_data(symbol.upper())

    if not candles:
        print(f"[market_models] No data for {symbol} — skipping")
        return None

    # start from the beginning of available data
    # the engine will step through candles one by one
    initial_candle = candles[0]
    intraday_path  = _simulate_intraday_path(initial_candle, INTRADAY_STEPS)

    # calculate recent volume and volatility for context
    vol        = _calculate_volatility(candles)
    avg_volume = sum(c["volume"] for c in candles[-20:]) / min(20, len(candles))

    state = SymbolState(
        symbol        = symbol.upper(),
        candles       = candles,
        candle_index  = 0,
        step_index    = 0,
        current_price = initial_candle["open"],
        intraday_path = intraday_path,
        volatility    = vol,
        daily_volume  = avg_volume,
    )

    print(f"[market_models] Loaded {len(candles)} candles for {symbol}")
    return state


def next_tick(state: SymbolState) -> dict:
    """
    Advances the simulation by one tick and returns the new price.

    Each call either:
      a. Moves to the next intraday step within the current candle
      b. Advances to the next candle when intraday steps are exhausted

    Returns a tick dict with price and candle info for the engine to use.
    """
    candle = state.candles[state.candle_index]

    # get the current price from our pre-computed intraday path
    if state.step_index < len(state.intraday_path):
        price = state.intraday_path[state.step_index]
    else:
        price = candle["close"]

    state.current_price = price
    state.step_index   += 1

    # if we've exhausted the intraday steps, move to the next candle
    if state.step_index >= len(state.intraday_path):
        if state.candle_index < len(state.candles) - 1:
            state.candle_index += 1
            next_candle         = state.candles[state.candle_index]
            state.intraday_path = _simulate_intraday_path(next_candle, INTRADAY_STEPS)
            state.step_index    = 0

            # update rolling stats
            state.volatility    = _calculate_volatility(
                state.candles[:state.candle_index + 1]
            )
            recent_vols         = state.candles[max(0, state.candle_index - 19):state.candle_index + 1]
            state.daily_volume  = sum(c["volume"] for c in recent_vols) / len(recent_vols)
        # if we've reached the end of history, hold at last close
        # in a real system you'd loop or fetch new data

    return {
        "symbol":        state.symbol,
        "price":         price,
        "candle":        candle,
        "candle_index":  state.candle_index,
        "step_index":    state.step_index,
        "is_new_candle": state.step_index == 1,  # True on first tick of each candle
    }


def get_current_candle(state: SymbolState) -> dict:
    """Returns the candle currently being replayed."""
    return state.candles[state.candle_index]


def get_next_candle(state: SymbolState) -> dict | None:
    """
    Returns the next candle in the sequence.
    Used by matching.py to fill market orders at next open.
    """
    idx = state.candle_index + 1
    if idx < len(state.candles):
        return state.candles[idx]
    return None
