"""Tests for morphir.sdk.tuple (Morphir.SDK.Tuple)."""

from morphir.sdk import tuple as tuple_


class TestTuple:
    def test_pair(self) -> None:
        assert tuple_.pair(3, "a") == (3, "a")

    def test_first_and_second(self) -> None:
        assert tuple_.first((3, "a")) == 3
        assert tuple_.second((3, "a")) == "a"

    def test_map_first(self) -> None:
        assert tuple_.map_first(str.upper, ("stressed", 16)) == ("STRESSED", 16)

    def test_map_second(self) -> None:
        assert tuple_.map_second(lambda n: n + 1, ("stressed", 16)) == ("stressed", 17)

    def test_map_both(self) -> None:
        assert tuple_.map_both(str.upper, lambda n: n + 1, ("stressed", 16)) == (
            "STRESSED",
            17,
        )
