"""Compatibility shim: re-exports `morphir.ir.v4.package`."""

from morphir.ir.v4.package import (
    AccessControlled,
    Definition,
    PackageName,
    Specification,
)

__all__ = [
    "AccessControlled",
    "Definition",
    "PackageName",
    "Specification",
]
