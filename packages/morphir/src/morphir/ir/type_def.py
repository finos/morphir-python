from dataclasses import dataclass
from typing import List, Union
from .name import Name
from .type import Type
from .type_spec import Constructors
from .access_controlled import AccessControlled

@dataclass(frozen=True)
class TypeAliasDefinition:
    type_params: List[Name]
    tpe: Type

@dataclass(frozen=True)
class CustomTypeDefinition:
    type_params: List[Name]
    constructors: AccessControlled[Constructors]

Definition = Union[TypeAliasDefinition, CustomTypeDefinition]
