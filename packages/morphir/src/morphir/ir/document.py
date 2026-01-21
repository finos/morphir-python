from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class DocNull:
    pass


@dataclass(frozen=True)
class DocBool:
    value: bool


@dataclass(frozen=True)
class DocInt:
    value: int


@dataclass(frozen=True)
class DocFloat:
    value: float


@dataclass(frozen=True)
class DocString:
    value: str


# Forward references for recursive types
@dataclass(frozen=True)
class DocArray:
    elements: list[Document]


@dataclass(frozen=True)
class DocObject:
    fields: dict[str, Document]


Document = Union[DocNull, DocBool, DocInt, DocFloat, DocString, DocArray, DocObject]


def null() -> Document:
    return DocNull()


def bool_(value: bool) -> Document:
    return DocBool(value)


def int_(value: int) -> Document:
    return DocInt(value)


def float_(value: float) -> Document:
    return DocFloat(value)


def string(value: str) -> Document:
    return DocString(value)


def array(elements: list[Document]) -> Document:
    return DocArray(elements)


def object_(fields: dict[str, Document]) -> Document:
    return DocObject(fields)
