from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Union

from .fqname import FQName
from .name import Name
from .type_constraints import TypeConstraints


@dataclass(frozen=True)
class SourceLocation:
    start_line: int
    start_column: int
    end_line: int
    end_column: int


@dataclass(frozen=True)
class TypeAttributes:
    source: SourceLocation | None = None
    constraints: TypeConstraints | None = None
    extensions: dict[FQName, Any] = field(
        default_factory=dict
    )  # Any for extensions due to circular dep with Value


EMPTY_TYPE_ATTRIBUTES = TypeAttributes()


@dataclass(frozen=True)
class Variable:
    attributes: TypeAttributes
    name: Name


@dataclass(frozen=True)
class Reference:
    attributes: TypeAttributes
    fqname: FQName
    args: list[Type] = field(default_factory=list)


@dataclass(frozen=True)
class Tuple:
    attributes: TypeAttributes
    elements: list[Type] = field(default_factory=list)


@dataclass(frozen=True)
class Record:
    attributes: TypeAttributes
    fields: list[Field] = field(default_factory=list)


@dataclass(frozen=True)
class ExtensibleRecord:
    attributes: TypeAttributes
    variable: Name
    fields: list[Field] = field(default_factory=list)


@dataclass(frozen=True)
class Function:
    attributes: TypeAttributes
    argument_type: Type
    return_type: Type


@dataclass(frozen=True)
class Unit:
    attributes: TypeAttributes


Type = Union[Variable, Reference, Tuple, Record, ExtensibleRecord, Function, Unit]


@dataclass(frozen=True)
class Field:
    name: Name
    tpe: Type


def get_attributes(tpe: Type) -> TypeAttributes:
    return tpe.attributes


def map_attributes(tpe: Type, f: Any) -> Type:
    # f should be Callable[[TypeAttributes], TypeAttributes]
    # But doing precise typing here might be verbose with Union destructuring
    # For now, simplistic implementation
    ta = tpe.attributes
    new_ta = f(ta)

    if isinstance(tpe, Variable):
        return Variable(new_ta, tpe.name)
    elif isinstance(tpe, Reference):
        return Reference(new_ta, tpe.fqname, [map_attributes(a, f) for a in tpe.args])
    elif isinstance(tpe, Tuple):
        return Tuple(new_ta, [map_attributes(e, f) for e in tpe.elements])
    elif isinstance(tpe, Record):
        return Record(
            new_ta, [Field(fl.name, map_attributes(fl.tpe, f)) for fl in tpe.fields]
        )
    elif isinstance(tpe, ExtensibleRecord):
        return ExtensibleRecord(
            new_ta,
            tpe.variable,
            [Field(fl.name, map_attributes(fl.tpe, f)) for fl in tpe.fields],
        )
    elif isinstance(tpe, Function):
        return Function(
            new_ta,
            map_attributes(tpe.argument_type, f),
            map_attributes(tpe.return_type, f),
        )
    elif isinstance(tpe, Unit):
        return Unit(new_ta)
