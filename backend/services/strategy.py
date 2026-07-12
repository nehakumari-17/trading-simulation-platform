import math
import pandas as pd
from datetime import datetime

from backend.utils.data_loader import get_candles_in_range


def run_ma_crossover(symbol: str, start_date: str, end_date: str, short_window: int = 20, long_window: int = 50) -> dict:
    """Moving Average Crossover — BUY on golden cross, SELL on death cross."""
    candles = _load_candles(symbol, start_date, end_date)
    if candles is None:
        return _empty_result("Not enough data for MA Crossover strategy.")

    df = candles.copy()
    df["ma_short"] = df["close"].rolling(window=short_window).mean()
    df["ma_long"]  = df["close"].rolling(window=long_window).mean()
    df = df.dropna(subset=["ma_short", "ma_long"]).reset_index(drop=True)

    if df.empty:
        return _empty_result("Not enough candles to compute moving averages.")

    trades   = []
    position = None

    for i in range(1, len(df)):
        prev, curr = df.iloc[i - 1], df.iloc[i]
        golden_cross = prev["ma_short"] <= prev["ma_long"] and curr["ma_short"] > curr["ma_long"]
        death_cross  = prev["ma_short"] >= prev["ma_long"] and curr["ma_short"] < curr["ma_long"]

        if golden_cross and position is None:
            position = {"entry_price": curr["close"], "entry_date": curr["date"]}
        elif death_cross and position is not None:
            trades.append(_make_trade(position, curr, "MA Crossover"))
            position = None

    return _build_result(trades, symbol, start_date, end_date, "ma_crossover")


def run_rsi_strategy(symbol: str, start_date: str, end_date: str, period: int = 14, oversold: int = 30, overbought: int = 70) -> dict:
    """RSI Strategy — BUY when oversold, SELL when overbought."""
    candles = _load_candles(symbol, start_date, end_date)
    if candles is None:
        return _empty_result("Not enough data for RSI strategy.")

    df = candles.copy()
    df["rsi"] = _calculate_rsi(df["close"], period)
    df = df.dropna(subset=["rsi"]).reset_index(drop=True)

    if df.empty:
        return _empty_result("Not enough candles to compute RSI.")

    trades   = []
    position = None

    for i in range(1, len(df)):
        prev, curr = df.iloc[i - 1], df.iloc[i]

        if prev["rsi"] < oversold and curr["rsi"] >= oversold and position is None:
            position = {"entry_price": curr["close"], "entry_date": curr["date"]}
        elif curr["rsi"] > overbought and position is not None:
            trades.append(_make_trade(position, curr, f"RSI({period})"))
            position = None

    return _build_result(trades, symbol, start_date, end_date, "rsi")


def run_vwap_strategy(symbol: str, start_date: str, end_date: str) -> dict:
    """VWAP Strategy — BUY when price crosses above VWAP, SELL when it drops below."""
    candles = _load_candles(symbol, start_date, end_date)
    if candles is None:
        return _empty_result("Not enough data for VWAP strategy.")

    df = candles.copy()
    df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3
    df["tp_vol"]        = df["typical_price"] * df["volume"]
    df["cum_tp_vol"]    = df["tp_vol"].rolling(window=20).sum()
    df["cum_vol"]       = df["volume"].rolling(window=20).sum()
    df["vwap"]          = df["cum_tp_vol"] / df["cum_vol"]
    df = df.dropna(subset=["vwap"]).reset_index(drop=True)

    if df.empty:
        return _empty_result("Not enough candles to compute VWAP.")

    trades   = []
    position = None

    for i in range(1, len(df)):
        prev, curr = df.iloc[i - 1], df.iloc[i]
        above_vwap = prev["close"] <= prev["vwap"] and curr["close"] > curr["vwap"]
        below_vwap = prev["close"] >= prev["vwap"] and curr["close"] < curr["vwap"]

        if above_vwap and position is None:
            position = {"entry_price": curr["close"], "entry_date": curr["date"]}
        elif below_vwap and position is not None:
            trades.append(_make_trade(position, curr, "VWAP Cross"))
            position = None

    return _build_result(trades, symbol, start_date, end_date, "vwap")


def _load_candles(symbol: str, start_date: str, end_date: str) -> pd.DataFrame | None:
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end   = datetime.strptime(end_date,   "%Y-%m-%d")
    except ValueError:
        return None

    candles = get_candles_in_range(symbol.upper(), start, end)
    if len(candles) < 60:
        return None

    df = pd.DataFrame(candles)
    df.rename(columns={"timestamp": "date"}, inplace=True)
    return df


def _make_trade(position: dict, curr, signal: str) -> dict:
    pnl = curr["close"] - position["entry_price"]
    return {
        "entry_date":  str(position["entry_date"].date()),
        "exit_date":   str(curr["date"].date()),
        "entry_price": round(position["entry_price"], 2),
        "exit_price":  round(curr["close"], 2),
        "pnl":         round(pnl, 2),
        "signal":      signal,
    }


def _calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    delta    = prices.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs       = avg_gain / avg_loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def _build_result(trades: list, symbol: str, start_date: str, end_date: str, strategy_name: str) -> dict:
    if not trades:
        return _empty_result("Strategy ran but generated no trades in this period.")

    pnl_list     = [t["pnl"] for t in trades]
    wins         = [p for p in pnl_list if p > 0]
    losses       = [p for p in pnl_list if p <= 0]
    total_trades = len(pnl_list)
    total_return = round(sum(pnl_list), 2)
    win_rate     = round(len(wins) / total_trades * 100, 2)
    avg_pnl      = round(total_return / total_trades, 2)
    gross_profit = sum(wins)
    gross_loss   = abs(sum(losses)) if losses else 0
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0.0

    peak = running = max_dd = 0.0
    for pnl in pnl_list:
        running += pnl
        if running > peak:
            peak = running
        dd = peak - running
        if dd > max_dd:
            max_dd = dd

    if total_trades >= 2:
        mean     = total_return / total_trades
        variance = sum((x - mean) ** 2 for x in pnl_list) / (total_trades - 1)
        std_dev  = math.sqrt(variance)
        sharpe   = round(mean / std_dev, 2) if std_dev > 0 else 0.0
    else:
        sharpe = 0.0

    return {
        "strategy":     strategy_name,
        "symbol":       symbol,
        "start_date":   start_date,
        "end_date":     end_date,
        "total_trades": total_trades,
        "total_return": total_return,
        "win_rate":     win_rate,
        "avg_pnl":      avg_pnl,
        "profit_factor":profit_factor,
        "max_drawdown": round(max_dd, 2),
        "sharpe_ratio": sharpe,
        "trades":       trades,
    }


def _empty_result(reason: str) -> dict:
    return {
        "strategy": None, "symbol": None, "start_date": None, "end_date": None,
        "total_trades": 0, "total_return": 0.0, "win_rate": 0.0, "avg_pnl": 0.0,
        "profit_factor": 0.0, "max_drawdown": 0.0, "sharpe_ratio": 0.0,
        "trades": [], "message": reason,
    }
