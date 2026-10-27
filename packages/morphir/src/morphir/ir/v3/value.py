"""V3 values and patterns (morphir-elm ``Morphir.IR.Value``).

Values take two attribute parameters, as in elm: ``TA`` for the types inside
definitions and ``VA`` for value and pattern nodes. A distribution fixes ``TA`` to
``None`` and ``VA`` to ``Type[None]``.
"""

from __future__ import annotations

from dataclasses import dataclass

from .fqname import FQName
from .literal import Literal
from .name import Name
from .type import Type

# --- Patterns ---


@dataclass(frozen=True)
class WildcardPattern[A]:
    attributes: A


@dataclass(frozen=True)
class AsPattern[A]:
    attributes: A
    pattern: Pattern[A]
    name: Name


@dataclass(frozen=True)
class TuplePattern[A]:
    attributes: A
    elements: tuple[Pattern[A], ...]


@dataclass(frozen=True)
class ConstructorPattern[A]:
    attributes: A
    constructor: FQName
    args: tuple[Pattern[A], ...]


@dataclass(frozen=True)
class EmptyListPattern[A]:
    attributes: A


@dataclass(frozen=True)
class HeadTailPattern[A]:
    attributes: A
    head: Pattern[A]
    tail: Pattern[A]


@dataclass(frozen=True)
class LiteralPattern[A]:
    attributes: A
    literal: Literal


@dataclass(frozen=True)
class UnitPattern[A]:
    attributes: A


type Pattern[A] = (
    WildcardPattern[A]
    | AsPattern[A]
    | TuplePattern[A]
    | ConstructorPattern[A]
    | EmptyListPattern[A]
    | HeadTailPattern[A]
    | LiteralPattern[A]
    | UnitPattern[A]
)

# --- Values ---


@dataclass(frozen=True)
class LiteralValue[TA, VA]:
    attributes: VA
    literal: Literal


@dataclass(frozen=True)
class Constructor[TA, VA]:
    attributes: VA
    fqname: FQName


@dataclass(frozen=True)
class Tuple[TA, VA]:
    attributes: VA
    elements: tuple[Value[TA, VA], ...]


@dataclass(frozen=True)
class List[TA, VA]:
    attributes: VA
    items: tuple[Value[TA, VA], ...]


@dataclass(frozen=True)
class Record[TA, VA]:
    attributes: VA
    fields: dict[Name, Value[TA, VA]]


@dataclass(frozen=True)
class Variable[TA, VA]:
    attributes: VA
    name: Name


@dataclass(frozen=True)
class Reference[TA, VA]:
    attributes: VA
    fqname: FQName


@dataclass(frozen=True)
class Field[TA, VA]:
    attributes: VA
    subject: Value[TA, VA]
    field_name: Name


@dataclass(frozen=True)
class FieldFunction[TA, VA]:
    attributes: VA
    name: Name


@dataclass(frozen=True)
class Apply[TA, VA]:
    attributes: VA
    function: Value[TA, VA]
    argument: Value[TA, VA]


@dataclass(frozen=True)
class Lambda[TA, VA]:
    attributes: VA
    pattern: Pattern[VA]
    body: Value[TA, VA]


@dataclass(frozen=True)
class LetDefinition[TA, VA]:
    attributes: VA
    name: Name
    definition: Definition[TA, VA]
    in_value: Value[TA, VA]


@dataclass(frozen=True)
class LetRecursion[TA, VA]:
    attributes: VA
    definitions: dict[Name, Definition[TA, VA]]
    in_value: Value[TA, VA]


@dataclass(frozen=True)
class Destructure[TA, VA]:
    attributes: VA
    pattern: Pattern[VA]
    value_to_destructure: Value[TA, VA]
    in_value: Value[TA, VA]


@dataclass(frozen=True)
class IfThenElse[TA, VA]:
    attributes: VA
    condition: Value[TA, VA]
    then_branch: Value[TA, VA]
    else_branch: Value[TA, VA]


@dataclass(frozen=True)
class PatternMatch[TA, VA]:
    attributes: VA
    branch_on: Value[TA, VA]
    cases: tuple[tuple[Pattern[VA], Value[TA, VA]], ...]


@dataclass(frozen=True)
class UpdateRecord[TA, VA]:
    attributes: VA
    value_to_update: Value[TA, VA]
    fields: dict[Name, Value[TA, VA]]


@dataclass(frozen=True)
class Unit[TA, VA]:
    attributes: VA


type Value[TA, VA] = (
    LiteralValue[TA, VA]
    | Constructor[TA, VA]
    | Tuple[TA, VA]
    | List[TA, VA]
    | Record[TA, VA]
    | Variable[TA, VA]
    | Reference[TA, VA]
    | Field[TA, VA]
    | FieldFunction[TA, VA]
    | Apply[TA, VA]
    | Lambda[TA, VA]
    | LetDefinition[TA, VA]
    | LetRecursion[TA, VA]
    | Destructure[TA, VA]
    | IfThenElse[TA, VA]
    | PatternMatch[TA, VA]
    | UpdateRecord[TA, VA]
    | Unit[TA, VA]
)

# --- Specifications and definitions ---


@dataclass(frozen=True)
class Specification[TA]:
    inputs: tuple[tuple[Name, Type[TA]], ...]
    output: Type[TA]


@dataclass(frozen=True)
class Definition[TA, VA]:
    input_types: tuple[tuple[Name, VA, Type[TA]], ...]
    output_type: Type[TA]
    body: Value[TA, VA]
