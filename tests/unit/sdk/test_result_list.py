"""Tests for morphir.sdk.result_list (Morphir.SDK.ResultList)."""

from typing import TYPE_CHECKING

from morphir.sdk import result_list
from morphir.sdk.result import Err, Ok, Result

if TYPE_CHECKING:
    from morphir.sdk.result_list import ResultList


def _is_odd(n: int) -> bool:
    return n % 2 == 1


def _odd_or_fail(n: int) -> Result[str, bool]:
    if n == 0:
        return Err("division by zero")
    return Ok(_is_odd(n))


def _divide(n: int) -> Result[str, float]:
    if n == 0:
        return Err("division by zero")
    return Ok(100 / n)


_ALL_OK: ResultList[str, int] = (Ok(1), Ok(2), Ok(3), Ok(4))
_MIXED: ResultList[str, int] = (Ok(1), Err("foo"), Ok(3), Err("bar"))
_ALL_ERR: ResultList[str, int] = (Err("foo"), Err("bar"))


class TestCreate:
    def test_from_list(self) -> None:
        assert result_list.from_list((1, 2, 3)) == (Ok(1), Ok(2), Ok(3))
        assert result_list.from_list(()) == ()

    def test_from_list_accepts_any_sequence(self) -> None:
        assert result_list.from_list([1, 2]) == (Ok(1), Ok(2))


class TestProcess:
    def test_filter(self) -> None:
        assert result_list.filter(_is_odd, (Ok(1), Ok(2), Ok(3))) == (Ok(1), Ok(3))

    def test_filter_keeps_earlier_errors(self) -> None:
        source: ResultList[str, int] = (Err("foo"), Ok(2), Ok(3))
        assert result_list.filter(_is_odd, source) == (Err("foo"), Ok(3))

    def test_filter_or_fail(self) -> None:
        source: ResultList[str, int] = (Ok(-1), Ok(0), Err("earlier"), Ok(2))
        assert result_list.filter_or_fail(_odd_or_fail, source) == (
            Ok(-1),
            Err("division by zero"),
            Err("earlier"),
        )

    def test_map(self) -> None:
        assert result_list.map(lambda n: n * 2, (Ok(1), Ok(2), Ok(3))) == (
            Ok(2),
            Ok(4),
            Ok(6),
        )

    def test_map_keeps_earlier_errors(self) -> None:
        source: ResultList[str, int] = (Err("foo"), Ok(2), Ok(3))
        assert result_list.map(lambda n: n * 2, source) == (Err("foo"), Ok(4), Ok(6))

    def test_map_or_fail(self) -> None:
        source: ResultList[str, int] = (Ok(-1), Ok(0), Err("earlier"))
        assert result_list.map_or_fail(_divide, source) == (
            Ok(-100.0),
            Err("division by zero"),
            Err("earlier"),
        )

    def test_functions_do_not_run_on_errors(self) -> None:
        calls: list[int] = []

        def spy(n: int) -> int:
            calls.append(n)
            return n

        result_list.map(spy, _MIXED)
        assert calls == [1, 3]

    def test_accepts_a_list_and_yields_a_tuple(self) -> None:
        source: list[Result[str, int]] = [Ok(1), Err("foo")]
        assert result_list.map(lambda n: n + 1, source) == (Ok(2), Err("foo"))
        assert source == [Ok(1), Err("foo")]


class TestDecompose:
    def test_errors(self) -> None:
        assert result_list.errors(_ALL_OK) == ()
        assert result_list.errors(_MIXED) == ("foo", "bar")
        assert result_list.errors(_ALL_ERR) == ("foo", "bar")

    def test_successes(self) -> None:
        assert result_list.successes(_ALL_OK) == (1, 2, 3, 4)
        assert result_list.successes(_MIXED) == (1, 3)
        assert result_list.successes(_ALL_ERR) == ()

    def test_partition(self) -> None:
        assert result_list.partition(_ALL_OK) == ((), (1, 2, 3, 4))
        assert result_list.partition(_MIXED) == (("foo", "bar"), (1, 3))
        assert result_list.partition(_ALL_ERR) == (("foo", "bar"), ())
        assert result_list.partition(()) == ((), ())


class TestToSingleResult:
    def test_keep_all_errors(self) -> None:
        assert result_list.keep_all_errors(_ALL_OK) == Ok((1, 2, 3, 4))
        assert result_list.keep_all_errors(_MIXED) == Err(("foo", "bar"))
        assert result_list.keep_all_errors(_ALL_ERR) == Err(("foo", "bar"))

    def test_keep_all_errors_of_empty_list(self) -> None:
        assert result_list.keep_all_errors(()) == Ok(())

    def test_keep_first_error(self) -> None:
        assert result_list.keep_first_error(_ALL_OK) == Ok((1, 2, 3, 4))
        assert result_list.keep_first_error(_MIXED) == Err("foo")
        assert result_list.keep_first_error(_ALL_ERR) == Err("foo")

    def test_keep_first_error_of_empty_list(self) -> None:
        assert result_list.keep_first_error(()) == Ok(())
