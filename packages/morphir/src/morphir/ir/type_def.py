"""Compatibility shim: re-exports `morphir.ir.v4.type_def`."""

from morphir.ir.v4.access_controlled import AccessControlled
from morphir.ir.v4.type import Type
from morphir.ir.v4.type_def import (
    CustomTypeDefinition,
    Definition,
    TypeAliasDefinition,
)
from morphir.ir.v4.type_spec import Constructors

__all__ = [
    "AccessControlled",
    "Constructors",
    "CustomTypeDefinition",
    "Definition",
    "Type",
    "TypeAliasDefinition",
]
