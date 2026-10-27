"""Compatibility shim: re-exports `morphir.ir.v4.module`."""

from morphir.ir.v4.access_controlled import AccessControlled
from morphir.ir.v4.module import (
    Definition,
    ModuleName,
    QualifiedModuleName,
    Specification,
)

__all__ = [
    "AccessControlled",
    "Definition",
    "ModuleName",
    "QualifiedModuleName",
    "Specification",
]
