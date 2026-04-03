from __future__ import annotations

SOURCE_REGISTRY: dict = {}
COLUMN_REGISTRY: dict[str, "DataColumnConfig"] = {}
TRANSFORM_REGISTRY: dict[str, "TransformDef"] = {}
ALIAS_REGISTRY: dict[str, list[str]] = {}


def register_source(cls):
    if cls.source_id in SOURCE_REGISTRY:
        raise ValueError(f"Source '{cls.source_id}' already registered")
    SOURCE_REGISTRY[cls.source_id] = cls
    return cls


def register_column(config: "DataColumnConfig") -> "DataColumnConfig":
    if "::" in config.id:
        raise ValueError(f"Column ID cannot contain '::': '{config.id}'")
    if config.id in COLUMN_REGISTRY:
        raise ValueError(f"Column '{config.id}' already registered")
    if config.id in ALIAS_REGISTRY:
        raise ValueError(f"Column ID '{config.id}' conflicts with alias name")
    COLUMN_REGISTRY[config.id] = config
    return config


def register_transform(name: str, transform_def: "TransformDef") -> "TransformDef":
    if "::" in name:
        raise ValueError(f"Transform name cannot contain '::': '{name}'")
    if name in TRANSFORM_REGISTRY:
        raise ValueError(f"Transform '{name}' already registered")
    TRANSFORM_REGISTRY[name] = transform_def
    return transform_def


def register_alias(name: str, column_ids: list[str]) -> None:
    if "::" in name:
        raise ValueError(f"Alias name cannot contain '::': '{name}'")
    if name in ALIAS_REGISTRY:
        raise ValueError(f"Alias '{name}' already registered")
    if name in COLUMN_REGISTRY:
        raise ValueError(f"Alias name '{name}' conflicts with column ID")
    for col_id in column_ids:
        if col_id not in COLUMN_REGISTRY:
            raise ValueError(f"Alias '{name}' references unknown column '{col_id}'")
    ALIAS_REGISTRY[name] = column_ids
