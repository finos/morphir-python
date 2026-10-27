"""Draft JSON codec for Morphir IR v4.

**Draft.** IR v4 is not frozen upstream. This codec follows the finos/morphir v4
JSON profile and schema (``website/static/schemas/morphir-ir-v4.json``) at the
pinned commit `FINOS_MORPHIR_PIN`. Spellings may change in a later minor release
of this package when the codec is re-synced against the Morphir Compatibility Kit.

The envelope is ``{"formatVersion": 4, "distribution": {"Library": {...}}}``, with
the distribution wrapped by its kind (``Library``, ``Specs``, or ``Application``).
The codec never writes a format-3 tagged-array shape.

Every node is written in the schema's expanded form, ``{"Kind": {members}}``, with
``attributes`` omitted when empty. The reader accepts exactly the spellings listed
in `TYPE_NODES`, `VALUE_NODES`, `PATTERN_NODES`, and the other tables below, and
fails with a located diagnostic on anything else; it does not guess.

The codec covers the value-definition bodies (``ExpressionBody``, ``NativeBody``,
``ExternalBody``, ``IncompleteBody``), ``IncompleteTypeDefinition`` with typed hole
reasons, annotations on specifications, and the draft ``Union`` type (from
``docs/spec/draft/types.md``, not yet in the pinned schema).

Known gaps between the Python v4 model and upstream v4, each handled explicitly:

- The deprecated Python ``Native`` and ``External`` value nodes have no spelling
  (upstream makes them definition bodies); encoding fails with ``no_v4_spelling``.
- Structured ``TypeConstraints`` (deprecated) have no spelling; encoding fails
  with ``no_v4_spelling``.
- Only the expanded spelling is read and written. Compact spellings, the legacy
  spellings readers accept for one release, and the 4.1.0 linked annotations
  wait for the re-sync when upstream v4 settles.
- Records are objects keyed by field name (finos decision 0004); duplicate field
  names fail encoding with ``duplicate_member``.
- ``ExpressionBody.inputTypes`` has no attribute slot: upstream spells an input as
  a bare type (kit case ``definitions-0027``). Encoding accepts per-input
  attributes that are empty or whose only member is ``inferred_type`` equal to the
  declared input type, and fails with ``no_v4_spelling`` otherwise; decoding sets
  ``inferred_type`` to the declared type. `morphir.ir.migrate.drop_input_attributes`
  resets the attributes on request and reports each input that lost information.
- The package release version has no member (finos decision 0017); it is not
  written and decodes as absent.
- Python names are word lists without an initialism marker. A run of two or more
  single-letter words is written as an uppercase initialism (``value-in-USD``).
  Names the word-list model cannot represent, such as a one-letter initialism,
  an initialism with digits, adjacent initialisms, or adjacent single-letter
  words, fail with ``invalid_name``.
- An entry point's ``doc`` is written from ``EntryPoint.doc.value`` and decodes as
  ``Documented(None, doc)``.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import Any

from .. import diagnostics as d
from ..diagnostics import DiagnosticError, Location, fail
from ..format_version import V4, V4_TABLE, read_document, write_format_version
from . import annotation as ann
from . import document as doc
from . import incompleteness as inc
from . import literal as lit
from . import module, package
from . import type as t
from . import type_def as td
from . import type_spec as ts
from . import value as v
from .access_controlled import AccessControlled, Private, Public
from .distribution import (
    ApplicationDistribution,
    Distribution,
    EntryPoint,
    EntryPointKind,
    LibraryDistribution,
    PackageInfo,
    SpecsDistribution,
)
from .documented import Documented
from .fqname import FQName
from .name import Name
from .path import Path

FINOS_MORPHIR_PIN = "efa36060"
"""The finos/morphir commit whose v4 JSON profile this draft codec follows."""

DRAFT_NOTICE = (
    "IR v4 support is draft: it follows the finos/morphir v4 JSON profile at "
    f"commit {FINOS_MORPHIR_PIN} and may change in a later minor release."
)

type Json = Any

# --- Spelling tables: node kind -> (required members, optional members) ---

type Members = tuple[frozenset[str], frozenset[str]]


def _m(required: str = "", optional: str = "attributes") -> Members:
    return frozenset(required.split()), frozenset(optional.split())


TYPE_NODES: dict[str, Members] = {
    "Variable": _m("name"),
    "Reference": _m("fqname", "attributes args"),
    "Tuple": _m("elements"),
    "Record": _m("fields"),
    "ExtensibleRecord": _m("variable fields"),
    "Function": _m("parameterType returnType"),
    "Unit": _m(),
    "Union": _m("alternatives"),
}

VALUE_NODES: dict[str, Members] = {
    "Literal": _m("literal"),
    "Constructor": _m("fqname"),
    "Tuple": _m("elements"),
    "List": _m("items"),
    "Record": _m("fields"),
    "Variable": _m("name"),
    "Reference": _m("fqname"),
    "Field": _m("target name"),
    "FieldFunction": _m("name"),
    "Apply": _m("function argument"),
    "Lambda": _m("pattern body"),
    "LetDefinition": _m("name definition in"),
    "LetRecursion": _m("definitions in"),
    "Destructure": _m("pattern value in"),
    "IfThenElse": _m("condition then else"),
    "PatternMatch": _m("value cases"),
    "UpdateRecord": _m("target fields"),
    "Unit": _m(),
    "Hole": _m("reason", "attributes expectedType"),
}

PATTERN_NODES: dict[str, Members] = {
    "WildcardPattern": _m(),
    "AsPattern": _m("pattern name"),
    "TuplePattern": _m("patterns"),
    "ConstructorPattern": _m("fqname patterns"),
    "EmptyListPattern": _m(),
    "HeadTailPattern": _m("head tail"),
    "LiteralPattern": _m("literal"),
    "UnitPattern": _m(),
}

TYPE_SPECIFICATION_NODES: dict[str, Members] = {
    "TypeAliasSpecification": _m("typeParams typeExp", "annotations"),
    "OpaqueTypeSpecification": _m("", "annotations typeParams"),
    "CustomTypeSpecification": _m("typeParams constructors", "annotations"),
    "DerivedTypeSpecification": _m(
        "typeParams baseType fromBaseType toBaseType", "annotations"
    ),
}

TYPE_DEFINITION_NODES: dict[str, Members] = {
    "TypeAliasDefinition": _m("typeParams typeExp", ""),
    "CustomTypeDefinition": _m("typeParams constructors", "access"),
    "IncompleteTypeDefinition": _m("typeParams incompleteness", "partialTypeExp"),
}

HOLE_REASON_NODES: dict[str, Members] = {
    "UnresolvedReference": _m("target", ""),
    "DeletedDuringRefactor": _m("tx-id", ""),
    "TypeMismatch": _m("expected found", ""),
}

INCOMPLETENESS_NODES: dict[str, Members] = {
    "Hole": _m("reason", "partialBody"),
    "Draft": _m("", ""),
}

VALUE_DEFINITION_NODES: dict[str, Members] = {
    "ExpressionBody": _m("inputTypes outputType body", ""),
    "NativeBody": _m("inputTypes outputType nativeInfo", ""),
    "ExternalBody": _m("inputTypes outputType externals", "body"),
    "IncompleteBody": _m("inputTypes incompleteness", "outputType partialBody"),
}

NATIVE_HINT_NODES: dict[str, Members] = {
    "Arithmetic": _m("", ""),
    "Comparison": _m("", ""),
    "StringOp": _m("", ""),
    "CollectionOp": _m("", ""),
    "PlatformSpecific": _m("platform", ""),
}

DISTRIBUTION_NODES: dict[str, Members] = {
    "Library": _m("packageName", "dependencies def"),
    "Specs": _m("packageName", "dependencies spec"),
    "Application": _m("packageName entryPoints", "dependencies def"),
}

LITERAL_KINDS = frozenset(
    {
        "BoolLiteral",
        "CharLiteral",
        "StringLiteral",
        "IntegerLiteral",
        "WholeNumberLiteral",
        "FloatLiteral",
        "DecimalLiteral",
        "DocumentLiteral",
    }
)

ACCESS_TAGS = {"Public": Public, "Private": Private}

ENTRY_POINT_KINDS = {kind: kind.value.lower() for kind in EntryPointKind}

# --- Helpers ---


def _construct_error(
    code: str, construct: str, loc: Location, msg: str
) -> DiagnosticError:
    return fail(code, construct, loc, msg)


def _expect_object(j: object, loc: Location, construct: str) -> dict[str, object]:
    if not isinstance(j, dict):
        raise fail(
            d.INVALID_JSON, construct, loc, f"expected an object for {construct}"
        )
    return j


def _expect_list(j: object, loc: Location, construct: str) -> list[object]:
    if not isinstance(j, list):
        raise fail(d.INVALID_JSON, construct, loc, f"expected an array for {construct}")
    return j


def _expect_str(j: object, loc: Location, construct: str) -> str:
    if not isinstance(j, str):
        raise fail(d.INVALID_JSON, construct, loc, f"expected a string for {construct}")
    return j


def _check_members(
    obj: dict[str, object], members: Members, loc: Location, construct: str
) -> None:
    required, optional = members
    for key in obj:
        if key not in required and key not in optional:
            raise fail(
                d.UNKNOWN_MEMBER,
                construct,
                (*loc, key),
                f"{construct} has no member {key!r} in the draft v4 codec",
            )
    for key in sorted(required):
        if key not in obj:
            raise fail(
                d.MISSING_MEMBER,
                construct,
                loc,
                f"{construct} requires member {key!r}",
            )


def _node(
    j: object, loc: Location, family: str, table: dict[str, Members]
) -> tuple[str, dict[str, object], Location]:
    obj = _expect_object(j, loc, family)
    if len(obj) != 1:
        raise fail(
            d.UNKNOWN_NODE,
            family,
            loc,
            f"expected a {family} wrapped by its kind, found members {sorted(obj)}",
        )
    ((tag, payload),) = obj.items()
    if tag not in table:
        raise fail(
            d.UNKNOWN_NODE,
            family,
            (*loc, tag),
            f"unknown {family} kind {tag!r} in the draft v4 codec",
        )
    here = (*loc, tag)
    body = _expect_object(payload, here, tag)
    _check_members(body, table[tag], here, tag)
    return tag, body, here


def _wrap(tag: str, members: dict[str, Json]) -> Json:
    return {tag: members}


def _keyed[K, A](
    items: list[tuple[K, A]] | dict[K, A],
    encode_key: Callable[[K, Location], str],
    encode_value: Callable[[A, Location], Json],
    loc: Location,
    construct: str,
) -> dict[str, Json]:
    pairs = list(items.items()) if isinstance(items, dict) else items
    result: dict[str, Json] = {}
    for key, value in pairs:
        text = encode_key(key, loc)
        if text in result:
            raise fail(
                d.DUPLICATE_MEMBER,
                construct,
                (*loc, text),
                f"{construct} has {text!r} more than once",
            )
        result[text] = encode_value(value, (*loc, text))
    return result


def _unkeyed[K, A](
    j: object,
    decode_key: Callable[[str, Location], K],
    decode_value: Callable[[object, Location], A],
    loc: Location,
    construct: str,
) -> list[tuple[K, A]]:
    obj = _expect_object(j, loc, construct)
    return [
        (decode_key(key, (*loc, key)), decode_value(value, (*loc, key)))
        for key, value in obj.items()
    ]


# --- Names ---

_WORD = re.compile(r"^[a-z0-9]+$")
_INITIALISM = re.compile(r"^[A-Z]{2,}$")
_LOWER_SEGMENT = re.compile(r"^[a-z0-9]+$")


def _single_letter(word: str) -> bool:
    return len(word) == 1 and word.isalpha()


def encode_name(name: Name, loc: Location = ()) -> str:
    """Write a name canonically, collapsing single-letter runs into initialisms.

    Example:
        >>> encode_name(Name(("value", "in", "u", "s", "d")))
        'value-in-USD'
    """
    segments: list[str] = []
    run: list[str] = []

    def flush() -> None:
        if len(run) >= 2:
            segments.append("".join(run).upper())
        else:
            segments.extend(run)
        run.clear()

    for word in name:
        if not _WORD.match(word):
            raise fail(
                d.INVALID_NAME,
                "Name",
                loc,
                f"name word {word!r} is not lowercase letters and digits",
            )
        if _single_letter(word):
            run.append(word)
        else:
            flush()
            segments.append(word)
    flush()
    if not segments:
        raise fail(d.INVALID_NAME, "Name", loc, "a name needs at least one word")
    return "-".join(segments)


def decode_name(j: object, loc: Location = ()) -> Name:
    """Read a canonical name string such as ``value-in-USD``."""
    text = _expect_str(j, loc, "Name")
    words: list[str] = []
    previous = ""
    for segment in text.split("-"):
        if _INITIALISM.match(segment):
            kind = "initialism"
            parts = [ch.lower() for ch in segment]
        elif _LOWER_SEGMENT.match(segment):
            kind = "single" if _single_letter(segment) else "word"
            parts = [segment]
        else:
            raise fail(
                d.INVALID_NAME,
                "Name",
                loc,
                f"name {text!r} has an invalid segment {segment!r}",
            )
        if kind in ("initialism", "single") and previous in ("initialism", "single"):
            raise fail(
                d.INVALID_NAME,
                "Name",
                loc,
                f"name {text!r} has adjacent initialisms or single letters, which "
                "the Python word-list model cannot represent",
            )
        previous = kind
        words.extend(parts)
    return Name(tuple(words))


def encode_path(path: Path, loc: Location = ()) -> str:
    return "/".join(encode_name(n, loc) for n in path)


def decode_path(j: object, loc: Location = ()) -> Path:
    text = _expect_str(j, loc, "Path")
    if not text:
        return Path(())
    return Path(tuple(decode_name(part, loc) for part in text.split("/")))


_FQNAME = re.compile(r"^([^:#]*):([^:#]*)#([^:#/]+)$")


def encode_fqname(fqn: FQName, loc: Location = ()) -> str:
    return (
        f"{encode_path(fqn.package_path, loc)}:{encode_path(fqn.module_path, loc)}"
        f"#{encode_name(fqn.local_name, loc)}"
    )


def decode_fqname(j: object, loc: Location = ()) -> FQName:
    text = _expect_str(j, loc, "FQName")
    match = _FQNAME.match(text)
    if match is None:
        raise fail(
            d.INVALID_NAME, "FQName", loc, f"{text!r} is not package:module#name"
        )
    pkg, mod, local = match.groups()
    return FQName(decode_path(pkg, loc), decode_path(mod, loc), decode_name(local, loc))


def _name_key(name: Name, loc: Location) -> str:
    return encode_name(name, loc)


def _path_key(path: Path, loc: Location) -> str:
    return encode_path(path, loc)


# --- Attributes ---


def _encode_source(
    src: t.SourceLocation | v.SourceLocation,
) -> dict[str, Json]:
    return {
        "startLine": src.start_line,
        "startColumn": src.start_column,
        "endLine": src.end_line,
        "endColumn": src.end_column,
    }


def _decode_source(j: object, loc: Location) -> tuple[int, int, int, int]:
    obj = _expect_object(j, loc, "SourceLocation")
    keys = ("startLine", "startColumn", "endLine", "endColumn")
    _check_members(obj, (frozenset(keys), frozenset()), loc, "SourceLocation")
    values = []
    for key in keys:
        value = obj[key]
        if isinstance(value, bool) or not isinstance(value, int):
            raise fail(
                d.INVALID_JSON,
                "SourceLocation",
                (*loc, key),
                f"{key} must be an integer",
            )
        values.append(value)
    return values[0], values[1], values[2], values[3]


def _encode_extensions(ext: dict[FQName, Any], loc: Location) -> dict[str, Json]:
    return {encode_fqname(k, loc): value for k, value in ext.items()}


def _decode_extensions(j: object, loc: Location) -> dict[FQName, Any]:
    obj = _expect_object(j, loc, "extensions")
    return {decode_fqname(k, (*loc, k)): value for k, value in obj.items()}


def _encode_type_attributes(a: t.TypeAttributes, loc: Location) -> dict[str, Json]:
    out: dict[str, Json] = {}
    if a.source is not None:
        out["source"] = _encode_source(a.source)
    if a.constraints is not None:
        raise fail(
            d.NO_V4_SPELLING,
            "TypeConstraints",
            (*loc, "attributes", "constraints"),
            "structured type constraints have no spelling in the draft v4 profile",
        )
    if a.extensions:
        out["extensions"] = _encode_extensions(a.extensions, (*loc, "attributes"))
    return out


def _decode_type_attributes(body: dict[str, object], loc: Location) -> t.TypeAttributes:
    if "attributes" not in body:
        return t.TypeAttributes()
    here = (*loc, "attributes")
    obj = _expect_object(body["attributes"], here, "TypeAttributes")
    _check_members(obj, _m("", "source extensions"), here, "TypeAttributes")
    source = (
        t.SourceLocation(*_decode_source(obj["source"], (*here, "source")))
        if "source" in obj
        else None
    )
    ext = (
        _decode_extensions(obj["extensions"], (*here, "extensions"))
        if "extensions" in obj
        else {}
    )
    return t.TypeAttributes(source=source, extensions=ext)


def _encode_value_attributes(a: v.ValueAttributes, loc: Location) -> dict[str, Json]:
    out: dict[str, Json] = {}
    if a.source is not None:
        out["source"] = _encode_source(a.source)
    if a.inferred_type is not None:
        out["inferredType"] = encode_type(
            a.inferred_type, (*loc, "attributes", "inferredType")
        )
    if a.extensions:
        out["extensions"] = _encode_extensions(a.extensions, (*loc, "attributes"))
    return out


def _decode_value_attributes(
    body: dict[str, object], loc: Location
) -> v.ValueAttributes:
    if "attributes" not in body:
        return v.ValueAttributes()
    here = (*loc, "attributes")
    obj = _expect_object(body["attributes"], here, "ValueAttributes")
    _check_members(
        obj, _m("", "source inferredType extensions"), here, "ValueAttributes"
    )
    return v.ValueAttributes(
        source=(
            v.SourceLocation(*_decode_source(obj["source"], (*here, "source")))
            if "source" in obj
            else None
        ),
        inferred_type=(
            decode_type(obj["inferredType"], (*here, "inferredType"))
            if "inferredType" in obj
            else None
        ),
        extensions=(
            _decode_extensions(obj["extensions"], (*here, "extensions"))
            if "extensions" in obj
            else {}
        ),
    )


def _with_attributes(
    attrs: dict[str, Json], members: dict[str, Json]
) -> dict[str, Json]:
    return {"attributes": attrs, **members} if attrs else members


# --- Types ---


def encode_type(tpe: t.Type, loc: Location = ()) -> Json:
    """Encode a v4 type in the expanded draft spelling."""
    attrs = _encode_type_attributes(tpe.attributes, loc)

    def node(tag: str, members: dict[str, Json]) -> Json:
        return _wrap(tag, _with_attributes(attrs, members))

    here = (*loc, type(tpe).__name__)
    match tpe:
        case t.Variable(_, name):
            return node("Variable", {"name": encode_name(name, here)})
        case t.Reference(_, fqn, args):
            members: dict[str, Json] = {"fqname": encode_fqname(fqn, here)}
            if args:
                members["args"] = [
                    encode_type(a, (*here, "args", i)) for i, a in enumerate(args)
                ]
            return node("Reference", members)
        case t.Tuple(_, elements):
            return node(
                "Tuple",
                {
                    "elements": [
                        encode_type(e, (*here, "elements", i))
                        for i, e in enumerate(elements)
                    ]
                },
            )
        case t.Record(_, fields):
            return node("Record", {"fields": _encode_type_fields(fields, here)})
        case t.ExtensibleRecord(_, var, fields):
            return node(
                "ExtensibleRecord",
                {
                    "variable": encode_name(var, here),
                    "fields": _encode_type_fields(fields, here),
                },
            )
        case t.Function(_, arg, ret):
            return node(
                "Function",
                {
                    "parameterType": encode_type(arg, (*here, "parameterType")),
                    "returnType": encode_type(ret, (*here, "returnType")),
                },
            )
        case t.Unit(_):
            return node("Unit", {})
        case t.Union(_, alternatives):
            _check_alternatives(len(alternatives), (*here, "alternatives"))
            return node(
                "Union",
                {
                    "alternatives": [
                        encode_type(x, (*here, "alternatives", i))
                        for i, x in enumerate(alternatives)
                    ]
                },
            )


def _check_alternatives(count: int, loc: Location) -> None:
    if count < 2:
        raise fail(
            d.INVALID_JSON,
            "Union",
            loc,
            f"a union needs two or more alternatives, found {count}",
        )


def _encode_type_fields(fields: list[t.Field], loc: Location) -> dict[str, Json]:
    return _keyed(
        [(f.name, f.tpe) for f in fields],
        _name_key,
        encode_type,
        (*loc, "fields"),
        "Record",
    )


def decode_type(j: object, loc: Location = ()) -> t.Type:
    """Decode a v4 type from the expanded draft spelling."""
    tag, body, here = _node(j, loc, "Type", TYPE_NODES)
    attrs = _decode_type_attributes(body, here)

    def fields() -> list[t.Field]:
        return [
            t.Field(n, tp)
            for n, tp in _unkeyed(
                body["fields"], decode_name, decode_type, (*here, "fields"), "Record"
            )
        ]

    match tag:
        case "Variable":
            return t.Variable(attrs, decode_name(body["name"], (*here, "name")))
        case "Reference":
            args = (
                _decode_list(decode_type, body["args"], (*here, "args"), "Type")
                if "args" in body
                else []
            )
            return t.Reference(attrs, decode_fqname(body["fqname"], here), args)
        case "Tuple":
            return t.Tuple(
                attrs,
                _decode_list(
                    decode_type, body["elements"], (*here, "elements"), "Type"
                ),
            )
        case "Record":
            return t.Record(attrs, fields())
        case "ExtensibleRecord":
            return t.ExtensibleRecord(
                attrs, decode_name(body["variable"], (*here, "variable")), fields()
            )
        case "Function":
            return t.Function(
                attrs,
                decode_type(body["parameterType"], (*here, "parameterType")),
                decode_type(body["returnType"], (*here, "returnType")),
            )
        case "Union":
            alternatives = _decode_list(
                decode_type, body["alternatives"], (*here, "alternatives"), "Union"
            )
            _check_alternatives(len(alternatives), (*here, "alternatives"))
            return t.Union(attrs, alternatives)
        case _:
            return t.Unit(attrs)


def _decode_list[A](
    decode: Callable[[object, Location], A], j: object, loc: Location, construct: str
) -> list[A]:
    return [
        decode(item, (*loc, i))
        for i, item in enumerate(_expect_list(j, loc, construct))
    ]


# --- Literals and documents ---


def _encode_document(value: doc.Document) -> Json:
    match value:
        case doc.DocNull():
            return None
        case doc.DocBool(b):
            return b
        case doc.DocInt(i):
            return i
        case doc.DocFloat(f):
            return f
        case doc.DocString(s):
            return s
        case doc.DocArray(elements):
            return [_encode_document(e) for e in elements]
        case doc.DocObject(fields):
            return {k: _encode_document(e) for k, e in fields.items()}


def _decode_document(j: object) -> doc.Document:
    if j is None:
        return doc.DocNull()
    if isinstance(j, bool):
        return doc.DocBool(j)
    if isinstance(j, int):
        return doc.DocInt(j)
    if isinstance(j, float):
        return doc.DocFloat(j)
    if isinstance(j, str):
        return doc.DocString(j)
    if isinstance(j, list):
        return doc.DocArray([_decode_document(e) for e in j])
    obj = _expect_object(j, (), "Document")
    return doc.DocObject({k: _decode_document(e) for k, e in obj.items()})


def encode_literal(literal: lit.Literal, loc: Location = ()) -> Json:
    """Encode a literal as ``{"IntegerLiteral": 42}`` and similar."""
    match literal:
        case lit.BoolLiteral(value):
            return {"BoolLiteral": value}
        case lit.CharLiteral(value):
            return {"CharLiteral": value}
        case lit.StringLiteral(value):
            return {"StringLiteral": value}
        case lit.IntegerLiteral(value):
            return {"IntegerLiteral": value}
        case lit.FloatLiteral(value):
            return {"FloatLiteral": value}
        case lit.DecimalLiteral(value):
            return {"DecimalLiteral": str(value)}
        case lit.DocumentLiteral(value):
            return {"DocumentLiteral": _encode_document(value)}


def decode_literal(j: object, loc: Location = ()) -> lit.Literal:
    """Decode a literal; ``WholeNumberLiteral`` reads as ``IntegerLiteral``."""
    obj = _expect_object(j, loc, "Literal")
    if len(obj) != 1 or next(iter(obj)) not in LITERAL_KINDS:
        raise fail(
            d.UNKNOWN_NODE,
            "Literal",
            loc,
            f"unknown literal spelling with members {sorted(obj)}",
        )
    ((tag, payload),) = obj.items()
    here = (*loc, tag)

    def bad(message: str) -> DiagnosticError:
        return fail(d.INVALID_LITERAL, tag, here, message)

    match tag:
        case "BoolLiteral":
            if not isinstance(payload, bool):
                raise bad("BoolLiteral expects a boolean")
            return lit.BoolLiteral(payload)
        case "CharLiteral":
            if not isinstance(payload, str) or len(payload) != 1:
                raise bad("CharLiteral expects a single character")
            return lit.CharLiteral(payload)
        case "StringLiteral":
            if not isinstance(payload, str):
                raise bad("StringLiteral expects a string")
            return lit.StringLiteral(payload)
        case "IntegerLiteral" | "WholeNumberLiteral":
            if isinstance(payload, bool) or not isinstance(payload, int):
                raise bad(f"{tag} expects an integer")
            return lit.IntegerLiteral(payload)
        case "FloatLiteral":
            if isinstance(payload, bool) or not isinstance(payload, (int, float)):
                raise bad("FloatLiteral expects a number")
            return lit.FloatLiteral(float(payload))
        case "DecimalLiteral":
            if not isinstance(payload, str):
                raise bad("DecimalLiteral expects a string")
            try:
                return lit.DecimalLiteral(Decimal(payload))
            except InvalidOperation:
                raise bad(f"invalid decimal {payload!r}") from None
        case _:
            return lit.DocumentLiteral(_decode_document(payload))


# --- Patterns ---


def encode_pattern(p: v.Pattern, loc: Location = ()) -> Json:
    """Encode a v4 pattern in the expanded draft spelling."""
    attrs = _encode_value_attributes(p.attributes, loc)
    here = (*loc, type(p).__name__)

    def node(tag: str, members: dict[str, Json]) -> Json:
        return _wrap(tag, _with_attributes(attrs, members))

    def many(items: list[v.Pattern], key: str) -> list[Json]:
        return [encode_pattern(x, (*here, key, i)) for i, x in enumerate(items)]

    match p:
        case v.WildcardPattern(_):
            return node("WildcardPattern", {})
        case v.AsPattern(_, inner, name):
            return node(
                "AsPattern",
                {
                    "pattern": encode_pattern(inner, (*here, "pattern")),
                    "name": encode_name(name, here),
                },
            )
        case v.TuplePattern(_, elements):
            return node("TuplePattern", {"patterns": many(elements, "patterns")})
        case v.ConstructorPattern(_, ctor, args):
            return node(
                "ConstructorPattern",
                {
                    "fqname": encode_fqname(ctor, here),
                    "patterns": many(args, "patterns"),
                },
            )
        case v.EmptyListPattern(_):
            return node("EmptyListPattern", {})
        case v.HeadTailPattern(_, head, tail):
            return node(
                "HeadTailPattern",
                {
                    "head": encode_pattern(head, (*here, "head")),
                    "tail": encode_pattern(tail, (*here, "tail")),
                },
            )
        case v.LiteralPattern(_, literal):
            return node("LiteralPattern", {"literal": encode_literal(literal, here)})
        case v.UnitPattern(_):
            return node("UnitPattern", {})


def decode_pattern(j: object, loc: Location = ()) -> v.Pattern:
    """Decode a v4 pattern from the expanded draft spelling."""
    tag, body, here = _node(j, loc, "Pattern", PATTERN_NODES)
    attrs = _decode_value_attributes(body, here)

    def sub(key: str) -> v.Pattern:
        return decode_pattern(body[key], (*here, key))

    def many(key: str) -> list[v.Pattern]:
        return _decode_list(decode_pattern, body[key], (*here, key), "Pattern")

    match tag:
        case "WildcardPattern":
            return v.WildcardPattern(attrs)
        case "AsPattern":
            return v.AsPattern(attrs, sub("pattern"), decode_name(body["name"], here))
        case "TuplePattern":
            return v.TuplePattern(attrs, many("patterns"))
        case "ConstructorPattern":
            return v.ConstructorPattern(
                attrs, decode_fqname(body["fqname"], here), many("patterns")
            )
        case "EmptyListPattern":
            return v.EmptyListPattern(attrs)
        case "HeadTailPattern":
            return v.HeadTailPattern(attrs, sub("head"), sub("tail"))
        case "LiteralPattern":
            return v.LiteralPattern(
                attrs, decode_literal(body["literal"], (*here, "literal"))
            )
        case _:
            return v.UnitPattern(attrs)


# --- Values ---


def encode_value(val: v.Value, loc: Location = ()) -> Json:
    """Encode a v4 value in the expanded draft spelling.

    Raises:
        DiagnosticError: With ``no_v4_spelling`` for ``Native`` and ``External``
            nodes, or ``duplicate_member`` for repeated record fields.
    """
    construct = type(val).__name__
    here = (*loc, construct)
    if isinstance(val, (v.Native, v.External)):
        raise fail(
            d.NO_V4_SPELLING,
            construct,
            loc,
            f"{construct} value nodes have no spelling in the draft v4 profile; "
            "upstream v4 makes them definition bodies",
        )
    attrs = _encode_value_attributes(val.attributes, loc)

    def node(tag: str, members: dict[str, Json]) -> Json:
        return _wrap(tag, _with_attributes(attrs, members))

    def sub(x: v.Value, key: str) -> Json:
        return encode_value(x, (*here, key))

    def many(items: list[v.Value], key: str) -> list[Json]:
        return [encode_value(x, (*here, key, i)) for i, x in enumerate(items)]

    def fields(items: list[tuple[Name, v.Value]], key: str = "fields") -> Json:
        return _keyed(items, _name_key, encode_value, (*here, key), construct)

    match val:
        case v.LiteralValue(_, literal):
            return node("Literal", {"literal": encode_literal(literal, here)})
        case v.Constructor(_, fqn):
            return node("Constructor", {"fqname": encode_fqname(fqn, here)})
        case v.Tuple(_, elements):
            return node("Tuple", {"elements": many(elements, "elements")})
        case v.List(_, elements):
            return node("List", {"items": many(elements, "items")})
        case v.Record(_, record_fields):
            return node("Record", {"fields": fields(record_fields)})
        case v.Variable(_, name):
            return node("Variable", {"name": encode_name(name, here)})
        case v.Reference(_, fqn):
            return node("Reference", {"fqname": encode_fqname(fqn, here)})
        case v.Field(_, subject, name):
            return node(
                "Field",
                {"target": sub(subject, "target"), "name": encode_name(name, here)},
            )
        case v.FieldFunction(_, name):
            return node("FieldFunction", {"name": encode_name(name, here)})
        case v.Apply(_, function, argument):
            return node(
                "Apply",
                {
                    "function": sub(function, "function"),
                    "argument": sub(argument, "argument"),
                },
            )
        case v.Lambda(_, pattern, body):
            return node(
                "Lambda",
                {
                    "pattern": encode_pattern(pattern, (*here, "pattern")),
                    "body": sub(body, "body"),
                },
            )
        case v.LetDefinition(_, name, definition, in_value):
            return node(
                "LetDefinition",
                {
                    "name": encode_name(name, here),
                    "definition": encode_value_definition(
                        definition, (*here, "definition")
                    ),
                    "in": sub(in_value, "in"),
                },
            )
        case v.LetRecursion(_, definitions, in_value):
            return node(
                "LetRecursion",
                {
                    "definitions": _keyed(
                        definitions,
                        _name_key,
                        encode_value_definition,
                        (*here, "definitions"),
                        construct,
                    ),
                    "in": sub(in_value, "in"),
                },
            )
        case v.Destructure(_, pattern, subject, in_value):
            return node(
                "Destructure",
                {
                    "pattern": encode_pattern(pattern, (*here, "pattern")),
                    "value": sub(subject, "value"),
                    "in": sub(in_value, "in"),
                },
            )
        case v.IfThenElse(_, cond, then_branch, else_branch):
            return node(
                "IfThenElse",
                {
                    "condition": sub(cond, "condition"),
                    "then": sub(then_branch, "then"),
                    "else": sub(else_branch, "else"),
                },
            )
        case v.PatternMatch(_, subject, cases):
            return node(
                "PatternMatch",
                {
                    "value": sub(subject, "value"),
                    "cases": [
                        {
                            "pattern": encode_pattern(
                                p, (*here, "cases", i, "pattern")
                            ),
                            "body": encode_value(b, (*here, "cases", i, "body")),
                        }
                        for i, (p, b) in enumerate(cases)
                    ],
                },
            )
        case v.UpdateRecord(_, subject, update_fields):
            return node(
                "UpdateRecord",
                {"target": sub(subject, "target"), "fields": fields(update_fields)},
            )
        case v.Unit(_):
            return node("Unit", {})
        case v.Hole(_, reason, expected_type):
            members: dict[str, Json] = {
                "reason": encode_hole_reason(reason, (*here, "reason"))
            }
            if expected_type is not None:
                members["expectedType"] = encode_type(
                    expected_type, (*here, "expectedType")
                )
            return node("Hole", members)


def decode_value(j: object, loc: Location = ()) -> v.Value:
    """Decode a v4 value from the expanded draft spelling."""
    tag, body, here = _node(j, loc, "Value", VALUE_NODES)
    attrs = _decode_value_attributes(body, here)

    def sub(key: str) -> v.Value:
        return decode_value(body[key], (*here, key))

    def many(key: str) -> list[v.Value]:
        return _decode_list(decode_value, body[key], (*here, key), "Value")

    def fields() -> list[tuple[Name, v.Value]]:
        return _unkeyed(
            body["fields"], decode_name, decode_value, (*here, "fields"), tag
        )

    match tag:
        case "Literal":
            return v.LiteralValue(
                attrs, decode_literal(body["literal"], (*here, "literal"))
            )
        case "Constructor":
            return v.Constructor(attrs, decode_fqname(body["fqname"], here))
        case "Tuple":
            return v.Tuple(attrs, many("elements"))
        case "List":
            return v.List(attrs, many("items"))
        case "Record":
            return v.Record(attrs, fields())
        case "Variable":
            return v.Variable(attrs, decode_name(body["name"], here))
        case "Reference":
            return v.Reference(attrs, decode_fqname(body["fqname"], here))
        case "Field":
            return v.Field(attrs, sub("target"), decode_name(body["name"], here))
        case "FieldFunction":
            return v.FieldFunction(attrs, decode_name(body["name"], here))
        case "Apply":
            return v.Apply(attrs, sub("function"), sub("argument"))
        case "Lambda":
            return v.Lambda(
                attrs, decode_pattern(body["pattern"], (*here, "pattern")), sub("body")
            )
        case "LetDefinition":
            return v.LetDefinition(
                attrs,
                decode_name(body["name"], here),
                decode_value_definition(body["definition"], (*here, "definition")),
                sub("in"),
            )
        case "LetRecursion":
            return v.LetRecursion(
                attrs,
                dict(
                    _unkeyed(
                        body["definitions"],
                        decode_name,
                        decode_value_definition,
                        (*here, "definitions"),
                        tag,
                    )
                ),
                sub("in"),
            )
        case "Destructure":
            return v.Destructure(
                attrs,
                decode_pattern(body["pattern"], (*here, "pattern")),
                sub("value"),
                sub("in"),
            )
        case "IfThenElse":
            return v.IfThenElse(attrs, sub("condition"), sub("then"), sub("else"))
        case "PatternMatch":
            cases: list[tuple[v.Pattern, v.Value]] = []
            for i, case in enumerate(
                _expect_list(body["cases"], (*here, "cases"), tag)
            ):
                case_loc = (*here, "cases", i)
                case_obj = _expect_object(case, case_loc, "Case")
                _check_members(case_obj, _m("pattern body", ""), case_loc, "Case")
                cases.append(
                    (
                        decode_pattern(case_obj["pattern"], (*case_loc, "pattern")),
                        decode_value(case_obj["body"], (*case_loc, "body")),
                    )
                )
            return v.PatternMatch(attrs, sub("value"), cases)
        case "UpdateRecord":
            return v.UpdateRecord(attrs, sub("target"), fields())
        case "Unit":
            return v.Unit(attrs)
        case _:
            return v.Hole(
                attrs,
                decode_hole_reason(body["reason"], (*here, "reason")),
                decode_type(body["expectedType"], (*here, "expectedType"))
                if "expectedType" in body
                else None,
            )


# --- Hole reasons and incompleteness ---


def encode_hole_reason(reason: inc.HoleReason, loc: Location = ()) -> Json:
    """Encode a hole reason as ``{"Kind": {members}}``."""
    match reason:
        case inc.UnresolvedReference(target):
            return _wrap(
                "UnresolvedReference",
                {"target": encode_fqname(target, (*loc, "UnresolvedReference"))},
            )
        case inc.DeletedDuringRefactor(tx_id):
            return _wrap("DeletedDuringRefactor", {"tx-id": tx_id})
        case inc.TypeMismatch(expected, found):
            return _wrap("TypeMismatch", {"expected": expected, "found": found})


def decode_hole_reason(j: object, loc: Location = ()) -> inc.HoleReason:
    """Decode a hole reason; ``Draft`` is an incompleteness, not a reason."""
    tag, body, here = _node(j, loc, "HoleReason", HOLE_REASON_NODES)
    match tag:
        case "UnresolvedReference":
            return inc.UnresolvedReference(
                decode_fqname(body["target"], (*here, "target"))
            )
        case "DeletedDuringRefactor":
            return inc.DeletedDuringRefactor(
                _expect_str(body["tx-id"], (*here, "tx-id"), tag)
            )
        case _:
            return inc.TypeMismatch(
                _expect_str(body["expected"], (*here, "expected"), tag),
                _expect_str(body["found"], (*here, "found"), tag),
            )


def encode_incompleteness(item: inc.Incompleteness, loc: Location = ()) -> Json:
    """Encode an incompleteness as ``{"Hole": {...}}`` or ``{"Draft": {}}``."""
    match item:
        case inc.HoleIncompleteness(reason, partial):
            here = (*loc, "Hole")
            members: dict[str, Json] = {
                "reason": encode_hole_reason(reason, (*here, "reason"))
            }
            if partial is not None:
                members["partialBody"] = encode_type(partial, (*here, "partialBody"))
            return _wrap("Hole", members)
        case inc.DraftIncompleteness():
            return _wrap("Draft", {})


def decode_incompleteness(j: object, loc: Location = ()) -> inc.Incompleteness:
    """Decode ``{"Hole": {...}}`` or ``{"Draft": {}}``."""
    tag, body, here = _node(j, loc, "Incompleteness", INCOMPLETENESS_NODES)
    if tag == "Draft":
        return inc.DraftIncompleteness()
    return inc.HoleIncompleteness(
        decode_hole_reason(body["reason"], (*here, "reason")),
        decode_type(body["partialBody"], (*here, "partialBody"))
        if "partialBody" in body
        else None,
    )


def _encode_inputs(
    inputs: list[tuple[Name, t.Type]], loc: Location, construct: str
) -> dict[str, Json]:
    return _keyed(inputs, _name_key, encode_type, loc, construct)


def _encode_expression_body(defn: v.Definition, loc: Location) -> Json:
    here = (*loc, "ExpressionBody")
    for i, (name, attrs, tpe) in enumerate(defn.input_types):
        derived = v.ValueAttributes(inferred_type=tpe)
        if attrs not in (v.ValueAttributes(), derived):
            raise fail(
                d.NO_V4_SPELLING,
                "ValueDefinition",
                (*here, "inputTypes", i),
                f"input {encode_name(name, here)!r} carries attributes other than its "
                "declared type; ExpressionBody.inputTypes has no attribute slot. "
                "Drop them with morphir.ir.migrate.drop_input_attributes or "
                "`morphir-tools ir convert --drop-input-attributes`",
            )
    return {
        "ExpressionBody": {
            "inputTypes": _encode_inputs(
                [(n, tp) for n, _, tp in defn.input_types],
                (*here, "inputTypes"),
                "ExpressionBody",
            ),
            "outputType": encode_type(defn.output_type, (*here, "outputType")),
            "body": encode_value(defn.body, (*here, "body")),
        }
    }


def _encode_native_hint(hint: v.NativeHint) -> Json:
    if isinstance(hint, v.PlatformSpecific):
        return _wrap("PlatformSpecific", {"platform": hint.platform})
    return _wrap(type(hint).__name__, {})


def _decode_native_hint(j: object, loc: Location) -> v.NativeHint:
    tag, body, here = _node(j, loc, "NativeHint", NATIVE_HINT_NODES)
    match tag:
        case "Arithmetic":
            return v.Arithmetic()
        case "Comparison":
            return v.Comparison()
        case "StringOp":
            return v.StringOp()
        case "CollectionOp":
            return v.CollectionOp()
        case _:
            return v.PlatformSpecific(
                _expect_str(body["platform"], (*here, "platform"), tag)
            )


def _encode_externals(bindings: list[v.ExternalBinding], loc: Location) -> list[Json]:
    if not bindings:
        raise fail(
            d.INVALID_JSON,
            "ExternalBody",
            loc,
            "an external body needs at least one platform binding",
        )
    seen: set[str] = set()
    result: list[Json] = []
    for i, binding in enumerate(bindings):
        if binding.target_platform in seen:
            raise fail(
                d.DUPLICATE_MEMBER,
                "ExternalBinding",
                (*loc, i, "targetPlatform"),
                f"target platform {binding.target_platform!r} is bound more than once",
            )
        seen.add(binding.target_platform)
        result.append(
            {
                "targetPlatform": binding.target_platform,
                "externalName": binding.external_name,
            }
        )
    return result


def _decode_externals(j: object, loc: Location) -> list[v.ExternalBinding]:
    items = _expect_list(j, loc, "ExternalBody")
    if not items:
        raise fail(
            d.INVALID_JSON,
            "ExternalBody",
            loc,
            "an external body needs at least one platform binding",
        )
    bindings: list[v.ExternalBinding] = []
    for i, item in enumerate(items):
        here = (*loc, i)
        obj = _expect_object(item, here, "ExternalBinding")
        _check_members(
            obj, _m("targetPlatform externalName", ""), here, "ExternalBinding"
        )
        bindings.append(
            v.ExternalBinding(
                _expect_str(
                    obj["targetPlatform"], (*here, "targetPlatform"), "ExternalBinding"
                ),
                _expect_str(
                    obj["externalName"], (*here, "externalName"), "ExternalBinding"
                ),
            )
        )
    # Re-encode to apply the same uniqueness rule as the writer.
    _encode_externals(bindings, loc)
    return bindings


def encode_value_definition(defn: v.ValueDefinitionBody, loc: Location = ()) -> Json:
    """Encode a value definition as ``{"<Kind>Body": {...}}``.

    Raises:
        DiagnosticError: With ``no_v4_spelling`` when an expression-body input
            carries attributes other than its declared type, ``duplicate_member``
            when an external body binds a platform twice, and ``invalid_json``
            when it binds none.
    """
    match defn:
        case v.Definition():
            return _encode_expression_body(defn, loc)
        case v.NativeBody(inputs, output, info):
            here = (*loc, "NativeBody")
            return _wrap(
                "NativeBody",
                {
                    "inputTypes": _encode_inputs(
                        inputs, (*here, "inputTypes"), "NativeBody"
                    ),
                    "outputType": encode_type(output, (*here, "outputType")),
                    "nativeInfo": {"hint": _encode_native_hint(info.hint)},
                },
            )
        case v.ExternalBody(inputs, output, externals, fallback):
            here = (*loc, "ExternalBody")
            members: dict[str, Json] = {
                "inputTypes": _encode_inputs(
                    inputs, (*here, "inputTypes"), "ExternalBody"
                ),
                "outputType": encode_type(output, (*here, "outputType")),
                "externals": _encode_externals(externals, (*here, "externals")),
            }
            if fallback is not None:
                members["body"] = encode_value(fallback, (*here, "body"))
            return _wrap("ExternalBody", members)
        case v.IncompleteBody(inputs, incompleteness, output, partial):
            here = (*loc, "IncompleteBody")
            members = {
                "inputTypes": _encode_inputs(
                    inputs, (*here, "inputTypes"), "IncompleteBody"
                )
            }
            if output is not None:
                members["outputType"] = encode_type(output, (*here, "outputType"))
            members["incompleteness"] = encode_incompleteness(
                incompleteness, (*here, "incompleteness")
            )
            if partial is not None:
                members["partialBody"] = encode_value(partial, (*here, "partialBody"))
            return _wrap("IncompleteBody", members)


def decode_value_definition(j: object, loc: Location = ()) -> v.ValueDefinitionBody:
    """Decode an expression, native, external or incomplete body."""
    tag, body, here = _node(j, loc, "ValueDefinition", VALUE_DEFINITION_NODES)
    inputs = _unkeyed(
        body["inputTypes"],
        decode_name,
        decode_type,
        (*here, "inputTypes"),
        "inputTypes",
    )

    def optional_type(key: str) -> t.Type | None:
        return decode_type(body[key], (*here, key)) if key in body else None

    def optional_value(key: str) -> v.Value | None:
        return decode_value(body[key], (*here, key)) if key in body else None

    match tag:
        case "ExpressionBody":
            return v.Definition(
                [(n, v.ValueAttributes(inferred_type=tp), tp) for n, tp in inputs],
                decode_type(body["outputType"], (*here, "outputType")),
                decode_value(body["body"], (*here, "body")),
            )
        case "NativeBody":
            info_loc = (*here, "nativeInfo")
            info = _expect_object(body["nativeInfo"], info_loc, "NativeInfo")
            _check_members(info, _m("hint", ""), info_loc, "NativeInfo")
            return v.NativeBody(
                inputs,
                decode_type(body["outputType"], (*here, "outputType")),
                v.NativeInfo(_decode_native_hint(info["hint"], (*info_loc, "hint"))),
            )
        case "ExternalBody":
            return v.ExternalBody(
                inputs,
                decode_type(body["outputType"], (*here, "outputType")),
                _decode_externals(body["externals"], (*here, "externals")),
                optional_value("body"),
            )
        case _:
            return v.IncompleteBody(
                inputs,
                decode_incompleteness(
                    body["incompleteness"], (*here, "incompleteness")
                ),
                optional_type("outputType"),
                optional_value("partialBody"),
            )


def encode_value_specification(spec: v.Specification, loc: Location = ()) -> Json:
    return _with_annotations(
        spec.annotations,
        loc,
        {
            "inputs": _encode_inputs(
                spec.inputs, (*loc, "inputs"), "ValueSpecification"
            ),
            "output": encode_type(spec.output, (*loc, "output")),
        },
    )


def decode_value_specification(j: object, loc: Location = ()) -> v.Specification:
    obj = _expect_object(j, loc, "ValueSpecification")
    _check_members(obj, _m("inputs output", "annotations"), loc, "ValueSpecification")
    return v.Specification(
        _unkeyed(obj["inputs"], decode_name, decode_type, (*loc, "inputs"), "inputs"),
        decode_type(obj["output"], (*loc, "output")),
        _decode_annotations(obj, loc),
    )


# --- Annotations ---


def encode_annotation(item: ann.Annotation, loc: Location = ()) -> Json:
    """Encode an annotation in the form it was written in."""
    match item:
        case ann.CompactAnnotation(name, text):
            fqn = encode_fqname(name, loc)
            return fqn if text is None else f"{fqn}:{text}"
        case ann.StructuredAnnotation(name, arguments):
            members: dict[str, Json] = {"name": encode_fqname(name, loc)}
            if arguments:
                members["arguments"] = [
                    _encode_annotation_argument(x, (*loc, "arguments", i))
                    for i, x in enumerate(arguments)
                ]
            return members


def _encode_annotation_argument(arg: ann.AnnotationArgument, loc: Location) -> Json:
    match arg:
        case ann.PositionalArgument(value):
            return encode_value(value, loc)
        case ann.NamedArgument(name, value):
            return {
                "name": encode_name(name, loc),
                "value": encode_value(value, (*loc, "value")),
            }


def decode_annotation(j: object, loc: Location = ()) -> ann.Annotation:
    """Decode a compact string or a structured annotation object.

    In the compact form the free text starts after the first colon after ``#``.
    """
    if isinstance(j, str):
        hash_at = j.find("#")
        colon_at = j.find(":", hash_at) if hash_at >= 0 else -1
        if colon_at < 0:
            return ann.CompactAnnotation(decode_fqname(j, loc))
        return ann.CompactAnnotation(
            decode_fqname(j[:colon_at], loc), j[colon_at + 1 :]
        )
    obj = _expect_object(j, loc, "Annotation")
    _check_members(obj, _m("name", "arguments"), loc, "Annotation")
    arguments = (
        _decode_list(
            _decode_annotation_argument,
            obj["arguments"],
            (*loc, "arguments"),
            "Annotation",
        )
        if "arguments" in obj
        else []
    )
    return ann.StructuredAnnotation(decode_fqname(obj["name"], loc), arguments)


def _decode_annotation_argument(j: object, loc: Location) -> ann.AnnotationArgument:
    if isinstance(j, dict) and set(j) == {"name", "value"}:
        return ann.NamedArgument(
            decode_name(j["name"], (*loc, "name")),
            decode_value(j["value"], (*loc, "value")),
        )
    return ann.PositionalArgument(decode_value(j, loc))


def _with_annotations(
    annotations: list[ann.Annotation], loc: Location, members: dict[str, Json]
) -> dict[str, Json]:
    """Put a non-empty ``annotations`` member first, as the kit writes it."""
    if not annotations:
        return members
    encoded = [
        encode_annotation(x, (*loc, "annotations", i))
        for i, x in enumerate(annotations)
    ]
    return {"annotations": encoded, **members}


def _decode_annotations(obj: dict[str, object], loc: Location) -> list[ann.Annotation]:
    if "annotations" not in obj:
        return []
    return _decode_list(
        decode_annotation, obj["annotations"], (*loc, "annotations"), "annotations"
    )


# --- Type specifications and definitions ---


def _encode_params(params: list[Name], loc: Location) -> list[Json]:
    return [encode_name(p, loc) for p in params]


def _decode_params(j: object, loc: Location) -> list[Name]:
    return _decode_list(decode_name, j, loc, "typeParams")


def _encode_constructors(ctors: ts.Constructors, loc: Location) -> Json:
    def encode_args(args: list[tuple[Name, t.Type]], here: Location) -> Json:
        return [
            [encode_name(n, here), encode_type(tp, (*here, i))]
            for i, (n, tp) in enumerate(args)
        ]

    return _keyed(ctors, _name_key, encode_args, (*loc, "constructors"), "Constructors")


def _decode_constructors(j: object, loc: Location) -> ts.Constructors:
    def decode_args(j: object, here: Location) -> list[tuple[Name, t.Type]]:
        args: list[tuple[Name, t.Type]] = []
        for i, pair in enumerate(_expect_list(j, here, "Constructor")):
            items = _expect_list(pair, (*here, i), "ConstructorArg")
            if len(items) != 2:
                raise fail(
                    d.INVALID_JSON,
                    "ConstructorArg",
                    (*here, i),
                    "a constructor argument is [name, type]",
                )
            args.append(
                (decode_name(items[0], (*here, i)), decode_type(items[1], (*here, i)))
            )
        return args

    return dict(_unkeyed(j, decode_name, decode_args, loc, "Constructors"))


def encode_type_specification(spec: ts.Specification, loc: Location = ()) -> Json:
    tag = type(spec).__name__
    encoded = _encode_type_specification(spec, loc)
    return _wrap(tag, _with_annotations(spec.annotations, (*loc, tag), encoded[tag]))


def _encode_type_specification(spec: ts.Specification, loc: Location) -> Json:
    params = _encode_params(spec.type_params, loc)
    match spec:
        case ts.TypeAliasSpecification(_, tpe):
            here = (*loc, "TypeAliasSpecification")
            return _wrap(
                "TypeAliasSpecification",
                {"typeParams": params, "typeExp": encode_type(tpe, (*here, "typeExp"))},
            )
        case ts.OpaqueTypeSpecification(_):
            return _wrap("OpaqueTypeSpecification", {"typeParams": params})
        case ts.CustomTypeSpecification(_, ctors):
            here = (*loc, "CustomTypeSpecification")
            return _wrap(
                "CustomTypeSpecification",
                {
                    "typeParams": params,
                    "constructors": _encode_constructors(ctors, here),
                },
            )
        case ts.DerivedTypeSpecification(_, details):
            here = (*loc, "DerivedTypeSpecification")
            return _wrap(
                "DerivedTypeSpecification",
                {
                    "typeParams": params,
                    "baseType": encode_type(details.base_type, (*here, "baseType")),
                    "fromBaseType": encode_fqname(details.from_base_type, here),
                    "toBaseType": encode_fqname(details.to_base_type, here),
                },
            )


def decode_type_specification(j: object, loc: Location = ()) -> ts.Specification:
    tag, body, here = _node(j, loc, "TypeSpecification", TYPE_SPECIFICATION_NODES)
    params = (
        _decode_params(body["typeParams"], (*here, "typeParams"))
        if "typeParams" in body
        else []
    )
    annotations = _decode_annotations(body, here)
    match tag:
        case "TypeAliasSpecification":
            return ts.TypeAliasSpecification(
                params, decode_type(body["typeExp"], (*here, "typeExp")), annotations
            )
        case "OpaqueTypeSpecification":
            return ts.OpaqueTypeSpecification(params, annotations)
        case "CustomTypeSpecification":
            return ts.CustomTypeSpecification(
                params,
                _decode_constructors(body["constructors"], (*here, "constructors")),
                annotations,
            )
        case _:
            return ts.DerivedTypeSpecification(
                params,
                ts.DerivedTypeSpecificationDetails(
                    decode_type(body["baseType"], (*here, "baseType")),
                    decode_fqname(body["fromBaseType"], here),
                    decode_fqname(body["toBaseType"], here),
                ),
                annotations,
            )


def encode_type_definition(defn: td.Definition, loc: Location = ()) -> Json:
    params = _encode_params(defn.type_params, loc)
    match defn:
        case td.TypeAliasDefinition(_, tpe):
            here = (*loc, "TypeAliasDefinition")
            return _wrap(
                "TypeAliasDefinition",
                {"typeParams": params, "typeExp": encode_type(tpe, (*here, "typeExp"))},
            )
        case td.CustomTypeDefinition(_, ctors):
            here = (*loc, "CustomTypeDefinition")
            return _wrap(
                "CustomTypeDefinition",
                {
                    "typeParams": params,
                    "access": "Public" if isinstance(ctors, Public) else "Private",
                    "constructors": _encode_constructors(ctors.value, here),
                },
            )
        case td.IncompleteTypeDefinition(_, incompleteness, partial):
            here = (*loc, "IncompleteTypeDefinition")
            members: dict[str, Json] = {
                "typeParams": params,
                "incompleteness": encode_incompleteness(
                    incompleteness, (*here, "incompleteness")
                ),
            }
            if partial is not None:
                members["partialTypeExp"] = encode_type(
                    partial, (*here, "partialTypeExp")
                )
            return _wrap("IncompleteTypeDefinition", members)


def decode_type_definition(j: object, loc: Location = ()) -> td.Definition:
    tag, body, here = _node(j, loc, "TypeDefinition", TYPE_DEFINITION_NODES)
    params = _decode_params(body["typeParams"], (*here, "typeParams"))
    if tag == "TypeAliasDefinition":
        return td.TypeAliasDefinition(
            params, decode_type(body["typeExp"], (*here, "typeExp"))
        )
    if tag == "IncompleteTypeDefinition":
        return td.IncompleteTypeDefinition(
            params,
            decode_incompleteness(body["incompleteness"], (*here, "incompleteness")),
            decode_type(body["partialTypeExp"], (*here, "partialTypeExp"))
            if "partialTypeExp" in body
            else None,
        )
    access = body.get("access", "Public")
    if access not in ACCESS_TAGS:
        raise fail(
            d.UNKNOWN_NODE, "Access", (*here, "access"), f"unknown access {access!r}"
        )
    ctors = _decode_constructors(body["constructors"], (*here, "constructors"))
    wrapped: AccessControlled[ts.Constructors] = (
        Public(ctors) if access == "Public" else Private(ctors)
    )
    return td.CustomTypeDefinition(params, wrapped)


# --- Documented and access-controlled wrappers ---


def _encode_documented[A](
    encode: Callable[[A, Location], Json],
) -> Callable[[Documented[A], Location], Json]:
    def run(item: Documented[A], loc: Location) -> Json:
        if item.doc is None:
            return encode(item.value, loc)
        return {"doc": item.doc, "value": encode(item.value, (*loc, "value"))}

    return run


def _decode_documented[A](
    decode: Callable[[object, Location], A],
) -> Callable[[object, Location], Documented[A]]:
    def run(j: object, loc: Location) -> Documented[A]:
        if isinstance(j, dict) and set(j) == {"doc", "value"}:
            text = _expect_str(j["doc"], (*loc, "doc"), "Documented")
            return Documented(text, decode(j["value"], (*loc, "value")))
        return Documented(None, decode(j, loc))

    return run


def _encode_access[A](
    encode: Callable[[A, Location], Json],
) -> Callable[[AccessControlled[A], Location], Json]:
    def run(item: AccessControlled[A], loc: Location) -> Json:
        tag = "Public" if isinstance(item, Public) else "Private"
        return {tag: encode(item.value, (*loc, tag))}

    return run


def _decode_access[A](
    decode: Callable[[object, Location], A],
) -> Callable[[object, Location], AccessControlled[A]]:
    def run(j: object, loc: Location) -> AccessControlled[A]:
        tag, payload = _single(j, loc, "AccessControlled", ACCESS_TAGS)
        value = decode(payload, (*loc, tag))
        return Public(value) if tag == "Public" else Private(value)

    return run


def _single(
    j: object, loc: Location, construct: str, tags: dict[str, Any]
) -> tuple[str, object]:
    obj = _expect_object(j, loc, construct)
    if len(obj) != 1 or next(iter(obj)) not in tags:
        raise fail(
            d.UNKNOWN_NODE,
            construct,
            loc,
            f"expected one of {sorted(tags)} for {construct}, found {sorted(obj)}",
        )
    ((tag, payload),) = obj.items()
    return tag, payload


# --- Modules and packages ---

_enc_type_spec = _encode_documented(encode_type_specification)
_dec_type_spec = _decode_documented(decode_type_specification)
_enc_value_spec = _encode_documented(encode_value_specification)
_dec_value_spec = _decode_documented(decode_value_specification)
_enc_type_def = _encode_access(_encode_documented(encode_type_definition))
_dec_type_def = _decode_access(_decode_documented(decode_type_definition))
_enc_value_def = _encode_access(_encode_documented(encode_value_definition))
_dec_value_def = _decode_access(_decode_documented(decode_value_definition))


def _with_doc(members: dict[str, Json], text: str | None) -> dict[str, Json]:
    return {**members, "doc": text} if text is not None else members


def _decode_doc(obj: dict[str, object], loc: Location) -> str | None:
    if "doc" not in obj:
        return None
    return _expect_str(obj["doc"], (*loc, "doc"), "doc")


def encode_module_specification(spec: module.Specification, loc: Location = ()) -> Json:
    return _with_annotations(
        spec.annotations,
        loc,
        _with_doc(
            {
                "types": _keyed(
                    spec.types, _name_key, _enc_type_spec, (*loc, "types"), "types"
                ),
                "values": _keyed(
                    spec.values, _name_key, _enc_value_spec, (*loc, "values"), "values"
                ),
            },
            spec.doc,
        ),
    )


def decode_module_specification(j: object, loc: Location = ()) -> module.Specification:
    obj = _expect_object(j, loc, "ModuleSpecification")
    _check_members(
        obj, _m("", "annotations types values doc"), loc, "ModuleSpecification"
    )
    return module.Specification(
        types=dict(
            _unkeyed(
                obj.get("types", {}),
                decode_name,
                _dec_type_spec,
                (*loc, "types"),
                "types",
            )
        ),
        values=dict(
            _unkeyed(
                obj.get("values", {}),
                decode_name,
                _dec_value_spec,
                (*loc, "values"),
                "values",
            )
        ),
        doc=_decode_doc(obj, loc),
        annotations=_decode_annotations(obj, loc),
    )


def encode_module_definition(defn: module.Definition, loc: Location = ()) -> Json:
    return _with_doc(
        {
            "types": _keyed(
                defn.types, _name_key, _enc_type_def, (*loc, "types"), "types"
            ),
            "values": _keyed(
                defn.values, _name_key, _enc_value_def, (*loc, "values"), "values"
            ),
        },
        defn.doc,
    )


def decode_module_definition(j: object, loc: Location = ()) -> module.Definition:
    obj = _expect_object(j, loc, "ModuleDefinition")
    _check_members(obj, _m("", "types values doc"), loc, "ModuleDefinition")
    return module.Definition(
        types=dict(
            _unkeyed(
                obj.get("types", {}),
                decode_name,
                _dec_type_def,
                (*loc, "types"),
                "types",
            )
        ),
        values=dict(
            _unkeyed(
                obj.get("values", {}),
                decode_name,
                _dec_value_def,
                (*loc, "values"),
                "values",
            )
        ),
        doc=_decode_doc(obj, loc),
    )


_enc_module_def = _encode_access(encode_module_definition)
_dec_module_def = _decode_access(decode_module_definition)


def encode_package_specification(
    spec: package.Specification, loc: Location = ()
) -> Json:
    return {
        "modules": _keyed(
            spec.modules,
            _path_key,
            encode_module_specification,
            (*loc, "modules"),
            "modules",
        )
    }


def decode_package_specification(
    j: object, loc: Location = ()
) -> package.Specification:
    obj = _expect_object(j, loc, "PackageSpecification")
    _check_members(obj, _m("", "modules"), loc, "PackageSpecification")
    return package.Specification(
        dict(
            _unkeyed(
                obj.get("modules", {}),
                decode_path,
                decode_module_specification,
                (*loc, "modules"),
                "modules",
            )
        )
    )


def encode_package_definition(defn: package.Definition, loc: Location = ()) -> Json:
    return {
        "modules": _keyed(
            defn.modules, _path_key, _enc_module_def, (*loc, "modules"), "modules"
        )
    }


def decode_package_definition(j: object, loc: Location = ()) -> package.Definition:
    obj = _expect_object(j, loc, "PackageDefinition")
    _check_members(obj, _m("", "modules"), loc, "PackageDefinition")
    return package.Definition(
        dict(
            _unkeyed(
                obj.get("modules", {}),
                decode_path,
                _dec_module_def,
                (*loc, "modules"),
                "modules",
            )
        )
    )


# --- Distributions ---


def _encode_entry_point(entry: EntryPoint, loc: Location) -> Json:
    out: dict[str, Json] = {
        "target": encode_fqname(entry.target, loc),
        "kind": ENTRY_POINT_KINDS[entry.kind],
    }
    if entry.doc is not None:
        out["doc"] = entry.doc.value
    return out


def _decode_entry_point(j: object, loc: Location) -> EntryPoint:
    obj = _expect_object(j, loc, "EntryPoint")
    _check_members(obj, _m("target kind", "doc"), loc, "EntryPoint")
    kinds = {text: kind for kind, text in ENTRY_POINT_KINDS.items()}
    kind_text = obj["kind"]
    if not isinstance(kind_text, str) or kind_text not in kinds:
        raise fail(
            d.UNKNOWN_NODE,
            "EntryPointKind",
            (*loc, "kind"),
            f"unknown entry point kind {kind_text!r}",
        )
    doc_text = _decode_doc(obj, loc)
    return EntryPoint(
        decode_fqname(obj["target"], (*loc, "target")),
        kinds[kind_text],
        Documented(None, doc_text) if doc_text is not None else None,
    )


def encode_distribution(dist: Distribution, loc: Location = ()) -> Json:
    """Encode a distribution wrapped by its kind.

    The package release version is not written; the v4 profile has no member for it.
    """
    name = encode_path(dist.package.name, loc)
    match dist:
        case LibraryDistribution(_, definition, deps):
            here = (*loc, "Library")
            return {
                "Library": {
                    "packageName": name,
                    "dependencies": _keyed(
                        deps,
                        _path_key,
                        encode_package_specification,
                        (*here, "dependencies"),
                        "dependencies",
                    ),
                    "def": encode_package_definition(definition, (*here, "def")),
                }
            }
        case SpecsDistribution(_, specification, deps):
            here = (*loc, "Specs")
            return {
                "Specs": {
                    "packageName": name,
                    "dependencies": _keyed(
                        deps,
                        _path_key,
                        encode_package_specification,
                        (*here, "dependencies"),
                        "dependencies",
                    ),
                    "spec": encode_package_specification(
                        specification, (*here, "spec")
                    ),
                }
            }
        case ApplicationDistribution(_, definition, deps, entry_points):
            here = (*loc, "Application")
            return {
                "Application": {
                    "packageName": name,
                    "dependencies": _keyed(
                        deps,
                        _path_key,
                        encode_package_definition,
                        (*here, "dependencies"),
                        "dependencies",
                    ),
                    "def": encode_package_definition(definition, (*here, "def")),
                    "entryPoints": _keyed(
                        entry_points,
                        _name_key,
                        _encode_entry_point,
                        (*here, "entryPoints"),
                        "entryPoints",
                    ),
                }
            }


def decode_distribution(j: object, loc: Location = ()) -> Distribution:
    """Decode a distribution wrapped by its kind; the release version is absent."""
    tag, body, here = _node(j, loc, "Distribution", DISTRIBUTION_NODES)
    info = PackageInfo(decode_path(body["packageName"], (*here, "packageName")))
    match tag:
        case "Library":
            return LibraryDistribution(
                info,
                decode_package_definition(body.get("def", {}), (*here, "def")),
                dict(
                    _unkeyed(
                        body.get("dependencies", {}),
                        decode_path,
                        decode_package_specification,
                        (*here, "dependencies"),
                        "dependencies",
                    )
                ),
            )
        case "Specs":
            return SpecsDistribution(
                info,
                decode_package_specification(body.get("spec", {}), (*here, "spec")),
                dict(
                    _unkeyed(
                        body.get("dependencies", {}),
                        decode_path,
                        decode_package_specification,
                        (*here, "dependencies"),
                        "dependencies",
                    )
                ),
            )
        case _:
            return ApplicationDistribution(
                info,
                decode_package_definition(body.get("def", {}), (*here, "def")),
                dict(
                    _unkeyed(
                        body.get("dependencies", {}),
                        decode_path,
                        decode_package_definition,
                        (*here, "dependencies"),
                        "dependencies",
                    )
                ),
                dict(
                    _unkeyed(
                        body["entryPoints"],
                        decode_name,
                        _decode_entry_point,
                        (*here, "entryPoints"),
                        "entryPoints",
                    )
                ),
            )


def encode_versioned_distribution(dist: Distribution) -> dict[str, Json]:
    """Encode ``{"formatVersion": 4, "distribution": ...}``, version first.

    Raises:
        DiagnosticError: When the distribution uses a construct with no draft
            spelling.
    """
    return {
        "formatVersion": write_format_version(V4),
        "distribution": encode_distribution(dist, ("distribution",)),
    }


def decode_versioned_distribution(document: str | object) -> Distribution:
    """Decode a draft v4 document; the version must be in ``[4.0.0,4.1.0)``.

    Args:
        document: JSON text or an already-decoded JSON value.

    Raises:
        DiagnosticError: On a format-version or decoding failure.
    """
    _, root = read_document(document, V4_TABLE)
    _check_members(root, _m("formatVersion distribution", ""), (), "document")
    return decode_distribution(root["distribution"], ("distribution",))


__all__ = [
    "DRAFT_NOTICE",
    "FINOS_MORPHIR_PIN",
    "decode_distribution",
    "decode_fqname",
    "decode_hole_reason",
    "decode_incompleteness",
    "decode_literal",
    "decode_name",
    "decode_path",
    "decode_pattern",
    "decode_type",
    "decode_value",
    "decode_versioned_distribution",
    "encode_distribution",
    "encode_fqname",
    "encode_hole_reason",
    "encode_incompleteness",
    "encode_literal",
    "encode_name",
    "encode_path",
    "encode_pattern",
    "encode_type",
    "encode_value",
    "encode_versioned_distribution",
]
