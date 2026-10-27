"""Compatibility shim: re-exports `morphir.ir.v4.decorations`."""

from morphir.ir.v4.decorations import (
    DecorationFormat,
    DecorationValuesFile,
    LayerManifest,
    SchemaRef,
    deep_merge,
    merge_decoration_values,
)

__all__ = [
    "DecorationFormat",
    "DecorationValuesFile",
    "LayerManifest",
    "SchemaRef",
    "deep_merge",
    "merge_decoration_values",
]
