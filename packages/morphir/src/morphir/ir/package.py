"""Compatibility shim: re-exports `morphir.ir.v4.package`."""

from morphir.ir.v4.access_controlled import AccessControlled
from morphir.ir.v4.package import (
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
