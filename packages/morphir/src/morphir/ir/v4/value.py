from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Union
from typing import List as TList
from typing import Tuple as TTuple

from .fqname import FQName
from .incompleteness import HoleReason, Incompleteness
from .literal import Literal
from .name import Name
from .type import Type

if TYPE_CHECKING:
    from .annotation import Annotation


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
    definition: ValueDefinitionBody
    in_value: Value


@dataclass(frozen=True)
class LetRecursion:
    """Represents a recursive let binding."""

    attributes: ValueAttributes
    definitions: dict[Name, ValueDefinitionBody]
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
    """A hole in an expression: a part that is missing, with the reason why.

    Attributes:
        attributes: The value attributes.
        reason: Why the hole exists.
        expected_type: The type the missing part should have, if known.
    """

    attributes: ValueAttributes
    reason: HoleReason
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
    """Value specification: the signature of a value, and its annotations."""

    inputs: TList[TTuple[Name, Type]]
    output: Type
    annotations: TList[Annotation] = field(default_factory=lambda: [])


@dataclass(frozen=True)
class Definition:
    """A value definition with an expression body (``ExpressionBody``).

    Attributes:
        input_types: Each input's name, value attributes and declared type. v4
            JSON spells an input as a bare type, so attributes other than the
            declared type cannot be encoded; see
            `morphir.ir.migrate.drop_input_attributes`.
        output_type: The declared output type.
        body: The expression.
    """

    input_types: TList[TTuple[Name, ValueAttributes, Type]]
    output_type: Type
    body: Value


# --- Native and external definition bodies ---


@dataclass(frozen=True)
class Arithmetic:
    """Native hint: a basic arithmetic or logic operation."""


@dataclass(frozen=True)
class Comparison:
    """Native hint: a comparison operation."""


@dataclass(frozen=True)
class StringOp:
    """Native hint: a string operation."""


@dataclass(frozen=True)
class CollectionOp:
    """Native hint: a collection operation such as map, filter or fold."""


@dataclass(frozen=True)
class PlatformSpecific:
    """Native hint: an operation specific to one platform.

    Attributes:
        platform: The platform, such as ``"wasm"`` or ``"javascript"``.
    """

    platform: str


NativeHint = Union[Arithmetic, Comparison, StringOp, CollectionOp, PlatformSpecific]
"""What kind of operation a native definition performs."""


@dataclass(frozen=True)
class NativeInfo:
    """Information about a native definition.

    Attributes:
        hint: The kind of operation.
    """

    hint: NativeHint


@dataclass(frozen=True)
class ExternalBinding:
    """One target platform's binding for an external definition.

    Attributes:
        target_platform: The platform. Unique within an external body.
        external_name: The name of the operation on that platform.
    """

    target_platform: str
    external_name: str


@dataclass(frozen=True)
class NativeBody:
    """A value definition implemented natively by each runtime (``NativeBody``).

    Attributes:
        input_types: Each input's name and declared type.
        output_type: The declared output type.
        native_info: What kind of operation it is.
    """

    input_types: TList[TTuple[Name, Type]]
    output_type: Type
    native_info: NativeInfo


@dataclass(frozen=True)
class ExternalBody:
    """A value definition bound to external operations (``ExternalBody``).

    Attributes:
        input_types: Each input's name and declared type.
        output_type: The declared output type.
        externals: One or more platform bindings, unique by platform.
        body: An optional fallback expression for other platforms.
    """

    input_types: TList[TTuple[Name, Type]]
    output_type: Type
    externals: TList[ExternalBinding]
    body: Value | None = None


@dataclass(frozen=True)
class IncompleteBody:
    """A value definition that is not complete yet (``IncompleteBody``).

    Attributes:
        input_types: Each input's name and declared type.
        incompleteness: Why the definition is incomplete.
        output_type: The declared output type, if known yet.
        partial_body: The expression written so far, if any.
    """

    input_types: TList[TTuple[Name, Type]]
    incompleteness: Incompleteness
    output_type: Type | None = None
    partial_body: Value | None = None


ValueDefinitionBody = Union[Definition, NativeBody, ExternalBody, IncompleteBody]
"""A v4 value definition: an expression, native, external or incomplete body."""
