from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar, Union


@dataclass(frozen=True)
class DefRef:
    """Shorthand reference to an entry in $defs."""

    name: str


@dataclass(frozen=True)
class PointerRef:
    """Full JSON Pointer reference."""

    pointer: list[str]

    @staticmethod
    def from_string(pointer_str: str) -> PointerRef:
        if pointer_str.startswith("#/"):
            # Remove #/ and split
            path = pointer_str[2:].split("/")
            return PointerRef(pointer=path)
        raise ValueError(f"Invalid pointer string: {pointer_str}")


Ref = Union[DefRef, PointerRef]

T = TypeVar("T")


@dataclass(frozen=True)
class FileWithDefs(Generic[T]):
    content: T
    defs: dict[str, Any] = field(default_factory=dict)
