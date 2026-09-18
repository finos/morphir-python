"""Tests for morphir.sdk.list (Morphir.SDK.List)."""

import pytest

from morphir.sdk import list as list_
from morphir.sdk.basics import Order, compare
from morphir.sdk.maybe import Just, Maybe, Nothing


def _is_even(n: int) -> bool:
    return n % 2 == 0


def _eq(a: int, b: int) -> bool:
    return a == b


class TestCreate:
    def test_singleton(self) -> None:
        assert list_.singleton(1234) == (1234,)

    def test_repeat(self) -> None:
        assert list_.repeat(3, (0, 0)) == ((0, 0), (0, 0), (0, 0))
        assert list_.repeat(0, "a") == ()
        assert list_.repeat(-1, "a") == ()

    def test_range_is_inclusive(self) -> None:
        assert list_.range(3, 6) == (3, 4, 5, 6)
        assert list_.range(3, 3) == (3,)
        assert list_.range(6, 3) == ()

    def test_cons(self) -> None:
        assert list_.cons(1, (2, 3)) == (1, 2, 3)
        assert list_.cons(1, ()) == (1,)


class TestTransform:
    def test_map(self) -> None:
        assert list_.map(lambda n: n * 2, (1, 2, 3)) == (2, 4, 6)
        assert list_.map(lambda n: n * 2, ()) == ()

    def test_accepts_any_sequence_and_yields_a_tuple(self) -> None:
        source = [1, 2, 3]
        assert list_.map(lambda n: n + 1, source) == (2, 3, 4)
        assert source == [1, 2, 3]

    def test_indexed_map(self) -> None:
        assert list_.indexed_map(lambda i, s: (i, s), ("Tom", "Sue", "Bob")) == (
            (0, "Tom"),
            (1, "Sue"),
            (2, "Bob"),
        )

    def test_foldl_and_foldr(self) -> None:
        assert list_.foldl(lambda x, acc: (x, *acc), (), (1, 2, 3)) == (3, 2, 1)
        assert list_.foldr(lambda x, acc: (x, *acc), (), (1, 2, 3)) == (1, 2, 3)
        assert list_.foldl(lambda x, acc: x + acc, 0, (1, 2, 3)) == 6

    def test_filter(self) -> None:
        assert list_.filter(_is_even, (1, 2, 3, 4, 5, 6)) == (2, 4, 6)

    def test_filter_map(self) -> None:
        def even_half(n: int) -> Maybe[int]:
            return Just(n // 2) if _is_even(n) else Nothing()

        assert list_.filter_map(even_half, (1, 2, 3, 4)) == (1, 2)


class TestUtilities:
    def test_length(self) -> None:
        assert list_.length((1, 2, 3)) == 3
        assert list_.length(()) == 0

    def test_reverse(self) -> None:
        assert list_.reverse((1, 2, 3, 4)) == (4, 3, 2, 1)

    def test_member_is_structural(self) -> None:
        assert list_.member(9, (1, 2, 3, 4)) is False
        assert list_.member(4, (1, 2, 3, 4)) is True
        assert list_.member((1, "a"), ((0, "z"), (1, "a"))) is True
        assert list_.member(Just(1), (Nothing(), Just(1))) is True

    def test_all_and_any(self) -> None:
        assert list_.all(_is_even, (2, 4))
        assert not list_.all(_is_even, (2, 3))
        assert list_.all(_is_even, ())
        assert list_.any(_is_even, (2, 3))
        assert not list_.any(_is_even, (1, 3))
        assert not list_.any(_is_even, ())

    def test_maximum_and_minimum(self) -> None:
        assert list_.maximum((1, 4, 2)) == Just(4)
        assert list_.maximum(()) == Nothing()
        assert list_.minimum((3, 2, 1)) == Just(1)
        assert list_.minimum(()) == Nothing()
        assert list_.maximum(("a", "c", "b")) == Just("c")
        assert list_.minimum(((2, "a"), (1, "b"))) == Just((1, "b"))

    def test_sum_and_product(self) -> None:
        assert list_.sum((1, 2, 3, 4)) == 10
        assert list_.sum(()) == 0
        assert list_.sum((0.5, 0.25)) == 0.75
        assert list_.product((1, 2, 3, 4)) == 24
        assert list_.product(()) == 1


class TestCombine:
    def test_append(self) -> None:
        assert list_.append((1, 1, 2), (3, 5, 8)) == (1, 1, 2, 3, 5, 8)
        assert list_.append(("a", "b"), ("c",)) == ("a", "b", "c")

    def test_concat(self) -> None:
        assert list_.concat(((1, 2), (3,), (4, 5))) == (1, 2, 3, 4, 5)
        assert list_.concat(()) == ()

    def test_concat_map(self) -> None:
        assert list_.concat_map(lambda n: (n, n), (1, 2)) == (1, 1, 2, 2)

    def test_intersperse(self) -> None:
        assert list_.intersperse("on", ("turtles", "turtles", "turtles")) == (
            "turtles",
            "on",
            "turtles",
            "on",
            "turtles",
        )
        assert list_.intersperse(0, ()) == ()
        assert list_.intersperse(0, (1,)) == (1,)

    def test_map2_to_map5_stop_at_the_shortest_list(self) -> None:
        assert list_.map2(lambda a, b: a + b, (1, 2, 3), (1, 2, 3, 4)) == (2, 4, 6)
        assert list_.map2(lambda a, b: (a, b), (1, 2, 3), ("a", "b")) == (
            (1, "a"),
            (2, "b"),
        )
        assert list_.map3(lambda a, b, c: a + b + c, (1, 2), (10, 20), (100,)) == (111,)
        assert list_.map4(
            lambda a, b, c, d: a + b + c + d, (1, 2), (10, 20), (100, 200), (1000, 2000)
        ) == (1111, 2222)
        assert list_.map5(
            lambda a, b, c, d, e: a + b + c + d + e, (1,), (2,), (3,), (4,), (5, 6)
        ) == (15,)


class TestSort:
    def test_sort(self) -> None:
        assert list_.sort((3, 1, 5)) == (1, 3, 5)
        assert list_.sort(("b", "B", "a")) == ("B", "a", "b")
        assert list_.sort(((2, "a"), (1, "b"), (1, "a"))) == (
            (1, "a"),
            (1, "b"),
            (2, "a"),
        )

    def test_sort_rejects_values_that_are_not_comparable(self) -> None:
        with pytest.raises(TypeError):
            list_.sort((1, "a"))  # type: ignore[arg-type]

    def test_sort_by_is_stable(self) -> None:
        assert list_.sort_by(len, ("mouse", "cat", "chuck", "cow", "alpha")) == (
            "cat",
            "cow",
            "mouse",
            "chuck",
            "alpha",
        )
        assert list_.sort_by(lambda s: s, ("chuck", "alice", "bob")) == (
            "alice",
            "bob",
            "chuck",
        )

    def test_sort_with_uses_order(self) -> None:
        def flipped(a: int, b: int) -> Order:
            return compare(b, a)

        assert list_.sort_with(flipped, (1, 2, 3, 4, 5)) == (5, 4, 3, 2, 1)
        assert list_.sort_with(lambda _a, _b: Order.EQ, (3, 1, 2)) == (3, 1, 2)


class TestDeconstruct:
    def test_is_empty(self) -> None:
        assert list_.is_empty(())
        assert not list_.is_empty((1,))

    def test_head_and_tail(self) -> None:
        assert list_.head((1, 2, 3)) == Just(1)
        assert list_.head(()) == Nothing()
        assert list_.tail((1, 2, 3)) == Just((2, 3))
        assert list_.tail((1,)) == Just(())
        assert list_.tail(()) == Nothing()

    def test_take(self) -> None:
        assert list_.take(2, (1, 2, 3, 4)) == (1, 2)
        assert list_.take(0, (1, 2)) == ()
        assert list_.take(-1, (1, 2)) == ()
        assert list_.take(5, (1, 2)) == (1, 2)

    def test_drop(self) -> None:
        assert list_.drop(2, (1, 2, 3, 4)) == (3, 4)
        assert list_.drop(0, (1, 2)) == (1, 2)
        assert list_.drop(-1, (1, 2)) == (1, 2)
        assert list_.drop(5, (1, 2)) == ()

    def test_partition(self) -> None:
        assert list_.partition(lambda x: x < 3, (0, 1, 2, 3, 4, 5)) == (
            (0, 1, 2),
            (3, 4, 5),
        )
        assert list_.partition(_is_even, (0, 1, 2, 3, 4, 5)) == ((0, 2, 4), (1, 3, 5))
        assert list_.partition(_is_even, ()) == ((), ())

    def test_unzip(self) -> None:
        assert list_.unzip(((0, True), (17, False), (1337, True))) == (
            (0, 17, 1337),
            (True, False, True),
        )
        assert list_.unzip(()) == ((), ())


class TestJoins:
    def test_inner_filters_left(self) -> None:
        assert list_.inner_join((1, 3), _eq, (1, 2, 3)) == ((1, 1), (3, 3))

    def test_inner_filters_right(self) -> None:
        assert list_.inner_join((1, 2, 3), _eq, (1, 2)) == ((1, 1), (2, 2))

    def test_inner_filters_both(self) -> None:
        assert list_.inner_join((1, 3), _eq, (1, 2)) == ((1, 1),)

    def test_inner_yields_every_matching_pair(self) -> None:
        assert list_.inner_join((1, 1), _eq, (1,)) == ((1, 1), (1, 1))

    def test_left_outer_keeps_left(self) -> None:
        assert list_.left_join((1, 3), _eq, (1, 2)) == ((1, Just(1)), (2, Nothing()))

    def test_left_outer_yields_every_matching_pair(self) -> None:
        assert list_.left_join((1, 1, 3), _eq, (1, 2)) == (
            (1, Just(1)),
            (1, Just(1)),
            (2, Nothing()),
        )
