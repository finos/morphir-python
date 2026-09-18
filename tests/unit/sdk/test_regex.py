"""Tests for morphir.sdk.regex (Morphir.SDK.Regex, elm/regex 1.0.0)."""

import dataclasses
import re

import pytest

from morphir.sdk import regex
from morphir.sdk.maybe import Just, Nothing, with_default
from morphir.sdk.regex import Match, Options, Regex


def _regex(pattern: str) -> Regex:
    return with_default(regex.never, regex.from_string(pattern))


class TestTypes:
    def test_regex_is_frozen(self) -> None:
        value = _regex("a")
        with pytest.raises(dataclasses.FrozenInstanceError):
            value.pattern = re.compile("b")  # type: ignore[misc]

    def test_regex_values_are_equal_by_pattern_and_options(self) -> None:
        assert regex.from_string("a+") == regex.from_string("a+")
        assert regex.from_string("a+") != regex.from_string("a*")
        assert regex.from_string("a+") != regex.from_string_with(
            Options(case_insensitive=True, multiline=False), "a+"
        )
        assert hash(_regex("a+")) == hash(_regex("a+"))

    def test_match_fields(self) -> None:
        value = Match(match="ab", index=3, number=1, submatches=(Just("a"), Nothing()))
        assert value.match == "ab"
        assert value.index == 3
        assert value.number == 1
        assert value.submatches == (Just("a"), Nothing())
        with pytest.raises(dataclasses.FrozenInstanceError):
            value.index = 4  # type: ignore[misc]

    def test_options_fields(self) -> None:
        options = Options(case_insensitive=True, multiline=False)
        assert options.case_insensitive is True
        assert options.multiline is False


class TestFromString:
    def test_valid(self) -> None:
        match regex.from_string("[0-9]+"):
            case Just(value):
                assert value.pattern.pattern == "[0-9]+"
            case Nothing():
                pytest.fail("from_string gave Nothing")

    @pytest.mark.parametrize(
        "pattern", ["(", "[a", "a**", "(?<n", "\\", "a{99999999999}"]
    )
    def test_invalid_gives_nothing(self, pattern: str) -> None:
        assert regex.from_string(pattern) == Nothing()

    def test_default_options(self) -> None:
        lower = _regex("abc")
        assert regex.contains(lower, "ABC") is False
        start = _regex("^b")
        assert regex.contains(start, "a\nb") is False

    def test_dot_does_not_match_a_line_feed(self) -> None:
        assert regex.contains(_regex("a.b"), "a\nb") is False


class TestFromStringWith:
    def test_case_insensitive(self) -> None:
        value = with_default(
            regex.never,
            regex.from_string_with(
                Options(case_insensitive=True, multiline=False), "abc"
            ),
        )
        assert regex.contains(value, "xABCx") is True

    def test_multiline(self) -> None:
        value = with_default(
            regex.never,
            regex.from_string_with(
                Options(case_insensitive=False, multiline=True), "^b$"
            ),
        )
        assert regex.contains(value, "a\nb\nc") is True
        assert regex.contains(value, "a\nB\nc") is False

    def test_both(self) -> None:
        value = with_default(
            regex.never,
            regex.from_string_with(
                Options(case_insensitive=True, multiline=True), "^b$"
            ),
        )
        assert regex.contains(value, "a\nB\nc") is True

    def test_invalid_gives_nothing(self) -> None:
        assert (
            regex.from_string_with(Options(case_insensitive=True, multiline=True), "(")
            == Nothing()
        )


class TestNever:
    @pytest.mark.parametrize("text", ["", "a", ".^", "\n", "abc\ndef"])
    def test_never_matches_nothing(self, text: str) -> None:
        assert regex.contains(regex.never, text) is False
        assert regex.find(regex.never, text) == ()
        assert regex.split(regex.never, text) == (text,)
        assert regex.replace(regex.never, lambda _: "x", text) == text


class TestContains:
    """The examples of the elm/regex documentation."""

    def test_contains(self) -> None:
        digit = _regex("[0-9]")
        assert regex.contains(digit, "abc123") is True
        assert regex.contains(digit, "abcxyz") is False

    def test_contains_searches_the_whole_string(self) -> None:
        assert regex.contains(_regex("c$"), "abc") is True
        assert regex.contains(_regex("^b"), "abc") is False


class TestSplit:
    def test_split(self) -> None:
        comma = _regex(" *, *")
        expected = ("tom", "99", "90", "85")
        assert regex.split(comma, "tom,99,90,85") == expected
        assert regex.split(comma, "tom, 99, 90, 85") == expected
        assert regex.split(comma, "tom , 99, 90, 85") == expected

    def test_no_match(self) -> None:
        assert regex.split(_regex(","), "abc") == ("abc",)
        assert regex.split(_regex(","), "") == ("",)

    def test_match_at_the_ends(self) -> None:
        assert regex.split(_regex(","), ",a,,b,") == ("", "a", "", "b", "")

    def test_groups_are_not_in_the_result(self) -> None:
        assert regex.split(_regex("(,)( )?"), "a,b, c") == ("a", "b", "c")

    def test_split_at_most(self) -> None:
        comma = _regex(",")
        assert regex.split_at_most(1, comma, "tom,99,90,85") == ("tom", "99,90,85")
        assert regex.split_at_most(2, comma, "tom,99,90,85") == ("tom", "99", "90,85")
        assert regex.split_at_most(3, comma, "tom,99,90,85") == (
            "tom",
            "99",
            "90",
            "85",
        )
        assert regex.split_at_most(99, comma, "tom,99,90,85") == (
            "tom",
            "99",
            "90",
            "85",
        )

    def test_split_at_most_zero_or_less(self) -> None:
        assert regex.split_at_most(0, _regex(","), "a,b") == ("a,b",)
        assert regex.split_at_most(-1, _regex(","), "a,b") == ("a,b",)

    def test_empty_matches(self) -> None:
        assert regex.split(_regex(""), "abc") == ("", "a", "b", "c", "")
        assert regex.split(_regex("x*"), "axxb") == ("", "a", "", "b", "")


class TestFind:
    def test_find(self) -> None:
        location = _regex(r"[oi]n a (\w+)")
        assert regex.find(location, "I am on a boat in a lake.") == (
            Match(match="on a boat", index=5, number=1, submatches=(Just("boat"),)),
            Match(match="in a lake", index=15, number=2, submatches=(Just("lake"),)),
        )

    def test_no_match(self) -> None:
        assert regex.find(_regex("x"), "abc") == ()

    def test_no_groups(self) -> None:
        assert regex.find(_regex("b"), "abc") == (
            Match(match="b", index=1, number=1, submatches=()),
        )

    def test_a_group_that_did_not_take_part_is_nothing(self) -> None:
        assert regex.find(_regex("(a)|(b)"), "ab") == (
            Match(match="a", index=0, number=1, submatches=(Just("a"), Nothing())),
            Match(match="b", index=1, number=2, submatches=(Nothing(), Just("b"))),
        )

    def test_an_empty_group_is_nothing_as_in_elm(self) -> None:
        assert regex.find(_regex("(x*)b"), "ab") == (
            Match(match="b", index=1, number=1, submatches=(Nothing(),)),
        )

    def test_named_group_is_a_submatch(self) -> None:
        assert regex.find(_regex(r"(?P<word>\w+)"), "hi") == (
            Match(match="hi", index=0, number=1, submatches=(Just("hi"),)),
        )

    def test_find_at_most(self) -> None:
        digit = _regex("[0-9]")
        assert regex.find_at_most(2, digit, "a1b2c3") == (
            Match(match="1", index=1, number=1, submatches=()),
            Match(match="2", index=3, number=2, submatches=()),
        )
        assert len(regex.find_at_most(99, digit, "a1b2c3")) == 3

    def test_find_at_most_zero_or_less(self) -> None:
        assert regex.find_at_most(0, _regex("a"), "aaa") == ()
        assert regex.find_at_most(-1, _regex("a"), "aaa") == ()

    def test_find_stops_at_an_empty_match_as_in_elm(self) -> None:
        assert regex.find(_regex("a*"), "baaa") == (
            Match(match="", index=0, number=1, submatches=()),
        )
        assert regex.find(_regex("a*"), "aab") == (
            Match(match="aa", index=0, number=1, submatches=()),
        )
        assert regex.find(_regex(""), "") == (
            Match(match="", index=0, number=1, submatches=()),
        )

    def test_start_anchor_matches_only_at_the_start(self) -> None:
        assert regex.find(_regex("^a"), "aaa") == (
            Match(match="a", index=0, number=1, submatches=()),
        )

    def test_lookbehind_sees_the_text_before_the_match(self) -> None:
        assert [m.index for m in regex.find(_regex("(?<=a)a"), "aaa")] == [1, 2]

    def test_index_counts_code_points(self) -> None:
        assert regex.find(_regex("b"), "\N{GRINNING FACE}b") == (
            Match(match="b", index=1, number=1, submatches=()),
        )


class TestReplace:
    def test_replace(self) -> None:
        vowel = _regex("[aeiou]")
        assert regex.replace(vowel, lambda _: "", "The quick brown fox") == (
            "Th qck brwn fx"
        )

    def test_replace_uses_the_match(self) -> None:
        word = _regex(r"\w+")
        assert (
            regex.replace(word, lambda m: m.match[::-1], "deliver mined parts")
            == "reviled denim strap"
        )

    def test_replace_gives_the_match_data(self) -> None:
        seen: list[Match] = []

        def record(match: Match) -> str:
            seen.append(match)
            return f"<{match.number}>"

        assert regex.replace(_regex("(a)|(b)"), record, "xaxb") == "x<1>x<2>"
        assert seen == [
            Match(match="a", index=1, number=1, submatches=(Just("a"), Nothing())),
            Match(match="b", index=3, number=2, submatches=(Nothing(), Just("b"))),
        ]

    def test_replacement_text_is_literal(self) -> None:
        assert regex.replace(_regex("(a)"), lambda _: r"\1$1\g<1>", "a") == (
            r"\1$1\g<1>"
        )

    def test_no_match(self) -> None:
        assert regex.replace(_regex("x"), lambda _: "y", "abc") == "abc"

    def test_empty_matches(self) -> None:
        assert regex.replace(_regex("x*"), lambda _: "-", "abxd") == "-a-b--d-"

    def test_replace_at_most(self) -> None:
        vowel = _regex("[aeiou]")
        assert regex.replace_at_most(2, vowel, lambda _: "_", "banana bread") == (
            "b_n_na bread"
        )
        assert regex.replace_at_most(99, vowel, lambda _: "_", "banana") == "b_n_n_"

    def test_replace_at_most_zero_or_less(self) -> None:
        def fail(_: Match) -> str:
            raise AssertionError("the function must not be called")

        assert regex.replace_at_most(0, _regex("a"), fail, "banana") == "banana"
        assert regex.replace_at_most(-1, _regex("a"), fail, "banana") == "banana"


class TestPythonSyntax:
    """The departures from JavaScript that the module docstring gives."""

    def test_digit_class_is_unicode(self) -> None:
        assert regex.contains(_regex(r"\d"), "\N{ARABIC-INDIC DIGIT TWO}") is True

    def test_javascript_named_group_is_not_valid(self) -> None:
        assert regex.from_string(r"(?<word>\w+)") == Nothing()

    def test_case_insensitive_is_unicode(self) -> None:
        value = with_default(
            regex.never,
            regex.from_string_with(
                Options(case_insensitive=True, multiline=False), "straße"
            ),
        )
        assert regex.contains(value, "STRAßE") is True
