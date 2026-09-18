"""Tests for morphir.sdk.number (Morphir.SDK.Number)."""

import decimal as stdlib_decimal

from morphir.sdk import number
from morphir.sdk.maybe import Just, Nothing
from morphir.sdk.number import DivisionByZero, Number
from morphir.sdk.result import Err, Ok


def make_number(n: int, d: int) -> Number:
    """Build n/d through `divide`, like the Elm test helper."""
    match number.divide(number.from_int(n), number.from_int(d)):
        case Ok(value):
            return value
        case Err(_):
            return number.zero


SAMPLES = (
    make_number(0, 1),
    make_number(1, 1),
    make_number(-1, 1),
    make_number(3, 4),
    make_number(-3, 4),
    make_number(3, -4),
    make_number(-3, -4),
    make_number(22, 7),
    make_number(1000000007, 13),
    make_number(-7, 5),
    make_number(10**40 + 1, 3),
)


class TestConstruction:
    def test_from_int_builds_an_integral_rational(self) -> None:
        assert number.from_int(5) == Number(5, 1)
        assert number.zero == Number(0, 1)
        assert number.one == Number(1, 1)


class TestComparison:
    def test_equal(self) -> None:
        for a in SAMPLES:
            assert not number.equal(a, number.add(a, number.from_int(1)))
            assert number.equal(a, a)
        assert number.equal(number.one, make_number(10, 10))
        assert not number.equal(number.one, number.zero)
        assert number.equal(make_number(1, 2), make_number(-2, -4))

    def test_not_equal(self) -> None:
        for a in SAMPLES:
            assert number.not_equal(a, number.add(a, number.from_int(1)))
            assert not number.not_equal(a, a)

    def test_less_than_and_greater_than(self) -> None:
        assert number.less_than(make_number(1, 2), make_number(2, 3))
        assert not number.less_than(make_number(2, 3), make_number(1, 2))
        assert number.greater_than(make_number(2, 3), make_number(1, 2))
        assert not number.greater_than(make_number(1, 2), make_number(1, 2))

    def test_less_than_or_equal_and_greater_than_or_equal(self) -> None:
        assert number.less_than_or_equal(make_number(1, 2), make_number(2, 4))
        assert not number.less_than_or_equal(make_number(2, 3), make_number(1, 2))
        assert number.greater_than_or_equal(make_number(1, 2), make_number(2, 4))
        assert not number.greater_than_or_equal(make_number(1, 2), make_number(2, 3))

    def test_negative_denominators_compare_by_value(self) -> None:
        # 3/-4 is -0.75, which is less than 1/2.
        assert number.less_than(make_number(3, -4), make_number(1, 2))
        assert number.greater_than(make_number(1, 2), make_number(3, -4))
        assert not number.less_than(make_number(-3, -4), make_number(1, 2))
        assert number.equal(make_number(3, -4), make_number(-3, 4))


class TestArithmetic:
    def test_add_does_not_reduce(self) -> None:
        assert number.add(make_number(1, 2), make_number(1, 3)) == Number(5, 6)
        assert number.add(make_number(1, 2), make_number(1, 2)) == Number(4, 4)

    def test_subtract(self) -> None:
        assert number.subtract(make_number(1, 2), make_number(1, 3)) == Number(1, 6)

    def test_multiply_does_not_reduce(self) -> None:
        assert number.multiply(make_number(2, 3), make_number(3, 4)) == Number(6, 12)

    def test_negate(self) -> None:
        assert number.negate(make_number(3, 4)) == Number(-3, 4)
        total = number.add(make_number(3, 4), number.negate(make_number(3, 4)))
        assert number.equal(number.zero, total)

    def test_abs(self) -> None:
        assert number.abs(make_number(-3, 4)) == Number(3, 4)
        assert number.abs(make_number(3, -4)) == Number(3, 4)

    def test_reciprocal_swaps_but_leaves_zero_alone(self) -> None:
        assert number.reciprocal(make_number(3, 4)) == Number(4, 3)
        assert number.reciprocal(number.zero) == number.zero
        assert number.reciprocal(make_number(0, 5)) == Number(0, 5)

    def test_big_values_stay_exact(self) -> None:
        big = make_number(10**40 + 1, 3)
        assert number.multiply(big, big) == Number((10**40 + 1) ** 2, 9)


class TestDivide:
    def test_dividing_by_zero_yields_division_by_zero(self) -> None:
        forty_two = number.from_int(42)
        assert number.divide(forty_two, number.from_int(0)) == Err(DivisionByZero())
        assert number.divide(forty_two, make_number(0, 7)) == Err(DivisionByZero())

    def test_dividing_a_number_by_itself_equals_one(self) -> None:
        for n in (1, -1, 2, 7, -13, 1000003):
            result = number.divide(number.from_int(n), number.from_int(n))
            assert isinstance(result, Ok)
            assert number.equal(number.one, result.value)

    def test_divide_cross_multiplies(self) -> None:
        assert number.divide(make_number(1, 2), make_number(3, 4)) == Ok(Number(4, 6))


class TestSimplify:
    def test_four_over_two_reduces_to_two_over_one(self) -> None:
        assert number.simplify(make_number(4, 2)) == Just(Number(2, 1))

    def test_seven_over_five_does_not_simplify(self) -> None:
        assert number.simplify(make_number(7, 5)) == Just(Number(7, 5))

    def test_a_zero_numerator_simplifies_to_zero(self) -> None:
        for d in (2, 3, 17, 999):
            assert number.simplify(make_number(0, d)) == Just(number.zero)

    def test_a_zero_denominator_cannot_simplify(self) -> None:
        assert number.simplify(Number(3, 0)) == Nothing()
        assert number.simplify(Number(0, 0)) == Nothing()

    def test_simplify_keeps_the_denominator_positive(self) -> None:
        assert number.simplify(make_number(3, -6)) == Just(Number(-1, 2))
        assert number.simplify(make_number(-4, -2)) == Just(Number(2, 1))

    def test_is_simplified(self) -> None:
        assert number.is_simplified(make_number(7, 5))
        assert not number.is_simplified(make_number(4, 2))
        assert number.is_simplified(number.zero)
        assert not number.is_simplified(make_number(0, 5))

    def test_a_zero_denominator_counts_as_simplified_like_elm(self) -> None:
        assert number.is_simplified(Number(3, 0))


class TestConvertTo:
    def test_to_fractional_string(self) -> None:
        assert number.to_fractional_string(make_number(3, 4)) == "3/4"
        assert number.to_fractional_string(make_number(-3, 4)) == "-3/4"
        assert number.to_fractional_string(number.from_int(7)) == "7/1"

    def test_to_decimal_divides_the_components(self) -> None:
        assert number.to_decimal(make_number(3, 4)) == Just(
            stdlib_decimal.Decimal("0.75")
        )
        assert number.to_decimal(make_number(1, 3)) == Just(
            stdlib_decimal.Decimal("0." + "3" * 50)
        )

    def test_to_decimal_is_nothing_when_the_denominator_is_zero(self) -> None:
        assert number.to_decimal(Number(3, 0)) == Nothing()

    def test_coerce_to_decimal_falls_back_on_a_zero_denominator(self) -> None:
        fallback = stdlib_decimal.Decimal(-1)
        assert number.coerce_to_decimal(
            fallback, make_number(1, 2)
        ) == stdlib_decimal.Decimal("0.5")
        assert number.coerce_to_decimal(fallback, Number(3, 0)) is fallback
