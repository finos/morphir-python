"""Compatibility shim: re-exports `morphir.ir.v4.json`."""

from morphir.ir.v4.json import (
    MorphirJSONEncoder,
    encode,
)

__all__ = [
    "MorphirJSONEncoder",
    "encode",
]
