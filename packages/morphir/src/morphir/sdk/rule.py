"""Morphir.SDK.Rule: business logic as a sequence of rules.

A `Rule[A, B]` is a partial function: a function from `A` to `Maybe[B]` that
yields `Just` a result when it applies to the input, and `Nothing` when it does
not. `chain` composes rules into one rule that tries them in sequence. Morphir
supports only sequential evaluation, so the result is always predictable.

`any`, `is_`, `any_of` and `none_of` are the matchers for the cells of a
decision table:

    >>> from morphir.sdk import rule as Rule
    >>> from morphir.sdk.maybe import Just, Maybe, Nothing
    >>> def discount(order: tuple[str, int]) -> Maybe[float]:
    ...     kind, quantity = order
    ...     if Rule.is_("gold", kind) and Rule.any(quantity):
    ...         return Just(0.2)
    ...     if Rule.any_of(("silver", "bronze"), kind) and Rule.none_of((0,), quantity):
    ...         return Just(0.1)
    ...     return Nothing()
    >>> Rule.chain((discount, lambda order: Just(0.0)))(("bronze", 3))
    Just(value=0.1)

`any` shadows the Python built-in, and `is` is a Python keyword, so it is `is_`.
Import the module with an alias, not the names.
"""

from typing import TYPE_CHECKING

from morphir.sdk import _compare
from morphir.sdk.maybe import Just, Maybe, Nothing

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

__all__ = [
    "Rule",
    "any",
    "any_of",
    "chain",
    "is_",
    "none_of",
]

type Rule[A, B] = Callable[[A], Maybe[B]]
"""A function that yields `Just` a result when it applies, else `Nothing`."""


def chain[A, B](rules: Sequence[Rule[A, B]]) -> Rule[A, B]:
    """Chain a list of rules into a single rule.

    The rules are evaluated in the sequence in which they were supplied. The
    first rule that yields a `Just` gives the result, and the rules after it do
    not run.

    Args:
        rules: The rules, in the sequence of evaluation.

    Returns:
        A rule that yields the result of the first rule that matches, or
        `Nothing` when no rule matches.
    """
    fixed = tuple(rules)

    def chained(value: A) -> Maybe[B]:
        for rule in fixed:
            result = rule(value)
            if isinstance(result, Just):
                return result
        return Nothing()

    return chained


def any(value: object) -> bool:
    """Return `True` for any input. Use as a wildcard in a decision table."""
    return True


def is_[A](ref: A, value: A) -> bool:
    """Check that the value is structurally equal to the reference (Elm `is`).

    Raises:
        TypeError: If a value is a function or holds a function.
    """
    return _compare.equal(ref, value)


def any_of[A](ref: Sequence[A], value: A) -> bool:
    """Check that the value is in the list of references, by structural equality.

    Raises:
        TypeError: If a value is a function or holds a function.
    """
    return next((True for item in ref if _compare.equal(value, item)), False)


def none_of[A](ref: Sequence[A], value: A) -> bool:
    """Check that the value is not in the list of references.

    Raises:
        TypeError: If a value is a function or holds a function.
    """
    return not any_of(ref, value)
