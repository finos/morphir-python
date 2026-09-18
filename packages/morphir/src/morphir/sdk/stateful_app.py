"""Morphir.SDK.StatefulApp: the model of a stateful application.

A `StatefulApp` holds one function, the business logic. The function gets the
current state (`Nothing` when there is no state yet) and a command. It yields
the new state (`Nothing` to delete the state) and an event:

    >>> from morphir.sdk.maybe import Just, Maybe, Nothing
    >>> from morphir.sdk.stateful_app import StatefulApp
    >>> def logic(state: Maybe[int], command: str) -> tuple[Maybe[int], str]:
    ...     total = (state.value if isinstance(state, Just) else 0) + 1
    ...     return (Just(total), f"{command}: {total}")
    >>> app: StatefulApp[str, str, int, str] = StatefulApp(logic)
    >>> app.logic(Nothing(), "open")
    (Just(value=1), 'open: 1')

The module has a type and no functions, as in Elm.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from morphir.sdk.maybe import (
    Maybe,  # noqa: TC001 - the dataclass field annotation needs it at run time
)

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["StatefulApp"]


@dataclass(frozen=True, slots=True)
class StatefulApp[K, C, S, E]:
    """A stateful application (Elm `StatefulApp (Maybe s -> c -> ( Maybe s, e ))`).

    The type parameters fit the application to a use case:

    * `K`: the key that partitions commands, events and state. No field uses
      it, as in Elm; it is there for the type checker only.
    * `C`: the commands that the application accepts.
    * `S`: the state that the application manages.
    * `E`: the events that the application publishes.

    Attributes:
        logic: The business logic. It gets the current state and a command, and
            yields the new state and an event.
    """

    logic: Callable[[Maybe[S], C], tuple[Maybe[S], E]]
