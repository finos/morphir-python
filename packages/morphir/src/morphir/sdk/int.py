"""Morphir.SDK.Int: fixed-width integers.

`Int8`, `Int16`, `Int32` and `Int64` are `NewType` wrappers over `int`. They
have no run-time cost and a type checker keeps them apart. `to_int8` and the
other `to_` functions check the range; `from_int8` and the other `from_`
functions give the plain `int` back.

Python integers have no size limit, so `Int64` covers the full signed 64-bit
range.
"""

from typing import NewType

from morphir.sdk.maybe import Just, Maybe, Nothing

__all__ = [
    "Int8",
    "Int16",
    "Int32",
    "Int64",
    "from_int8",
    "from_int16",
    "from_int32",
    "from_int64",
    "to_int8",
    "to_int16",
    "to_int32",
    "to_int64",
]

Int8 = NewType("Int8", int)
"""A signed 8-bit integer."""

Int16 = NewType("Int16", int)
"""A signed 16-bit integer."""

Int32 = NewType("Int32", int)
"""A signed 32-bit integer."""

Int64 = NewType("Int64", int)
"""A signed 64-bit integer."""


def _fits(bits: int, n: int) -> bool:
    limit = 1 << (bits - 1)
    return isinstance(n, int) and not isinstance(n, bool) and -limit <= n < limit


def from_int8(n: Int8) -> int:
    """Convert an `Int8` to an `int`."""
    return int(n)


def to_int8(n: int) -> Maybe[Int8]:
    """Convert an `int` to an `Int8`, or `Nothing` when it is out of range."""
    return Just(Int8(n)) if _fits(8, n) else Nothing()


def from_int16(n: Int16) -> int:
    """Convert an `Int16` to an `int`."""
    return int(n)


def to_int16(n: int) -> Maybe[Int16]:
    """Convert an `int` to an `Int16`, or `Nothing` when it is out of range."""
    return Just(Int16(n)) if _fits(16, n) else Nothing()


def from_int32(n: Int32) -> int:
    """Convert an `Int32` to an `int`."""
    return int(n)


def to_int32(n: int) -> Maybe[Int32]:
    """Convert an `int` to an `Int32`, or `Nothing` when it is out of range."""
    return Just(Int32(n)) if _fits(32, n) else Nothing()


def from_int64(n: Int64) -> int:
    """Convert an `Int64` to an `int`."""
    return int(n)


def to_int64(n: int) -> Maybe[Int64]:
    """Convert an `int` to an `Int64`, or `Nothing` when it is out of range."""
    return Just(Int64(n)) if _fits(64, n) else Nothing()
