from datetime import timedelta

from DataFlow.data_column import DataColumnConfig, DownsamplePolicy
from DataFlow.registry import register_column

BINANCE_INTERVALS = (
    timedelta(minutes=1),
    timedelta(minutes=3),
    timedelta(minutes=5),
    timedelta(minutes=15),
    timedelta(minutes=30),
    timedelta(hours=1),
    timedelta(hours=2),
    timedelta(hours=4),
    timedelta(hours=6),
    timedelta(hours=8),
    timedelta(hours=12),
    timedelta(days=1),
    timedelta(weeks=1),
)

KLINE_COLUMNS: list[tuple[str, DownsamplePolicy]] = [
    ("open", DownsamplePolicy.FIRST),
    ("high", DownsamplePolicy.MAX),
    ("low", DownsamplePolicy.MIN),
    ("close", DownsamplePolicy.LAST),
    ("volume", DownsamplePolicy.SUM),
    ("quote_volume", DownsamplePolicy.SUM),
    ("trades", DownsamplePolicy.SUM),
    ("taker_buy_base", DownsamplePolicy.SUM),
    ("taker_buy_quote", DownsamplePolicy.SUM),
]


def register_binance_columns(symbol: str):
    sym = symbol.lower()
    for field, downsample in KLINE_COLUMNS:
        register_column(DataColumnConfig(
            id=f"binance_{sym}_{field}",
            source_id="binance",
            available_intervals=BINANCE_INTERVALS,
            params={"symbol": symbol.upper(), "field": field},
            downsample_policy=downsample,
        ))


register_binance_columns("btcusdt")
register_binance_columns("ethusdt")
