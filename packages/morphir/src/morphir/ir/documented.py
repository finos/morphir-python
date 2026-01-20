from dataclasses import dataclass
from typing import Generic, TypeVar, Optional

T = TypeVar("T")

@dataclass(frozen=True)
class Documented(Generic[T]):
    doc: Optional[str]
    value: T
