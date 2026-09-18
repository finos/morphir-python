"""Tests for morphir.sdk.key (Morphir.SDK.Key)."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from morphir.sdk import dict as dict_
from morphir.sdk import key
from morphir.sdk.basics import Order, compare
from morphir.sdk.maybe import Just

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True, slots=True)
class _Entity:
    foo: str
    bar: int
    baz: float


_ENTITY = _Entity("a", 1, 2.5)


def _getter(index: int) -> Callable[[tuple[int, ...]], int]:
    return lambda row: row[index]


_ROW = tuple(range(100, 116))


class TestKey0:
    def test_no_key_is_zero(self) -> None:
        assert key.no_key(_ENTITY) == 0
        assert key.no_key("anything") == 0

    def test_key0_is_zero(self) -> None:
        assert key.key0(_ENTITY) == 0

    def test_key0_is_comparable(self) -> None:
        assert compare(key.key0(1), key.no_key(2)) is Order.EQ


class TestCompositeKeys:
    def test_key2(self) -> None:
        assert key.key2(lambda e: e.foo, lambda e: e.bar, _ENTITY) == ("a", 1)

    def test_key3(self) -> None:
        assert key.key3(lambda e: e.bar, lambda e: e.foo, lambda e: e.baz, _ENTITY) == (
            1,
            "a",
            2.5,
        )

    @pytest.mark.parametrize("size", range(2, 17))
    def test_every_size_yields_a_flat_tuple(self, size: int) -> None:
        make = getattr(key, f"key{size}")
        getters = [_getter(index) for index in range(size)]
        assert make(*getters, _ROW) == _ROW[:size]

    @pytest.mark.parametrize("size", range(2, 17))
    def test_keys_are_comparable(self, size: int) -> None:
        make = getattr(key, f"key{size}")
        getters = [_getter(index) for index in range(size)]
        low = make(*getters, _ROW)
        high = make(*getters, (*_ROW[: size - 1], 999, *_ROW[size:]))
        assert compare(low, high) is Order.LT
        assert compare(low, low) is Order.EQ

    def test_keys_work_as_dict_keys(self) -> None:
        rows = (_Entity("b", 1, 0.0), _Entity("a", 2, 0.0), _Entity("a", 1, 0.0))
        entries = tuple(
            (key.key2(lambda e: e.foo, lambda e: e.bar, row), row) for row in rows
        )
        by_key = dict_.from_list(entries)
        assert dict_.keys(by_key) == (("a", 1), ("a", 2), ("b", 1))
        assert dict_.get(("a", 2), by_key) == Just(rows[1])
