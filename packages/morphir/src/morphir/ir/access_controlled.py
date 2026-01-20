from dataclasses import dataclass
from typing import Generic, TypeVar, Union

T = TypeVar("T")

@dataclass(frozen=True)
class Public(Generic[T]):
    value: T

@dataclass(frozen=True)
class Private(Generic[T]):
    value: T

AccessControlled = Union[Public[T], Private[T]]
