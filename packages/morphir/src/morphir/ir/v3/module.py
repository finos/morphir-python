"""V3 modules (morphir-elm ``Morphir.IR.Module``)."""

from __future__ import annotations

from dataclasses import dataclass, field

from . import type as t
from . import value as v
from .access_controlled import AccessControlled
from .documented import Documented
from .name import Name
from .path import Path

type ModuleName = Path


@dataclass(frozen=True)
class Specification[TA]:
    types: dict[Name, Documented[t.Specification[TA]]] = field(default_factory=dict)
    values: dict[Name, Documented[v.Specification[TA]]] = field(default_factory=dict)
    doc: str | None = None


@dataclass(frozen=True)
class Definition[TA, VA]:
    types: dict[Name, AccessControlled[Documented[t.Definition[TA]]]] = field(
        default_factory=dict
    )
    values: dict[Name, AccessControlled[Documented[v.Definition[TA, VA]]]] = field(
        default_factory=dict
    )
    doc: str | None = None
