"""Tests for morphir.sdk.decimal (Morphir.SDK.Decimal)."""

import decimal as stdlib_decimal
import math

import pytest

from morphir.sdk import decimal as decimal_
from morphir.sdk.basics import Order
from morphir.sdk.decimal import (
    Decimal,
    from_float,
    from_int,
    from_string,
    to_string,
)
from morphir.sdk.maybe import Just, Nothing, with_default

SAMPLE_INTS = (0, 1, -1, 7, -42, 1000, 123456789, -987654321)
SAMPLE_DECIMALS = (
    from_float(0.0),
    from_float(1.5),
    from_float(-2.25),
    from_float(3.14),
    from_float(-1000.001),
    with_default(decimal_.zero, from_string("123456789.987654321")),
)


def _parse(s: str) -> Decimal:
    return with_default(decimal_.zero, from_string(s))


class TestAbs:
    def test_abs(self) -> None:
        assert decimal_.abs(from_int(-42)) == from_int(42)
        assert decimal_.abs(from_int(42)) == from_int(42)
        assert decimal_.abs(from_int(0)) == from_int(0)


class TestArithmetic:
    def test_add_mirrors_normal_addition(self) -> None:
        for a in SAMPLE_INTS:
            for b in SAMPLE_INTS:
                assert decimal_.add(from_int(a), from_int(b)) == from_int(a + b)

    def test_add_is_commutative(self) -> None:
        for a in SAMPLE_DECIMALS:
            for b in SAMPLE_DECIMALS:
                assert decimal_.add(a, b) == decimal_.add(b, a)

    def test_add_is_exact_where_floats_are_not(self) -> None:
        assert to_string(decimal_.add(from_float(0.1), from_float(0.2))) == "0.3"

    def test_sub_mirrors_normal_subtraction(self) -> None:
        for a in SAMPLE_INTS:
            for b in SAMPLE_INTS:
                assert decimal_.sub(from_int(a), from_int(b)) == from_int(a - b)

    def test_sub_in_the_other_order_is_the_negation(self) -> None:
        for a in SAMPLE_DECIMALS:
            for b in SAMPLE_DECIMALS:
                assert decimal_.sub(a, b) == decimal_.negate(decimal_.sub(b, a))

    def test_mul_mirrors_normal_multiplication(self) -> None:
        for a in (0, 1, -1, 3, -7, 46340, -46340):
            for b in (0, 1, -1, 3, -7, 46340, -46340):
                assert decimal_.mul(from_int(a), from_int(b)) == from_int(a * b)

    def test_mul_is_commutative(self) -> None:
        for a in SAMPLE_DECIMALS:
            for b in SAMPLE_DECIMALS:
                assert decimal_.mul(a, b) == decimal_.mul(b, a)

    def test_results_are_rounded_half_up_to_50_digits(self) -> None:
        big = _parse("1" + "0" * 49 + "5")
        assert to_string(decimal_.add(big, decimal_.zero)) == "1" + "0" * 48 + "10"

    def test_div_divides_exactly(self) -> None:
        assert decimal_.div(from_int(10), from_int(4)) == Just(from_float(2.5))

    def test_div_is_nothing_on_a_zero_divisor(self) -> None:
        assert decimal_.div(from_int(1), decimal_.zero) == Nothing()
        assert decimal_.div(decimal_.zero, decimal_.zero) == Nothing()

    def test_div_gives_50_significant_digits(self) -> None:
        third = with_default(decimal_.zero, decimal_.div(decimal_.one, from_int(3)))
        assert to_string(third) == "0." + "3" * 50
        two_thirds = with_default(decimal_.zero, decimal_.div(from_int(2), from_int(3)))
        assert to_string(two_thirds) == "0." + "6" * 49 + "7"

    def test_div_with_default(self) -> None:
        minus_one = decimal_.minus_one
        assert (
            decimal_.div_with_default(minus_one, from_int(1), decimal_.zero)
            == minus_one
        )
        assert decimal_.div_with_default(
            minus_one, from_int(6), from_int(3)
        ) == from_int(2)


class TestConstruction:
    def test_from_int(self) -> None:
        for n in SAMPLE_INTS:
            assert to_string(from_int(n)) == str(n)

    def test_from_int_is_exact_for_big_ints(self) -> None:
        assert to_string(from_int(10**60 + 1)) == str(10**60 + 1)

    def test_from_string(self) -> None:
        assert from_string("42") == Just(from_int(42))
        assert from_string("-21") == Just(from_int(-21))
        assert from_string("0") == Just(from_int(0))
        assert from_string("esdf") == Nothing()
        assert from_string("1.1") == Just(from_float(1.1))

    def test_from_string_with_exponent_and_explicit_sign(self) -> None:
        assert from_string("1.5e3") == Just(from_int(1500))
        assert from_string("+7") == Just(from_int(7))
        assert from_string("2E-2") == Just(from_float(0.02))

    def test_from_string_rejects_forms_that_elm_does_not_parse(self) -> None:
        for s in (
            "0x10",
            "0b1",
            "0o7",
            "Infinity",
            "-Infinity",
            "NaN",
            "nan",
            "sNaN",
            "inf",
            " 1",
            "1 ",
            "1\n",
            "",
            ".5",
            "1.",
            "1_000",
            "١٢",
        ):
            assert from_string(s) == Nothing(), s

    def test_from_float(self) -> None:
        assert from_float(1.0) == from_int(1)
        assert from_float(-1.0) == from_int(-1)
        assert from_float(0.0) == from_int(0)
        assert to_string(from_float(-0.0)) == "0"
        assert from_float(3.3) == decimal_.shift_decimal_left(1, from_int(33))
        assert from_float(1.1) == decimal_.shift_decimal_left(1, from_int(11))

    def test_from_float_is_the_same_as_from_string(self) -> None:
        for text in ("0", "1", "-1", "0.5", "3.14", "-1234.5678", "1e10", "123456.789"):
            assert from_float(float(text)) == _parse(text)

    def test_from_float_rejects_values_that_are_not_finite(self) -> None:
        for f in (math.nan, math.inf, -math.inf):
            with pytest.raises(ValueError):
                from_float(f)


class TestKnownExponents:
    def test_hundred_thousand_million(self) -> None:
        assert to_string(decimal_.hundred(42)) == "4200"
        assert to_string(decimal_.hundred(-2)) == "-200"
        assert to_string(decimal_.thousand(4)) == "4000"
        assert to_string(decimal_.thousand(-7)) == "-7000"
        assert to_string(decimal_.million(21)) == "21000000"
        assert to_string(decimal_.million(-99)) == "-99000000"

    def test_tenth(self) -> None:
        assert decimal_.tenth(1000) == from_int(100)
        assert decimal_.tenth(10) == from_float(1.0)
        assert decimal_.tenth(-1000) == from_float(-100.0)
        assert decimal_.tenth(-50) == from_float(-5.0)
        assert to_string(decimal_.tenth(3)) == "0.3"

    def test_hundredth(self) -> None:
        assert decimal_.hundredth(100) == from_float(1.0)
        assert decimal_.hundredth(10) == from_float(0.1)
        assert decimal_.hundredth(-1000) == from_float(-10.0)
        assert decimal_.hundredth(-50) == from_float(-0.5)

    def test_thousandth(self) -> None:
        assert to_string(decimal_.thousandth(7)) == "0.007"
        assert decimal_.thousandth(-1500) == from_float(-1.5)

    def test_bps(self) -> None:
        assert decimal_.bps(10001) == from_float(1.0001)
        assert to_string(decimal_.bps(2)) == "0.0002"
        assert decimal_.bps(-100001) == from_float(-10.0001)
        assert decimal_.bps(-5) == from_float(-0.0005)

    def test_millionth(self) -> None:
        assert decimal_.millionth(1000000) == from_float(1.0)
        assert decimal_.millionth(-10000000) == from_float(-10.0)
        assert to_string(decimal_.millionth(1)) == "0.000001"


class TestConvertTo:
    def test_to_string(self) -> None:
        assert to_string(from_int(1)) == "1"
        assert to_string(from_int(0)) == "0"
        assert to_string(from_int(-1)) == "-1"
        assert to_string(from_float(-1234.5678)) == "-1234.5678"

    def test_to_string_never_uses_exponent_notation(self) -> None:
        assert to_string(_parse("1e21")) == "1000000000000000000000"
        assert to_string(_parse("1e-7")) == "0.0000001"
        assert to_string(_parse("-1.5e-10")) == "-0.00000000015"

    def test_to_string_drops_trailing_zeros(self) -> None:
        assert to_string(_parse("1.50")) == "1.5"
        assert to_string(_parse("100")) == "100"
        assert to_string(_parse("2.000")) == "2"
        assert to_string(_parse("-0.0")) == "0"
        assert to_string(decimal_.mul(_parse("2.5"), _parse("4"))) == "10"

    def test_to_float(self) -> None:
        assert decimal_.to_float(from_int(1)) == 1.0
        assert decimal_.to_float(from_int(0)) == 0.0
        assert decimal_.to_float(from_int(-1)) == -1.0
        assert decimal_.to_float(from_float(3.14)) == 3.14
        assert isinstance(decimal_.to_float(from_int(1)), float)


class TestCompare:
    def test_compare(self) -> None:
        for a in SAMPLE_INTS:
            assert decimal_.compare(from_int(a), from_int(a)) is Order.EQ
            assert decimal_.compare(from_int(a), from_int(a + 1)) is Order.LT
            assert decimal_.compare(from_int(a), from_int(a - 1)) is Order.GT

    def test_compare_ignores_trailing_zeros(self) -> None:
        assert decimal_.compare(_parse("1.50"), from_float(1.5)) is Order.EQ

    def test_eq_and_neq(self) -> None:
        for a in SAMPLE_DECIMALS:
            assert decimal_.neq(a, decimal_.add(a, decimal_.minus_one))
            assert not decimal_.neq(a, a)
            assert decimal_.eq(a, a)

    def test_ordering_predicates(self) -> None:
        a = from_int(1)
        b = from_int(2)
        assert decimal_.eq(a, from_float(1.0))
        assert decimal_.gt(b, a)
        assert not decimal_.gt(a, a)
        assert decimal_.gte(a, a)
        assert not decimal_.gte(a, b)
        assert decimal_.lt(a, b)
        assert not decimal_.lt(a, a)
        assert decimal_.lte(a, a)
        assert not decimal_.lte(b, a)


class TestShift:
    def test_shift_decimal_left(self) -> None:
        assert decimal_.shift_decimal_left(2, from_int(314)) == from_float(3.14)
        assert decimal_.shift_decimal_left(2, from_float(199.95)) == from_float(1.9995)

    def test_shift_decimal_right(self) -> None:
        assert decimal_.shift_decimal_right(3, from_int(314)) == from_float(314000.0)
        assert decimal_.shift_decimal_right(1, from_float(199.95)) == from_float(1999.5)

    def test_negative_shifts_go_the_other_way(self) -> None:
        assert decimal_.shift_decimal_left(-2, from_int(3)) == from_int(300)
        assert decimal_.shift_decimal_right(-2, from_int(300)) == from_int(3)


class TestRounding:
    def test_truncate_goes_toward_zero(self) -> None:
        assert to_string(decimal_.truncate(from_float(2.7))) == "2"
        assert to_string(decimal_.truncate(from_float(-2.7))) == "-2"
        assert to_string(decimal_.truncate(from_int(5))) == "5"

    def test_round_goes_half_up(self) -> None:
        assert to_string(decimal_.round(from_float(2.4))) == "2"
        assert to_string(decimal_.round(from_float(2.5))) == "3"
        assert to_string(decimal_.round(from_float(3.5))) == "4"
        assert to_string(decimal_.round(from_float(-2.4))) == "-2"
        assert to_string(decimal_.round(from_float(-2.5))) == "-3"


class TestNegateAndConstants:
    def test_negate(self) -> None:
        assert decimal_.negate(from_int(3)) == from_int(-3)
        assert decimal_.negate(decimal_.zero) == decimal_.zero
        assert to_string(decimal_.negate(decimal_.zero)) == "0"

    def test_constants(self) -> None:
        assert to_string(decimal_.zero) == "0"
        assert to_string(decimal_.one) == "1"
        assert to_string(decimal_.minus_one) == "-1"


class TestContext:
    def test_the_global_decimal_context_does_not_change(self) -> None:
        before = stdlib_decimal.getcontext().copy()
        decimal_.div(decimal_.one, from_int(3))
        decimal_.round(from_float(2.5))
        decimal_.mul(from_float(1.1), from_float(2.2))
        after = stdlib_decimal.getcontext()
        assert after.prec == before.prec == 28
        assert after.rounding == before.rounding == stdlib_decimal.ROUND_HALF_EVEN

    def test_the_global_decimal_context_has_no_effect(self) -> None:
        with stdlib_decimal.localcontext() as ctx:
            ctx.prec = 5
            third = with_default(decimal_.zero, decimal_.div(decimal_.one, from_int(3)))
        assert to_string(third) == "0." + "3" * 50

    def test_decimal_is_the_stdlib_type(self) -> None:
        assert isinstance(from_int(1), stdlib_decimal.Decimal)


class TestLimits:
    def test_from_string_keeps_all_digits(self) -> None:
        text = "1234567890" * 6 + ".5"
        assert to_string(_parse(text)) == text

    def test_from_string_is_nothing_for_an_exponent_out_of_range(self) -> None:
        assert from_string("1e99999999999999999999") == Nothing()
