"""Tests for morphir.sdk.aggregate (Morphir.SDK.Aggregate).

The `TestAggregateMap` cases are a port of `Morphir.SDK.AggregateTests`.
"""

import math
from dataclasses import dataclass

from morphir.sdk import aggregate as agg
from morphir.sdk import dict as dict_
from morphir.sdk import key
from morphir.sdk.aggregate import Aggregation, Aggregator


@dataclass(frozen=True, slots=True)
class _Input:
    key1: str
    key2: str
    value: float


_DATA: tuple[_Input, ...] = (
    _Input("k1_1", "k2_1", 1),
    _Input("k1_1", "k2_1", 2),
    _Input("k1_1", "k2_2", 3),
    _Input("k1_1", "k2_2", 4),
    _Input("k1_2", "k2_1", 5),
    _Input("k1_2", "k2_1", 6),
    _Input("k1_2", "k2_2", 7),
    _Input("k1_2", "k2_2", 8),
)


def _value(a: _Input) -> float:
    return a.value


def _key1(a: _Input) -> str:
    return a.key1


def _key2(a: _Input) -> str:
    return a.key2


def _key12(a: _Input) -> tuple[str, str]:
    return key.key2(_key1, _key2, a)


def _expect(values: tuple[float, ...]) -> tuple[tuple[_Input, float], ...]:
    return tuple(zip(_DATA, values, strict=True))


def _pair(total: float, a: _Input) -> tuple[_Input, float]:
    return (a, total)


def _ratio(total: float, a: _Input) -> tuple[_Input, float]:
    return (a, total / a.value)


class TestAggregateMap:
    def test_aggregate_by_single_key(self) -> None:
        result = agg.aggregate_map(agg.by_key(_key1, agg.sum_of(_value)), _ratio, _DATA)
        assert result == _expect(
            (10 / 1, 10 / 2, 10 / 3, 10 / 4, 26 / 5, 26 / 6, 26 / 7, 26 / 8)
        )

    def test_aggregate_by_composite_key(self) -> None:
        result = agg.aggregate_map(
            agg.by_key(_key12, agg.sum_of(_value)), _ratio, _DATA
        )
        assert result == _expect(
            (3 / 1, 3 / 2, 7 / 3, 7 / 4, 11 / 5, 11 / 6, 15 / 7, 15 / 8)
        )

    def test_aggregate_by_no_key_and_filter(self) -> None:
        result = agg.aggregate_map(
            agg.with_filter(lambda a: a.value > 3, agg.sum_of(_value)), _ratio, _DATA
        )
        assert result == _expect(tuple(30 / n for n in range(1, 9)))

    def test_aggregate_2(self) -> None:
        result = agg.aggregate_map2(
            agg.by_key(_key1, agg.sum_of(_value)),
            agg.by_key(_key2, agg.maximum_of(_value)),
            lambda total, maximum, a: (a, total * maximum / a.value),
            _DATA,
        )
        assert result == _expect(
            (
                10 * 6 / 1,
                10 * 6 / 2,
                10 * 8 / 3,
                10 * 8 / 4,
                26 * 6 / 5,
                26 * 6 / 6,
                26 * 8 / 7,
                26 * 8 / 8,
            )
        )

    def test_aggregate_3(self) -> None:
        result = agg.aggregate_map3(
            agg.by_key(_key1, agg.sum_of(_value)),
            agg.by_key(_key2, agg.maximum_of(_value)),
            agg.by_key(_key12, agg.minimum_of(_value)),
            lambda total, maximum, minimum, a: (
                a,
                total * maximum / a.value + minimum,
            ),
            _DATA,
        )
        assert result == _expect(
            (
                10 * 6 / 1 + 1,
                10 * 6 / 2 + 1,
                10 * 8 / 3 + 3,
                10 * 8 / 4 + 3,
                26 * 6 / 5 + 5,
                26 * 6 / 6 + 5,
                26 * 8 / 7 + 7,
                26 * 8 / 8 + 7,
            )
        )

    def test_aggregate_4(self) -> None:
        result = agg.aggregate_map4(
            agg.by_key(_key1, agg.sum_of(_value)),
            agg.by_key(_key2, agg.maximum_of(_value)),
            agg.by_key(_key12, agg.minimum_of(_value)),
            agg.by_key(_key12, agg.average_of(_value)),
            lambda total, maximum, minimum, average, a: (
                a,
                total * maximum / a.value + minimum + average,
            ),
            _DATA,
        )
        assert result == _expect(
            (
                10 * 6 / 1 + 1 + 1.5,
                10 * 6 / 2 + 1 + 1.5,
                10 * 8 / 3 + 3 + 3.5,
                10 * 8 / 4 + 3 + 3.5,
                26 * 6 / 5 + 5 + 5.5,
                26 * 6 / 6 + 5 + 5.5,
                26 * 8 / 7 + 7 + 7.5,
                26 * 8 / 8 + 7 + 7.5,
            )
        )

    def test_count_by_single_key(self) -> None:
        result = agg.aggregate_map(agg.by_key(_key1, agg.count()), _pair, _DATA)
        assert result == _expect((4, 4, 4, 4, 4, 4, 4, 4))

    def test_sum_by_single_key(self) -> None:
        result = agg.aggregate_map(agg.by_key(_key1, agg.sum_of(_value)), _pair, _DATA)
        assert result == _expect((10, 10, 10, 10, 26, 26, 26, 26))

    def test_avg_by_single_key(self) -> None:
        result = agg.aggregate_map(
            agg.by_key(_key1, agg.average_of(_value)), _pair, _DATA
        )
        assert result == _expect((2.5, 2.5, 2.5, 2.5, 6.5, 6.5, 6.5, 6.5))

    def test_min_by_single_key(self) -> None:
        result = agg.aggregate_map(
            agg.by_key(_key1, agg.minimum_of(_value)), _pair, _DATA
        )
        assert result == _expect((1, 1, 1, 1, 5, 5, 5, 5))

    def test_max_by_single_key(self) -> None:
        result = agg.aggregate_map(
            agg.by_key(_key1, agg.maximum_of(_value)), _pair, _DATA
        )
        assert result == _expect((4, 4, 4, 4, 8, 8, 8, 8))

    def test_weighted_average_by_single_key(self) -> None:
        result = agg.aggregate_map(
            agg.by_key(_key1, agg.weighted_average_of(_value, _value)), _pair, _DATA
        )
        assert result == _expect((3, 3, 3, 3, 174 / 26, 174 / 26, 174 / 26, 174 / 26))


class TestAggregateMapEdges:
    def test_key_with_no_row_after_the_filter_gives_zero(self) -> None:
        result = agg.aggregate_map(
            agg.with_filter(
                lambda a: a.key1 == "k1_2", agg.by_key(_key1, agg.sum_of(_value))
            ),
            _pair,
            _DATA,
        )
        assert result == _expect((0, 0, 0, 0, 26, 26, 26, 26))

    def test_empty_list(self) -> None:
        assert agg.aggregate_map(agg.count(), _pair, ()) == ()

    def test_accepts_a_list_and_yields_a_tuple(self) -> None:
        result = agg.aggregate_map(agg.count(), _pair, list(_DATA[:2]))
        assert result == ((_DATA[0], 2), (_DATA[1], 2))

    def test_average_with_zero_weight_is_nan(self) -> None:
        result = agg.aggregate_map(
            agg.weighted_average_of(lambda _: 0.0, _value), _pair, _DATA[:1]
        )
        assert math.isnan(result[0][1])


class TestOperators:
    def test_operators_start_with_no_key_and_no_filter(self) -> None:
        aggregation = agg.sum_of(_value)
        assert aggregation.key(_DATA[0]) == 0
        assert aggregation.filter(_DATA[0]) is True
        assert aggregation.operator == agg.Sum(_value)

    def test_operator_cases(self) -> None:
        assert agg.count().operator == agg.Count()
        assert agg.average_of(_value).operator == agg.Avg(_value)
        assert agg.minimum_of(_value).operator == agg.Min(_value)
        assert agg.maximum_of(_value).operator == agg.Max(_value)
        assert agg.weighted_average_of(_key_weight, _value).operator == agg.WAvg(
            _key_weight, _value
        )

    def test_by_key_changes_only_the_key(self) -> None:
        source = agg.with_filter(_is_small, agg.sum_of(_value))
        keyed = agg.by_key(_key1, source)
        assert keyed == Aggregation(_key1, _is_small, agg.Sum(_value))

    def test_with_filter_changes_only_the_filter(self) -> None:
        source: Aggregation[_Input, str] = agg.by_key(_key1, agg.count())
        assert agg.with_filter(_is_small, source) == Aggregation(
            _key1, _is_small, agg.Count()
        )


def _key_weight(a: _Input) -> float:
    return a.value * 2


def _is_small(a: _Input) -> bool:
    return a.value < 7


class TestGroupBy:
    def test_group_by(self) -> None:
        assert agg.group_by(_key1, _DATA) == dict_.from_list(
            (("k1_1", _DATA[:4]), ("k1_2", _DATA[4:]))
        )

    def test_group_by_composite_key(self) -> None:
        grouped = agg.group_by(_key12, _DATA)
        assert dict_.keys(grouped) == (
            ("k1_1", "k2_1"),
            ("k1_1", "k2_2"),
            ("k1_2", "k2_1"),
            ("k1_2", "k2_2"),
        )
        assert dict_.values(grouped)[0] == _DATA[:2]

    def test_group_by_keeps_the_source_order_in_a_group(self) -> None:
        grouped = agg.group_by(_key2, _DATA)
        assert dict_.to_list(grouped) == (
            ("k2_1", (_DATA[0], _DATA[1], _DATA[4], _DATA[5])),
            ("k2_2", (_DATA[2], _DATA[3], _DATA[6], _DATA[7])),
        )

    def test_group_by_empty_list(self) -> None:
        assert agg.group_by(_key1, ()) == dict_.empty()


@dataclass(frozen=True, slots=True)
class _Summary:
    key: str
    count: float
    sum: float
    max: float
    min: float


def _summarise(group: str, inputs: Aggregator[_Input, int]) -> _Summary:
    return _Summary(
        key=group,
        count=inputs(agg.with_filter(_is_small, agg.count())),
        sum=inputs(agg.sum_of(_value)),
        max=inputs(agg.maximum_of(_value)),
        min=inputs(agg.minimum_of(_value)),
    )


class TestAggregate:
    def test_aggregate_after_group_by(self) -> None:
        assert agg.aggregate(_summarise, agg.group_by(_key1, _DATA)) == (
            _Summary("k1_1", 4, 10, 4, 1),
            _Summary("k1_2", 2, 26, 8, 5),
        )

    def test_aggregate_with_all_rows_filtered_out_gives_zero(self) -> None:
        def count_none(_: str, inputs: Aggregator[_Input, int]) -> float:
            return inputs(agg.with_filter(lambda _: False, agg.count()))

        result = agg.aggregate(count_none, agg.group_by(_key1, _DATA))
        assert result == (0, 0)

    def test_aggregate_empty_dict(self) -> None:
        assert agg.aggregate(_summarise, dict_.empty()) == ()
