from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict

import pandas as pd
from pydantic import BaseModel, ConfigDict


class DataTransformerConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    target_interval: timedelta
    target_columns: list[str] = []
    target_derived_columns: list[str] = []


@dataclass(frozen=True)
class TransformResult:
    transformed_data: pd.DataFrame


class DataTransformer:

    def transform(
        self,
        data: Dict[timedelta, pd.DataFrame],
        config: DataTransformerConfig,
        date_range: tuple[datetime, datetime],
    ) -> TransformResult:
        print(["DataTransformer.transform", config.target_columns])
        return TransformResult(transformed_data=pd.DataFrame())
