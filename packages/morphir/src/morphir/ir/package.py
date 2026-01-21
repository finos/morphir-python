from dataclasses import dataclass, field

from . import module
from .access_controlled import AccessControlled
from .path import Path

PackageName = Path


@dataclass(frozen=True)
class Specification:
    modules: dict[module.ModuleName, module.Specification] = field(default_factory=dict)


@dataclass(frozen=True)
class Definition:
    modules: dict[module.ModuleName, AccessControlled[module.Definition]] = field(
        default_factory=dict
    )
