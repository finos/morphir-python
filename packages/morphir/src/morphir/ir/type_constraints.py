"""Compatibility shim: re-exports `morphir.ir.v4.type_constraints`."""

from morphir.ir.v4.type_constraints import (
    Bounded,
    CollectionConstraint,
    CustomConstraint,
    Decimal,
    FloatingPoint,
    FloatWidth,
    IntWidth,
    NumericConstraint,
    Signed,
    StringConstraint,
    StringEncoding,
    TypeConstraints,
    Unsigned,
)

__all__ = [
    "Bounded",
    "CollectionConstraint",
    "CustomConstraint",
    "Decimal",
    "FloatWidth",
    "FloatingPoint",
    "IntWidth",
    "NumericConstraint",
    "Signed",
    "StringConstraint",
    "StringEncoding",
    "TypeConstraints",
    "Unsigned",
]
