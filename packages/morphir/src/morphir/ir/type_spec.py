from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Union
from .name import Name
from .fqname import FQName
from .type import Type

ConstructorArgs = List[Tuple[Name, Type]]
Constructors = Dict[Name, ConstructorArgs]

@dataclass(frozen=True)
class TypeAliasSpecification:
    type_params: List[Name]
    tpe: Type

@dataclass(frozen=True)
class OpaqueTypeSpecification:
    type_params: List[Name]

@dataclass(frozen=True)
class CustomTypeSpecification:
    type_params: List[Name]
    constructors: Constructors

@dataclass(frozen=True)
class DerivedTypeSpecificationDetails:
    base_type: Type
    from_base_type: FQName
    to_base_type: FQName

@dataclass(frozen=True)
class DerivedTypeSpecification:
    type_params: List[Name]
    details: DerivedTypeSpecificationDetails

Specification = Union[
    TypeAliasSpecification,
    OpaqueTypeSpecification,
    CustomTypeSpecification,
    DerivedTypeSpecification
]
