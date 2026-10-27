"""V3 access control (morphir-elm ``Morphir.IR.AccessControlled``)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Access(Enum):
    """Whether a member is visible outside its module or package."""

    PUBLIC = "Public"
    PRIVATE = "Private"


@dataclass(frozen=True)
class AccessControlled[T]:
    """A value with an access level, encoded as ``{"access", "value"}``."""

    access: Access
    value: T


def public[T](value: T) -> AccessControlled[T]:
    """Wrap a value as public."""
    return AccessControlled(Access.PUBLIC, value)


def private[T](value: T) -> AccessControlled[T]:
    """Wrap a value as private."""
    return AccessControlled(Access.PRIVATE, value)
