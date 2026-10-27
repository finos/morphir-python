"""V3 fully qualified names (morphir-elm ``Morphir.IR.FQName``)."""

from __future__ import annotations

from dataclasses import dataclass

from . import name, path
from .name import Name
from .path import Path


@dataclass(frozen=True)
class FQName:
    """A package path, a module path, and a local name."""

    package_path: Path
    module_path: Path
    local_name: Name


def fqn(package: str, module: str, local: str) -> FQName:
    """Build an FQName from strings, as elm ``FQName.fqn`` does.

    Example:
        >>> fqn("Morphir.SDK", "Basics", "Int").local_name
        ('int',)
    """
    return FQName(
        path.from_string(package), path.from_string(module), name.from_string(local)
    )
