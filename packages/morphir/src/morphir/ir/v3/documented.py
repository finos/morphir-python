"""V3 documented values (morphir-elm ``Morphir.IR.Documented``)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Documented[T]:
    """A value with documentation. In v3 the documentation is always a string."""

    doc: str
    value: T
