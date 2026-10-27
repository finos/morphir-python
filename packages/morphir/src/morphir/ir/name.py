"""Compatibility shim: re-exports `morphir.ir.v4.name`."""

from morphir.ir.v4.name import (
    Name,
    from_list,
    from_string,
    to_camel_case,
    to_human_words,
    to_kebab_case,
    to_list,
    to_snake_case,
    to_string,
    to_title_case,
)

__all__ = [
    "Name",
    "from_list",
    "from_string",
    "to_camel_case",
    "to_human_words",
    "to_kebab_case",
    "to_list",
    "to_snake_case",
    "to_string",
    "to_title_case",
]
