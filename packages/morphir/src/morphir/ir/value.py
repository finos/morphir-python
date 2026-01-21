from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Union
from typing import List as TList
from typing import Tuple as TTuple

from .fqname import FQName
from .literal import Literal
from .name import Name
from .type import Type


@dataclass(frozen=True)
class SourceLocation:
    """Represents a source location (line, column)."""
    start_line: int
    start_column: int
    end_line: int
    end_column: int


@dataclass(frozen=True)
class ValueAttributes:
    """Attributes associated with a value."""
    source: SourceLocation | None = None
    inferred_type: Type | None = None
    extensions: dict[FQName, Any] = field(default_factory=dict)


# --- Patterns ---
@dataclass(frozen=True)
class WildcardPattern:
    """Represents a wildcard pattern (_)."""
    attributes: ValueAttributes


@dataclass(frozen=True)
class AsPattern:
    """Represents an as-pattern (alias)."""
    attributes: ValueAttributes
    pattern: Pattern
    name: Name


@dataclass(frozen=True)
class TuplePattern:
    """Represents a tuple pattern."""
    attributes: ValueAttributes
    elements: TList[Pattern]


@dataclass(frozen=True)
class ConstructorPattern:
    """Represents a constructor pattern."""
    attributes: ValueAttributes
    constructor: FQName
    args: TList[Pattern]


@dataclass(frozen=True)
class EmptyListPattern:
    """Represents an empty list pattern."""
    attributes: ValueAttributes


@dataclass(frozen=True)
class HeadTailPattern:
    """Represents a head-tail list pattern."""
    attributes: ValueAttributes
    head: Pattern
    tail: Pattern


@dataclass(frozen=True)
class LiteralPattern:
    """Represents a literal pattern."""
    attributes: ValueAttributes
    literal: Literal


@dataclass(frozen=True)
class UnitPattern:
    """Represents a unit pattern."""
    attributes: ValueAttributes


Pattern = Union[
    WildcardPattern,
    AsPattern,
    TuplePattern,
    ConstructorPattern,
    EmptyListPattern,
    HeadTailPattern,
    LiteralPattern,
    UnitPattern,
]

# --- Values ---


@dataclass(frozen=True)
class LiteralValue:
    """Represents a literal value."""
    attributes: ValueAttributes
    literal: Literal


@dataclass(frozen=True)
class Constructor:
    """Represents a constructor value."""
    attributes: ValueAttributes
    fqname: FQName


@dataclass(frozen=True)
class Tuple:
    """Represents a Tuple value."""
    attributes: ValueAttributes
    elements: TList["Value"]


@dataclass(frozen=True)
class List:
    """Represents a List value."""
    attributes: ValueAttributes
    elements: TList["Value"]


@dataclass(frozen=True)
class Record:
    """Represents a Record value."""
    attributes: ValueAttributes
    fields: TList[TTuple[Name, "Value"]]


@dataclass(frozen=True)
class Variable:
    """Represents a variable reference."""
    attributes: ValueAttributes
    name: Name


@dataclass(frozen=True)
class Reference:
    """Represents a reference to a fully qualified name."""
    attributes: ValueAttributes
    fqname: FQName


@dataclass(frozen=True)
class Field:
    """Represents a field access."""
    attributes: ValueAttributes
    subject: Value
    field_name: Name


@dataclass(frozen=True)
class FieldFunction:
    """Represents a field accessor function."""
    attributes: ValueAttributes
    name: Name


@dataclass(frozen=True)
class Apply:
    """Represents function application."""
    attributes: ValueAttributes
    function: Value
    argument: Value


@dataclass(frozen=True)
class Lambda:
    """Represents a lambda abstraction."""
    attributes: ValueAttributes
    pattern: Pattern
    body: Value


@dataclass(frozen=True)
class LetDefinition:
    """Represents a let definition."""
    attributes: ValueAttributes
    name: Name
    definition: Definition
    in_value: Value


@dataclass(frozen=True)
class LetRecursion:
    """Represents a recursive let binding."""
    attributes: ValueAttributes
    definitions: dict[Name, Definition]
    in_value: Value


@dataclass(frozen=True)
class Destructure:
    """Represents a destructuring let binding."""
    attributes: ValueAttributes
    pattern: Pattern
    value_to_destructure: Value
    in_value: Value


@dataclass(frozen=True)
class IfThenElse:
    """Represents an if-then-else expression."""
    attributes: ValueAttributes
    condition: Value
    then_branch: Value
    else_branch: Value


@dataclass(frozen=True)
class PatternMatch:
    """Represents a pattern match expression."""
    attributes: ValueAttributes
    branch_on: Value
    cases: TList[TTuple[Pattern, Value]]


@dataclass(frozen=True)
class UpdateRecord:
    """Represents a record update."""
    attributes: ValueAttributes
    value_to_update: Value
    fields: TList[TTuple[Name, Value]]


@dataclass(frozen=True)
class Unit:
    """Represents the Unit value."""
    attributes: ValueAttributes


@dataclass(frozen=True)
class Hole:
    """Represents a hole in the AST."""
    attributes: ValueAttributes
    reason: Any
    expected_type: Type | None


@dataclass(frozen=True)
class Native:
    """Represents a native reference."""
    attributes: ValueAttributes
    fqname: FQName
    native_info: Any


@dataclass(frozen=True)
class External:
    """Represents an external reference."""
    attributes: ValueAttributes
    external_name: str
    target_platform: str


Value = (
    LiteralValue
    | Constructor
    | Tuple
    | List
    | Record
    | Variable
    | Reference
    | Field
    | FieldFunction
    | Apply
    | Lambda
    | LetDefinition
    | LetRecursion
    | Destructure
    | IfThenElse
    | PatternMatch
    | UpdateRecord
    | Unit
    | Hole
    | Native
    | External
)

# --- Definitions & Specs ---


@dataclass(frozen=True)
class Specification:
    """Value specification."""
    inputs: TList[TTuple[Name, Type]]
    output: Type


@dataclass(frozen=True)
class Definition:
    """Value definition."""
    input_types: TList[TTuple[Name, ValueAttributes, Type]]
    output_type: Type
    body: Value
