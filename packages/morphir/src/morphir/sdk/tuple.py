"""Morphir.SDK.Tuple: helpers for pairs.

An Elm tuple `( a, b )` is a Python `tuple[A, B]`.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["first", "map_both", "map_first", "map_second", "pair", "second"]


def pair[A, B](a: A, b: B) -> tuple[A, B]:
    """Create a pair."""
    return (a, b)


def first[A, B](pair: tuple[A, B]) -> A:
    """Return the first value of a pair."""
    return pair[0]


def second[A, B](pair: tuple[A, B]) -> B:
    """Return the second value of a pair."""
    return pair[1]


def map_first[A, B, X](f: Callable[[A], X], pair: tuple[A, B]) -> tuple[X, B]:
    """Apply a function to the first value of a pair."""
    return (f(pair[0]), pair[1])


def map_second[A, B, Y](f: Callable[[B], Y], pair: tuple[A, B]) -> tuple[A, Y]:
    """Apply a function to the second value of a pair."""
    return (pair[0], f(pair[1]))


def map_both[A, B, X, Y](
    f: Callable[[A], X], g: Callable[[B], Y], pair: tuple[A, B]
) -> tuple[X, Y]:
    """Apply one function to each value of a pair."""
    return (f(pair[0]), g(pair[1]))
