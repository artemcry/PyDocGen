import requests
from datetime import datetime, timezone

def get_first_candle_date(symbol, interval='1h'):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": 1,
        "startTime": 0  # з початку епохи UNIX
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data:
            first_open_time_ms = data[0][0]  # час відкриття першої свічки (мілісекунди)
            first_date = datetime.fromtimestamp(first_open_time_ms / 1000, tz=timezone.utc)
            return first_date.isoformat()
        else:
            return "Дані відсутні"
    else:
        return f"Помилка: {response.status_code}"

# Приклад використання:
coin="SOL"


top30_symbols = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "LTCUSDT",
    "BCHUSDT", "EOSUSDT", "TRXUSDT", "ADAUSDT", "XLMUSDT",
    "LINKUSDT", "DOTUSDT", "DOGEUSDT", "MATICUSDT", "ATOMUSDT",
    "VETUSDT", "THETAUSDT", "FILUSDT", "ALGOUSDT", "XTZUSDT",
    "NEOUSDT", "KSMUSDT", "CAKEUSDT", "ZILUSDT", "AVAXUSDT",
    "FTMUSDT", "MKRUSDT", "COMPUSDT", "SNXUSDT", "CRVUSDT"
]

for symbol in top30_symbols:
    date = get_first_candle_date(symbol)
    print(f"Перша доступна свічка для {symbol}: {date}")