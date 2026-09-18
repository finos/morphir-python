"""Morphir.SDK.Instant: a point on the timeline.

An `Instant` is the standard library `datetime.datetime` with a time zone, and
the recommended time zone is `datetime.UTC`. Two aware `datetime` values are
equal when they are the same point on the timeline, whatever their time zones.
A naive `datetime` (one with no `tzinfo`) is not an `Instant`, because it does
not identify a point on the timeline.

In the Elm runtime an `Instant` is a `Time.Posix`, a whole number of
milliseconds since 1970-01-01T00:00:00Z. The IR specification has the type and
no functions. `from_milliseconds_since_epoch` and `to_milliseconds_since_epoch`
are additions to the specification that convert between the two forms:

    >>> from morphir.sdk import instant as Instant
    >>> Instant.from_milliseconds_since_epoch(1643374590000).isoformat()
    '2022-01-28T12:56:30+00:00'
    >>> Instant.to_milliseconds_since_epoch(
    ...     datetime.datetime(2022, 1, 28, 12, 56, 30, tzinfo=datetime.UTC)
    ... )
    1643374590000

Departure from the Elm runtime: a `datetime` holds the years 1 to 9999 only, with
a precision of one microsecond.
"""

import datetime

__all__ = [
    "Instant",
    "from_milliseconds_since_epoch",
    "to_milliseconds_since_epoch",
]

Instant = datetime.datetime
"""The standard library datetime type, used with a time zone."""

_EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.UTC)
_MILLISECOND = datetime.timedelta(milliseconds=1)


def from_milliseconds_since_epoch(millis: int) -> Instant:
    """Make an instant from a number of milliseconds since the epoch.

    This function is an addition to the specification.

    Args:
        millis: The number of milliseconds since 1970-01-01T00:00:00Z. It can be
            negative.

    Returns:
        The instant, in UTC.

    Raises:
        OverflowError: If the instant is not in the years 1 to 9999.
    """
    return _EPOCH + datetime.timedelta(milliseconds=millis)


def to_milliseconds_since_epoch(instant: Instant) -> int:
    """Return the number of milliseconds from the epoch to an instant.

    This function is an addition to the specification.

    Args:
        instant: The instant. It must have a time zone.

    Returns:
        The number of milliseconds since 1970-01-01T00:00:00Z. A part below one
        millisecond is rounded down.

    Raises:
        ValueError: If the `datetime` has no time zone.
    """
    if instant.utcoffset() is None:
        raise ValueError("to_milliseconds_since_epoch: the datetime has no time zone")
    return (instant - _EPOCH) // _MILLISECOND
