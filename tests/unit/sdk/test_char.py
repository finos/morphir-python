"""Tests for morphir.sdk.char (Morphir.SDK.Char)."""

from morphir.sdk import char


class TestClassification:
    def test_is_upper(self) -> None:
        assert char.is_upper("A")
        assert char.is_upper("Z")
        assert not char.is_upper("a")
        assert not char.is_upper("0")
        assert not char.is_upper("Σ")

    def test_is_lower(self) -> None:
        assert char.is_lower("a")
        assert char.is_lower("z")
        assert not char.is_lower("A")
        assert not char.is_lower("π")

    def test_is_alpha(self) -> None:
        assert char.is_alpha("a")
        assert char.is_alpha("B")
        assert not char.is_alpha("1")
        assert not char.is_alpha("é")

    def test_is_alpha_num(self) -> None:
        assert char.is_alpha_num("a")
        assert char.is_alpha_num("Z")
        assert char.is_alpha_num("7")
        assert not char.is_alpha_num("-")
        assert not char.is_alpha_num("π")

    def test_is_digit_is_ascii_only(self) -> None:
        assert char.is_digit("0")
        assert char.is_digit("9")
        assert not char.is_digit("a")
        assert not char.is_digit("٣")

    def test_is_oct_digit(self) -> None:
        assert char.is_oct_digit("0")
        assert char.is_oct_digit("7")
        assert not char.is_oct_digit("8")
        assert not char.is_oct_digit("a")

    def test_is_hex_digit(self) -> None:
        assert char.is_hex_digit("0")
        assert char.is_hex_digit("a")
        assert char.is_hex_digit("F")
        assert not char.is_hex_digit("g")
        assert not char.is_hex_digit("G")

    def test_predicates_reject_strings_that_are_not_one_char(self) -> None:
        assert not char.is_upper("")
        assert not char.is_digit("12")
        assert not char.is_alpha("ab")


class TestConversion:
    def test_case(self) -> None:
        assert char.to_upper("a") == "A"
        assert char.to_upper("A") == "A"
        assert char.to_lower("A") == "a"
        assert char.to_locale_upper("z") == "Z"
        assert char.to_locale_lower("Z") == "z"
        assert char.to_upper("1") == "1"

    def test_to_code(self) -> None:
        assert char.to_code("A") == 65
        assert char.to_code("B") == 66
        assert char.to_code("木") == 0x6728
        assert char.to_code("😃") == 0x1F603

    def test_from_code(self) -> None:
        assert char.from_code(65) == "A"
        assert char.from_code(0x6728) == "木"
        assert char.from_code(0x1F603) == "😃"

    def test_from_code_outside_unicode_yields_replacement_char(self) -> None:
        assert char.from_code(-1) == "\N{REPLACEMENT CHARACTER}"
        assert char.from_code(0x110000) == "\N{REPLACEMENT CHARACTER}"

    def test_round_trip(self) -> None:
        for c in ("a", "Z", "0", "木", "😃"):
            assert char.from_code(char.to_code(c)) == c
