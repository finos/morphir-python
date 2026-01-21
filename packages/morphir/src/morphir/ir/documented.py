from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Documented(Generic[T]):
    doc: str | None
    value: T
