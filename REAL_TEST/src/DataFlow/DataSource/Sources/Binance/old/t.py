# pip install requests pandas pytz  (pandas не обов'язково; можна прибрати)
import requests
from datetime import datetime, timedelta, timezone
import time

BINANCE_SPOT = "https://api.binance.com"      # для ф'ючерсів візьми https://fapi.binance.com

def get_server_time_ms(base_url=BINANCE_SPOT) -> int:
    r = requests.get(f"{base_url}/api/v3/time", timeout=10)
    r.raise_for_status()
    return int(r.json()["serverTime"])

def floor_to_hour_ms(ts_ms: int) -> int:
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    dt_floor = dt.replace(minute=0, second=0, microsecond=0)
    return int(dt_floor.timestamp() * 1000)

def get_last_n_hourly_klines(symbol: str, n: int = 5, base_url=BINANCE_SPOT):
    assert n > 0
    # 1) вирівнюємось по часу Binance, а не локальному
    now_ms = get_server_time_ms(base_url)
    # 2) закрита остання година закінчується на початку поточної (виключно)
    end_ms = floor_to_hour_ms(now_ms)              # права межа (НЕ включно), тобто t_close поточної - 1 год
    start_ms = end_ms - n * 60 * 60 * 1000         # ліва межа для n годин

    params = {
        "symbol": symbol.upper(),
        "interval": "1h",
        "startTime": start_ms,
        "endTime": end_ms - 1,   # Binance включає endTime; ставимо -1ms, щоб не захопити поточну незакриту
        "limit": n
    }

    # Проста обробка rate limit
    for attempt in range(3):
        r = requests.get(f"{base_url}/api/v3/klines", params=params, timeout=15)
        if r.status_code in (418, 429):
            time.sleep(60)  # почекаємо і повторимо
            continue
        r.raise_for_status()
        data = r.json()
        break
    else:
        raise RuntimeError("Binance API rate-limited 3 times in a row")

    # Розпаковка у зручний формат (t_open як ISO, t_close = t_open + 1h)
    rows = []
    for k in data:
        open_time_ms = int(k[0])
        # closeTime у відповіді зазвичай = t_open + 1h - 1ms; рахуємо t_close самі
        close_time_ms = open_time_ms + 60 * 60 * 1000
        rows.append({
            "symbol": symbol.upper(),
            "t_open": datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc).isoformat(),
            "t_close": datetime.fromtimestamp(close_time_ms / 1000, tz=timezone.utc).isoformat(),
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume_base": float(k[5]),
            "quote_volume": float(k[7]),
            "trades": int(k[8]),
            "taker_buy_base": float(k[9]),
            "taker_buy_quote": float(k[10]),
        })

    # Binance може повернути менше n свічок, якщо торгівля щойно почалась для символу
    if len(rows) != n:
        print(f"Warning: expected {n} rows, got {len(rows)} (range {datetime.fromtimestamp(start_ms/1000, tz=timezone.utc)}"
              f"–{datetime.fromtimestamp(end_ms/1000, tz=timezone.utc)})")

    return rows

if __name__ == "__main__":
    symbol = "BTCUSDT"   # заміни на потрібний
    rows = get_last_n_hourly_klines(symbol, n=5, base_url=BINANCE_SPOT)
    for r in rows:
        print(r)
