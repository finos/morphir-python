r"""Morphir.SDK.Regex: regular expressions.

The reference is the API of elm/regex 1.0.0. A `Regex` holds a compiled pattern
of the standard library `re` module. Lists are tuples, as in `morphir.sdk.list`.

    >>> from morphir.sdk import regex as Regex
    >>> from morphir.sdk import maybe as Maybe
    >>> comma = Maybe.with_default(Regex.never, Regex.from_string(" *, *"))
    >>> Regex.split(comma, "tom , 99, 90")
    ('tom', '99', '90')
    >>> Regex.replace(comma, lambda match: ";", "tom , 99, 90")
    'tom;99;90'

Departures from elm/regex:

* **Pattern syntax.** elm/regex compiles a pattern with the JavaScript `RegExp`
  (with no `u` flag). This module compiles it with Python `re`. Most patterns
  mean the same in the two, but not all. The known differences are:

  * A named group is `(?P<name>...)` and a reference to it is `(?P=name)`. The
    JavaScript forms `(?<name>...)` and `\k<name>` are not valid.
  * `\d`, `\w`, `\s` and `\b` use the Unicode character properties. In
    JavaScript `\d` and `\w` match ASCII characters only. Write `[0-9]` for the
    ASCII digits.
  * `case_insensitive` uses the Unicode case rules.
  * `$` with no `multiline` option also matches before a line feed at the end
    of the text. Use `\Z` for the end of the text only.
  * Python rejects an escape of an ASCII letter that it does not know, such as
    the JavaScript control escape `\cJ`. The JavaScript classes `[^]` and `[]`
    are not valid.
  * A lookbehind must have a fixed width.
  * A pattern that JavaScript accepts can therefore give `Nothing` here, and the
    reverse is also possible.

* **Index.** `Match.index` counts Unicode code points, as all string functions
  in this SDK do. In Elm it counts UTF-16 code units.
* **Empty matches in `split`.** In Elm, `split` does not stop when the pattern
  matches the empty string. Here the search continues after an empty match one
  character later, as `re.finditer` does: `split` with the pattern `""` gives
  the characters with an empty string at the two ends.
* **A negative count.** `split_at_most` with a negative count does no split. In
  Elm a negative count means no limit.

Behaviour of elm/regex that this module keeps:

* A group that matched the empty string is `Nothing` in `Match.submatches`, the
  same as a group that did not take part in the match.
* `find` and `find_at_most` stop at an empty match that ends where the search
  for it started: `find` with `a*` on `"baaa"` gives one empty match.
* `replace` replaces empty matches in the same way as JavaScript and Python.
"""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from morphir.sdk.maybe import Just, Maybe, Nothing

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = [
    "Match",
    "Options",
    "Regex",
    "contains",
    "find",
    "find_at_most",
    "from_string",
    "from_string_with",
    "never",
    "replace",
    "replace_at_most",
    "split",
    "split_at_most",
]


@dataclass(frozen=True, slots=True)
class Regex:
    """A compiled regular expression.

    Make one with `from_string` or `from_string_with`. Two values are equal when
    they have the same pattern text and the same options.
    """

    pattern: re.Pattern[str]


@dataclass(frozen=True, slots=True)
class Options:
    """The options of `from_string_with`."""

    case_insensitive: bool
    """Ignore the case of letters."""

    multiline: bool
    """Let `^` and `$` match at the start and the end of each line."""


@dataclass(frozen=True, slots=True)
class Match:
    """The data of one match."""

    match: str
    """The text that matched."""

    index: int
    """The position of the match in the text, in code points from 0."""

    number: int
    """The number of the match: 1 for the first match, 2 for the second."""

    submatches: tuple[Maybe[str], ...]
    """The text of each group in the pattern.

    A group that took no part in the match, or that matched the empty string, is
    `Nothing`.
    """


def from_string_with(options: Options, string: str) -> Maybe[Regex]:
    """Compile a pattern with options.

    Args:
        options: The options.
        string: The pattern, in the syntax of the Python `re` module.

    Returns:
        `Just` the regular expression, or `Nothing` when the pattern is not
        valid.
    """
    flags = re.NOFLAG
    if options.case_insensitive:
        flags |= re.IGNORECASE
    if options.multiline:
        flags |= re.MULTILINE
    try:
        return Just(Regex(re.compile(string, flags)))
    except (re.PatternError, OverflowError, RecursionError):
        return Nothing()


def from_string(string: str) -> Maybe[Regex]:
    """Compile a pattern that is case sensitive and not multiline.

    Args:
        string: The pattern, in the syntax of the Python `re` module.

    Returns:
        `Just` the regular expression, or `Nothing` when the pattern is not
        valid.
    """
    return from_string_with(Options(case_insensitive=False, multiline=False), string)


never: Regex = Regex(re.compile(r".^"))
"""A regular expression that never matches."""


def contains(regex: Regex, string: str) -> bool:
    """Check that a regular expression matches somewhere in a string."""
    return regex.pattern.search(string) is not None


def _to_match(found: re.Match[str], number: int) -> Match:
    return Match(
        match=found.group(0),
        index=found.start(),
        number=number,
        submatches=tuple(
            Just(group) if group else Nothing() for group in found.groups()
        ),
    )


def split_at_most(number: int, regex: Regex, string: str) -> tuple[str, ...]:
    """Split a string at the first matches of a regular expression.

    Args:
        number: The maximum number of splits. Zero or less gives no split.
        regex: The regular expression that matches the separators.
        string: The string to split.

    Returns:
        The parts between the separators. The text of the groups in the pattern
        is not in the result.
    """
    parts: list[str] = []
    start = 0
    for count, found in enumerate(regex.pattern.finditer(string)):
        if count >= number:
            break
        parts.append(string[start : found.start()])
        start = found.end()
    parts.append(string[start:])
    return tuple(parts)


def split(regex: Regex, string: str) -> tuple[str, ...]:
    """Split a string at all matches of a regular expression.

    Args:
        regex: The regular expression that matches the separators.
        string: The string to split.

    Returns:
        The parts between the separators.
    """
    return split_at_most(len(string) + 1, regex, string)


def find_at_most(number: int, regex: Regex, string: str) -> tuple[Match, ...]:
    """Find the first matches of a regular expression in a string.

    Args:
        number: The maximum number of matches.
        regex: The regular expression.
        string: The string to search.

    Returns:
        The matches, in the sequence in which they occur.
    """
    matches: list[Match] = []
    position = 0
    previous_end = -1
    while len(matches) < number:
        found = regex.pattern.search(string, position)
        if found is None or found.end() == previous_end:
            break
        matches.append(_to_match(found, len(matches) + 1))
        previous_end = position = found.end()
    return tuple(matches)


def find(regex: Regex, string: str) -> tuple[Match, ...]:
    """Find all matches of a regular expression in a string.

    Args:
        regex: The regular expression.
        string: The string to search.

    Returns:
        The matches, in the sequence in which they occur.
    """
    return find_at_most(len(string) + 1, regex, string)


def replace_at_most(
    number: int, regex: Regex, with_: Callable[[Match], str], string: str
) -> str:
    r"""Replace the first matches of a regular expression in a string.

    Args:
        number: The maximum number of replacements.
        regex: The regular expression.
        with_: A function that gives the replacement text for a match. The text
            is used as it is: `\1` and `$1` have no special meaning.
        string: The string to change.

    Returns:
        The string with the replacements.
    """
    if number <= 0:
        return string
    count = 0

    def replacement(found: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return with_(_to_match(found, count))

    return regex.pattern.sub(replacement, string, count=number)


def replace(regex: Regex, with_: Callable[[Match], str], string: str) -> str:
    """Replace all matches of a regular expression in a string.

    Args:
        regex: The regular expression.
        with_: A function that gives the replacement text for a match.
        string: The string to change.

    Returns:
        The string with the replacements.
    """
    return replace_at_most(len(string) + 1, regex, with_, string)
