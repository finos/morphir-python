"""Tests for morphir.sdk.local_time (Morphir.SDK.LocalTime)."""

import dataclasses
import datetime

import pytest

from morphir.sdk import local_time
from morphir.sdk.basics import Order
from morphir.sdk.local_time import LocalTime
from morphir.sdk.maybe import Just, Nothing, with_default

BASE = 1643374590000
"""2022-01-28T12:56:30Z in milliseconds from the epoch."""

HOUR = 3_600_000
MINUTE = 60_000
SECOND = 1000
DAY = 24 * HOUR

_ARABIC_INDIC_DIGITS = {ord("0") + i: 0x0660 + i for i in range(10)}
"""A map from the ASCII digits to digits that Elm's `Char.isDigit` rejects."""


def _iso(text: str) -> LocalTime:
    return with_default(local_time.from_milliseconds(0), local_time.from_iso(text))


def _utc(time: LocalTime) -> datetime.datetime:
    """The UTC date and time of a value, as `Time.toHour utc` gives in Elm."""
    epoch = datetime.datetime(1970, 1, 1, tzinfo=datetime.UTC)
    return epoch + datetime.timedelta(milliseconds=time.milliseconds)


class TestType:
    def test_local_time_holds_milliseconds_from_the_epoch(self) -> None:
        assert LocalTime(5).milliseconds == 5

    def test_local_time_is_frozen(self) -> None:
        value = LocalTime(5)
        with pytest.raises(dataclasses.FrozenInstanceError):
            value.milliseconds = 6  # type: ignore[misc]

    def test_local_time_has_value_equality_and_a_hash(self) -> None:
        assert LocalTime(5) == LocalTime(5)
        assert LocalTime(5) != LocalTime(6)
        assert hash(LocalTime(5)) == hash(LocalTime(5))

    def test_local_time_has_an_order(self) -> None:
        assert LocalTime(5) < LocalTime(6)
        assert LocalTime(-1) < LocalTime(0)
        assert sorted([LocalTime(3), LocalTime(-2), LocalTime(1)]) == [
            LocalTime(-2),
            LocalTime(1),
            LocalTime(3),
        ]


class TestMath:
    """The Elm `mathTests`."""

    def test_add_hours(self) -> None:
        assert _utc(local_time.add_hours(1, _iso("2022-01-28T12:56:30"))).hour == 13

    def test_subtract_hours(self) -> None:
        assert _utc(local_time.add_hours(-1, _iso("2022-01-28T12:56:30"))).hour == 11

    def test_add_minutes(self) -> None:
        assert _utc(local_time.add_minutes(1, _iso("2022-01-28T12:56:30"))).minute == 57

    def test_subtract_minutes(self) -> None:
        assert (
            _utc(local_time.add_minutes(-1, _iso("2022-01-28T12:56:30"))).minute == 55
        )

    def test_add_seconds(self) -> None:
        assert _utc(local_time.add_seconds(1, _iso("2022-01-28T12:56:30"))).second == 31

    def test_subtract_seconds(self) -> None:
        assert (
            _utc(local_time.add_seconds(-1, _iso("2022-01-28T12:56:30"))).second == 29
        )

    def test_diff_in_minutes(self) -> None:
        assert (
            local_time.diff_in_minutes(
                _iso("2022-01-28T13:49:30"), _iso("2022-01-28T12:56:30")
            )
            == 53
        )

    def test_diff_in_hours_less_than_an_hour_elapsed(self) -> None:
        assert (
            local_time.diff_in_hours(
                _iso("2022-01-28T13:49:30"), _iso("2022-01-28T12:56:30")
            )
            == 0
        )

    def test_diff_in_hours_more_than_an_hour_elapsed(self) -> None:
        assert (
            local_time.diff_in_hours(
                _iso("2022-01-28T15:49:30"), _iso("2022-01-28T12:56:30")
            )
            == 2
        )

    def test_diff_in_seconds(self) -> None:
        assert (
            local_time.diff_in_seconds(
                _iso("2022-01-28T12:58:30"), _iso("2022-01-28T12:56:30")
            )
            == 120
        )


class TestConstructors:
    """The Elm `constructorTests`."""

    def test_valid_from_iso(self) -> None:
        assert local_time.from_iso("2022-01-28T12:56:30") == Just(
            LocalTime(1643374590000)
        )

    def test_invalid_from_iso_parsing(self) -> None:
        assert local_time.from_iso("2022-01-28TTTTT") == Nothing()

    def test_invalid_from_iso_numeric(self) -> None:
        assert local_time.from_iso("12:56:30") == Nothing()

    def test_from_milliseconds(self) -> None:
        assert local_time.from_milliseconds(0) == LocalTime(0)


class TestFromMilliseconds:
    def test_the_value_is_stored_as_given(self) -> None:
        for millis in (0, 1, -1, DAY, DAY + 1, -DAY - 1, BASE, 10**30, -(10**30)):
            assert local_time.from_milliseconds(millis) == LocalTime(millis)

    def test_no_wrap_at_the_end_of_the_day(self) -> None:
        assert local_time.from_milliseconds(DAY) != local_time.from_milliseconds(0)
        assert local_time.from_milliseconds(DAY).milliseconds == 86_400_000

    def test_a_float_is_truncated_toward_zero(self) -> None:
        assert local_time.from_milliseconds(1.9) == LocalTime(1)  # type: ignore[arg-type]
        assert local_time.from_milliseconds(-1.9) == LocalTime(-1)  # type: ignore[arg-type]
        result = local_time.from_milliseconds(2.0)  # type: ignore[arg-type]
        assert type(result.milliseconds) is int

    def test_to_milliseconds_is_the_inverse(self) -> None:
        for millis in (0, 1, -1, 999, BASE, DAY * 400_000, -DAY * 400_000):
            assert (
                local_time.to_milliseconds(local_time.from_milliseconds(millis))
                == millis
            )


class TestFromIsoForms:
    """The forms that `Iso8601.toTime` of rtfeldman/elm-iso8601-date-strings reads."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("1970-01-01", 0),
            ("1970-01-01T00:00:00.000Z", 0),
            ("1970-01-02", DAY),
            ("1969-12-31T23:59:59.999Z", -1),
            ("2022-01-28", BASE - 12 * HOUR - 56 * MINUTE - 30 * SECOND),
            ("20220128", BASE - 12 * HOUR - 56 * MINUTE - 30 * SECOND),
            ("2022-01-28T12:56", BASE - 30 * SECOND),
            ("2022-01-28T1256", BASE - 30 * SECOND),
            ("2022-01-28T125630", BASE),
            ("20220128T125630Z", BASE),
            ("2022-01-28T12:56:30Z", BASE),
            ("2022-01-28T12:56:30.5", BASE + 500),
            ("2022-01-28T12:56:30.123Z", BASE + 123),
            ("2022-01-28T12:56:30.123456789Z", BASE + 123),
            ("2022-01-28T12:56:30.1236Z", BASE + 124),
            ("2022-01-28T12:56:30.9996Z", BASE + 1000),
            ("2022-01-28T12:56:30.", BASE),
            ("2022-01-28T12:56:30+01:00", BASE - HOUR),
            ("2022-01-28T12:56:30+0100", BASE - HOUR),
            ("2022-01-28T12:56:30+01", BASE - HOUR),
            ("2022-01-28T12:56:30-05:30", BASE + 5 * HOUR + 30 * MINUTE),
            ("2022-01-28T23:56:30-01:00", BASE + 12 * HOUR),
            ("2022-01-28T00:10:00+01:00", BASE - 13 * HOUR - 46 * MINUTE - 30 * SECOND),
            ("2020-02-29T00:00:00", 1582934400000),
            ("2000-03-01", 951868800000),
            ("1900-03-01", -2203891200000),
            ("0001-01-01", -62135596800000),
            ("9999-12-31T23:59:59.999Z", 253402300799999),
        ],
    )
    def test_accepted(self, text: str, expected: int) -> None:
        assert local_time.from_iso(text) == Just(LocalTime(expected))

    def test_agrees_with_the_standard_library(self) -> None:
        for text in ("1583-10-15T01:02:03", "2024-02-29T23:59:59", "2399-12-31T00:00"):
            aware = datetime.datetime.fromisoformat(text).replace(tzinfo=datetime.UTC)
            assert _utc(_iso(text)) == aware

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "T12:56:30",
            "2022-01-28T",
            "2022-01-28T12",
            "2022-01-28T12:56:",
            "2022-01-28T12:56:3",
            "2022-01-28 12:56:30",
            "2022-01-28t12:56:30",
            "2022-01-28T12:56:30z",
            "2022-01-28T12:56:30.1234567890",
            "2022-01-28T12:56:30+1",
            "2022-01-28T12:56:30Z ",
            "2022-01-28T12:56:30\n",
            "2022-13-28T12:56:30",
            "2022-00-28T12:56:30",
            "2022-01-32T12:56:30",
            "2021-02-29T12:56:30",
            "2022-04-31T12:56:30",
            "22-01-28T12:56:30",
            "-2022-01-28T12:56:30",
            "2022-01-28".translate(_ARABIC_INDIC_DIGITS),
        ],
    )
    def test_rejected(self, text: str) -> None:
        assert local_time.from_iso(text) == Nothing()

    @pytest.mark.parametrize(
        "text",
        [
            "2022-01-00T12:56:30",
            "2022-01-28T24:00:00",
            "2022-01-28T12:60:00",
            "2022-01-28T12:56:60",
            "2022-01-28T12:56:30+24:00",
            "2022-01-28T12:56:30+01:60",
        ],
    )
    def test_a_part_out_of_range_gives_nothing(self, text: str) -> None:
        assert local_time.from_iso(text) == Nothing()

    def test_the_year_0000_gives_nothing(self) -> None:
        assert local_time.from_iso("0000-01-01T00:00:00") == Nothing()

    def test_an_offset_can_move_the_result_out_of_the_years_1_to_9999(self) -> None:
        assert local_time.from_iso("0001-01-01T00:00:00+01:00") == Just(
            LocalTime(-62135596800000 - HOUR)
        )


class TestAdd:
    def test_add_is_plain_addition(self) -> None:
        start = LocalTime(BASE)
        assert local_time.add_hours(2, start) == LocalTime(BASE + 2 * HOUR)
        assert local_time.add_hours(-2, start) == LocalTime(BASE - 2 * HOUR)
        assert local_time.add_minutes(45, start) == LocalTime(BASE + 45 * MINUTE)
        assert local_time.add_minutes(-45, start) == LocalTime(BASE - 45 * MINUTE)
        assert local_time.add_seconds(7, start) == LocalTime(BASE + 7 * SECOND)
        assert local_time.add_seconds(-7, start) == LocalTime(BASE - 7 * SECOND)
        assert local_time.add_hours(0, start) == start

    def test_add_hours_does_not_wrap_at_midnight(self) -> None:
        start = _iso("2022-01-28T12:56:30")
        later = local_time.add_hours(25, start)
        assert later == _iso("2022-01-29T13:56:30")
        assert later != local_time.add_hours(1, start)
        assert _utc(later).day == 29

    def test_add_minutes_and_seconds_do_not_wrap_at_midnight(self) -> None:
        start = _iso("2022-01-28T23:30:00")
        assert local_time.add_minutes(45, start) == _iso("2022-01-29T00:15:00")
        assert local_time.add_seconds(86_400, start) == _iso("2022-01-29T23:30:00")
        assert local_time.add_seconds(-1, _iso("2022-01-28T00:00:00")) == _iso(
            "2022-01-27T23:59:59"
        )

    def test_add_keeps_the_milliseconds(self) -> None:
        assert local_time.add_seconds(1, LocalTime(BASE + 456)) == LocalTime(
            BASE + 1456
        )

    def test_add_has_no_limit(self) -> None:
        assert local_time.add_hours(10**20, LocalTime(0)) == LocalTime(10**20 * HOUR)


class TestDiff:
    def test_diff_is_the_first_argument_minus_the_second(self) -> None:
        a = _iso("2022-01-28T12:56:30")
        b = _iso("2022-01-28T15:49:30")
        assert local_time.diff_in_hours(b, a) == 2
        assert local_time.diff_in_hours(a, b) == -2
        assert local_time.diff_in_minutes(b, a) == 173
        assert local_time.diff_in_minutes(a, b) == -173
        assert local_time.diff_in_seconds(b, a) == 173 * 60
        assert local_time.diff_in_seconds(a, b) == -173 * 60

    def test_diff_truncates_toward_zero(self) -> None:
        a = LocalTime(BASE)
        b = LocalTime(BASE + 1500)
        assert local_time.diff_in_seconds(b, a) == 1
        assert local_time.diff_in_seconds(a, b) == -1
        assert local_time.diff_in_minutes(a, b) == 0
        c = LocalTime(BASE + 2 * HOUR - 1)
        assert local_time.diff_in_hours(c, a) == 1
        assert local_time.diff_in_hours(a, c) == -1
        assert local_time.diff_in_minutes(a, c) == -119

    def test_diff_does_not_wrap_across_days(self) -> None:
        a = _iso("2022-01-28T23:00:00")
        b = _iso("2022-01-30T01:00:00")
        assert local_time.diff_in_hours(b, a) == 26
        assert local_time.diff_in_hours(a, b) == -26
        assert local_time.diff_in_minutes(b, a) == 26 * 60
        assert local_time.diff_in_seconds(b, a) == 26 * 3600

    def test_diff_of_equal_values_is_zero(self) -> None:
        a = LocalTime(BASE)
        assert local_time.diff_in_hours(a, a) == 0
        assert local_time.diff_in_minutes(a, a) == 0
        assert local_time.diff_in_seconds(a, a) == 0


class TestCompare:
    def test_compare(self) -> None:
        assert local_time.compare(LocalTime(1), LocalTime(2)) is Order.LT
        assert local_time.compare(LocalTime(2), LocalTime(1)) is Order.GT
        assert local_time.compare(LocalTime(2), LocalTime(2)) is Order.EQ

    def test_compare_across_days(self) -> None:
        early = _iso("2022-01-28T23:00:00")
        late = _iso("2022-01-29T01:00:00")
        assert local_time.compare(early, late) is Order.LT
