# binance_api_request.py — RAW CSV only (no derived metrics)

import os
import time
import argparse
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
COIN = "BTC"          # base asset
INTERVAL = "1h"       # Binance kline interval
CSV_DIR = "out"
CSV_PATH = os.path.join(CSV_DIR, f"{COIN}_binance_scrd.csv")
RAW_LIMIT = 1000      # max klines per request

# ----------------------------------------------------------------------------
# Binance helpers
# ----------------------------------------------------------------------------
def get_first_candle_date(symbol: str, interval: str = INTERVAL) -> datetime:
    url = "https://api.binance.com/api/v3/klines"
    r = requests.get(url, params={"symbol": symbol, "interval": interval, "limit": 1, "startTime": 0})
    r.raise_for_status()
    return datetime.fromtimestamp(r.json()[0][0] / 1000, tz=timezone.utc)

def fetch_binance_ohlcv(symbol: str, interval: str, start: datetime | None, end: datetime | None, limit: int):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    if start is not None:
        params["startTime"] = int(start.timestamp() * 1000)
    if end is not None:
        params["endTime"] = int(end.timestamp() * 1000)
    r = requests.get(url, params=params)
    r.raise_for_status()
    return r.json()

def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser("Binance RAW fetch → CSV (no derived features)")
    ap.add_argument("-sd", type=str, help="Start date YYYY-MM-DD (UTC) – ignored with -u")
    ap.add_argument("-u", action="store_true", help="Update existing CSV (append new candles)")
    args = ap.parse_args()

    symbol = f"{COIN}USDT"

    # Decide start date
    if args.u and os.path.exists(CSV_PATH):
        exist = pd.read_csv(CSV_PATH)
        # last recorded open_time (ms)
        last_ms = int(exist["timestamp"].max())
        # start from next hour after the last row
        start_date = datetime.fromtimestamp(last_ms / 1000, tz=timezone.utc) + timedelta(hours=1)
        print(f"🔄 Update mode: fetching from {start_date} UTC")
    else:
        exist = None
        start_date = (
            datetime.strptime(args.sd, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if args.sd else get_first_candle_date(symbol)
        )
        print(f"▶️ Full fetch from: {start_date} UTC")

    end_date = datetime.now(timezone.utc)

    # Pull in batches
    raw = []
    cur = start_date
    while cur < end_date:
        batch = fetch_binance_ohlcv(symbol, INTERVAL, cur, cur + timedelta(hours=RAW_LIMIT), RAW_LIMIT)
        if not batch:
            break
        raw.extend(batch)
        # move to next candle after the last returned (based on open_time)
        last_open = batch[-1][0]
        cur = datetime.fromtimestamp(last_open / 1000, tz=timezone.utc) + timedelta(hours=1)
        time.sleep(0.05)

    if not raw:
        print("❌ No new data fetched")
        return 1

    # Build DataFrame from Binance kline schema
    df = pd.DataFrame(raw, columns=[
        "open_time", "open_price", "high_price", "low_price", "close_price", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore",
    ])

    # Keep only required columns, with required names and order
    out = pd.DataFrame()
    # Use OPEN time as the candle timestamp (matches your sample "2025-08-02 08:00:00")
    out["timestamp"] = (df["close_time"] - 3599999).astype("int64")  # convert to period start

    out["datetime"] = pd.to_datetime(out["timestamp"], unit="ms", utc=True).dt.strftime("%Y-%m-%d %H:%M:%S")
    out["high_price"] = df["high_price"].astype(float)
    out["low_price"] = df["low_price"].astype(float)
    out["close_price"] = df["close_price"].astype(float)
    out["volume"] = df["volume"].astype(float)
    out["quote_asset_volume"] = df["quote_asset_volume"].astype(float)
    out["number_of_trades"] = df["number_of_trades"].astype(int)
    out["taker_buy_base_asset_volume"] = df["taker_buy_base_asset_volume"].astype(float)
    out["taker_buy_quote_asset_volume"] = df["taker_buy_quote_asset_volume"].astype(float)

    # Merge with existing (if -u) and dedupe on timestamp
    if exist is not None:
        out = pd.concat([exist, out], ignore_index=True)
        out.drop_duplicates(subset="timestamp", keep="last", inplace=True)

    # Sort by time ascending (oldest → newest)
    out.sort_values("timestamp", inplace=True)
    out.reset_index(drop=True, inplace=True)

    ensure_dir(CSV_DIR)
    out.to_csv(CSV_PATH, index=False)
    print(f"💾 Saved {len(out)} rows → {CSV_PATH}")
    print("✅ Columns:", ", ".join(out.columns))

if __name__ == "__main__":
    raise SystemExit(main())
