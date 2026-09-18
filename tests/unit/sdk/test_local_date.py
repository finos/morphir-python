"""Tests for morphir.sdk.local_date (Morphir.SDK.LocalDate)."""

import datetime

import pytest

from morphir.sdk import local_date
from morphir.sdk.local_date import DayOfWeek, LocalDate, Month
from morphir.sdk.maybe import Just, Nothing, with_default

FALLBACK = datetime.date(2019, 2, 1)


def _elm_diff_in_months(a: LocalDate, b: LocalDate) -> int:
    """The float formula of justinmimbs/date, used as an oracle."""

    def to_months(d: LocalDate) -> float:
        return float(12 * (d.year - 1) + (d.month - 1)) + d.day / 100

    return int(to_months(b) - to_months(a))


class TestType:
    def test_local_date_is_the_standard_library_date(self) -> None:
        assert LocalDate is datetime.date

    def test_month_has_the_elm_constructor_names(self) -> None:
        assert [m.name for m in Month] == [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]

    def test_day_of_week_has_the_elm_constructor_names(self) -> None:
        assert [d.name for d in DayOfWeek] == [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]


class TestMath:
    """The Elm `mathTests`."""

    def test_add_day(self) -> None:
        assert local_date.add_days(1, datetime.date(2020, 1, 1)) == datetime.date(
            2020, 1, 2
        )

    def test_subtract_day(self) -> None:
        assert local_date.add_days(-1, datetime.date(2020, 1, 2)) == datetime.date(
            2020, 1, 1
        )

    def test_add_week(self) -> None:
        assert local_date.add_weeks(1, datetime.date(2020, 1, 7)) == datetime.date(
            2020, 1, 14
        )

    def test_subtract_week(self) -> None:
        assert local_date.add_weeks(-1, datetime.date(2020, 1, 14)) == datetime.date(
            2020, 1, 7
        )

    def test_add_month(self) -> None:
        assert local_date.add_months(1, datetime.date(2020, 1, 1)) == datetime.date(
            2020, 2, 1
        )

    def test_subtract_month(self) -> None:
        assert local_date.add_months(-1, datetime.date(2020, 2, 1)) == datetime.date(
            2020, 1, 1
        )

    def test_add_year(self) -> None:
        assert local_date.add_years(1, datetime.date(2020, 1, 1)) == datetime.date(
            2021, 1, 1
        )

    def test_subtract_year(self) -> None:
        assert local_date.add_years(-1, datetime.date(2020, 2, 1)) == datetime.date(
            2019, 2, 1
        )

    def test_from_iso_string_to_local_date(self) -> None:
        assert with_default(
            FALLBACK, local_date.from_iso("2023-06-13")
        ) == datetime.date(2023, 6, 13)

    def test_to_iso_string(self) -> None:
        assert local_date.to_iso_string(datetime.date(2023, 6, 13)) == "2023-06-13"

    def test_from_parts(self) -> None:
        assert with_default(
            FALLBACK, local_date.from_parts(2023, 6, 9)
        ) == datetime.date(2023, 6, 9)

    def test_diff_in_days(self) -> None:
        assert (
            local_date.diff_in_days(
                datetime.date(2023, 6, 9), datetime.date(2023, 6, 19)
            )
            == 10
        )

    def test_diff_in_weeks(self) -> None:
        assert (
            local_date.diff_in_weeks(
                datetime.date(2023, 6, 9), datetime.date(2023, 6, 19)
            )
            == 1
        )

    def test_diff_in_months(self) -> None:
        assert (
            local_date.diff_in_months(
                datetime.date(2023, 6, 9), datetime.date(2023, 6, 19)
            )
            == 0
        )

    def test_diff_in_years(self) -> None:
        assert (
            local_date.diff_in_years(
                datetime.date(2023, 6, 9), datetime.date(2024, 6, 19)
            )
            == 1
        )


class TestConstructors:
    """The Elm `constructorTests`."""

    def test_valid_from_iso(self) -> None:
        assert local_date.from_iso("2020-01-01") == Just(datetime.date(2020, 1, 1))

    def test_invalid_from_iso_parsing(self) -> None:
        assert local_date.from_iso("2020-01 hello") == Nothing()

    def test_invalid_from_iso_numeric(self) -> None:
        assert local_date.from_iso("2020-01-55") == Nothing()

    def test_valid_from_parts(self) -> None:
        assert local_date.from_parts(2020, 1, 1) == Just(datetime.date(2020, 1, 1))

    def test_invalid_month_from_parts(self) -> None:
        assert local_date.from_parts(2020, 13, 1) == Nothing()
        assert local_date.from_parts(2020, 0, 1) == Nothing()

    def test_invalid_day_from_parts(self) -> None:
        assert local_date.from_parts(2020, 2, 30) == Nothing()
        assert local_date.from_parts(2020, 2, 0) == Nothing()

    def test_valid_from_calendar_date(self) -> None:
        assert local_date.from_calendar_date(2023, Month.December, 25) == datetime.date(
            2023, 12, 25
        )

    def test_invalid_but_pinned_from_calendar_date(self) -> None:
        assert local_date.from_calendar_date(2023, Month.December, 39) == datetime.date(
            2023, 12, 31
        )
        assert local_date.from_calendar_date(2023, Month.February, -4) == datetime.date(
            2023, 2, 1
        )

    def test_valid_from_ordinal_date(self) -> None:
        assert local_date.from_ordinal_date(2023, 15) == datetime.date(2023, 1, 15)


class TestFromIsoForms:
    """The forms that `Date.fromIsoString` of justinmimbs/date accepts."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("2018", datetime.date(2018, 1, 1)),
            ("2018-09", datetime.date(2018, 9, 1)),
            ("2018-09-26", datetime.date(2018, 9, 26)),
            ("201809", datetime.date(2018, 9, 1)),
            ("20180926", datetime.date(2018, 9, 26)),
            ("2018-269", datetime.date(2018, 9, 26)),
            ("2018269", datetime.date(2018, 9, 26)),
            ("2018-W39", datetime.date(2018, 9, 24)),
            ("2018-W39-3", datetime.date(2018, 9, 26)),
            ("2018W39", datetime.date(2018, 9, 24)),
            ("2018W393", datetime.date(2018, 9, 26)),
            ("2020-366", datetime.date(2020, 12, 31)),
            ("2020-W53-7", datetime.date(2021, 1, 3)),
            ("2009-W01-1", datetime.date(2008, 12, 29)),
        ],
    )
    def test_accepted(self, text: str, expected: LocalDate) -> None:
        assert local_date.from_iso(text) == Just(expected)

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "18-09-26",
            "2018-9-26",
            "2018-09-26T00:00:00.000Z",
            "2018-09-26 ",
            " 2018-09-26",
            "2018-09-26\n",
            "2018-00-01",
            "2018-13-01",
            "2018-02-29",
            "2018-09-00",
            "2018-000",
            "2018-366",
            "2018-W00-1",
            "2018-W53-1",
            "2018-W39-0",
            "2018-W39-8",
            "2018-09-",
            "2018-0926",
            "2018/09/26",
            "\u0662\u0660\u0661\u0668-\u0660\u0669-\u0662\u0666",
        ],
    )
    def test_rejected(self, text: str) -> None:
        assert local_date.from_iso(text) == Nothing()

    def test_a_year_that_date_cannot_hold_gives_nothing(self) -> None:
        assert local_date.from_iso("0000-01-01") == Nothing()
        assert local_date.from_iso("-0001-01-01") == Nothing()

    def test_round_trip(self) -> None:
        d = datetime.date(987, 3, 4)
        assert local_date.to_iso_string(d) == "0987-03-04"
        assert local_date.from_iso("0987-03-04") == Just(d)


class TestOrdinalAndCalendar:
    def test_from_ordinal_date_clamps(self) -> None:
        assert local_date.from_ordinal_date(2023, 0) == datetime.date(2023, 1, 1)
        assert local_date.from_ordinal_date(2023, -9) == datetime.date(2023, 1, 1)
        assert local_date.from_ordinal_date(2023, 366) == datetime.date(2023, 12, 31)
        assert local_date.from_ordinal_date(2024, 366) == datetime.date(2024, 12, 31)
        assert local_date.from_ordinal_date(2024, 999) == datetime.date(2024, 12, 31)

    def test_from_calendar_date_leap_february(self) -> None:
        assert local_date.from_calendar_date(2024, Month.February, 30) == datetime.date(
            2024, 2, 29
        )
        assert local_date.from_calendar_date(2023, Month.February, 30) == datetime.date(
            2023, 2, 28
        )

    def test_year_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="year"):
            local_date.from_calendar_date(0, Month.January, 1)
        with pytest.raises(ValueError, match="year"):
            local_date.from_ordinal_date(10000, 1)

    def test_from_parts_year_out_of_range_gives_nothing(self) -> None:
        assert local_date.from_parts(0, 1, 1) == Nothing()
        assert local_date.from_parts(10000, 1, 1) == Nothing()


class TestAdd:
    def test_add_months_clamps_to_the_end_of_the_month(self) -> None:
        assert local_date.add_months(1, datetime.date(2020, 1, 31)) == datetime.date(
            2020, 2, 29
        )
        assert local_date.add_months(1, datetime.date(2021, 1, 31)) == datetime.date(
            2021, 2, 28
        )
        assert local_date.add_months(-1, datetime.date(2021, 3, 31)) == datetime.date(
            2021, 2, 28
        )
        assert local_date.add_months(1, datetime.date(2021, 3, 31)) == datetime.date(
            2021, 4, 30
        )

    def test_add_months_across_years(self) -> None:
        assert local_date.add_months(14, datetime.date(2020, 11, 15)) == datetime.date(
            2022, 1, 15
        )
        assert local_date.add_months(-11, datetime.date(2020, 11, 15)) == datetime.date(
            2019, 12, 15
        )
        assert local_date.add_months(-12, datetime.date(2020, 1, 15)) == datetime.date(
            2019, 1, 15
        )
        assert local_date.add_months(0, datetime.date(2020, 1, 15)) == datetime.date(
            2020, 1, 15
        )

    def test_add_years_clamps_february_29(self) -> None:
        assert local_date.add_years(1, datetime.date(2020, 2, 29)) == datetime.date(
            2021, 2, 28
        )
        assert local_date.add_years(4, datetime.date(2020, 2, 29)) == datetime.date(
            2024, 2, 29
        )

    def test_add_days_across_a_year(self) -> None:
        assert local_date.add_days(366, datetime.date(2020, 1, 1)) == datetime.date(
            2021, 1, 1
        )

    def test_result_out_of_range_raises(self) -> None:
        with pytest.raises(OverflowError):
            local_date.add_days(1, datetime.date.max)
        with pytest.raises(OverflowError):
            local_date.add_weeks(-1, datetime.date.min)
        with pytest.raises(OverflowError):
            local_date.add_months(1, datetime.date(9999, 12, 1))
        with pytest.raises(OverflowError):
            local_date.add_years(-1, datetime.date(1, 1, 1))


class TestDiff:
    def test_diff_is_negative_when_the_second_date_is_earlier(self) -> None:
        a = datetime.date(2023, 6, 19)
        b = datetime.date(2023, 6, 9)
        assert local_date.diff_in_days(a, b) == -10
        assert local_date.diff_in_weeks(a, b) == -1
        assert local_date.diff_in_months(a, b) == 0
        assert local_date.diff_in_years(a, b) == 0

    def test_diff_in_weeks_truncates_toward_zero(self) -> None:
        a = datetime.date(2023, 6, 1)
        assert local_date.diff_in_weeks(a, datetime.date(2023, 6, 14)) == 1
        assert local_date.diff_in_weeks(a, datetime.date(2023, 6, 15)) == 2
        assert local_date.diff_in_weeks(datetime.date(2023, 6, 14), a) == -1
        assert local_date.diff_in_weeks(datetime.date(2023, 6, 15), a) == -2

    def test_diff_in_months_counts_whole_months(self) -> None:
        a = datetime.date(2023, 1, 31)
        assert local_date.diff_in_months(a, datetime.date(2023, 2, 28)) == 0
        assert local_date.diff_in_months(a, datetime.date(2023, 3, 30)) == 1
        assert local_date.diff_in_months(a, datetime.date(2023, 3, 31)) == 2
        assert local_date.diff_in_months(datetime.date(2023, 3, 31), a) == -2
        assert local_date.diff_in_months(datetime.date(2023, 3, 30), a) == -1

    def test_diff_in_years(self) -> None:
        a = datetime.date(2020, 2, 29)
        assert local_date.diff_in_years(a, datetime.date(2021, 2, 28)) == 0
        assert local_date.diff_in_years(a, datetime.date(2021, 3, 1)) == 1
        assert local_date.diff_in_years(datetime.date(2021, 3, 1), a) == -1
        assert local_date.diff_in_years(a, datetime.date(2030, 2, 28)) == 9

    def test_diff_in_months_agrees_with_the_elm_formula(self) -> None:
        start = datetime.date(2019, 1, 1)
        dates = [start + datetime.timedelta(days=17 * i) for i in range(60)]
        disagreements = [
            (a, b)
            for a in dates
            for b in dates
            if local_date.diff_in_months(a, b) != _elm_diff_in_months(a, b)
        ]
        assert disagreements == []

    def test_same_day_of_month_is_a_whole_number_of_months(self) -> None:
        for months in range(-40, 41):
            a = datetime.date(2020, 5, 15)
            b = local_date.add_months(months, a)
            assert local_date.diff_in_months(a, b) == months


class TestQuery:
    def test_year_month_day(self) -> None:
        d = datetime.date(2023, 6, 13)
        assert local_date.year(d) == 2023
        assert local_date.month(d) is Month.June
        assert local_date.month_number(d) == 6
        assert local_date.day(d) == 13

    def test_day_of_week(self) -> None:
        monday = datetime.date(2023, 6, 12)
        for offset, expected in enumerate(DayOfWeek):
            assert (
                local_date.day_of_week(local_date.add_days(offset, monday)) is expected
            )

    def test_is_weekend_and_is_weekday(self) -> None:
        monday = datetime.date(2023, 6, 12)
        weekend = [
            local_date.is_weekend(local_date.add_days(i, monday)) for i in range(7)
        ]
        assert weekend == [False, False, False, False, False, True, True]
        weekday = [
            local_date.is_weekday(local_date.add_days(i, monday)) for i in range(7)
        ]
        assert weekday == [True, True, True, True, True, False, False]

    def test_month_to_int(self) -> None:
        assert [local_date.month_to_int(m) for m in Month] == list(range(1, 13))

    def test_int_to_month(self) -> None:
        for number, expected in enumerate(Month, start=1):
            assert local_date.int_to_month(number) == Just(expected)
        assert local_date.int_to_month(0) == Nothing()
        assert local_date.int_to_month(13) == Nothing()
