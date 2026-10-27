"""V3 distributions (morphir-elm ``Morphir.IR.Distribution``).

Format 3.0.0 has only the ``Library`` distribution. Type attributes are unit
(``None``) and value attributes are the value's type. There is no package release
version.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import package
from .path import Path
from .type import Type

type TypedValueAttributes = Type[None]


@dataclass(frozen=True)
class Library:
    """A format-3 library: a package name, dependencies, and a definition."""

    package_name: Path
    definition: package.Definition[None, Type[None]]
    dependencies: dict[Path, package.Specification[None]] = field(default_factory=dict)


type Distribution = Library
