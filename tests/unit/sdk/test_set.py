"""Tests for morphir.sdk.set (Morphir.SDK.Set)."""

import pytest

from morphir.sdk import basics
from morphir.sdk import set as set_
from morphir.sdk.set import Set

S123: Set[int] = set_.from_list((3, 1, 2))


def _is_even(n: int) -> bool:
    return n % 2 == 0


class TestBuild:
    def test_empty_and_singleton(self) -> None:
        assert set_.to_list(set_.empty()) == ()
        assert set_.is_empty(set_.empty())
        assert set_.to_list(set_.singleton(1)) == (1,)
        assert not set_.is_empty(set_.singleton(1))
        assert isinstance(set_.empty(), Set)

    def test_from_list_sorts_and_removes_duplicates(self) -> None:
        assert set_.to_list(set_.from_list((3, 1, 2, 3, 1))) == (1, 2, 3)
        assert set_.to_list(set_.from_list(("b", "B", "a"))) == ("B", "a", "b")

    def test_tuple_members(self) -> None:
        s = set_.from_list(((2, "a"), (1, "b"), (1, "a"), (1, "b")))
        assert set_.to_list(s) == ((1, "a"), (1, "b"), (2, "a"))
        assert set_.member((1, "b"), s)
        assert not set_.member((3, "a"), s)

    def test_members_that_are_not_comparable_raise(self) -> None:
        with pytest.raises(TypeError):
            set_.from_list((1, "a"))  # type: ignore[arg-type]

    def test_insert(self) -> None:
        assert set_.to_list(set_.insert(0, S123)) == (0, 1, 2, 3)
        assert set_.to_list(set_.insert(4, S123)) == (1, 2, 3, 4)
        assert set_.insert(2, S123) == S123
        assert set_.to_list(S123) == (1, 2, 3)

    def test_remove(self) -> None:
        assert set_.to_list(set_.remove(2, S123)) == (1, 3)
        assert set_.remove(9, S123) == S123


class TestQuery:
    def test_member_and_size(self) -> None:
        assert set_.member(1, S123)
        assert not set_.member(9, S123)
        assert set_.size(S123) == 3
        assert set_.size(set_.empty()) == 0


class TestTransform:
    def test_map_sorts_again_and_removes_duplicates(self) -> None:
        assert set_.to_list(set_.map(lambda n: -n, S123)) == (-3, -2, -1)
        assert set_.to_list(set_.map(lambda n: n // 2, S123)) == (0, 1)

    def test_foldl_ascending_and_foldr_descending(self) -> None:
        assert set_.foldl(lambda n, acc: (*acc, n), (), S123) == (1, 2, 3)
        assert set_.foldr(lambda n, acc: (*acc, n), (), S123) == (3, 2, 1)

    def test_filter_and_partition(self) -> None:
        assert set_.to_list(set_.filter(_is_even, S123)) == (2,)
        even, odd = set_.partition(_is_even, S123)
        assert set_.to_list(even) == (2,)
        assert set_.to_list(odd) == (1, 3)


class TestCombine:
    def test_union_intersect_diff(self) -> None:
        other = set_.from_list((2, 3, 4))
        assert set_.to_list(set_.union(S123, other)) == (1, 2, 3, 4)
        assert set_.to_list(set_.intersect(S123, other)) == (2, 3)
        assert set_.to_list(set_.diff(S123, other)) == (1,)
        assert set_.to_list(set_.diff(other, S123)) == (4,)


class TestEquality:
    def test_structural_equality_is_independent_of_insertion_order(self) -> None:
        empty: Set[int] = set_.empty()
        s1 = set_.insert(3, set_.insert(1, set_.insert(2, empty)))
        s2 = set_.insert(1, set_.insert(2, set_.insert(3, empty)))
        assert s1 == s2
        assert basics.equal(s1, S123)
        assert hash(s1) == hash(s2)
        assert not basics.equal(s1, set_.insert(4, s2))
