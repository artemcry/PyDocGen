from collections import defaultdict
from datetime import datetime, timedelta, timezone

import pandas as pd

from DataFlow.DataSource.idata_source import IDataSource, FetchResult, FetchColumnSpec
from DataFlow.registry import register_source, COLUMN_REGISTRY
from DataFlow.DataSource.Sources.Binance.binance_api import (
    fetch_klines,
    KLINE_FIELD_INDEX,
)


@register_source
class BinanceSource(IDataSource):
    source_id = "binance"

    def fetch(
        self,
        date_range: tuple[datetime, datetime],
        specs: list[FetchColumnSpec],
    ) -> FetchResult:
        # Group specs by (symbol, fetch_interval) → one API call per group
        groups: dict[tuple[str, timedelta], list[FetchColumnSpec]] = defaultdict(list)
        for spec in specs:
            col = COLUMN_REGISTRY[spec.column_id]
            symbol = col.params["symbol"]
            groups[(symbol, spec.fetch_interval)].append(spec)

        result: dict[timedelta, pd.DataFrame] = {}

        for (symbol, interval), group_specs in groups.items():
            klines = fetch_klines(symbol, interval, date_range[0], date_range[1])

            if not klines:
                continue

            # Build DatetimeIndex from open_time
            timestamps = [
                datetime.fromtimestamp(int(k[0]) / 1000, tz=timezone.utc)
                for k in klines
            ]
            index = pd.DatetimeIndex(timestamps, name="datetime")

            # Extract only requested fields
            df = pd.DataFrame(index=index)
            for spec in group_specs:
                col = COLUMN_REGISTRY[spec.column_id]
                field = col.params["field"]
                col_idx = KLINE_FIELD_INDEX[field]
                dtype = int if field == "trades" else float
                df[spec.column_id] = [dtype(k[col_idx]) for k in klines]

            # Merge into result by interval
            if interval in result:
                result[interval] = result[interval].join(df, how="outer")
            else:
                result[interval] = df

        return FetchResult(data=result)
