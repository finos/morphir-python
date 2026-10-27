"""Compatibility shim: re-exports `morphir.ir.v4.access_controlled`."""

from morphir.ir.v4.access_controlled import (
    AccessControlled,
    Private,
    Public,
    T,
)

__all__ = [
    "AccessControlled",
    "Private",
    "Public",
    "T",
]
