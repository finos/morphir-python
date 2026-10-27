from dataclasses import dataclass
from typing import Union

from .access_controlled import AccessControlled
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


Definition = Union[TypeAliasDefinition, CustomTypeDefinition]
