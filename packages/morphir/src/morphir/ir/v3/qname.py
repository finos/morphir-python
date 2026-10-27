"""V3 qualified names (morphir-elm ``Morphir.IR.QName``)."""

from __future__ import annotations

from dataclasses import dataclass

from .name import Name
from .path import Path


@dataclass(frozen=True)
class QName:
    """A module path and a local name."""

    module_path: Path
    local_name: Name
