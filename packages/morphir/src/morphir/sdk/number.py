"""Morphir.SDK.Number: exact rational numbers.

A `Number` is a frozen dataclass with an integer `numerator` and `denominator`.
Python integers have no size limit, so all arithmetic is exact.

As in the Elm runtime, arithmetic does not reduce its result:
`add(1/2, 1/2)` is `4/4`. Use `simplify` to reduce a number. Because of this,
`==` on two `Number` values is structural (`Number(1, 2) != Number(2, 4)`); use
`equal` to compare by value.

The name `abs` in this module shadows a Python built-in. Import the module with
an alias, not the names:

    >>> from morphir.sdk import number as Number
    >>> Number.to_fractional_string(Number.add(Number.from_int(1), Number.one))
    '2/1'

Departures from the Elm runtime:

* Comparisons move a negative sign out of the denominator before they
  cross-multiply. The Elm runtime does not, so it orders `3/-4` and `1/2`
  wrongly.
* `simplify` yields a positive denominator: `3/-6` becomes `-1/2`. The Elm
  runtime yields `1/-2`.
"""

import builtins
import math
from dataclasses import dataclass

from morphir.sdk import decimal as _sdk_decimal
from morphir.sdk import maybe
from morphir.sdk.maybe import Just, Maybe, Nothing
from morphir.sdk.result import Err, Ok, Result

__all__ = [
    "DivisionByZero",
    "Number",
    "abs",
    "add",
    "coerce_to_decimal",
    "divide",
    "equal",
    "from_int",
    "greater_than",
    "greater_than_or_equal",
    "is_simplified",
    "less_than",
    "less_than_or_equal",
    "multiply",
    "negate",
    "not_equal",
    "one",
    "reciprocal",
    "simplify",
    "subtract",
    "to_decimal",
    "to_fractional_string",
    "zero",
]


@dataclass(frozen=True, slots=True)
class Number:
    """A rational number. The fraction is not reduced."""

    numerator: int
    denominator: int


@dataclass(frozen=True, slots=True)
class DivisionByZero:
    """The error that `divide` yields for a zero divisor."""


zero: Number = Number(0, 1)
"""The number 0, as 0/1."""

one: Number = Number(1, 1)
"""The number 1, as 1/1."""


def from_int(n: int) -> Number:
    """Convert an integer to a `Number` with a denominator of 1."""
    return Number(n, 1)


# Convert to


def to_decimal(n: Number) -> Maybe[_sdk_decimal.Decimal]:
    """Convert to a `Decimal`, or `Nothing` when the denominator is zero.

    A quotient that is not exact has 50 significant digits.
    """
    return _sdk_decimal.div(
        _sdk_decimal.from_int(n.numerator), _sdk_decimal.from_int(n.denominator)
    )


def coerce_to_decimal(default: _sdk_decimal.Decimal, n: Number) -> _sdk_decimal.Decimal:
    """Convert to a `Decimal`, or yield the default when the denominator is zero."""
    return maybe.with_default(default, to_decimal(n))


def to_fractional_string(n: Number) -> str:
    """Convert to a string of the form "numerator/denominator"."""
    return f"{n.numerator}/{n.denominator}"


# Comparison


def _cross_products(a: Number, b: Number) -> tuple[int, int]:
    """Return the two integers whose order is the order of `a` and `b`.

    A negative denominator changes the direction of the comparison, so the sign
    moves to the numerator first.
    """
    sign = (-1 if a.denominator < 0 else 1) * (-1 if b.denominator < 0 else 1)
    return (
        sign * a.numerator * b.denominator,
        sign * b.numerator * a.denominator,
    )


def equal(a: Number, b: Number) -> bool:
    """Check `a == b` by value, so 1/2 equals 2/4."""
    x, y = _cross_products(a, b)
    return x == y


def not_equal(a: Number, b: Number) -> bool:
    """Check `a /= b` by value."""
    return not equal(a, b)


def less_than(a: Number, b: Number) -> bool:
    """Check `a < b`."""
    x, y = _cross_products(a, b)
    return x < y


def less_than_or_equal(a: Number, b: Number) -> bool:
    """Check `a <= b`."""
    x, y = _cross_products(a, b)
    return x <= y


def greater_than(a: Number, b: Number) -> bool:
    """Check `a > b`."""
    x, y = _cross_products(a, b)
    return x > y


def greater_than_or_equal(a: Number, b: Number) -> bool:
    """Check `a >= b`."""
    x, y = _cross_products(a, b)
    return x >= y


# Arithmetic


def _is_zero(n: Number) -> bool:
    return n.numerator == 0


def negate(n: Number) -> Number:
    """Change the sign of a number."""
    return Number(-n.numerator, n.denominator)


def abs(n: Number) -> Number:
    """Return the absolute value of a number."""
    return Number(builtins.abs(n.numerator), builtins.abs(n.denominator))


def reciprocal(n: Number) -> Number:
    """Swap the numerator and the denominator. Zero stays as it is, as in Elm."""
    return n if _is_zero(n) else Number(n.denominator, n.numerator)


def add(a: Number, b: Number) -> Number:
    """Add two numbers. The result is not reduced."""
    return Number(
        a.numerator * b.denominator + a.denominator * b.numerator,
        a.denominator * b.denominator,
    )


def subtract(a: Number, b: Number) -> Number:
    """Subtract the second number from the first. The result is not reduced."""
    return Number(
        a.numerator * b.denominator - a.denominator * b.numerator,
        a.denominator * b.denominator,
    )


def multiply(a: Number, b: Number) -> Number:
    """Multiply two numbers. The result is not reduced."""
    return Number(a.numerator * b.numerator, a.denominator * b.denominator)


def divide(a: Number, b: Number) -> Result[DivisionByZero, Number]:
    """Divide two numbers, or yield `Err(DivisionByZero())` for a zero divisor.

    The result is not reduced.
    """
    if _is_zero(b):
        return Err(DivisionByZero())
    return Ok(Number(a.numerator * b.denominator, a.denominator * b.numerator))


# Simplify


def simplify(n: Number) -> Maybe[Number]:
    """Reduce a number to lowest terms, with a positive denominator.

    Yields `Nothing` when the denominator is zero.
    """
    if n.denominator == 0:
        return Nothing()
    factor = math.gcd(n.numerator, n.denominator)
    if n.denominator < 0:
        factor = -factor
    return Just(Number(n.numerator // factor, n.denominator // factor))


def is_simplified(n: Number) -> bool:
    """Check that `simplify` does not change a number.

    A number with a zero denominator counts as simplified, as in the Elm
    runtime.
    """
    return maybe.with_default(n, simplify(n)) == n
