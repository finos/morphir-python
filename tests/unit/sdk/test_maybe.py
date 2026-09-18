"""Tests for morphir.sdk.maybe (Morphir.SDK.Maybe)."""

import dataclasses

import pytest

from morphir.sdk import maybe
from morphir.sdk.maybe import Just, Maybe, Nothing


class TestMaybeType:
    def test_structural_equality_and_hash(self) -> None:
        assert Just(1) == Just(1)
        assert Just(1) != Just(2)
        assert Nothing() == Nothing()
        assert Just(1) != Nothing()
        assert hash(Just((1, "a"))) == hash(Just((1, "a")))
        assert hash(Nothing()) == hash(Nothing())

    def test_values_are_frozen(self) -> None:
        with pytest.raises(dataclasses.FrozenInstanceError):
            Just(1).value = 2  # type: ignore[misc]

    def test_pattern_matching(self) -> None:
        def describe(m: Maybe[int]) -> str:
            match m:
                case Just(value):
                    return f"just {value}"
                case Nothing():
                    return "nothing"

        assert describe(Just(3)) == "just 3"
        assert describe(Nothing()) == "nothing"


class TestMaybeFunctions:
    def test_with_default(self) -> None:
        assert maybe.with_default(0, Just(5)) == 5
        assert maybe.with_default(0, Nothing()) == 0

    def test_has_value(self) -> None:
        assert maybe.has_value(Just(1))
        assert not maybe.has_value(Nothing())

    def test_map(self) -> None:
        assert maybe.map(lambda n: n + 1, Just(1)) == Just(2)
        assert maybe.map(lambda n: n + 1, Nothing()) == Nothing()

    def test_map2_to_map5(self) -> None:
        assert maybe.map2(lambda a, b: a + b, Just(1), Just(2)) == Just(3)
        assert maybe.map2(lambda a, b: a + b, Just(1), Nothing()) == Nothing()
        assert maybe.map2(lambda a, b: a + b, Nothing(), Just(2)) == Nothing()
        assert maybe.map3(lambda a, b, c: a + b + c, Just(1), Just(2), Just(3)) == Just(
            6
        )
        assert (
            maybe.map3(lambda a, b, c: a + b + c, Just(1), Just(2), Nothing())
            == Nothing()
        )
        assert maybe.map4(
            lambda a, b, c, d: a + b + c + d, Just(1), Just(2), Just(3), Just(4)
        ) == Just(10)
        assert (
            maybe.map4(
                lambda a, b, c, d: a + b + c + d, Just(1), Just(2), Nothing(), Just(4)
            )
            == Nothing()
        )
        assert maybe.map5(
            lambda a, b, c, d, e: a + b + c + d + e,
            Just(1),
            Just(2),
            Just(3),
            Just(4),
            Just(5),
        ) == Just(15)
        assert (
            maybe.map5(
                lambda a, b, c, d, e: a + b + c + d + e,
                Just(1),
                Just(2),
                Just(3),
                Just(4),
                Nothing(),
            )
            == Nothing()
        )

    def test_and_then(self) -> None:
        def half(n: int) -> Maybe[int]:
            return Just(n // 2) if n % 2 == 0 else Nothing()

        assert maybe.and_then(half, Just(4)) == Just(2)
        assert maybe.and_then(half, Just(3)) == Nothing()
        assert maybe.and_then(half, Nothing()) == Nothing()
