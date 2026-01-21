from dataclasses import dataclass
from decimal import Decimal
from typing import Union

from .document import Document


@dataclass(frozen=True)
class BoolLiteral:
    value: bool


@dataclass(frozen=True)
class CharLiteral:
    value: str


@dataclass(frozen=True)
class StringLiteral:
    value: str


@dataclass(frozen=True)
class IntegerLiteral:
    value: int


@dataclass(frozen=True)
class FloatLiteral:
    value: float


@dataclass(frozen=True)
class DecimalLiteral:
    value: Decimal


@dataclass(frozen=True)
class DocumentLiteral:
    value: Document


Literal = Union[
    BoolLiteral,
    CharLiteral,
    StringLiteral,
    IntegerLiteral,
    FloatLiteral,
    DecimalLiteral,
    DocumentLiteral,
]
