from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SchemaRef:
    display_name: str
    local_path: str
    entry_point: str  # FQName as string for simplicity in meta structures
    description: str | None = None
    remote_ref: str | None = None
    cached_at: str | None = None


@dataclass(frozen=True)
class DecorationFormat:
    format_version: str
    schema_registry: dict[str, SchemaRef] = field(default_factory=dict)
    layers: list[str] = field(default_factory=list)
    layer_priority: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class LayerManifest:
    format_version: str
    layer: str
    display_name: str
    priority: int
    created_at: str
    updated_at: str
    description: str | None = None
    decoration_types: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DecorationValuesFile:
    format_version: str
    decoration_type: str
    layer: str
    values: dict[str, Any] = field(default_factory=dict)  # Key is FQName string


def deep_merge(base: Any, override: Any) -> Any:
    """Deep merge two values.

    - If both are dicts, merge recursively.
    - If both are lists, concatenate (override extends base).
    - Otherwise, override wins.
    """
    if isinstance(base, dict) and isinstance(override, dict):
        merged = base.copy()
        for k, v in override.items():
            if k in merged:
                merged[k] = deep_merge(merged[k], v)
            else:
                merged[k] = v
        return merged
    elif isinstance(base, list) and isinstance(override, list):
        return base + override
    else:
        return override


def merge_decoration_values(layers: list[tuple[int, dict[str, Any]]]) -> dict[str, Any]:
    """Merge decoration values from multiple layers based on priority.

    Args:
        layers: List of (priority, values_dict) tuples.

    Returns:
        Merged dictionary of decoration values.
    """
    # Sort by priority (ascending) -> processed in order, so higher priority overrides later
    # Wait, simple override logic usually means last one wins.
    # If priority 0 is base, and 100 is override, then 0 should be processed first, then 100 merged on top.
    # So ascending sort is correct for standard "last write wins" merge logic.
    sorted_layers = sorted(layers, key=lambda x: x[0])

    merged: dict[str, Any] = {}

    for _, values in sorted_layers:
        for key, value in values.items():
            if key in merged:
                merged[key] = deep_merge(merged[key], value)
            else:
                merged[key] = value

    return merged
