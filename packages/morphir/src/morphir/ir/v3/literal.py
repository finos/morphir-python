"""V3 literals (morphir-elm ``Morphir.IR.Literal``)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


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
class WholeNumberLiteral:
    value: int


@dataclass(frozen=True)
class FloatLiteral:
    value: float


@dataclass(frozen=True)
class DecimalLiteral:
    value: Decimal


type Literal = (
    BoolLiteral
    | CharLiteral
    | StringLiteral
    | WholeNumberLiteral
    | FloatLiteral
    | DecimalLiteral
)
