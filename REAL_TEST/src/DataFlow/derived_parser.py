from __future__ import annotations

import inspect
import re
from typing import Callable

from DataFlow.data_column import ComputeStage, ParsedDerived
from DataFlow.registry import COLUMN_REGISTRY, ALIAS_REGISTRY, TRANSFORM_REGISTRY


def parse_derived(expr: str) -> list[ParsedDerived]:
    """
    Parse "name::func(params)::>func2(params)" into list of ParsedDerived.

    Returns all steps including intermediates. E.g.:
      "close::ema(14)::>zscore(100)" → [ParsedDerived(close::ema(14)), ParsedDerived(close::ema(14)::>zscore(100))]
    """
    sep = expr.rfind("::")
    if sep == -1:
        raise ValueError(f"Invalid derived expression (no '::'): '{expr}'")

    left = expr[:sep]
    right = expr[sep + 2:]

    is_after, func_name, positional = _parse_func_call(right)
    compute_stage = ComputeStage.AFTER_RESAMPLE if is_after else ComputeStage.BEFORE_RESAMPLE

    if func_name not in TRANSFORM_REGISTRY:
        raise KeyError(f"Transform '{func_name}' not found in TRANSFORM_REGISTRY")
    transform_def = TRANSFORM_REGISTRY[func_name]

    if "::" in left:
        # chain — left is itself a derived expression
        previous_steps = parse_derived(left)
        inputs = [left]
    else:
        previous_steps = []
        inputs = _resolve_name(left)

    params = _params_to_dict(transform_def.func, positional, n_inputs=len(inputs))

    current = ParsedDerived(
        id=expr,
        transform_def=transform_def,
        params=params,
        inputs=inputs,
        compute_stage=compute_stage,
    )

    return previous_steps + [current]


def _parse_func_call(s: str) -> tuple[bool, str, list]:
    """Parse ">func(p1, p2)" → (is_after, "func", [p1, p2])"""
    is_after = s.startswith(">")
    if is_after:
        s = s[1:]

    match = re.fullmatch(r'(\w+)\((.*)\)', s, re.DOTALL)
    if not match:
        raise ValueError(f"Invalid function call syntax: '{s}'")

    func_name = match.group(1)
    args_str = match.group(2).strip()

    positional = [_parse_value(a.strip()) for a in args_str.split(",")] if args_str else []

    return is_after, func_name, positional


def _resolve_name(name: str) -> list[str]:
    """Resolve name via COLUMN_REGISTRY then ALIAS_REGISTRY."""
    if name in COLUMN_REGISTRY:
        return [name]
    if name in ALIAS_REGISTRY:
        return ALIAS_REGISTRY[name]
    raise KeyError(f"Name '{name}' not found in COLUMN_REGISTRY or ALIAS_REGISTRY")


def _params_to_dict(func: Callable, positional: list, n_inputs: int = 1) -> dict:
    """Map positional args to named params using func signature (skips first n_inputs params)."""
    sig = inspect.signature(func)
    params = list(sig.parameters.values())[n_inputs:]  # skip data input params
    param_names = [p.name for p in params]
    if len(positional) > len(param_names):
        raise ValueError(
            f"'{func.__name__}' accepts {len(param_names)} params, got {len(positional)}"
        )
    result = dict(zip(param_names, positional))
    missing = [
        p.name for p in params
        if p.default is inspect.Parameter.empty and p.name not in result
    ]
    if missing:
        raise ValueError(
            f"'{func.__name__}' missing required params: {missing}"
        )
    return result


def _parse_value(s: str) -> int | float | str:
    """Parse string literal to int, float, or str."""
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s
