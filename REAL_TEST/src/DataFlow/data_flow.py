# <FILEDESCRIPTION>: Main entry point for data processing pipeline



from __future__ import annotations

from datetime import datetime, timedelta
from collections import defaultdict
import threading

import pandas as pd
from pydantic import BaseModel, ConfigDict

from DataFlow.DataSource.idata_source import IDataSource, FetchResult, FetchColumnSpec
from DataFlow.DataTransformer.data_transformer import DataTransformer, TransformResult, DataTransformerConfig
from DataFlow.registry import SOURCE_REGISTRY, COLUMN_REGISTRY
from DataFlow.data_flow_prepare import FetchPlan, prepare as prepare_fetch_plan


class DataFlowConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    date_range: tuple[datetime, datetime]
    transform_config: DataTransformerConfig

    @classmethod
    def from_json(cls, json_str: str) -> "DataFlowConfig":
        return cls.model_validate_json(json_str)


class DataFlow:

    def __init__(self):
        self._sources: dict[str, IDataSource] = {}
        self._transformer = DataTransformer()
        self._sources_lock = threading.Lock()

    def get_data(
        self,
        config: DataFlowConfig,
    ) -> TransformResult:
        plan = prepare_fetch_plan(config.transform_config, config.date_range)
        raw_data = self._fetch(plan)
        return self._transformer.transform(raw_data, config.transform_config, config.date_range)

    def _fetch(self, plan: FetchPlan) -> dict[timedelta, pd.DataFrame]:
        groups: dict[str, list[FetchColumnSpec]] = defaultdict(list)
        for spec in plan.fetch_specs:
            source_id = COLUMN_REGISTRY[spec.column_id].source_id
            groups[source_id].append(spec)
        merged: dict[timedelta, pd.DataFrame] = {}
        for source_id, specs in groups.items():
            source = self._get_source(source_id)
            result: FetchResult = source.fetch(plan.extended_fetch_range, specs)
            for interval, df in result.data.items():
                if interval in merged:
                    merged[interval] = merged[interval].join(df, how="outer")
                else:
                    merged[interval] = df
        return merged

    def _get_source(self, source_id: str) -> IDataSource:
        if source_id not in self._sources:
            with self._sources_lock:
                if source_id not in self._sources:
                    if source_id not in SOURCE_REGISTRY:
                        raise KeyError(f"Source '{source_id}' not found in registry")
                    self._sources[source_id] = SOURCE_REGISTRY[source_id]()
        return self._sources[source_id]
