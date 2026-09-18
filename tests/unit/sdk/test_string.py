"""Tests for morphir.sdk.string (Morphir.SDK.String)."""

import math

from morphir.sdk import string
from morphir.sdk.maybe import Just, Nothing


def _is_digit(c: str) -> bool:
    return "0" <= c <= "9"


class TestBasics:
    def test_is_empty(self) -> None:
        assert string.is_empty("")
        assert not string.is_empty("the world")

    def test_length_counts_code_points(self) -> None:
        assert string.length("innumerable") == 11
        assert string.length("") == 0
        assert string.length("😃") == 1

    def test_reverse(self) -> None:
        assert string.reverse("stressed") == "desserts"
        assert string.reverse("") == ""
        assert string.reverse("a😃b") == "b😃a"

    def test_repeat(self) -> None:
        assert string.repeat(3, "ha") == "hahaha"
        assert string.repeat(0, "ha") == ""
        assert string.repeat(-2, "ha") == ""

    def test_replace_replaces_every_occurrence(self) -> None:
        assert string.replace(".", "-", "Json.Decode.succeed") == "Json-Decode-succeed"
        assert string.replace(",", "/", "a,b,c,d,e") == "a/b/c/d/e"
        assert string.replace("x", "y", "abc") == "abc"

    def test_replace_with_an_empty_match_goes_between_chars(self) -> None:
        assert string.replace("", "-", "abc") == "a-b-c"
        assert string.replace("", "-", "") == ""


class TestBuildingAndSplitting:
    def test_append(self) -> None:
        assert string.append("butter", "fly") == "butterfly"
        assert string.append("", "") == ""

    def test_concat(self) -> None:
        assert string.concat(("never", "the", "less")) == "nevertheless"
        assert string.concat(()) == ""

    def test_split(self) -> None:
        assert string.split(",", "cat,dog,cow") == ("cat", "dog", "cow")
        assert string.split("/", "home/evan/Desktop/") == (
            "home",
            "evan",
            "Desktop",
            "",
        )
        assert string.split(",", "") == ("",)

    def test_split_on_an_empty_separator_yields_chars(self) -> None:
        assert string.split("", "abc") == ("a", "b", "c")
        assert string.split("", "") == ()

    def test_join(self) -> None:
        assert string.join("a", ("H", "w", "ii", "n")) == "Hawaiian"
        assert string.join(" ", ("cat", "dog", "cow")) == "cat dog cow"
        assert string.join(",", ()) == ""

    def test_words_splits_on_whitespace_runs_after_trimming(self) -> None:
        assert string.words("How are \t you? \n Good?") == (
            "How",
            "are",
            "you?",
            "Good?",
        )
        assert string.words("  leading and trailing  ") == (
            "leading",
            "and",
            "trailing",
        )
        assert string.words("") == ("",)
        assert string.words("   ") == ("",)

    def test_lines(self) -> None:
        assert string.lines("How are you?\nGood?") == ("How are you?", "Good?")
        assert string.lines("a\r\nb\nc\rd") == ("a", "b", "c", "d")
        assert string.lines("") == ("",)
        assert string.lines("a\n") == ("a", "")


class TestSubstrings:
    def test_slice_with_elm_negative_index_semantics(self) -> None:
        assert string.slice(7, 9, "snakes on a plane!") == "on"
        assert string.slice(0, 6, "snakes on a plane!") == "snakes"
        assert string.slice(0, -7, "snakes on a plane!") == "snakes on a"
        assert string.slice(-6, -1, "snakes on a plane!") == "plane"
        assert string.slice(-3, -1, "abcde") == "cd"
        assert string.slice(0, 3, "abcde") == "abc"
        assert string.slice(3, 1, "abcde") == ""
        assert string.slice(-100, 100, "abcde") == "abcde"

    def test_left(self) -> None:
        assert string.left(2, "Mulder") == "Mu"
        assert string.left(0, "Mulder") == ""
        assert string.left(-1, "Mulder") == ""
        assert string.left(10, "Mulder") == "Mulder"

    def test_right(self) -> None:
        assert string.right(2, "Scully") == "ly"
        assert string.right(0, "Scully") == ""
        assert string.right(-1, "Scully") == ""
        assert string.right(10, "Scully") == "Scully"

    def test_drop_left(self) -> None:
        assert string.drop_left(2, "The Lone Gunmen") == "e Lone Gunmen"
        assert string.drop_left(0, "abc") == "abc"
        assert string.drop_left(-1, "abc") == "abc"
        assert string.drop_left(10, "abc") == ""

    def test_drop_right(self) -> None:
        assert string.drop_right(2, "Cigarette Smoking Man") == "Cigarette Smoking M"
        assert string.drop_right(0, "abc") == "abc"
        assert string.drop_right(-1, "abc") == "abc"
        assert string.drop_right(10, "abc") == ""


class TestChecks:
    def test_contains(self) -> None:
        assert string.contains("the", "theory")
        assert not string.contains("hat", "theory")
        assert not string.contains("THE", "theory")
        assert string.contains("", "theory")

    def test_starts_with(self) -> None:
        assert string.starts_with("the", "theory")
        assert not string.starts_with("ory", "theory")

    def test_ends_with(self) -> None:
        assert not string.ends_with("the", "theory")
        assert string.ends_with("ory", "theory")

    def test_indexes_yields_every_non_overlapping_match_start(self) -> None:
        assert string.indexes("i", "Mississippi") == (1, 4, 7, 10)
        assert string.indexes("ss", "Mississippi") == (2, 5)
        assert string.indexes("needle", "haystack") == ()
        assert string.indexes("", "abc") == ()
        assert string.indexes("aa", "aaaa") == (0, 2)

    def test_indices_is_an_alias_of_indexes(self) -> None:
        assert string.indices("i", "Mississippi") == (1, 4, 7, 10)
        assert string.indices is string.indexes


class TestIntConversions:
    def test_to_int(self) -> None:
        assert string.to_int("123") == Just(123)
        assert string.to_int("-42") == Just(-42)
        assert string.to_int("+7") == Just(7)
        assert string.to_int("0") == Just(0)
        assert string.to_int("007") == Just(7)

    def test_to_int_rejects_everything_else(self) -> None:
        for s in ("3.1", "1.5", "31a", "", " 1", "1 ", "-", "+", "0x10", "1_000", "٣"):
            assert string.to_int(s) == Nothing(), s

    def test_from_int(self) -> None:
        assert string.from_int(123) == "123"
        assert string.from_int(-42) == "-42"
        assert string.from_int(0) == "0"


class TestFloatConversions:
    def test_to_float(self) -> None:
        assert string.to_float("123") == Just(123.0)
        assert string.to_float("-42") == Just(-42.0)
        assert string.to_float("3.1") == Just(3.1)
        assert string.to_float("+1.5") == Just(1.5)
        assert string.to_float("1e3") == Just(1000.0)
        assert string.to_float("1.5E-2") == Just(0.015)

    def test_to_float_yields_a_float(self) -> None:
        result = string.to_float("123")
        assert isinstance(result, Just)
        assert isinstance(result.value, float)

    def test_to_float_rejects_everything_else(self) -> None:
        for s in (
            "31a",
            "",
            " 1",
            "1 ",
            "1\n",
            "0x10",
            "0b1",
            "0o7",
            "-",
            ".",
            "1e",
            "abc",
            "nan",
            "NaN",
            "inf",
            "infinity",
            "1_000",
        ):
            assert string.to_float(s) == Nothing(), s

    def test_to_float_accepts_js_numeric_forms_like_elm(self) -> None:
        assert string.to_float(".5") == Just(0.5)
        assert string.to_float("1.") == Just(1.0)
        assert string.to_float("Infinity") == Just(math.inf)
        assert string.to_float("-Infinity") == Just(-math.inf)

    def test_from_float_prints_like_elm(self) -> None:
        assert string.from_float(123.0) == "123"
        assert string.from_float(-42.0) == "-42"
        assert string.from_float(3.9) == "3.9"
        assert string.from_float(1.0) == "1"
        assert string.from_float(0.1 + 0.2) == "0.30000000000000004"
        assert string.from_float(0.0) == "0"
        assert string.from_float(-0.0) == "0"
        assert string.from_float(1e21) == "1e+21"
        assert string.from_float(1e20) == "100000000000000000000"
        assert string.from_float(1.5e-7) == "1.5e-7"
        assert string.from_float(0.000001) == "0.000001"
        assert string.from_float(123456789012345680000.0) == "123456789012345680000"
        assert string.from_float(math.nan) == "NaN"
        assert string.from_float(math.inf) == "Infinity"
        assert string.from_float(-math.inf) == "-Infinity"


class TestCharConversions:
    def test_from_char(self) -> None:
        assert string.from_char("a") == "a"

    def test_cons(self) -> None:
        assert string.cons("T", "he truth is out there") == "The truth is out there"
        assert string.cons("a", "") == "a"

    def test_uncons(self) -> None:
        assert string.uncons("abc") == Just(("a", "bc"))
        assert string.uncons("a") == Just(("a", ""))
        assert string.uncons("") == Nothing()
        assert string.uncons("😃x") == Just(("😃", "x"))

    def test_to_list(self) -> None:
        assert string.to_list("abc") == ("a", "b", "c")
        assert string.to_list("🙈🙉🙊") == ("🙈", "🙉", "🙊")
        assert string.to_list("") == ()

    def test_from_list(self) -> None:
        assert string.from_list(("a", "b", "c")) == "abc"
        assert string.from_list(()) == ""


class TestFormatting:
    def test_to_upper_and_to_lower(self) -> None:
        assert string.to_upper("skinner") == "SKINNER"
        assert string.to_lower("X-FILES") == "x-files"

    def test_pad_puts_the_extra_character_on_the_left(self) -> None:
        assert string.pad(5, " ", "1") == "  1  "
        assert string.pad(5, " ", "11") == "  11 "
        assert string.pad(5, " ", "121") == " 121 "
        assert string.pad(5, ".", "1") == "..1.."
        assert string.pad(5, ".", "11") == "..11."
        assert string.pad(2, ".", "12345") == "12345"

    def test_pad_left(self) -> None:
        assert string.pad_left(5, ".", "1") == "....1"
        assert string.pad_left(5, ".", "11") == "...11"
        assert string.pad_left(5, ".", "121") == "..121"
        assert string.pad_left(2, ".", "12345") == "12345"

    def test_pad_right(self) -> None:
        assert string.pad_right(5, ".", "1") == "1...."
        assert string.pad_right(5, ".", "11") == "11..."
        assert string.pad_right(5, ".", "121") == "121.."
        assert string.pad_right(2, ".", "12345") == "12345"

    def test_trim(self) -> None:
        assert string.trim("  hats  \n") == "hats"
        assert string.trim_left("  hats  \n") == "hats  \n"
        assert string.trim_right("  hats  \n") == "  hats"
        assert string.trim("") == ""
        assert (
            string.trim("\N{ZERO WIDTH NO-BREAK SPACE}\N{NO-BREAK SPACE}x\N{EM SPACE}")
            == "x"
        )

    def test_trim_keeps_control_chars_that_js_does_not_treat_as_space(self) -> None:
        assert string.trim("\x1cx\x1f") == "\x1cx\x1f"


class TestHigherOrderHelpers:
    def test_map(self) -> None:
        assert string.map(lambda c: "." if c == "/" else c, "a/b/c") == "a.b.c"
        assert string.map(str.upper, "") == ""
        assert string.map(lambda c: "!" if c == "😃" else c, "a😃b") == "a!b"

    def test_filter(self) -> None:
        assert string.filter(_is_digit, "R2-D2") == "22"
        assert string.filter(_is_digit, "") == ""

    def test_foldl_calls_f_with_char_then_acc_from_the_left(self) -> None:
        assert string.foldl(lambda c, acc: c + acc, "", "time") == "emit"
        assert string.foldl(lambda _c, acc: acc + 1, 0, "time") == 4

    def test_foldr_calls_f_with_char_then_acc_from_the_right(self) -> None:
        assert string.foldr(lambda c, acc: c + acc, "", "time") == "time"
        assert string.foldr(lambda c, acc: (*acc, c), (), "abc") == ("c", "b", "a")

    def test_any(self) -> None:
        assert string.any(_is_digit, "90210")
        assert string.any(_is_digit, "R2-D2")
        assert not string.any(_is_digit, "heart")
        assert not string.any(_is_digit, "")

    def test_all(self) -> None:
        assert string.all(_is_digit, "90210")
        assert not string.all(_is_digit, "R2-D2")
        assert not string.all(_is_digit, "heart")
        assert string.all(_is_digit, "")
