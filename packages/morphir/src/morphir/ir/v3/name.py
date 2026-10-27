"""V3 names: lists of lowercase words (morphir-elm ``Morphir.IR.Name``)."""

from __future__ import annotations

import re


class Name(tuple[str, ...]):
    """A v3 name such as ``["value", "in", "u", "s", "d"]``.

    Distinct from `morphir.ir.v4.Name` so that a type checker catches mixing.
    """

    __slots__ = ()


def from_list(words: list[str] | tuple[str, ...]) -> Name:
    """Build a name from words, as elm ``Name.fromList`` does."""
    return Name(tuple(words))


def to_list(name: Name) -> list[str]:
    """Return the words of a name."""
    return list(name)


def from_string(text: str) -> Name:
    """Split text into lowercase words, as elm ``Name.fromString`` does.

    Example:
        >>> from_string("valueInUSD")
        ('value', 'in', 'u', 's', 'd')
    """
    words = re.findall(r"[a-zA-Z][a-z]*|[0-9]+", text)
    return Name(tuple(word.lower() for word in words))


def to_camel_case(name: Name) -> str:
    """Render as camelCase, as elm ``Name.toCamelCase`` does."""
    if not name:
        return ""
    return name[0] + "".join(word.capitalize() for word in name[1:])
