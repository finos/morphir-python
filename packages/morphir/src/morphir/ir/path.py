"""Compatibility shim: re-exports `morphir.ir.v4.path`."""

from morphir.ir.v4.path import (
    Path,
    append,
    concat,
    empty,
    from_list,
    from_string,
    is_prefix_of,
    to_list,
    to_string,
)

__all__ = [
    "Path",
    "append",
    "concat",
    "empty",
    "from_list",
    "from_string",
    "is_prefix_of",
    "to_list",
    "to_string",
]
