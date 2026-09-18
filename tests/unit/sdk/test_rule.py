"""Tests for morphir.sdk.rule (Morphir.SDK.Rule)."""

import pytest

from morphir.sdk import rule
from morphir.sdk.maybe import Just, Maybe, Nothing


def _never(_: int) -> Maybe[int]:
    return Nothing()


def _identity(a: int) -> Maybe[int]:
    return Just(a)


def _double(a: int) -> Maybe[int]:
    return Just(a * 2)


class TestChain:
    def test_first_match_wins(self) -> None:
        my_chain = rule.chain((_never, _identity))
        assert my_chain(42) == Just(42)

    def test_rules_run_in_order(self) -> None:
        assert rule.chain((_double, _identity))(21) == Just(42)
        assert rule.chain((_identity, _double))(21) == Just(21)

    def test_no_match_is_nothing(self) -> None:
        assert rule.chain((_never, _never))(1) == Nothing()

    def test_no_rules_is_nothing(self) -> None:
        no_rules: tuple[rule.Rule[int, int], ...] = ()
        assert rule.chain(no_rules)(1) == Nothing()

    def test_rules_after_the_match_do_not_run(self) -> None:
        calls: list[int] = []

        def spy(a: int) -> Maybe[int]:
            calls.append(a)
            return Nothing()

        assert rule.chain([_identity, spy])(7) == Just(7)
        assert calls == []

    def test_decision_table(self) -> None:
        def table(row: tuple[str, int]) -> Maybe[str]:
            kind, size = row
            if rule.is_("a", kind) and rule.any(size):
                return Just("is a")
            if rule.any_of(("b", "c"), kind) and rule.none_of((0,), size):
                return Just("b or c, not empty")
            return Nothing()

        chained = rule.chain((table, lambda _: Just("other")))
        assert chained(("a", 0)) == Just("is a")
        assert chained(("c", 3)) == Just("b or c, not empty")
        assert chained(("c", 0)) == Just("other")


class TestMatchers:
    def test_any_is_always_true(self) -> None:
        assert rule.any(1) is True
        assert rule.any("x") is True
        assert rule.any(Nothing()) is True

    def test_is(self) -> None:
        assert rule.is_(1, 1) is True
        assert rule.is_(1, 2) is False

    def test_is_is_structural(self) -> None:
        assert rule.is_((1, Just("a")), (1, Just("a"))) is True
        assert rule.is_((1, Just("a")), (1, Just("b"))) is False

    def test_is_fails_on_functions(self) -> None:
        with pytest.raises(TypeError):
            rule.is_(_never, _never)

    def test_any_of(self) -> None:
        assert rule.any_of((1, 2, 3), 2) is True
        assert rule.any_of((1, 2, 3), 4) is False
        assert rule.any_of((), 4) is False
        assert rule.any_of([(1, "a")], (1, "a")) is True

    def test_none_of(self) -> None:
        assert rule.none_of((1, 2, 3), 2) is False
        assert rule.none_of((1, 2, 3), 4) is True
        assert rule.none_of((), 4) is True
