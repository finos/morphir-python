from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union, Any
from .name import Name
from .fqname import FQName
from .type import Type
from .literal import Literal

@dataclass(frozen=True)
class SourceLocation:
    start_line: int
    start_column: int
    end_line: int
    end_column: int

@dataclass(frozen=True)
class ValueAttributes:
    source: Optional[SourceLocation] = None
    inferred_type: Optional[Type] = None
    extensions: Dict[FQName, Any] = field(default_factory=dict)

# --- Patterns ---
@dataclass(frozen=True)
class WildcardPattern:
    attributes: ValueAttributes

@dataclass(frozen=True)
class AsPattern:
    attributes: ValueAttributes
    pattern: Pattern
    name: Name

@dataclass(frozen=True)
class TuplePattern:
    attributes: ValueAttributes
    elements: List[Pattern]

@dataclass(frozen=True)
class ConstructorPattern:
    attributes: ValueAttributes
    constructor: FQName
    args: List[Pattern]

@dataclass(frozen=True)
class EmptyListPattern:
    attributes: ValueAttributes

@dataclass(frozen=True)
class HeadTailPattern:
    attributes: ValueAttributes
    head: Pattern
    tail: Pattern

@dataclass(frozen=True)
class LiteralPattern:
    attributes: ValueAttributes
    literal: Literal

@dataclass(frozen=True)
class UnitPattern:
    attributes: ValueAttributes

Pattern = Union[
    WildcardPattern,
    AsPattern,
    TuplePattern,
    ConstructorPattern,
    EmptyListPattern,
    HeadTailPattern,
    LiteralPattern,
    UnitPattern
]

# --- Values ---

@dataclass(frozen=True)
class LiteralValue:
    attributes: ValueAttributes
    literal: Literal

@dataclass(frozen=True)
class Constructor:
    attributes: ValueAttributes
    fqname: FQName

@dataclass(frozen=True)
class Tuple:
    attributes: ValueAttributes
    elements: List[Value]

@dataclass(frozen=True)
class List:
    attributes: ValueAttributes
    elements: List[Value]

@dataclass(frozen=True)
class Record:
    attributes: ValueAttributes
    fields: List[Tuple[Name, Value]]

@dataclass(frozen=True)
class Variable:
    attributes: ValueAttributes
    name: Name

@dataclass(frozen=True)
class Reference:
    attributes: ValueAttributes
    fqname: FQName

@dataclass(frozen=True)
class Field:
    attributes: ValueAttributes
    subject: Value
    field_name: Name

@dataclass(frozen=True)
class FieldFunction:
    attributes: ValueAttributes
    name: Name

@dataclass(frozen=True)
class Apply:
    attributes: ValueAttributes
    function: Value
    argument: Value

@dataclass(frozen=True)
class Lambda:
    attributes: ValueAttributes
    pattern: Pattern
    body: Value

@dataclass(frozen=True)
class LetDefinition:
    attributes: ValueAttributes
    name: Name
    definition: Definition
    in_value: Value

@dataclass(frozen=True)
class LetRecursion:
    attributes: ValueAttributes
    definitions: Dict[Name, Definition]
    in_value: Value

@dataclass(frozen=True)
class Destructure:
    attributes: ValueAttributes
    pattern: Pattern
    value_to_destructure: Value
    in_value: Value

@dataclass(frozen=True)
class IfThenElse:
    attributes: ValueAttributes
    condition: Value
    then_branch: Value
    else_branch: Value

@dataclass(frozen=True)
class PatternMatch:
    attributes: ValueAttributes
    branch_on: Value
    cases: List[Tuple[Pattern, Value]]

@dataclass(frozen=True)
class UpdateRecord:
    attributes: ValueAttributes
    value_to_update: Value
    fields: List[Tuple[Name, Value]]

@dataclass(frozen=True)
class Unit:
    attributes: ValueAttributes

@dataclass(frozen=True)
class Hole:
    attributes: ValueAttributes
    reason: Any
    expected_type: Optional[Type]

@dataclass(frozen=True)
class Native:
    attributes: ValueAttributes
    fqname: FQName
    native_info: Any

@dataclass(frozen=True)
class External:
    attributes: ValueAttributes
    external_name: str
    target_platform: str

Value = Union[
    LiteralValue,
    Constructor,
    Tuple,
    List,
    Record,
    Variable,
    Reference,
    Field,
    FieldFunction,
    Apply,
    Lambda,
    LetDefinition,
    LetRecursion,
    Destructure,
    IfThenElse,
    PatternMatch,
    UpdateRecord,
    Unit,
    Hole,
    Native,
    External
]

# --- Definitions & Specs ---

@dataclass(frozen=True)
class Specification:
    inputs: List[Tuple[Name, Type]]
    output: Type

@dataclass(frozen=True)
class Definition:
    input_types: List[Tuple[Name, ValueAttributes, Type]]
    output_type: Type
    body: Value
