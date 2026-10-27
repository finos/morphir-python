"""Compatibility shim: re-exports `morphir.ir.v4.module`."""

from morphir.ir.v4.module import (
    AccessControlled,
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
