"""Morphir.SDK.Aggregate: aggregations for large data sets.

An `Aggregation[A, K]` tells how to aggregate rows of type `A`: the key that
groups the rows, a filter that removes rows before the aggregation, and the
operator (count, sum, average, minimum, maximum or weighted average). Build one
with `count`, `sum_of`, `average_of`, `minimum_of`, `maximum_of` or
`weighted_average_of`, then set the key with `by_key` and the filter with
`with_filter`. All aggregated values are floats.

There are two ways to use an aggregation:

* `aggregate_map` to `aggregate_map4` map each row together with the aggregated
  values of the group of that row.
* `group_by` and then `aggregate` yield one item for each group.

    >>> from morphir.sdk import aggregate as Aggregate
    >>> rows = (("a", 1.0), ("a", 2.0), ("b", 5.0))
    >>> total = Aggregate.by_key(lambda r: r[0], Aggregate.sum_of(lambda r: r[1]))
    >>> Aggregate.aggregate_map(total, lambda t, r: (r[0], r[1] / t), rows)
    (('a', 0.3333333333333333), ('a', 0.6666666666666666), ('b', 1.0))
    >>> Aggregate.aggregate(
    ...     lambda key, inputs: (key, inputs(Aggregate.count())),
    ...     Aggregate.group_by(lambda r: r[0], rows),
    ... )
    (('a', 2.0), ('b', 1.0))

All functions take their arguments in Elm order, with the data last, and are
not curried. Lists are tuples: the functions accept any `Sequence` and yield a
tuple.

This module is the runtime API only. The Elm module also has
`constructAggregationCall`, `AggregationCall`, `AggregateValue` and
`ConstructAggregationError`. Those inspect Morphir IR values (`TypedValue`) for
the backends. They are tooling, they are not in the `Morphir.IR.SDK.Aggregate`
specification, and they are not part of this module.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from morphir.sdk import _compare, basics
from morphir.sdk import dict as dict_
from morphir.sdk.key import Key0, key0

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from morphir.sdk._compare import Comparable
    from morphir.sdk.dict import Dict

__all__ = [
    "Aggregation",
    "Aggregator",
    "Avg",
    "Count",
    "Max",
    "Min",
    "Operator",
    "Sum",
    "WAvg",
    "aggregate",
    "aggregate_map",
    "aggregate_map2",
    "aggregate_map3",
    "aggregate_map4",
    "average_of",
    "by_key",
    "count",
    "group_by",
    "maximum_of",
    "minimum_of",
    "sum_of",
    "weighted_average_of",
    "with_filter",
]


# Operators


@dataclass(frozen=True, slots=True)
class Count:
    """The operator that counts the rows."""


@dataclass(frozen=True, slots=True)
class Sum[A]:
    """The operator that adds the values of the rows."""

    get_value: Callable[[A], float]


@dataclass(frozen=True, slots=True)
class Avg[A]:
    """The operator that gives the average of the values of the rows."""

    get_value: Callable[[A], float]


@dataclass(frozen=True, slots=True)
class Min[A]:
    """The operator that gives the smallest of the values of the rows."""

    get_value: Callable[[A], float]


@dataclass(frozen=True, slots=True)
class Max[A]:
    """The operator that gives the largest of the values of the rows."""

    get_value: Callable[[A], float]


@dataclass(frozen=True, slots=True)
class WAvg[A]:
    """The operator that gives the weighted average of the values of the rows."""

    get_weight: Callable[[A], float]
    get_value: Callable[[A], float]


type Operator[A] = Count | Sum[A] | Avg[A] | Min[A] | Max[A] | WAvg[A]
"""The aggregation operation to apply to the rows of a group."""


@dataclass(frozen=True, slots=True)
class Aggregation[A, K]:
    """An aggregation on rows of type `A` with a key of type `K`.

    Attributes:
        key: A function that gives the key of a row. Rows with equal keys are
            aggregated together.
        filter: A test that a row must pass to be part of the aggregation.
        operator: The aggregation operation to apply.
    """

    key: Callable[[A], K]
    filter: Callable[[A], bool]
    operator: Operator[A]


type Aggregator[A, K] = Callable[[Aggregation[A, K]], float]
"""A function that applies an aggregation to the rows of one group."""


def _always_true(_: object) -> bool:
    return True


def _one(_: object) -> float:
    return 1.0


def _operator_to_aggregation[A](operator: Operator[A]) -> Aggregation[A, Key0]:
    return Aggregation(key=key0, filter=_always_true, operator=operator)


def count[A]() -> Aggregation[A, Key0]:  # pyright: ignore[reportInvalidTypeVarUse]
    """Count the rows in a group.

    In Elm `count` is a value. Here it is a function with no arguments, so that
    the type checker can give each use its own row type.
    """
    return _operator_to_aggregation(Count())


def sum_of[A](get_value: Callable[[A], float]) -> Aggregation[A, Key0]:
    """Add the values that a function gives for each row of a group."""
    return _operator_to_aggregation(Sum(get_value))


def average_of[A](get_value: Callable[[A], float]) -> Aggregation[A, Key0]:
    """Give the average of the values that a function gives for each row."""
    return _operator_to_aggregation(Avg(get_value))


def minimum_of[A](get_value: Callable[[A], float]) -> Aggregation[A, Key0]:
    """Give the smallest of the values that a function gives for each row."""
    return _operator_to_aggregation(Min(get_value))


def maximum_of[A](get_value: Callable[[A], float]) -> Aggregation[A, Key0]:
    """Give the largest of the values that a function gives for each row."""
    return _operator_to_aggregation(Max(get_value))


def weighted_average_of[A](
    get_weight: Callable[[A], float], get_value: Callable[[A], float]
) -> Aggregation[A, Key0]:
    """Give the weighted average of the values of the rows of a group.

    Args:
        get_weight: A function that gives the weight of a row.
        get_value: A function that gives the value of a row.

    Returns:
        An aggregation that divides the sum of `weight * value` by the sum of
        the weights. When the sum of the weights is zero the division follows
        IEEE 754, as in Elm: the result is `NaN` or an infinity.
    """
    return _operator_to_aggregation(WAvg(get_weight, get_value))


def by_key[A, K](
    key: Callable[[A], K], aggregation: Aggregation[A, Key0]
) -> Aggregation[A, K]:
    """Set the key of an aggregation. The filter and the operator stay."""
    return Aggregation(
        key=key, filter=aggregation.filter, operator=aggregation.operator
    )


def with_filter[A, K](
    filter: Callable[[A], bool],
    aggregation: Aggregation[A, K],
) -> Aggregation[A, K]:
    """Set the filter of an aggregation. The key and the operator stay.

    A filter that the aggregation already has is replaced, as in Elm.
    """
    return Aggregation(
        key=aggregation.key, filter=filter, operator=aggregation.operator
    )


# Aggregation of rows


def _elm_min(a: float, b: float) -> float:
    return a if a < b else b


def _elm_max(a: float, b: float) -> float:
    return a if a > b else b


def _fold[A](
    get_key: Callable[[A], object],
    get_value: Callable[[A], float],
    combine: Callable[[float, float], float],
    rows: Sequence[A],
) -> dict[object, float]:
    totals: dict[object, float] = {}
    for row in rows:
        key = _compare.freeze(get_key(row))
        value = get_value(row)
        totals[key] = combine(totals[key], value) if key in totals else value
    return totals


def _add(a: float, b: float) -> float:
    return a + b


def _ratio(
    numerators: dict[object, float], denominators: dict[object, float]
) -> dict[object, float]:
    return {
        key: basics.divide(numerator, denominators.get(key, 0.0))
        for key, numerator in numerators.items()
    }


def _aggregate_help[A](
    get_key: Callable[[A], object], operator: Operator[A], rows: Sequence[A]
) -> dict[object, float]:
    match operator:
        case Count():
            return _fold(get_key, _one, _add, rows)
        case Sum(get_value):
            return _fold(get_key, get_value, _add, rows)
        case Avg(get_value):
            return _ratio(
                _fold(get_key, get_value, _add, rows),
                _fold(get_key, _one, _add, rows),
            )
        case Min(get_value):
            return _fold(get_key, get_value, _elm_min, rows)
        case Max(get_value):
            return _fold(get_key, get_value, _elm_max, rows)
        case WAvg(get_weight, get_value):

            def weighted(row: A) -> float:
                return get_weight(row) * get_value(row)

            return _ratio(
                _fold(get_key, weighted, _add, rows),
                _fold(get_key, get_weight, _add, rows),
            )


def _lookup[A, K](
    aggregation: Aggregation[A, K], rows: Sequence[A]
) -> Callable[[A], float]:
    included = tuple(row for row in rows if aggregation.filter(row))
    totals = _aggregate_help(aggregation.key, aggregation.operator, included)

    def value_for(row: A) -> float:
        return totals.get(_compare.freeze(aggregation.key(row)), 0.0)

    return value_for


def aggregate_map[A, B, K1](
    agg1: Aggregation[A, K1], f: Callable[[float, A], B], xs: Sequence[A]
) -> tuple[B, ...]:
    """Map each row together with one aggregated value.

    The aggregation is computed one time on the rows that pass its filter. Each
    row of the list, also one that does not pass the filter, then gets the
    aggregated value for its key.

    Args:
        agg1: The aggregation.
        f: The mapping function. It gets the aggregated value for the key of
            the row, then the row. The value is 0 when no row with that key
            passed the filter.
        xs: The rows.

    Returns:
        The mapped rows, in the order of the input.
    """
    value1 = _lookup(agg1, xs)
    return tuple(f(value1(x), x) for x in xs)


def aggregate_map2[A, B, K1, K2](
    agg1: Aggregation[A, K1],
    agg2: Aggregation[A, K2],
    f: Callable[[float, float, A], B],
    xs: Sequence[A],
) -> tuple[B, ...]:
    """Map each row together with two aggregated values. See `aggregate_map`."""
    value1 = _lookup(agg1, xs)
    value2 = _lookup(agg2, xs)
    return tuple(f(value1(x), value2(x), x) for x in xs)


def aggregate_map3[A, B, K1, K2, K3](
    agg1: Aggregation[A, K1],
    agg2: Aggregation[A, K2],
    agg3: Aggregation[A, K3],
    f: Callable[[float, float, float, A], B],
    xs: Sequence[A],
) -> tuple[B, ...]:
    """Map each row together with three aggregated values. See `aggregate_map`."""
    value1 = _lookup(agg1, xs)
    value2 = _lookup(agg2, xs)
    value3 = _lookup(agg3, xs)
    return tuple(f(value1(x), value2(x), value3(x), x) for x in xs)


def aggregate_map4[A, B, K1, K2, K3, K4](
    agg1: Aggregation[A, K1],
    agg2: Aggregation[A, K2],
    agg3: Aggregation[A, K3],
    agg4: Aggregation[A, K4],
    f: Callable[[float, float, float, float, A], B],
    xs: Sequence[A],
) -> tuple[B, ...]:
    """Map each row together with four aggregated values. See `aggregate_map`."""
    value1 = _lookup(agg1, xs)
    value2 = _lookup(agg2, xs)
    value3 = _lookup(agg3, xs)
    value4 = _lookup(agg4, xs)
    return tuple(f(value1(x), value2(x), value3(x), value4(x), x) for x in xs)


# Grouping


def group_by[A, K: Comparable](
    get_key: Callable[[A], K], xs: Sequence[A]
) -> Dict[K, tuple[A, ...]]:
    """Group the rows of a list into a dictionary.

    Args:
        get_key: A function that gives the key of a row.
        xs: The rows.

    Returns:
        A dictionary from each key to the rows with that key. The rows of a
        group keep the order that they have in the list.

    Raises:
        TypeError: If the keys are not comparable.
    """
    groups: dict[K, list[A]] = {}
    for x in xs:
        groups.setdefault(_compare.freeze(get_key(x)), []).append(x)
    return dict_.from_list([(key, tuple(rows)) for key, rows in groups.items()])


def aggregate[A, B, K: Comparable](
    f: Callable[[K, Aggregator[A, Key0]], B], groups: Dict[K, tuple[A, ...]]
) -> tuple[B, ...]:
    """Aggregate a dictionary of groups into a list with one item for each key.

    This function is for use after `group_by`.

    Args:
        f: A function that gets a key and an aggregator, and yields the item for
            that key. The aggregator is a function that takes an aggregation
            with no key (`count()`, `sum_of(...)`, also with `with_filter`) and
            yields the aggregated value for the rows of the group. The value is
            0 when no row passes the filter.
        groups: The dictionary of groups.

    Returns:
        One item for each key, in key order.
    """

    def item(key: K, rows: tuple[A, ...]) -> B:
        def aggregator(aggregation: Aggregation[A, Key0]) -> float:
            included = tuple(row for row in rows if aggregation.filter(row))
            totals = _aggregate_help(aggregation.key, aggregation.operator, included)
            return totals.get(0, 0.0)

        return f(key, aggregator)

    return tuple(item(key, rows) for key, rows in dict_.to_list(groups))
