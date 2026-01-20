from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional
from .name import Name
from .path import Path
from .documented import Documented
from .access_controlled import AccessControlled
from . import type_spec, type_def, value

ModuleName = Path
QualifiedModuleName = Tuple[Path, Path]

@dataclass(frozen=True)
class Specification:
    types: Dict[Name, Documented[type_spec.Specification]] = field(default_factory=dict)
    values: Dict[Name, Documented[value.Specification]] = field(default_factory=dict)
    doc: Optional[str] = None

@dataclass(frozen=True)
class Definition:
    types: Dict[Name, AccessControlled[Documented[type_def.Definition]]] = field(default_factory=dict)
    values: Dict[Name, AccessControlled[Documented[value.Definition]]] = field(default_factory=dict)
    doc: Optional[str] = None
