"""V3 distributions (morphir-elm ``Morphir.IR.Distribution``).

Format 3.0.0 has only the ``Library`` distribution. Format 3.1.0 adds ``Specs``,
which publishes a package's specification without its definitions (finos/morphir
decision record 0018). Type attributes are unit (``None``) and value attributes
are the value's type. There is no package release version.
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


@dataclass(frozen=True)
class Specs:
    """A format-3.1.0 Specs distribution: a package's public face.

    It has the shape of a `Library`, with a package specification in place of the
    package definition. Writers declare ``formatVersion`` ``"3.1.0"`` for it.
    """

    package_name: Path
    specification: package.Specification[None]
    dependencies: dict[Path, package.Specification[None]] = field(default_factory=dict)


type Distribution = Library | Specs
