from datetime import datetime

from backend.utils.data_loader import (
    load_historical_data,
    get_latest_candle,
    get_available_symbols,
    get_candles_in_range,
)


INSTRUMENT_INFO = {
    "RELIANCE":   {"name": "Reliance Industries Ltd",       "sector": "Energy"},
    "TCS":        {"name": "Tata Consultancy Services Ltd", "sector": "IT"},
    "INFY":       {"name": "Infosys Ltd",                   "sector": "IT"},
    "HDFCBANK":   {"name": "HDFC Bank Ltd",                 "sector": "Banking"},
    "ICICIBANK":  {"name": "ICICI Bank Ltd",                "sector": "Banking"},
    "SBIN":       {"name": "State Bank of India",           "sector": "Banking"},
    "WIPRO":      {"name": "Wipro Ltd",                     "sector": "IT"},
    "AXISBANK":   {"name": "Axis Bank Ltd",                 "sector": "Banking"},
    "BAJFINANCE": {"name": "Bajaj Finance Ltd",             "sector": "Finance"},
    "TATAMOTORS": {"name": "Tata Motors Ltd",               "sector": "Auto"},
    "MARUTI":     {"name": "Maruti Suzuki India Ltd",       "sector": "Auto"},
    "SUNPHARMA":  {"name": "Sun Pharmaceutical Industries", "sector": "Pharma"},
    "LTIM":       {"name": "LTIMindtree Ltd",               "sector": "IT"},
    "HINDUNILVR": {"name": "Hindustan Unilever Ltd",        "sector": "FMCG"},
    "ITC":        {"name": "ITC Ltd",                       "sector": "FMCG"},
}


async def get_latest_price(symbol: str) -> float | None:
    """Returns the latest closing price for a symbol. Used by order execution."""
    candle = get_latest_candle(symbol.upper())
    if candle is None:
        return None
    return candle["close"]


async def get_quote(symbol: str) -> dict | None:
    """Builds a full price quote — LTP, change, change%, volume."""
    symbol  = symbol.upper()
    candles = load_historical_data(symbol)

    if not candles:
        return None

    latest     = candles[-1]
    prev_close = candles[-2]["close"] if len(candles) >= 2 else latest["open"]
    change     = round(latest["close"] - prev_close, 2)
    change_pct = round((change / prev_close) * 100, 2) if prev_close else 0.0

    return {
        "symbol":     symbol,
        "ltp":        latest["close"],
        "open":       latest["open"],
        "high":       latest["high"],
        "low":        latest["low"],
        "close":      prev_close,
        "change":     change,
        "change_pct": change_pct,
        "volume":     latest["volume"],
        "timestamp":  latest["timestamp"],
    }


async def get_candles(symbol: str, interval: str = "1d", limit: int = 100) -> list[dict]:
    """Returns the most recent N candles for a symbol."""
    candles = load_historical_data(symbol.upper())
    if not candles:
        return []
    return candles[-limit:]


async def get_candles_for_range(symbol: str, start_date: str, end_date: str) -> list[dict]:
    """Returns candles between two dates. Used by the strategy backtester."""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end   = datetime.strptime(end_date,   "%Y-%m-%d")
    except ValueError:
        return []

    return get_candles_in_range(symbol.upper(), start, end)


async def get_all_instruments() -> list[dict]:
    """Returns all available stocks with name, sector, and latest price."""
    instruments = []
    for symbol in get_available_symbols():
        candle = get_latest_candle(symbol)
        if candle is None:
            continue
        info = INSTRUMENT_INFO.get(symbol, {"name": symbol, "sector": "Unknown"})
        instruments.append({
            "symbol":     symbol,
            "name":       info["name"],
            "sector":     info["sector"],
            "last_price": candle["close"],
        })
    return instruments


async def search_instruments(query: str) -> list[dict]:
    """Filters instruments by symbol or name. Used for the search bar."""
    query    = query.upper().strip()
    all_items = await get_all_instruments()
    return [
        item for item in all_items
        if query in item["symbol"] or query in item["name"].upper()
    ]
