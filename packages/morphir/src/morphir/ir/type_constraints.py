from dataclasses import dataclass, field
from typing import Optional, Literal, List, Union
from enum import Enum, auto
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
    min: Optional[int] = None
    max: Optional[int] = None

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
    encoding: Optional[StringEncoding] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None

# Collection Constraints
@dataclass(frozen=True)
class CollectionConstraint:
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    unique_items: bool = False

# Custom Constraints
# We use 'Any' for arguments to avoid circular dependency with Value for now
# Ideally this should be Value, but Value depends on Type (sometimes)
from typing import Any
@dataclass(frozen=True)
class CustomConstraint:
    predicate: FQName
    arguments: List[Any]

@dataclass(frozen=True)
class TypeConstraints:
    numeric: Optional[NumericConstraint] = None
    string: Optional[StringConstraint] = None
    collection: Optional[CollectionConstraint] = None
    custom: List[CustomConstraint] = field(default_factory=list)
