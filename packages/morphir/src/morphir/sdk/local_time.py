"""Morphir.SDK.LocalTime: a point in time with no time zone.

A `LocalTime` is an instant: a whole number of milliseconds from the Unix epoch,
1970-01-01T00:00:00Z. It holds a date and a time of day. This is the data of the
Elm runtime, where `LocalTime` is an alias of `Time.Posix`. Thus arithmetic does
not go around midnight: 25 hours after a time is on the next day, and the
difference between two times can be more than 24 hours.

    >>> from morphir.sdk import local_time as LocalTime
    >>> LocalTime.from_iso("2022-01-28T12:56:30")
    Just(value=LocalTime(milliseconds=1643374590000))
    >>> start = LocalTime.from_milliseconds(1643374590000)
    >>> LocalTime.diff_in_hours(LocalTime.add_hours(25, start), start)
    25

The number of milliseconds is a Python `int` with no limit. `LocalTime` values
have value equality, a hash and an order (`<`, `sorted`).

`from_iso` reads the text that `Iso8601.toTime` of
rtfeldman/elm-iso8601-date-strings reads: a date `YYYY-MM-DD`, then optionally
`T` and a time. Text with a time and no date (`12:56:30`) gives `Nothing`.

Additions to the specification: `to_milliseconds` and `compare`.

Departures from the Elm runtime:

* `from_iso` gives `Nothing` for an hour above 23, a minute or a second above
  59, a UTC offset above 23:59 and the day number 00. The Elm parser accepts
  these values and carries them into the result.
* For a negative UTC offset with minutes (`-05:30`), `from_iso` subtracts the
  minutes. The Elm parser adds them.
* `from_iso` gives `Nothing` for the year 0000. The text form permits the years
  0000 to 9999 only, in Elm also. A UTC offset can move the result a small
  distance out of the years 1 to 9999, and that result is given.
* A value has no upper or lower limit. In Elm the number is a JavaScript number,
  which is exact only to 2^53.
"""

import datetime
import math
import re
from dataclasses import dataclass

from morphir.sdk._compare import Order
from morphir.sdk.maybe import Just, Maybe, Nothing

__all__ = [
    "LocalTime",
    "add_hours",
    "add_minutes",
    "add_seconds",
    "compare",
    "diff_in_hours",
    "diff_in_minutes",
    "diff_in_seconds",
    "from_iso",
    "from_milliseconds",
    "to_milliseconds",
]


@dataclass(frozen=True, slots=True, order=True)
class LocalTime:
    """A point in time, as milliseconds from 1970-01-01T00:00:00Z."""

    milliseconds: int
    """The number of milliseconds from the epoch. It can be negative."""


_MILLIS_PER_SECOND = 1000
_MILLIS_PER_MINUTE = 60_000
_MILLIS_PER_HOUR = 3_600_000
_MILLIS_PER_DAY = 86_400_000
_EPOCH_ORDINAL = datetime.date(1970, 1, 1).toordinal()

# Only ASCII digits are accepted, as in Elm.
_ISO = re.compile(
    r"(?P<year>[0-9]{4})-?(?P<month>[0-9]{2})-?(?P<day>[0-9]{2})"
    r"(?:T(?P<hour>[0-9]{2}):?(?P<minute>[0-9]{2})(?::?(?P<second>[0-9]{2}))?"
    r"(?:\.(?P<fraction>[0-9]{0,9}))?"
    r"(?P<offset>Z|(?P<sign>[+-])(?P<offset_hour>[0-9]{2})"
    r"(?::?(?P<offset_minute>[0-9]{2}))?)?"
    r")?"
)


def _truncated_div(a: int, b: int) -> int:
    # Elm's `//` rounds toward zero. Python's `//` rounds down.
    quotient = abs(a) // abs(b)
    return quotient if (a >= 0) == (b >= 0) else -quotient


def from_milliseconds(millis: int) -> LocalTime:
    """Make a time from a number of milliseconds from the epoch.

    The number is kept as it is, with no limit and no wrap at the end of a day.

    Args:
        millis: The number of milliseconds from 1970-01-01T00:00:00Z. It can be
            negative. A `float` is truncated toward zero.

    Returns:
        The time.
    """
    return LocalTime(int(millis))


def to_milliseconds(time: LocalTime) -> int:
    """Return the number of milliseconds from the epoch to a time.

    This function is an addition to the specification.
    """
    return time.milliseconds


def compare(time_a: LocalTime, time_b: LocalTime) -> Order:
    """Compare two times. The earlier time is the smaller one.

    This function is an addition to the specification.

    Args:
        time_a: The first time.
        time_b: The second time.

    Returns:
        `Order.LT`, `Order.EQ` or `Order.GT`.
    """
    if time_a.milliseconds < time_b.milliseconds:
        return Order.LT
    if time_a.milliseconds > time_b.milliseconds:
        return Order.GT
    return Order.EQ


def add_hours(hours: int, time: LocalTime) -> LocalTime:
    """Add a number of hours to a time. The result can be on a different day.

    Args:
        hours: The number of hours. It can be negative.
        time: The time to start from.

    Returns:
        The new time.
    """
    return LocalTime(time.milliseconds + hours * _MILLIS_PER_HOUR)


def add_minutes(minutes: int, time: LocalTime) -> LocalTime:
    """Add a number of minutes to a time. The result can be on a different day.

    Args:
        minutes: The number of minutes. It can be negative.
        time: The time to start from.

    Returns:
        The new time.
    """
    return LocalTime(time.milliseconds + minutes * _MILLIS_PER_MINUTE)


def add_seconds(seconds: int, time: LocalTime) -> LocalTime:
    """Add a number of seconds to a time. The result can be on a different day.

    Args:
        seconds: The number of seconds. It can be negative.
        time: The time to start from.

    Returns:
        The new time.
    """
    return LocalTime(time.milliseconds + seconds * _MILLIS_PER_SECOND)


def diff_in_hours(time_a: LocalTime, time_b: LocalTime) -> int:
    """Find the number of whole hours from the second time to the first time.

    Args:
        time_a: The time to subtract from.
        time_b: The time that is subtracted.

    Returns:
        `time_a - time_b` in hours, rounded toward zero. It is negative when
        `time_a` is before `time_b`.
    """
    return _truncated_div(time_a.milliseconds - time_b.milliseconds, _MILLIS_PER_HOUR)


def diff_in_minutes(time_a: LocalTime, time_b: LocalTime) -> int:
    """Find the number of whole minutes from the second time to the first time.

    Args:
        time_a: The time to subtract from.
        time_b: The time that is subtracted.

    Returns:
        `time_a - time_b` in minutes, rounded toward zero. It is negative when
        `time_a` is before `time_b`.
    """
    return _truncated_div(time_a.milliseconds - time_b.milliseconds, _MILLIS_PER_MINUTE)


def diff_in_seconds(time_a: LocalTime, time_b: LocalTime) -> int:
    """Find the number of whole seconds from the second time to the first time.

    Args:
        time_a: The time to subtract from.
        time_b: The time that is subtracted.

    Returns:
        `time_a - time_b` in seconds, rounded toward zero. It is negative when
        `time_a` is before `time_b`.
    """
    return _truncated_div(time_a.milliseconds - time_b.milliseconds, _MILLIS_PER_SECOND)


def from_iso(iso: str) -> Maybe[LocalTime]:
    """Read a time from ISO 8601 text that has a date.

    The accepted text is `YYYY-MM-DD`, then optionally `T`, `HH:MM`, optional
    `:SS`, an optional fraction of a second with at most 9 digits, and an
    optional UTC offset (`Z`, `+HH:MM`, `+HHMM` or `+HH`). The `-` and `:`
    separators are optional. A fraction is rounded to the nearest millisecond.
    Text with no UTC offset is read as UTC. Text with no time part gives
    midnight.

    Args:
        iso: The text to read.

    Returns:
        `Just` the time, or `Nothing` when the text is not valid, a part is out
        of range, or the year is 0000.
    """
    match = _ISO.fullmatch(iso)
    if match is None:
        return Nothing()
    try:
        date = datetime.date(int(match["year"]), int(match["month"]), int(match["day"]))
    except ValueError:
        return Nothing()
    hour = int(match["hour"] or "0")
    minute = int(match["minute"] or "0")
    second = int(match["second"] or "0")
    offset_hour = int(match["offset_hour"] or "0")
    offset_minute = int(match["offset_minute"] or "0")
    if (
        hour > 23
        or minute > 59
        or second > 59
        or offset_hour > 23
        or offset_minute > 59
    ):
        return Nothing()
    fraction = match["fraction"]
    millisecond = math.floor(float(f"0.{fraction}") * 1000 + 0.5) if fraction else 0
    offset = offset_hour * _MILLIS_PER_HOUR + offset_minute * _MILLIS_PER_MINUTE
    if match["sign"] == "-":
        offset = -offset
    return Just(
        LocalTime(
            (date.toordinal() - _EPOCH_ORDINAL) * _MILLIS_PER_DAY
            + hour * _MILLIS_PER_HOUR
            + minute * _MILLIS_PER_MINUTE
            + second * _MILLIS_PER_SECOND
            + millisecond
            - offset
        )
    )
