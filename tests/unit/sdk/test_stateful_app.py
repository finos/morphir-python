"""Tests for morphir.sdk.stateful_app (Morphir.SDK.StatefulApp)."""

import dataclasses

import pytest

from morphir.sdk.maybe import Just, Maybe, Nothing
from morphir.sdk.stateful_app import StatefulApp


def _counter(state: Maybe[int], command: str) -> tuple[Maybe[int], str]:
    current = state.value if isinstance(state, Just) else 0
    if command == "reset":
        return (Nothing(), "was reset")
    return (Just(current + 1), f"now {current + 1}")


class TestStatefulApp:
    def test_holds_the_logic(self) -> None:
        app: StatefulApp[str, str, int, str] = StatefulApp(_counter)
        assert app.logic(Nothing(), "inc") == (Just(1), "now 1")
        assert app.logic(Just(4), "inc") == (Just(5), "now 5")
        assert app.logic(Just(4), "reset") == (Nothing(), "was reset")

    def test_matches_as_a_pattern(self) -> None:
        app: StatefulApp[str, str, int, str] = StatefulApp(_counter)
        match app:
            case StatefulApp(logic):
                assert logic is _counter

    def test_is_frozen(self) -> None:
        app: StatefulApp[str, str, int, str] = StatefulApp(_counter)
        with pytest.raises(dataclasses.FrozenInstanceError):
            app.logic = _counter  # type: ignore[misc]

    def test_equal_when_the_logic_is_the_same_function(self) -> None:
        assert StatefulApp(_counter) == StatefulApp(_counter)
