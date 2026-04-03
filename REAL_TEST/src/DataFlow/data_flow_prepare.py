from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from DataFlow.data_column import ParsedDerived, ComputeStage
from DataFlow.DataSource.idata_source import FetchColumnSpec
from DataFlow.DataTransformer.data_transformer import DataTransformerConfig
from DataFlow.utils import topo_sort_derived
from DataFlow.registry import COLUMN_REGISTRY
from DataFlow.derived_parser import parse_derived


@dataclass(frozen=True)
class FetchPlan:
    fetch_specs: list[FetchColumnSpec]
    extended_fetch_range: tuple[datetime, datetime]


def prepare(transform_config: DataTransformerConfig, date_range: tuple[datetime, datetime]) -> FetchPlan:
    derived = _parse_all_derived(transform_config.target_derived_columns)
    resolved_ids = _resolve_dependencies(
        explicit_ids=list(transform_config.target_columns),
        derived=derived,
    )
    _validate_no_duplicate_ids(resolved_ids, derived)
    derived_sorted = topo_sort_derived(derived)
    target_interval = transform_config.target_interval
    fetch_specs = [
        FetchColumnSpec(column_id=col_id, fetch_interval=_pick_fetch_interval(col_id, target_interval))
        for col_id in resolved_ids
    ]
    _validate_before_resample_intervals(derived_sorted, fetch_specs, target_interval)
    warmup = _calculate_warmup(fetch_specs, derived_sorted, target_interval)
    resolved_fetch_range = (date_range[0] - warmup, date_range[1])
    return FetchPlan(
        fetch_specs=fetch_specs,
        extended_fetch_range=resolved_fetch_range,
    )


def _parse_all_derived(exprs: list[str]) -> list[ParsedDerived]:
    """Parse all derived expressions, deduplicating shared intermediates."""
    result: list[ParsedDerived] = []
    seen: set[str] = set()
    for expr in exprs:
        for step in parse_derived(expr):
            if step.id not in seen:
                result.append(step)
                seen.add(step.id)
    return result


def _pick_fetch_interval(col_id: str, target: timedelta) -> timedelta:
    # TODO: add warning to logger if target % i != timedelta(0)
    available = COLUMN_REGISTRY[col_id].available_intervals
    below = [i for i in available if i <= target]
    if below:
        divisible = [i for i in below if target % i == timedelta(0)]
        return max(divisible) if divisible else max(below)
    return min(available)


def _resolve_dependencies(
    explicit_ids: list[str],
    derived: list[ParsedDerived],
) -> list[str]:
    for col_id in explicit_ids:
        if col_id not in COLUMN_REGISTRY:
            raise KeyError(f"Column '{col_id}' not found in COLUMN_REGISTRY")
    raw_ids = list(dict.fromkeys(explicit_ids))  # preserve order, dedupe
    raw_id_set = set(raw_ids)
    derived_ids = {d.id for d in derived}
    missing_ids: list[str] = []
    for d in derived:
        for inp in d.inputs:
            if inp not in raw_id_set and inp not in derived_ids:
                missing_ids.append(inp)
                raw_id_set.add(inp)
    for col_id in missing_ids:
        if col_id not in COLUMN_REGISTRY:
            raise KeyError(
                f"Derived column depends on '{col_id}' which is not in "
                f"target_columns and not found in COLUMN_REGISTRY"
            )
        raw_ids.append(col_id)
    return raw_ids


def _validate_no_duplicate_ids(
    raw_ids: list[str],
    derived: list[ParsedDerived],
) -> None:
    all_ids = raw_ids + [d.id for d in derived]
    seen: set[str] = set()
    for col_id in all_ids:
        if col_id in seen:
            raise ValueError(f"Duplicate column id: '{col_id}'")
        seen.add(col_id)


def _validate_before_resample_intervals(
    derived_sorted: list[ParsedDerived],
    fetch_specs: list[FetchColumnSpec],
    target_interval: timedelta,
) -> None:
    bar_duration: dict[str, timedelta] = {spec.column_id: spec.fetch_interval for spec in fetch_specs}
    after_resample_ids: set[str] = set()
    for d in derived_sorted:
        if d.compute_stage == ComputeStage.AFTER_RESAMPLE:
            bar_duration[d.id] = target_interval
            after_resample_ids.add(d.id)
        else:
            invalid_inputs = [inp for inp in d.inputs if inp in after_resample_ids]
            if invalid_inputs:
                raise ValueError(
                    f"Derived '{d.id}' (BEFORE_RESAMPLE) depends on AFTER_RESAMPLE "
                    f"columns: {invalid_inputs}"
                )
            intervals = {bar_duration[inp] for inp in d.inputs if inp in bar_duration}
            if len(intervals) > 1:
                raise ValueError(
                    f"Derived '{d.id}' (BEFORE_RESAMPLE) has inputs with "
                    f"different fetch intervals: {intervals}"
                )
            if intervals:
                bar_duration[d.id] = max(intervals)


def _calculate_warmup(
    fetch_specs: list[FetchColumnSpec],
    derived_sorted: list[ParsedDerived],
    target_interval: timedelta,
) -> timedelta:
    bar_duration: dict[str, timedelta] = {}
    total_warmup: dict[str, timedelta] = {}
    for spec in fetch_specs:
        bar_duration[spec.column_id] = spec.fetch_interval
        total_warmup[spec.column_id] = timedelta(0)
    for d in derived_sorted:
        my_bar = (
            max(bar_duration[inp] for inp in d.inputs)
            if d.compute_stage == ComputeStage.BEFORE_RESAMPLE
            else target_interval
        )
        bar_duration[d.id] = my_bar
        own_warmup = d.warmup_bars * my_bar
        inherited_warmup = max(
            (total_warmup[inp] for inp in d.inputs if inp in total_warmup),
            default=timedelta(0),
        )
        total_warmup[d.id] = own_warmup + inherited_warmup
    if not total_warmup:
        return timedelta(0)
    return max(total_warmup.values())
