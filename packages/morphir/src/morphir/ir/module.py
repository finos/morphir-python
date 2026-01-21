from dataclasses import dataclass, field

from . import type_def, type_spec, value
from .access_controlled import AccessControlled
from .documented import Documented
from .name import Name
from .path import Path

ModuleName = Path
QualifiedModuleName = tuple[Path, Path]


@dataclass(frozen=True)
class Specification:
    types: dict[Name, Documented[type_spec.Specification]] = field(default_factory=dict)
    values: dict[Name, Documented[value.Specification]] = field(default_factory=dict)
    doc: str | None = None


@dataclass(frozen=True)
class Definition:
    types: dict[Name, AccessControlled[Documented[type_def.Definition]]] = field(
        default_factory=dict
    )
    values: dict[Name, AccessControlled[Documented[value.Definition]]] = field(
        default_factory=dict
    )
    doc: str | None = None
