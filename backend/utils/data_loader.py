import os
import pandas as pd
from datetime import datetime

from backend.config import settings


# Simple in-memory cache — avoids re-reading the same CSV on every request
# Key = symbol (e.g. "RELIANCE"), Value = list of candle dicts
_cache: dict[str, list[dict]] = {}


def load_historical_data(symbol: str) -> list[dict]:
    """
    Loads OHLCV data for a stock from a CSV file.

    Expects a file named <SYMBOL>.csv inside the data/ folder.
    For example: data/RELIANCE.csv, data/TCS.csv

    The CSV must have columns: Date, Open, High, Low, Close, Volume
    Returns a list of candle dicts sorted oldest to newest.
    Returns an empty list if the file doesn't exist.
    """
    symbol = symbol.upper()

    if symbol in _cache:
        return _cache[symbol]

    file_path = os.path.join(settings.historical_data_dir, f"{symbol}.csv")

    if not os.path.exists(file_path):
        return []

    try:
        df = pd.read_csv(file_path)

        # normalize column names to lowercase so casing doesn't matter
        df.columns = [col.strip().lower() for col in df.columns]

        required = {"date", "open", "high", "low", "close", "volume"}
        if not required.issubset(set(df.columns)):
            print(f"[data_loader] {symbol}.csv is missing required columns: {required}")
            return []

        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        df = df.dropna(subset=["open", "high", "low", "close", "volume"])

        candles = []
        for _, row in df.iterrows():
            candles.append({
                "timestamp": row["date"].to_pydatetime(),
                "open":      float(row["open"]),
                "high":      float(row["high"]),
                "low":       float(row["low"]),
                "close":     float(row["close"]),
                "volume":    float(row["volume"]),
            })

        _cache[symbol] = candles
        print(f"[data_loader] Loaded {len(candles)} candles for {symbol}")
        return candles

    except Exception as e:
        print(f"[data_loader] Failed to load {symbol}.csv — {e}")
        return []


def get_latest_candle(symbol: str) -> dict | None:
    """Returns the most recent candle for a symbol."""
    candles = load_historical_data(symbol)
    if not candles:
        return None
    return candles[-1]


def get_available_symbols() -> list[str]:
    """
    Scans the data/ folder and returns all symbols that have a CSV file.
    Example: ["HDFCBANK", "INFY", "RELIANCE", "TCS"]
    """
    data_dir = settings.historical_data_dir

    if not os.path.exists(data_dir):
        return []

    symbols = []
    for filename in os.listdir(data_dir):
        if filename.endswith(".csv"):
            symbols.append(filename.replace(".csv", "").upper())

    return sorted(symbols)


def get_candles_in_range(symbol: str, start: datetime, end: datetime) -> list[dict]:
    """
    Returns candles between a start and end date (inclusive).
    Used by the strategy runner for backtesting over a specific period.
    """
    all_candles = load_historical_data(symbol)

    if not all_candles:
        return []

    return [c for c in all_candles if start <= c["timestamp"] <= end]


def clear_cache(symbol: str | None = None):
    """Clears cached data. Pass a symbol to clear just that one, or nothing to clear all."""
    if symbol:
        _cache.pop(symbol.upper(), None)
    else:
        _cache.clear()
