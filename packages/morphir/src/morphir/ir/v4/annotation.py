"""Annotations on v4 specifications.

Follows the finos/morphir v4 schema (``Annotation``, ``AnnotationArgument``) at
the pinned commit and the morphir-rust v4 model. An annotation keeps the form it
was written in, because the kit writes an argument-less structured annotation as
an object and a compact one as a string. Annotations belong to specifications,
the public face; definitions carry none.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union

from .fqname import FQName
from .name import Name
from .value import Value


@dataclass(frozen=True)
class PositionalArgument:
    """An annotation argument written on its own.

    Attributes:
        value: The argument expression.
    """

    value: Value


@dataclass(frozen=True)
class NamedArgument:
    """An annotation argument written under the name it answers to.

    Attributes:
        name: The parameter name.
        value: The argument expression.
    """

    name: Name
    value: Value


AnnotationArgument = Union[PositionalArgument, NamedArgument]
"""A positional or named annotation argument."""


@dataclass(frozen=True)
class CompactAnnotation:
    """The compact spelling: ``"pkg:mod#name"`` or ``"pkg:mod#name:text"``.

    Attributes:
        name: The annotation type.
        text: The free text after the first colon after ``#``, if any.
    """

    name: FQName
    text: str | None = None


@dataclass(frozen=True)
class StructuredAnnotation:
    """The structured spelling: ``{"name": ..., "arguments": [...]}``.

    Attributes:
        name: The annotation type.
        arguments: Positional and named arguments, in order.
    """

    name: FQName
    arguments: list[AnnotationArgument] = field(default_factory=list)


Annotation = Union[CompactAnnotation, StructuredAnnotation]
"""An annotation on a module, type or value specification."""
