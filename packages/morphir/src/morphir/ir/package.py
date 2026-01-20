from dataclasses import dataclass, field
from typing import Dict
from .path import Path
from .access_controlled import AccessControlled
from . import module

PackageName = Path

@dataclass(frozen=True)
class Specification:
    modules: Dict[module.ModuleName, module.Specification] = field(default_factory=dict)

@dataclass(frozen=True)
class Definition:
    modules: Dict[module.ModuleName, AccessControlled[module.Definition]] = field(default_factory=dict)
