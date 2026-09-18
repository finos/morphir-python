"""Morphir.SDK.Instant: a point on the timeline.

An `Instant` holds a whole number of milliseconds since 1970-01-01T00:00:00Z.
This is the form of the Elm runtime, where an `Instant` is a `Time.Posix`, and of
`morphir.sdk.local_time.LocalTime`. The number has no limit.

The type is its own class, not an alias of `datetime.datetime`. A `datetime` can
be naive (it can have no time zone), and a naive `datetime` does not identify a
point on the timeline. With a class that holds only the number, a value that is
not a point on the timeline cannot be made.

The IR specification has the type and no functions. All the functions here are
additions to the specification:

    >>> from morphir.sdk import instant as Instant
    >>> moment = Instant.from_milliseconds_since_epoch(1643374590000)
    >>> Instant.to_datetime(moment).isoformat()
    '2022-01-28T12:56:30+00:00'
    >>> Instant.to_milliseconds_since_epoch(
    ...     Instant.from_datetime(
    ...         datetime.datetime(2022, 1, 28, 12, 56, 30, tzinfo=datetime.UTC)
    ...     )
    ... )
    1643374590000
"""

import datetime
from dataclasses import dataclass

from morphir.sdk._compare import Order

__all__ = [
    "Instant",
    "compare",
    "from_datetime",
    "from_milliseconds_since_epoch",
    "to_datetime",
    "to_milliseconds_since_epoch",
]

_EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.UTC)
_MILLISECOND = datetime.timedelta(milliseconds=1)


@dataclass(frozen=True, slots=True, order=True)
class Instant:
    """A point on the timeline, as milliseconds since 1970-01-01T00:00:00Z.

    Raises:
        TypeError: If `milliseconds` is not an `int`. A `bool`, a `float` and a
            `datetime` are rejected.
    """

    milliseconds: int

    def __post_init__(self) -> None:
        value: object = self.milliseconds
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(
                f"Instant: milliseconds must be an int, not {type(value).__name__}; "
                f"use from_datetime to convert a datetime"
            )


def from_milliseconds_since_epoch(millis: int) -> Instant:
    """Make an instant from a number of milliseconds since the epoch.

    Args:
        millis: The number of milliseconds since 1970-01-01T00:00:00Z. It can be
            negative.

    Raises:
        TypeError: If `millis` is not an `int`.
    """
    return Instant(millis)


def to_milliseconds_since_epoch(instant: Instant) -> int:
    """Return the number of milliseconds from the epoch to an instant."""
    return instant.milliseconds


def compare(a: Instant, b: Instant) -> Order:
    """Compare two instants. The earlier instant is less."""
    if a.milliseconds < b.milliseconds:
        return Order.LT
    if a.milliseconds > b.milliseconds:
        return Order.GT
    return Order.EQ


def from_datetime(moment: datetime.datetime) -> Instant:
    """Make an instant from a `datetime` that has a time zone.

    A part below one millisecond is rounded down.

    Raises:
        ValueError: If the `datetime` has no time zone. A naive `datetime` does
            not identify a point on the timeline.
    """
    if moment.utcoffset() is None:
        raise ValueError("from_datetime: the datetime has no time zone")
    return Instant((moment - _EPOCH) // _MILLISECOND)


def to_datetime(instant: Instant) -> datetime.datetime:
    """Return the instant as a `datetime` in UTC.

    Raises:
        OverflowError: If the instant is not in the years 1 to 9999, which is
            the range of a `datetime`.
    """
    try:
        return _EPOCH + datetime.timedelta(milliseconds=instant.milliseconds)
    except OverflowError:
        raise
    except (ValueError, OSError) as error:
        raise OverflowError(str(error)) from error
