"""Compatibility shim: re-exports `morphir.ir.v4.ref`."""

from morphir.ir.v4.ref import (
    DefRef,
    FileWithDefs,
    PointerRef,
    Ref,
    T,
)

__all__ = [
    "DefRef",
    "FileWithDefs",
    "PointerRef",
    "Ref",
    "T",
]
