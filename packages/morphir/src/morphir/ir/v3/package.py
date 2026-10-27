"""V3 packages (morphir-elm ``Morphir.IR.Package``)."""

from __future__ import annotations

from dataclasses import dataclass, field

from . import module
from .access_controlled import AccessControlled
from .path import Path

type PackageName = Path


@dataclass(frozen=True)
class Specification[TA]:
    modules: dict[Path, module.Specification[TA]] = field(default_factory=dict)


@dataclass(frozen=True)
class Definition[TA, VA]:
    modules: dict[Path, AccessControlled[module.Definition[TA, VA]]] = field(
        default_factory=dict
    )
