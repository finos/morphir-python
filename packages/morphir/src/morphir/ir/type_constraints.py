from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Literal, Union

from .fqname import FQName

# Numeric Constraints
IntWidth = Literal[8, 16, 32, 64]
FloatWidth = Literal[32, 64]


@dataclass(frozen=True)
class Signed:
    bits: IntWidth


@dataclass(frozen=True)
class Unsigned:
    bits: IntWidth


@dataclass(frozen=True)
class FloatingPoint:
    bits: FloatWidth


@dataclass(frozen=True)
class Bounded:
    min: int | None = None
    max: int | None = None


@dataclass(frozen=True)
class Decimal:
    precision: int
    scale: int


NumericConstraint = Union[Signed, Unsigned, FloatingPoint, Bounded, Decimal]


# String Constraints
class StringEncoding(Enum):
    UTF8 = auto()
    UTF16 = auto()
    ASCII = auto()
    LATIN1 = auto()


@dataclass(frozen=True)
class StringConstraint:
    encoding: StringEncoding | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None


# Collection Constraints
@dataclass(frozen=True)
class CollectionConstraint:
    min_length: int | None = None
    max_length: int | None = None
    unique_items: bool = False


# Custom Constraints
# We use 'Any' for arguments to avoid circular dependency with Value for now
# Ideally this should be Value, but Value depends on Type (sometimes)
from typing import Any


@dataclass(frozen=True)
class CustomConstraint:
    predicate: FQName
    arguments: list[Any]


@dataclass(frozen=True)
class TypeConstraints:
    numeric: NumericConstraint | None = None
    string: StringConstraint | None = None
    collection: CollectionConstraint | None = None
    custom: list[CustomConstraint] = field(default_factory=list)
