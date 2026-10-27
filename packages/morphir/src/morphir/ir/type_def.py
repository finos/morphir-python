"""Compatibility shim: re-exports `morphir.ir.v4.type_def`."""

from morphir.ir.v4.type_def import (
    AccessControlled,
    Constructors,
    CustomTypeDefinition,
    Definition,
    Type,
    TypeAliasDefinition,
)

__all__ = [
    "AccessControlled",
    "Constructors",
    "CustomTypeDefinition",
    "Definition",
    "Type",
    "TypeAliasDefinition",
]
