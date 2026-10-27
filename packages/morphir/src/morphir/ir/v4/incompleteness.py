"""Incompleteness: why a type or value definition is not complete yet.

Follows the finos/morphir v4 schema (``Incompleteness``, ``HoleReason``) at the
pinned commit and the morphir-rust v4 model. A hole names its reason; a draft is
work in progress and names none.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from .fqname import FQName
from .type import Type


@dataclass(frozen=True)
class UnresolvedReference:
    """A reference that could not be resolved.

    Attributes:
        target: The name that did not resolve.
    """

    target: FQName


@dataclass(frozen=True)
class DeletedDuringRefactor:
    """A reference removed by a refactoring.

    Attributes:
        tx_id: The transaction id of the refactoring (JSON member ``tx-id``).
    """

    tx_id: str


@dataclass(frozen=True)
class TypeMismatch:
    """Type checking failed.

    Attributes:
        expected: A description of the expected type.
        found: A description of the type found.
    """

    expected: str
    found: str


HoleReason = Union[UnresolvedReference, DeletedDuringRefactor, TypeMismatch]
"""Why a hole exists. ``Draft`` is an incompleteness, not a hole reason."""


@dataclass(frozen=True)
class HoleIncompleteness:
    """A definition with a hole.

    Attributes:
        reason: Why the hole exists.
        partial_body: The type the author had written when the definition stopped
            being complete, if any. The schema gives this member the type
            ``Type``; an incomplete value keeps its partial expression on
            `IncompleteBody.partial_body` instead.
    """

    reason: HoleReason
    partial_body: Type | None = None


@dataclass(frozen=True)
class DraftIncompleteness:
    """A definition the author marked as work in progress."""


Incompleteness = Union[HoleIncompleteness, DraftIncompleteness]
"""Why a definition is incomplete: a hole or a draft."""
