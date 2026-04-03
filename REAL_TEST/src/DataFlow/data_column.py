from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from enum import Enum
from typing import Callable



class DownsamplePolicy(str, Enum):
    LAST = "last"
    FIRST = "first"
    MEAN = "mean"
    SUM = "sum"
    MAX = "max"
    MIN = "min"


class UpsamplePolicy(str, Enum):
    FFILL = "ffill"
    BFILL = "bfill"
    INTERPOLATE = "interpolate"


class ComputeStage(str, Enum):
    BEFORE_RESAMPLE = "before_resample"
    AFTER_RESAMPLE = "after_resample"


@dataclass(frozen=True)
class DataColumnConfig:
    id: str
    source_id: str
    available_intervals: tuple[timedelta, ...]
    params: dict = field(default_factory=dict)
    downsample_policy: DownsamplePolicy = DownsamplePolicy.LAST
    upsample_policy: UpsamplePolicy = UpsamplePolicy.FFILL


@dataclass(frozen=True)
class TransformDef:
    func: Callable
    warmup_bars: int | Callable[[dict], int]
    downsample_policy: DownsamplePolicy = DownsamplePolicy.LAST
    upsample_policy: UpsamplePolicy = UpsamplePolicy.FFILL


@dataclass(frozen=True)
class ParsedDerived:
    id: str
    transform_def: TransformDef
    params: dict
    inputs: list[str]
    compute_stage: ComputeStage

    @property
    def warmup_bars(self) -> int:
        w = self.transform_def.warmup_bars
        return w(self.params) if callable(w) else w
