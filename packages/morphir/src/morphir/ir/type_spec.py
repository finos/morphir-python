from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from .fqname import FQName
from .name import Name
from .type import Type

ConstructorArgs = list[tuple[Name, Type]]
Constructors = dict[Name, ConstructorArgs]


@dataclass(frozen=True)
class TypeAliasSpecification:
    """Specification for a type alias."""
    type_params: list[Name]
    tpe: Type


@dataclass(frozen=True)
class OpaqueTypeSpecification:
    """Specification for an opaque type."""
    type_params: list[Name]


@dataclass(frozen=True)
class CustomTypeSpecification:
    """Specification for a custom type (ADT)."""
    type_params: list[Name]
    constructors: Constructors


@dataclass(frozen=True)
class DerivedTypeSpecificationDetails:
    """Details for a derived type."""
    base_type: Type
    from_base_type: FQName
    to_base_type: FQName


@dataclass(frozen=True)
class DerivedTypeSpecification:
    """Specification for a derived type."""
    type_params: list[Name]
    details: DerivedTypeSpecificationDetails


Specification = Union[
    TypeAliasSpecification,
    OpaqueTypeSpecification,
    CustomTypeSpecification,
    DerivedTypeSpecification,
]
