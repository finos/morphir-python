"""V3 types (morphir-elm ``Morphir.IR.Type``).

Every node is parameterized by its attribute type ``A``. A distribution fixes
``A`` to ``None``, which is elm's unit ``()``.
"""

from __future__ import annotations

from dataclasses import dataclass

from .access_controlled import AccessControlled
from .fqname import FQName
from .name import Name


@dataclass(frozen=True)
class Variable[A]:
    attributes: A
    name: Name


@dataclass(frozen=True)
class Reference[A]:
    attributes: A
    fqname: FQName
    args: tuple[Type[A], ...] = ()


@dataclass(frozen=True)
class Tuple[A]:
    attributes: A
    elements: tuple[Type[A], ...] = ()


@dataclass(frozen=True)
class Record[A]:
    attributes: A
    fields: tuple[Field[A], ...] = ()


@dataclass(frozen=True)
class ExtensibleRecord[A]:
    attributes: A
    variable: Name
    fields: tuple[Field[A], ...] = ()


@dataclass(frozen=True)
class Function[A]:
    attributes: A
    argument_type: Type[A]
    return_type: Type[A]


@dataclass(frozen=True)
class Unit[A]:
    attributes: A


type Type[A] = (
    Variable[A]
    | Reference[A]
    | Tuple[A]
    | Record[A]
    | ExtensibleRecord[A]
    | Function[A]
    | Unit[A]
)


@dataclass(frozen=True)
class Field[A]:
    name: Name
    tpe: Type[A]


type ConstructorArgs[A] = tuple[tuple[Name, Type[A]], ...]
type Constructors[A] = dict[Name, ConstructorArgs[A]]


@dataclass(frozen=True)
class TypeAliasSpecification[A]:
    type_params: tuple[Name, ...]
    tpe: Type[A]


@dataclass(frozen=True)
class OpaqueTypeSpecification:
    type_params: tuple[Name, ...]


@dataclass(frozen=True)
class CustomTypeSpecification[A]:
    type_params: tuple[Name, ...]
    constructors: Constructors[A]


@dataclass(frozen=True)
class DerivedTypeSpecification[A]:
    type_params: tuple[Name, ...]
    base_type: Type[A]
    from_base_type: FQName
    to_base_type: FQName


type Specification[A] = (
    TypeAliasSpecification[A]
    | OpaqueTypeSpecification
    | CustomTypeSpecification[A]
    | DerivedTypeSpecification[A]
)


@dataclass(frozen=True)
class TypeAliasDefinition[A]:
    type_params: tuple[Name, ...]
    tpe: Type[A]


@dataclass(frozen=True)
class CustomTypeDefinition[A]:
    type_params: tuple[Name, ...]
    constructors: AccessControlled[Constructors[A]]


type Definition[A] = TypeAliasDefinition[A] | CustomTypeDefinition[A]
