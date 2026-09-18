"""Tests for morphir.sdk.instant (Morphir.SDK.Instant)."""

import dataclasses
import datetime

import pytest

from morphir.sdk import basics, instant
from morphir.sdk._compare import Order
from morphir.sdk.instant import Instant


class TestType:
    def test_instant_holds_milliseconds_since_the_epoch(self) -> None:
        assert Instant(1643374590000).milliseconds == 1643374590000

    def test_instant_is_immutable(self) -> None:
        value = Instant(0)
        with pytest.raises(dataclasses.FrozenInstanceError):
            value.milliseconds = 1  # type: ignore[misc]

    def test_a_naive_datetime_is_not_an_instant(self) -> None:
        with pytest.raises(TypeError):
            Instant(datetime.datetime(2026, 9, 18))  # type: ignore[arg-type]

    def test_a_float_or_a_bool_is_not_a_number_of_milliseconds(self) -> None:
        with pytest.raises(TypeError):
            Instant(1.5)  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            Instant(True)

    def test_equality_and_hash_are_by_value(self) -> None:
        assert Instant(5) == Instant(5)
        assert Instant(5) != Instant(6)
        assert hash(Instant(5)) == hash(Instant(5))
        assert basics.equal(Instant(5), Instant(5))

    def test_instants_are_ordered(self) -> None:
        assert Instant(1) < Instant(2)
        assert sorted([Instant(3), Instant(-1), Instant(2)]) == [
            Instant(-1),
            Instant(2),
            Instant(3),
        ]

    def test_there_is_no_limit(self) -> None:
        far = Instant(10**30)
        assert instant.to_milliseconds_since_epoch(far) == 10**30


class TestMillisecondsSinceEpoch:
    def test_from_and_to(self) -> None:
        value = instant.from_milliseconds_since_epoch(1643374590123)
        assert value == Instant(1643374590123)
        assert instant.to_milliseconds_since_epoch(value) == 1643374590123

    def test_negative(self) -> None:
        assert instant.from_milliseconds_since_epoch(-1) == Instant(-1)


class TestCompare:
    def test_compare(self) -> None:
        assert instant.compare(Instant(1), Instant(2)) is Order.LT
        assert instant.compare(Instant(2), Instant(2)) is Order.EQ
        assert instant.compare(Instant(3), Instant(2)) is Order.GT


class TestDatetimeConversion:
    def test_from_datetime_in_utc(self) -> None:
        moment = datetime.datetime(2022, 1, 28, 12, 56, 30, tzinfo=datetime.UTC)
        assert instant.from_datetime(moment) == Instant(1643374590000)

    def test_from_datetime_in_another_time_zone(self) -> None:
        zone = datetime.timezone(datetime.timedelta(hours=-5))
        moment = datetime.datetime(2022, 1, 28, 7, 56, 30, tzinfo=zone)
        assert instant.from_datetime(moment) == Instant(1643374590000)

    def test_from_datetime_rounds_a_part_below_a_millisecond_down(self) -> None:
        after = datetime.datetime(1970, 1, 1, 0, 0, 0, 1999, tzinfo=datetime.UTC)
        before = datetime.datetime(
            1969, 12, 31, 23, 59, 59, 999001, tzinfo=datetime.UTC
        )
        assert instant.from_datetime(after) == Instant(1)
        assert instant.from_datetime(before) == Instant(-1)

    def test_from_datetime_rejects_a_naive_datetime(self) -> None:
        with pytest.raises(ValueError, match="time zone"):
            instant.from_datetime(datetime.datetime(2022, 1, 28))

    def test_to_datetime_is_in_utc(self) -> None:
        moment = instant.to_datetime(Instant(1643374590123))
        assert moment.tzinfo is datetime.UTC
        assert moment == datetime.datetime(
            2022, 1, 28, 12, 56, 30, 123000, tzinfo=datetime.UTC
        )

    def test_round_trip(self) -> None:
        for millis in (0, -1, 1, 1643374590123, -62135596800000, 253402300799999):
            assert instant.from_datetime(instant.to_datetime(Instant(millis))) == (
                Instant(millis)
            )

    def test_to_datetime_out_of_range_raises(self) -> None:
        with pytest.raises(OverflowError):
            instant.to_datetime(Instant(10**18))
