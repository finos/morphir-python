"""Morphir.SDK.ResultList: operations on lists of results.

A `ResultList[E, A]` is a tuple of `Result[E, A]` values: a list that holds a
mix of failed and successful records. These operations model a processing
pipeline where an error can occur at any step, but must not stop the pipeline.
A record that failed at an earlier step stays in the list as it is, and each
step works on the successful records only.

All functions take their arguments in Elm order, with the result list last.
They accept any `Sequence` and always yield a tuple.

`filter` and `map` shadow Python built-ins. Import the module with an alias,
not the names:

    >>> from morphir.sdk import result_list as ResultList
    >>> from morphir.sdk.result import Err, Ok
    >>> ResultList.keep_all_errors((Ok(1), Err("foo"), Ok(3), Err("bar")))
    Err(error=('foo', 'bar'))
"""

from typing import TYPE_CHECKING

from morphir.sdk.result import Err, Ok, Result

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

__all__ = [
    "ResultList",
    "errors",
    "filter",
    "filter_or_fail",
    "from_list",
    "keep_all_errors",
    "keep_first_error",
    "map",
    "map_or_fail",
    "partition",
    "successes",
]

type ResultList[E, A] = tuple[Result[E, A], ...]
"""A list that holds a mix of failed (`Err`) and successful (`Ok`) records."""


# Create


def from_list[E, A](xs: Sequence[A]) -> ResultList[E, A]:  # pyright: ignore[reportInvalidTypeVarUse]
    """Create a result list from a list. Every element becomes an `Ok`."""
    return tuple(Ok(x) for x in xs)


# Process


def filter[E, A](
    f: Callable[[A], bool], result_list: Sequence[Result[E, A]]
) -> ResultList[E, A]:
    """Keep the successful records that pass the test, and all failed records."""
    return tuple(
        result for result in result_list if isinstance(result, Err) or f(result.value)
    )


def filter_or_fail[E, A](
    f: Callable[[A], Result[E, bool]], result_list: Sequence[Result[E, A]]
) -> ResultList[E, A]:
    """Filter with a test that can fail.

    A successful record stays when the test yields `Ok(True)` and goes when the
    test yields `Ok(False)`. When the test yields an `Err`, that error replaces
    the record. All records that failed before stay.

    Args:
        f: The test.
        result_list: The result list.

    Returns:
        The filtered result list.
    """
    kept: list[Result[E, A]] = []
    for result in result_list:
        if isinstance(result, Err):
            kept.append(result)
            continue
        match f(result.value):
            case Ok(passed):
                if passed:
                    kept.append(result)
            case Err() as failure:
                kept.append(failure)
    return tuple(kept)


def map[E, A, B](
    f: Callable[[A], B], result_list: Sequence[Result[E, A]]
) -> ResultList[E, B]:
    """Apply a function to every successful record. Failed records stay."""
    return tuple(
        Ok(f(result.value)) if isinstance(result, Ok) else result
        for result in result_list
    )


def map_or_fail[E, A, B](
    f: Callable[[A], Result[E, B]], result_list: Sequence[Result[E, A]]
) -> ResultList[E, B]:
    """Apply a function that can fail to every successful record.

    An `Err` from the function replaces the record. All records that failed
    before stay.
    """
    return tuple(
        f(result.value) if isinstance(result, Ok) else result for result in result_list
    )


# Decompose


def errors[E, A](result_list: Sequence[Result[E, A]]) -> tuple[E, ...]:
    """Extract the errors of all failed records."""
    return tuple(result.error for result in result_list if isinstance(result, Err))


def successes[E, A](result_list: Sequence[Result[E, A]]) -> tuple[A, ...]:
    """Extract the values of all successful records."""
    return tuple(result.value for result in result_list if isinstance(result, Ok))


def partition[E, A](
    result_list: Sequence[Result[E, A]],
) -> tuple[tuple[E, ...], tuple[A, ...]]:
    """Divide a result list into its errors and its successful values."""
    return (errors(result_list), successes(result_list))


# Map to a single result


def keep_all_errors[E, A](
    result_list: Sequence[Result[E, A]],
) -> Result[tuple[E, ...], tuple[A, ...]]:
    """Turn a result list into a single result that keeps all errors.

    Returns:
        `Ok` with all values when no record failed (also for an empty list),
        else `Err` with all errors in list order.
    """
    errs = errors(result_list)
    if errs:
        return Err(errs)
    return Ok(successes(result_list))


def keep_first_error[E, A](
    result_list: Sequence[Result[E, A]],
) -> Result[E, tuple[A, ...]]:
    """Turn a result list into a single result that keeps only the first error.

    Returns:
        `Ok` with all values when no record failed (also for an empty list),
        else `Err` with the error of the first failed record.
    """
    errs = errors(result_list)
    if errs:
        return Err(errs[0])
    return Ok(successes(result_list))
