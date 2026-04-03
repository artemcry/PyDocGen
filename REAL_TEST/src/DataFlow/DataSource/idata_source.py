from dataclasses import dataclass
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from typing import Dict

import pandas as pd



"""
    TEST

"""
class TEST:
    pass

@dataclass(frozen=True)
class FetchColumnSpec:
    """Specifies which interval to request from the API for a given column.

    Passed to IDataSource.fetch() so the source knows at what granularity
    to retrieve each column. The interval must be one of the values declared
    in the column's DataColumnConfig.available_intervals — resolved by
    DataFlowPrepare before the fetch.
    """

    column_id: str
    fetch_interval: timedelta  # one of the column's declared available_intervals


@dataclass(frozen=True)
class FetchResult:
    """Result returned by IDataSource.fetch().

    Contains raw data grouped by fetch interval. Each DataFrame holds all
    columns retrieved at that interval, indexed by timestamp.

    # TODO: extend with fetch metadata (success status, partial failures, etc.)
    """

    data: Dict[timedelta, pd.DataFrame]  # interval → raw OHLCV/metric DataFrame


class IDataSource(ABC):
    """Abstract interface for all data sources (Binance, CryptoQuant, etc.).

    Standardizes how DataFlow interacts with any external data provider.
    Each implementation encapsulates the provider-specific API logic while
    exposing a uniform fetch() contract. Sources are registered globally via
    @register_source and lazily instantiated by DataFlow on first use.

    Subclasses must define a unique `source_id` class attribute — enforced at
    class definition time.
    """

    source_id: str

    def __init_subclass__(cls, **kwargs):
        # Enforce that every concrete source declares a unique source_id.
        super().__init_subclass__(**kwargs)
        if not getattr(cls, 'source_id', None):
            raise TypeError(f"{cls.__name__} must define 'source_id'")

    @abstractmethod
    def fetch(
        self,
        date_range: tuple[datetime, datetime],
        specs: list[FetchColumnSpec],
    ) -> FetchResult:
        """Fetch raw data for the requested columns over the given date range.

        Results are grouped by fetch_interval from the specs — one DataFrame
        per distinct interval, containing all columns requested at that interval.

        Args:
            date_range: (start, end) range to fetch. The end bound is inclusive:
                if end=2021-02-02 00:00 and the column interval is 1d, the candle
                for 2021-02-02 is included in the result.
            specs: list of (column_id, fetch_interval) pairs describing what to fetch.

        Returns:
            FetchResult with data grouped by fetch_interval.
        """
        pass
