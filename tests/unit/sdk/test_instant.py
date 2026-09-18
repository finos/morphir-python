"""Tests for morphir.sdk.instant (Morphir.SDK.Instant)."""

import datetime

import pytest

from morphir.sdk import instant
from morphir.sdk.instant import Instant


class TestType:
    def test_instant_is_the_standard_library_datetime(self) -> None:
        assert Instant is datetime.datetime


class TestFromMillisecondsSinceEpoch:
    def test_epoch(self) -> None:
        assert instant.from_milliseconds_since_epoch(0) == datetime.datetime(
            1970, 1, 1, tzinfo=datetime.UTC
        )

    def test_result_is_in_utc(self) -> None:
        value = instant.from_milliseconds_since_epoch(1643374590000)
        assert value.tzinfo is datetime.UTC
        assert value == datetime.datetime(2022, 1, 28, 12, 56, 30, tzinfo=datetime.UTC)

    def test_milliseconds_are_exact(self) -> None:
        value = instant.from_milliseconds_since_epoch(1643374590123)
        assert value.microsecond == 123000

    def test_negative(self) -> None:
        assert instant.from_milliseconds_since_epoch(-1) == datetime.datetime(
            1969, 12, 31, 23, 59, 59, 999000, tzinfo=datetime.UTC
        )

    def test_out_of_range_raises(self) -> None:
        with pytest.raises(OverflowError):
            instant.from_milliseconds_since_epoch(10**18)


class TestToMillisecondsSinceEpoch:
    def test_round_trip(self) -> None:
        for millis in (0, 1, -1, 1643374590123, -62135596800000, 253402300799999):
            assert (
                instant.to_milliseconds_since_epoch(
                    instant.from_milliseconds_since_epoch(millis)
                )
                == millis
            )

    def test_other_time_zone(self) -> None:
        zone = datetime.timezone(datetime.timedelta(hours=1))
        value = datetime.datetime(2022, 1, 28, 13, 56, 30, tzinfo=zone)
        assert instant.to_milliseconds_since_epoch(value) == 1643374590000

    def test_part_below_a_millisecond_rounds_down(self) -> None:
        after = datetime.datetime(1970, 1, 1, 0, 0, 0, 1999, tzinfo=datetime.UTC)
        assert instant.to_milliseconds_since_epoch(after) == 1
        before = datetime.datetime(
            1969, 12, 31, 23, 59, 59, 999999, tzinfo=datetime.UTC
        )
        assert instant.to_milliseconds_since_epoch(before) == -1

    def test_naive_datetime_raises(self) -> None:
        with pytest.raises(ValueError, match="time zone"):
            instant.to_milliseconds_since_epoch(datetime.datetime(2022, 1, 28))
