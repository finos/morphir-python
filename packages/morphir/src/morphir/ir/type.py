"""Compatibility shim: re-exports `morphir.ir.v4.type`."""

from morphir.ir.v4.type import (
    EMPTY_TYPE_ATTRIBUTES,
    ExtensibleRecord,
    Field,
    Function,
    Record,
    Reference,
    SourceLocation,
    Tuple,
    Type,
    TypeAttributes,
    Unit,
    Variable,
    get_attributes,
    map_attributes,
)

__all__ = [
    "EMPTY_TYPE_ATTRIBUTES",
    "ExtensibleRecord",
    "Field",
    "Function",
    "Record",
    "Reference",
    "SourceLocation",
    "Tuple",
    "Type",
    "TypeAttributes",
    "Unit",
    "Variable",
    "get_attributes",
    "map_attributes",
]
