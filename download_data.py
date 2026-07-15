"""
download_data.py

Run this once to download 2 years of historical OHLCV data
for popular NSE stocks from Yahoo Finance.

Usage:
    backend\venv\Scripts\python.exe download_data.py

It saves one CSV per stock in the data/ folder.
The backend reads these files when serving charts and running strategies.
"""

import os
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# folder where CSVs will be saved
DATA_DIR = "./data"

# Yahoo Finance uses .NS suffix for NSE stocks
# Left side = what we call it in the app, Right side = Yahoo ticker
STOCKS = {
    "RELIANCE":   "RELIANCE.NS",
    "TCS":        "TCS.NS",
    "INFY":       "INFY.NS",
    "HDFCBANK":   "HDFCBANK.NS",
    "ICICIBANK":  "ICICIBANK.NS",
    "SBIN":       "SBIN.NS",
    "WIPRO":      "WIPRO.NS",
    "AXISBANK":   "AXISBANK.NS",
    "BAJFINANCE": "BAJFINANCE.NS",
    "KOTAKBANK":  "KOTAKBANK.NS",
    "MARUTI":     "MARUTI.NS",
    "SUNPHARMA":  "SUNPHARMA.NS",
    "ITC":        "ITC.NS",
    "HINDUNILVR": "HINDUNILVR.NS",
    "ASIANPAINT": "ASIANPAINT.NS",
}

# download last 2 years of daily data
END_DATE   = datetime.today().strftime("%Y-%m-%d")
START_DATE = (datetime.today() - timedelta(days=730)).strftime("%Y-%m-%d")

os.makedirs(DATA_DIR, exist_ok=True)

print(f"Downloading data from {START_DATE} to {END_DATE}")
print(f"Saving to: {os.path.abspath(DATA_DIR)}\n")

success = []
failed  = []

for symbol, ticker in STOCKS.items():
    try:
        print(f"  Downloading {symbol} ({ticker})...", end=" ")

        df = yf.download(
            ticker,
            start=START_DATE,
            end=END_DATE,
            interval="1d",
            progress=False,
            auto_adjust=True,   # adjusts for splits and dividends
        )

        if df.empty:
            print("no data returned — skipping")
            failed.append(symbol)
            continue

        # flatten multi-level columns if present (yfinance sometimes does this)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # rename to match what data_loader.py expects
        df = df.rename(columns={
            "Open":   "open",
            "High":   "high",
            "Low":    "low",
            "Close":  "close",
            "Volume": "volume",
        })

        # keep only the columns we need
        df = df[["open", "high", "low", "close", "volume"]]

        # reset index so Date becomes a regular column
        df.index.name = "date"
        df = df.reset_index()

        # format date as YYYY-MM-DD string
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

        # drop any rows with missing prices
        df = df.dropna(subset=["open", "high", "low", "close"])

        # save to CSV
        output_path = os.path.join(DATA_DIR, f"{symbol}.csv")
        df.to_csv(output_path, index=False)

        print(f"saved {len(df)} rows → {symbol}.csv")
        success.append(symbol)

    except Exception as e:
        print(f"FAILED — {e}")
        failed.append(symbol)

# summary
print(f"\n{'='*50}")
print(f"Done!")
print(f"  Successfully downloaded: {len(success)} stocks")
if success:
    print(f"  {', '.join(success)}")

if failed:
    print(f"\n  Failed ({len(failed)}): {', '.join(failed)}")
    print("  These might be unavailable on Yahoo Finance today.")
    print("  Try again later or check the ticker symbol.\n")

print(f"\nYou can now start the backend and these stocks will")
print(f"appear in the watchlist and be available for strategy backtests.")
