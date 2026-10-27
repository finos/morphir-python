"""Compatibility shim: re-exports `morphir.ir.v4.type_spec`."""

from morphir.ir.v4.type_spec import (
    ConstructorArgs,
    Constructors,
    CustomTypeSpecification,
    DerivedTypeSpecification,
    DerivedTypeSpecificationDetails,
    OpaqueTypeSpecification,
    Specification,
    Type,
    TypeAliasSpecification,
)

__all__ = [
    "ConstructorArgs",
    "Constructors",
    "CustomTypeSpecification",
    "DerivedTypeSpecification",
    "DerivedTypeSpecificationDetails",
    "OpaqueTypeSpecification",
    "Specification",
    "Type",
    "TypeAliasSpecification",
]
