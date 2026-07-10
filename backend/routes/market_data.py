from fastapi import APIRouter, HTTPException, status, Query
from backend.services import market_data as md_service

router = APIRouter()


# GET /api/market/instruments
# full list of stocks available on the platform
@router.get("/instruments")
async def list_instruments():
    """
    Returns all stocks that have data available.
    This populates the watchlist and the search dropdown.
    """
    instruments = await md_service.get_all_instruments()
    return instruments


# GET /api/market/search?q=reliance
# search stocks by name or symbol
@router.get("/search")
async def search_instruments(q: str = Query(..., min_length=1)):
    """
    Search for a stock by typing part of its name or symbol.
    Example: /api/market/search?q=tata
    Returns all matches — symbol, name, sector, last price.
    """
    results = await md_service.search_instruments(query=q)

    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No instruments found matching '{q}'"
        )

    return results


# GET /api/market/quote/RELIANCE
# current price info for one stock
@router.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """
    Returns a live-style quote for a stock:
    LTP, open, high, low, previous close, change, change%, volume.

    This is what goes in the top price bar in the trading UI.
    """
    quote = await md_service.get_quote(symbol.upper())

    if quote is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for symbol '{symbol.upper()}'. Make sure the CSV file exists in the data/ folder."
        )

    return quote


# GET /api/market/candles/RELIANCE?limit=100
# OHLCV candles for the chart
@router.get("/candles/{symbol}")
async def get_candles(
    symbol: str,
    limit: int = Query(default=100, ge=10, le=500),
    interval: str = Query(default="1d"),
):
    """
    Returns OHLCV candle data for a stock.
    The frontend uses this to draw the candlestick chart.

    limit  — how many candles to return (10 to 500, default 100)
    interval — timeframe, default is daily ("1d")
    """
    candles = await md_service.get_candles(
        symbol=symbol.upper(),
        interval=interval,
        limit=limit,
    )

    if not candles:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No candle data found for '{symbol.upper()}'."
        )

    return candles


# GET /api/market/candles/RELIANCE/range?start=2024-01-01&end=2024-12-31
# candles between specific dates — used by the strategy backtester
@router.get("/candles/{symbol}/range")
async def get_candles_range(
    symbol: str,
    start: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end:   str = Query(..., description="End date in YYYY-MM-DD format"),
):
    """
    Returns candles for a symbol within a date range.
    Used when running a strategy backtest over a specific period.

    Example: /api/market/candles/TCS/range?start=2024-01-01&end=2024-06-30
    """
    candles = await md_service.get_candles_for_range(
        symbol=symbol.upper(),
        start_date=start,
        end_date=end,
    )

    if not candles:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for '{symbol.upper()}' in the range {start} to {end}."
        )

    return candles
