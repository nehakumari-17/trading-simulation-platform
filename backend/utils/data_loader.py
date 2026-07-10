import os
import pandas as pd
from datetime import datetime

from backend.config import settings




#Key = symbol(e.g. "RELIANCE"), Value = list of candle dicts


   _cache: dict[str, list[dict]] = {}


 def load_historical_data(symbol: str) -> list[dict]:
    """
     Loads OHLCV data for a stock from a CSV file.

    Expects a file named <SYMBOL>.csv inside the data/ folder.
    For example: data/RELIANCE.csv, data/TCS.csv

    The CSV must have these columns (case-insensitive):
        Date, Open, High, Low, Close, Volume

     Returns a list of candle dicts sorted oldest to newest.
     Returns an empty list if the file doesn't exist.

    """
    symbol = symbol.upper()

    # return from cache if already loaded
        if symbol in _cache:
        return _cache[symbol]

    file_path = os.path.join(settings.historical_data_dir, f"{symbol}.csv")

    if not os.path.exists(file_path):
        return []

    try:
        df = pd.read_csv(file_path)

        # normalize column names to lowercase so casing doesn't matter
        df.columns = [col.strip().lower() for col in df.columns]

        # make sure all the columns we need are actually there
        required = {"date", "open", "high", "low", "close", "volume"}
        if not required.issubset(set(df.columns)):
            print(f"[data_loader] {symbol}.csv is missing required columns. Expected: {required}")
            return []

        # parse the date column into actual datetime objects
        df["date"] = pd.to_datetime(df["date"])
         df = df.sort_values("date").reset_index(drop=True)

        # drop any rows where the price columns have missing values
        df = df.dropna(subset=["open", "high", "low", "close", "volume"])

        #convert each row into a plain dict for easy JSON serialization
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

        # store in cache so next request is instant
        _cache[symbol] = candles
        print(f"[data_loader] Loaded {len(candles)} candles for {symbol}")
        return candles

      except Exception as e:
        print(f"[data_loader] Failed to load {symbol}.csv — {e}")
        return []


   def get_latest_candle(symbol: str) -> dict | None:
    """
    Returns just the most recent candle for a symbol.
    Used to get the current price quickly without loading everything.
    """
     candles = load_historical_data(symbol)
    if not candles:
        return None
    return candles[-1]


  def get_available_symbols() -> list[str]:
    """
    Scans the data/ folder and returns a list of all symbols
    that have a CSV file available.

    Example return: ["RELIANCE", "TCS", "INFY", "HDFCBANK"]
    """
    data_dir = settings.historical_data_dir

    if not os.path.exists(data_dir):
        return []

    symbols = []
    for filename in os.listdir(data_dir):
         if filename.endswith(".csv"):
            symbol = filename.replace(".csv", "").upper()
            symbols.append(symbol)

     return sorted(symbols)


      def get_candles_in_range(symbol: str, start: datetime, end: datetime) -> list[dict]:
    """
      Returns candles for a symbol between a start and end date.
      Used by the strategy runner to get data for a specific backtest period.
    """
    all_candles = load_historical_data(symbol)

     if not all_candles:
        return []

    filtered = [
        c for c in all_candles
        if start <= c["timestamp"] <= end
    ]

    return filtered


def clear_cache(symbol: str | None = None):
    """
    Clears the in-memory cache.
    Pass a symbol to clear just that one, or nothing to clear everything.
    Useful in tests or when CSV files are updated.
    """
    if symbol:
        _cache.pop(symbol.upper(), None)
    else:
        _cache.clear()
