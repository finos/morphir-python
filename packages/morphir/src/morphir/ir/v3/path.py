"""V3 paths: lists of names (morphir-elm ``Morphir.IR.Path``)."""

from __future__ import annotations

from .name import Name
from .name import from_string as name_from_string


class Path(tuple[Name, ...]):
    """A v3 path such as ``[["morphir"], ["s", "d", "k"]]``."""

    __slots__ = ()


def from_list(names: list[Name] | tuple[Name, ...]) -> Path:
    """Build a path from names."""
    return Path(tuple(names))


def to_list(path: Path) -> list[Name]:
    """Return the names of a path."""
    return list(path)


def from_string(text: str) -> Path:
    """Split ``Morphir.SDK`` or ``morphir/sdk`` into a path of names."""
    import re

    return Path(tuple(name_from_string(p) for p in re.split(r"[./]", text) if p))
