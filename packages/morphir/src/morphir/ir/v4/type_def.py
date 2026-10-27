from dataclasses import dataclass
from typing import Union

from .access_controlled import AccessControlled
from .incompleteness import Incompleteness
from .name import Name
from .type import Type
from .type_spec import Constructors


@dataclass(frozen=True)
class TypeAliasDefinition:
    type_params: list[Name]
    tpe: Type


@dataclass(frozen=True)
class CustomTypeDefinition:
    type_params: list[Name]
    constructors: AccessControlled[Constructors]


@dataclass(frozen=True)
class IncompleteTypeDefinition:
    """A type definition that is not complete yet.

    Attributes:
        type_params: The declared type parameters.
        incompleteness: Why the definition is incomplete.
        partial_type_exp: The type expression written so far, if any.
    """

    type_params: list[Name]
    incompleteness: Incompleteness
    partial_type_exp: Type | None = None


Definition = Union[TypeAliasDefinition, CustomTypeDefinition, IncompleteTypeDefinition]
