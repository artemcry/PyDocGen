import time
from datetime import datetime, timedelta, timezone

import requests

BINANCE_BASE_URL = "https://api.binance.com"
KLINES_ENDPOINT = "/api/v3/klines"
KLINE_LIMIT = 1000

INTERVAL_MAP: dict[timedelta, str] = {
    timedelta(minutes=1): "1m",
    timedelta(minutes=3): "3m",
    timedelta(minutes=5): "5m",
    timedelta(minutes=15): "15m",
    timedelta(minutes=30): "30m",
    timedelta(hours=1): "1h",
    timedelta(hours=2): "2h",
    timedelta(hours=4): "4h",
    timedelta(hours=6): "6h",
    timedelta(hours=8): "8h",
    timedelta(hours=12): "12h",
    timedelta(days=1): "1d",
    timedelta(weeks=1): "1w",
}

KLINE_FIELDS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades",
    "taker_buy_base", "taker_buy_quote", "ignore",
]

KLINE_FIELD_INDEX = {name: i for i, name in enumerate(KLINE_FIELDS)}


def _to_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _from_ms(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def _request_klines(symbol: str, interval_str: str, start_ms: int, end_ms: int, limit: int) -> list[list]:
    params = {
        "symbol": symbol,
        "interval": interval_str,
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": limit,
    }
    for attempt in range(3):
        r = requests.get(f"{BINANCE_BASE_URL}{KLINES_ENDPOINT}", params=params, timeout=15)
        if r.status_code in (418, 429):
            time.sleep(60)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"Binance API rate-limited 3 times for {symbol} {interval_str}")


def fetch_klines(
    symbol: str,
    interval: timedelta,
    start: datetime,
    end: datetime,
) -> list[list]:
    interval_str = INTERVAL_MAP.get(interval)
    if interval_str is None:
        raise ValueError(f"Unsupported interval: {interval}. Supported: {list(INTERVAL_MAP.keys())}")

    start_ms = _to_ms(start)
    end_ms = _to_ms(end) - 1  # Binance includes endTime; -1ms to exclude boundary candle
    interval_ms = int(interval.total_seconds() * 1000)

    all_klines: list[list] = []
    cursor_ms = start_ms

    while cursor_ms < end_ms:
        batch = _request_klines(symbol, interval_str, cursor_ms, end_ms, KLINE_LIMIT)
        if not batch:
            break
        all_klines.extend(batch)
        last_open_ms = int(batch[-1][0])
        cursor_ms = last_open_ms + interval_ms
        if len(batch) < KLINE_LIMIT:
            break
        time.sleep(0.05)

    return all_klines
