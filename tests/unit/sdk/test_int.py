"""Tests for morphir.sdk.int (Morphir.SDK.Int)."""

import pytest

from morphir.sdk import int as int_
from morphir.sdk import maybe
from morphir.sdk.maybe import Just, Nothing

_CASES = [
    (int_.to_int8, int_.from_int8, -(2**7), 2**7 - 1),
    (int_.to_int16, int_.from_int16, -(2**15), 2**15 - 1),
    (int_.to_int32, int_.from_int32, -(2**31), 2**31 - 1),
    (int_.to_int64, int_.from_int64, -(2**63), 2**63 - 1),
]


class TestFixedWidthInts:
    @pytest.mark.parametrize(("to_int", "from_int", "low", "high"), _CASES)
    def test_accepts_the_full_range(self, to_int, from_int, low, high) -> None:
        for n in (low, -1, 0, 1, high):
            assert to_int(n) == Just(n)

    @pytest.mark.parametrize(("to_int", "from_int", "low", "high"), _CASES)
    def test_rejects_values_out_of_range(self, to_int, from_int, low, high) -> None:
        assert to_int(low - 1) == Nothing()
        assert to_int(high + 1) == Nothing()

    @pytest.mark.parametrize(("to_int", "from_int", "low", "high"), _CASES)
    def test_round_trip(self, to_int, from_int, low, high) -> None:
        for n in (low, 0, 42, high):
            assert maybe.map(from_int, to_int(n)) == Just(n)

    def test_rejects_bools(self) -> None:
        assert int_.to_int8(True) == Nothing()

    def test_from_int_yields_a_plain_int(self) -> None:
        wrapped = maybe.with_default(int_.Int8(0), int_.to_int8(5))
        assert int_.from_int8(wrapped) == 5
        assert type(int_.from_int8(wrapped)) is int
