"""Morphir.SDK.LocalDate: a date with no time zone.

A `LocalDate` is the standard library `datetime.date`, a date in the proleptic
Gregorian calendar. The reference behaviour is the Elm runtime, which uses
justinmimbs/date.

    >>> from morphir.sdk import local_date as LocalDate
    >>> LocalDate.from_iso("2020-01-31")
    Just(value=datetime.date(2020, 1, 31))
    >>> LocalDate.to_iso_string(LocalDate.add_months(1, datetime.date(2020, 1, 31)))
    '2020-02-29'

`from_iso` accepts the ISO 8601 date forms that the Elm parser accepts: calendar
dates (`2018-09-26`, `20180926`, `2018-09`, `201809`), ordinal dates
(`2018-269`, `2018269`), week dates (`2018-W39-3`, `2018W393`, `2018-W39`,
`2018W39`) and a year alone (`2018`). Text with a time part gives `Nothing`.

`int_to_month` is in the Elm runtime but not in the IR specification.

Departures from the Elm runtime:

* A `datetime.date` holds the years 1 to 9999 only. `from_iso` and `from_parts`
  give `Nothing` for a year outside these limits. `from_calendar_date` and
  `from_ordinal_date` raise `ValueError`. The `add_*` functions raise
  `OverflowError` when the result is outside these limits.
* `diff_in_months` and `diff_in_years` use integer arithmetic. The Elm runtime
  uses a float formula, which in rare cases loses one month when the two dates
  have the same day of the month (for example between the years 1366 and 1367).
"""

import calendar
import datetime
import re
from enum import Enum

from morphir.sdk.maybe import Just, Maybe, Nothing

__all__ = [
    "DayOfWeek",
    "LocalDate",
    "Month",
    "add_days",
    "add_months",
    "add_weeks",
    "add_years",
    "day",
    "day_of_week",
    "diff_in_days",
    "diff_in_months",
    "diff_in_weeks",
    "diff_in_years",
    "from_calendar_date",
    "from_iso",
    "from_ordinal_date",
    "from_parts",
    "int_to_month",
    "is_weekday",
    "is_weekend",
    "month",
    "month_number",
    "month_to_int",
    "to_iso_string",
    "year",
]

LocalDate = datetime.date
"""The standard library date type."""


class DayOfWeek(Enum):
    """A day of the week."""

    Monday = "Monday"
    Tuesday = "Tuesday"
    Wednesday = "Wednesday"
    Thursday = "Thursday"
    Friday = "Friday"
    Saturday = "Saturday"
    Sunday = "Sunday"


class Month(Enum):
    """A month of the Gregorian calendar."""

    January = "January"
    February = "February"
    March = "March"
    April = "April"
    May = "May"
    June = "June"
    July = "July"
    August = "August"
    September = "September"
    October = "October"
    November = "November"
    December = "December"


_MONTHS = tuple(Month)
_DAYS_OF_WEEK = tuple(DayOfWeek)

# The year can have a minus sign. Only ASCII digits are accepted, as in Elm.
_ISO = re.compile(
    r"(?P<year>-?[0-9]{4})"
    r"(?:"
    r"-(?P<ordinal>[0-9]{3})"
    r"|-(?P<month>[0-9]{2})(?:-(?P<day>[0-9]{2}))?"
    r"|-W(?P<week>[0-9]{2})(?:-(?P<weekday>[0-9]))?"
    r"|(?P<basic_month>[0-9]{2})(?P<basic_day>[0-9]{2})?"
    r"|(?P<basic_ordinal>[0-9]{3})"
    r"|W(?P<basic_week>[0-9]{2})(?P<basic_weekday>[0-9])?"
    r")?"
)


def _check_year(year: int, owner: str) -> None:
    if not datetime.MINYEAR <= year <= datetime.MAXYEAR:
        raise ValueError(
            f"{owner}: year {year} is not in the range "
            f"{datetime.MINYEAR} to {datetime.MAXYEAR}"
        )


def _days_in_month(year: int, month_number: int) -> int:
    return calendar.monthrange(year, month_number)[1]


def _days_in_year(year: int) -> int:
    return 366 if calendar.isleap(year) else 365


def _truncated_div(a: int, b: int) -> int:
    quotient = abs(a) // abs(b)
    return quotient if (a >= 0) == (b >= 0) else -quotient


def _month_units(date: LocalDate) -> int:
    # Whole months since year 1, scaled by 100, plus the day of the month. The
    # day is at most 31, so the day part never carries into the month part.
    return (12 * (date.year - 1) + (date.month - 1)) * 100 + date.day


def diff_in_days(date1: LocalDate, date2: LocalDate) -> int:
    """Find the number of days from the first date to the second date.

    Args:
        date1: The start date.
        date2: The end date.

    Returns:
        The number of days. It is negative when `date2` is before `date1`.
    """
    return date2.toordinal() - date1.toordinal()


def diff_in_weeks(date1: LocalDate, date2: LocalDate) -> int:
    """Find the number of whole weeks from the first date to the second date.

    Args:
        date1: The start date.
        date2: The end date.

    Returns:
        The number of whole weeks, rounded toward zero.
    """
    return _truncated_div(diff_in_days(date1, date2), 7)


def diff_in_months(date1: LocalDate, date2: LocalDate) -> int:
    """Find the number of whole months from the first date to the second date.

    A month is complete when the day of the month of `date2` is equal to or
    after the day of the month of `date1`.

    Args:
        date1: The start date.
        date2: The end date.

    Returns:
        The number of whole months, rounded toward zero.
    """
    return _truncated_div(_month_units(date2) - _month_units(date1), 100)


def diff_in_years(date1: LocalDate, date2: LocalDate) -> int:
    """Find the number of whole years from the first date to the second date.

    Args:
        date1: The start date.
        date2: The end date.

    Returns:
        The number of whole years, rounded toward zero.
    """
    return _truncated_div(diff_in_months(date1, date2), 12)


def add_days(offset: int, start_date: LocalDate) -> LocalDate:
    """Add a number of days to a date.

    Args:
        offset: The number of days. It can be negative.
        start_date: The date to start from.

    Returns:
        The new date.

    Raises:
        OverflowError: If the result is not in the years 1 to 9999.
    """
    return start_date + datetime.timedelta(days=offset)


def add_weeks(offset: int, start_date: LocalDate) -> LocalDate:
    """Add a number of weeks to a date.

    Args:
        offset: The number of weeks. It can be negative.
        start_date: The date to start from.

    Returns:
        The new date.

    Raises:
        OverflowError: If the result is not in the years 1 to 9999.
    """
    return start_date + datetime.timedelta(weeks=offset)


def add_months(offset: int, start_date: LocalDate) -> LocalDate:
    """Add a number of months to a date.

    When the new month has fewer days than the day of the start date, the result
    is the last day of the new month: one month after 31 January is 28 or 29
    February.

    Args:
        offset: The number of months. It can be negative.
        start_date: The date to start from.

    Returns:
        The new date.

    Raises:
        OverflowError: If the result is not in the years 1 to 9999.
    """
    whole_months = 12 * (start_date.year - 1) + (start_date.month - 1) + offset
    new_year = whole_months // 12 + 1
    new_month = whole_months % 12 + 1
    if not datetime.MINYEAR <= new_year <= datetime.MAXYEAR:
        raise OverflowError("add_months: date value out of range")
    new_day = min(start_date.day, _days_in_month(new_year, new_month))
    return datetime.date(new_year, new_month, new_day)


def add_years(offset: int, start_date: LocalDate) -> LocalDate:
    """Add a number of years to a date.

    One year after 29 February is 28 February.

    Args:
        offset: The number of years. It can be negative.
        start_date: The date to start from.

    Returns:
        The new date.

    Raises:
        OverflowError: If the result is not in the years 1 to 9999.
    """
    return add_months(12 * offset, start_date)


def from_calendar_date(y: int, m: Month, d: int) -> LocalDate:
    """Make a date from a year, a month and a day of the month.

    A day that is out of range is clamped to the first or the last day of the
    month.

    Args:
        y: The year.
        m: The month.
        d: The day of the month.

    Returns:
        The date.

    Raises:
        ValueError: If the year is not in the range 1 to 9999.
    """
    _check_year(y, "from_calendar_date")
    month_num = month_to_int(m)
    return datetime.date(y, month_num, max(1, min(d, _days_in_month(y, month_num))))


def from_ordinal_date(y: int, day_of_year: int) -> LocalDate:
    """Make a date from a year and a day of the year.

    A day that is out of range is clamped to the first or the last day of the
    year.

    Args:
        y: The year.
        day_of_year: The day of the year, where 1 January is day 1.

    Returns:
        The date.

    Raises:
        ValueError: If the year is not in the range 1 to 9999.
    """
    _check_year(y, "from_ordinal_date")
    ordinal = max(1, min(day_of_year, _days_in_year(y)))
    return datetime.date(y, 1, 1) + datetime.timedelta(days=ordinal - 1)


def _from_iso_match(match: re.Match[str]) -> LocalDate:
    # Raises ValueError when a part is out of range.
    year_num = int(match["year"])
    if not datetime.MINYEAR <= year_num <= datetime.MAXYEAR:
        raise ValueError("year out of range")
    month_text = match["month"] or match["basic_month"]
    if month_text is not None:
        day_text = match["day"] or match["basic_day"] or "01"
        return datetime.date(year_num, int(month_text), int(day_text))
    week_text = match["week"] or match["basic_week"]
    if week_text is not None:
        weekday_text = match["weekday"] or match["basic_weekday"] or "1"
        return datetime.date.fromisocalendar(
            year_num, int(week_text), int(weekday_text)
        )
    ordinal = int(match["ordinal"] or match["basic_ordinal"] or "001")
    if not 1 <= ordinal <= _days_in_year(year_num):
        raise ValueError("day of year out of range")
    return datetime.date(year_num, 1, 1) + datetime.timedelta(days=ordinal - 1)


def from_iso(iso: str) -> Maybe[LocalDate]:
    """Read a date from ISO 8601 text.

    The module docstring lists the accepted forms. Parts that are out of range
    are not clamped: `2020-01-55` gives `Nothing`.

    Args:
        iso: The text to read.

    Returns:
        `Just` the date, or `Nothing` when the text is not a valid date.
    """
    match = _ISO.fullmatch(iso)
    if match is None:
        return Nothing()
    try:
        return Just(_from_iso_match(match))
    except ValueError, OverflowError:
        return Nothing()


def to_iso_string(date: LocalDate) -> str:
    """Convert a date to ISO 8601 text, in the form `YYYY-MM-DD`."""
    return f"{date.year:04d}-{date.month:02d}-{date.day:02d}"


def from_parts(year: int, month: int, day: int) -> Maybe[LocalDate]:
    """Make a date from a year, a month number and a day of the month.

    No value is clamped: `from_parts(2000, 2, 30)` gives `Nothing`.

    Args:
        year: The year.
        month: The month number, where January is 1.
        day: The day of the month.

    Returns:
        `Just` the date, or `Nothing` when a part is out of range.
    """
    try:
        return Just(datetime.date(year, month, day))
    except ValueError, OverflowError:
        return Nothing()


def year(local_date: LocalDate) -> int:
    """Return the year of a date."""
    return local_date.year


def month(local_date: LocalDate) -> Month:
    """Return the month of a date."""
    return _MONTHS[local_date.month - 1]


def month_number(local_date: LocalDate) -> int:
    """Return the month of a date as a number, where January is 1."""
    return local_date.month


def month_to_int(m: Month) -> int:
    """Convert a month to a number, where January is 1 and December is 12."""
    return _MONTHS.index(m) + 1


def int_to_month(i: int) -> Maybe[Month]:
    """Convert a number to a month, where January is 1.

    This function is in the Elm runtime but not in the IR specification.

    Args:
        i: The month number.

    Returns:
        `Just` the month, or `Nothing` when the number is not in 1 to 12.
    """
    if 1 <= i <= 12:
        return Just(_MONTHS[i - 1])
    return Nothing()


def day(local_date: LocalDate) -> int:
    """Return the day of the month of a date (1 to 31)."""
    return local_date.day


def day_of_week(local_date: LocalDate) -> DayOfWeek:
    """Return the day of the week of a date."""
    return _DAYS_OF_WEEK[local_date.weekday()]


def is_weekend(local_date: LocalDate) -> bool:
    """Check that a date is a Saturday or a Sunday."""
    return local_date.weekday() >= 5


def is_weekday(local_date: LocalDate) -> bool:
    """Check that a date is not a Saturday or a Sunday."""
    return not is_weekend(local_date)
