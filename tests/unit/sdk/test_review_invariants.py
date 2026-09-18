"""Invariants that keep invalid SDK states from being represented.

These cover the raw `Dict` and `Set` constructors, mutable list keys, equality
over functions held inside SDK data types, and the real-number domain of
`basics.power`.
"""

import math

import pytest

from morphir.sdk import basics
from morphir.sdk import dict as Dict  # noqa: N812
from morphir.sdk import set as Set  # noqa: N812
from morphir.sdk.maybe import Just, Nothing
from morphir.sdk.result import Err, Ok


class TestDictConstructorInvariant:
    """The raw `Dict` constructor must not hold unsorted or repeated keys."""

    def test_rejects_unsorted_entries(self) -> None:
        with pytest.raises(ValueError, match="sorted"):
            Dict.Dict((("z", 1), ("a", 2)))

    def test_rejects_a_key_that_appears_twice(self) -> None:
        with pytest.raises(ValueError, match="sorted"):
            Dict.Dict((("a", 1), ("a", 2)))

    def test_rejects_keys_that_are_not_comparable(self) -> None:
        with pytest.raises(TypeError):
            Dict.Dict(((1, "x"), ("a", "y")))

    def test_accepts_sorted_entries(self) -> None:
        d = Dict.Dict((("a", 2), ("z", 1)))
        assert Dict.get("z", d) == Just(1)
        assert Dict.get("a", d) == Just(2)

    def test_empty_needs_no_arguments(self) -> None:
        assert Dict.Dict() == Dict.empty()


class TestSetConstructorInvariant:
    """The raw `Set` constructor must not hold unsorted or repeated members."""

    def test_rejects_unsorted_members(self) -> None:
        with pytest.raises(ValueError, match="sorted"):
            Set.Set((3, 1, 2))

    def test_rejects_a_member_that_appears_twice(self) -> None:
        with pytest.raises(ValueError, match="sorted"):
            Set.Set((1, 1))

    def test_accepts_sorted_members(self) -> None:
        assert Set.member(2, Set.Set((1, 2, 3)))


class TestListKeysAreFrozen:
    """A list used as a key is stored as a tuple, so a later change is harmless."""

    def test_dict_key_does_not_follow_a_later_mutation(self) -> None:
        first = [1]
        d = Dict.from_list([(first, "one"), ([2], "two")])
        first[0] = 3
        assert Dict.get([1], d) == Just("one")
        assert Dict.get([2], d) == Just("two")
        assert Dict.get([3], d) == Nothing()
        assert Dict.keys(d) == ((1,), (2,))

    def test_nested_list_keys_are_frozen(self) -> None:
        d = Dict.singleton([[1, 2], [3]], "v")
        assert Dict.keys(d) == (((1, 2), (3,)),)
        assert Dict.get(((1, 2), (3,)), d) == Just("v")

    def test_insert_freezes_the_key(self) -> None:
        key = ["a", "b"]
        d = Dict.insert(key, 1, Dict.empty())
        key.append("c")
        assert Dict.get(["a", "b"], d) == Just(1)

    def test_dict_with_list_keys_is_hashable(self) -> None:
        d = Dict.from_list([([1], "one")])
        assert hash(d) == hash(Dict.from_list([((1,), "one")]))

    def test_list_and_tuple_keys_build_equal_dicts(self) -> None:
        assert Dict.from_list([([1], "x")]) == Dict.from_list([((1,), "x")])

    def test_set_member_does_not_follow_a_later_mutation(self) -> None:
        first = [1]
        s = Set.from_list([first, [2]])
        first[0] = 3
        assert Set.member([1], s)
        assert not Set.member([3], s)
        assert Set.to_list(s) == ((1,), (2,))

    def test_set_insert_and_singleton_freeze_the_member(self) -> None:
        assert Set.to_list(Set.insert([2], Set.singleton([1]))) == ((1,), (2,))

    def test_set_map_freezes_the_results(self) -> None:
        assert Set.to_list(Set.map(lambda n: [n], Set.from_list([2, 1]))) == (
            (1,),
            (2,),
        )


def _f(x: int) -> int:
    return x


def _g(x: int) -> int:
    return x + 1


class TestEqualOverFunctionsInsideDataTypes:
    """`equal` must fail on a function wherever it is held, as Elm does."""

    def test_just(self) -> None:
        with pytest.raises(TypeError):
            basics.equal(Just(_f), Just(_f))

    def test_ok_and_err(self) -> None:
        with pytest.raises(TypeError):
            basics.equal(Ok(_f), Ok(_g))
        with pytest.raises(TypeError):
            basics.equal(Err(_f), Err(_f))

    def test_dict_value(self) -> None:
        d = Dict.singleton("k", _f)
        with pytest.raises(TypeError):
            basics.equal(d, d)

    def test_nested(self) -> None:
        with pytest.raises(TypeError):
            basics.equal((1, Just([Ok(_f)])), (1, Just([Ok(_f)])))

    def test_not_equal_also_fails(self) -> None:
        with pytest.raises(TypeError):
            basics.not_equal(Just(_f), Nothing())

    def test_data_without_functions_still_compares(self) -> None:
        assert basics.equal(Just((1, Ok("a"))), Just((1, Ok("a"))))
        assert not basics.equal(Just(1), Nothing())
        assert basics.equal(Dict.singleton("k", 1), Dict.singleton("k", 1))


class TestPowerStaysReal:
    """`power` follows JavaScript `Math.pow`: a real number, NaN or an infinity."""

    def test_negative_base_with_fractional_exponent_is_nan(self) -> None:
        result = basics.power(-1.0, 0.5)
        assert isinstance(result, float)
        assert math.isnan(result)

    def test_zero_to_a_negative_power_is_infinity(self) -> None:
        assert basics.power(0.0, -1.0) == math.inf
        assert basics.power(-0.0, -1.0) == -math.inf
        assert basics.power(-0.0, -2.0) == math.inf
        assert basics.power(0, -1) == math.inf

    def test_overflow_is_an_infinity(self) -> None:
        assert basics.power(10.0, 400.0) == math.inf
        assert basics.power(-10.0, 401.0) == -math.inf

    def test_integers_stay_exact_integers(self) -> None:
        result = basics.power(2, 100)
        assert isinstance(result, int)
        assert result == 2**100
        assert basics.power(-2, 3) == -8
        assert basics.power(0, 0) == 1

    def test_integer_with_negative_exponent_is_a_float(self) -> None:
        assert basics.power(2, -1) == 0.5

    def test_ordinary_floats(self) -> None:
        assert basics.power(2.0, 10.0) == 1024.0
        assert basics.power(4.0, 0.5) == 2.0
        assert basics.power(-8.0, 3.0) == -512.0

    def test_nan_and_one_follow_javascript(self) -> None:
        assert math.isnan(basics.power(math.nan, 1.0))
        assert basics.power(math.nan, 0.0) == 1.0
        assert math.isnan(basics.power(1.0, math.inf))
