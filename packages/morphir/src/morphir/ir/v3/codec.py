"""JSON codecs for Morphir IR format 3 (3.0.0 and 3.1.0).

Each section mirrors one morphir-elm codec module at commit bc99af69
(``src/Morphir/IR/*/Codec.elm``). The ``Specs`` distribution of format 3.1.0,
which elm does not have, follows the finos/morphir v3 specification
(``docs/spec/ir/schemas/v3/whats-new.md``) and morphir-rust commit cd9f7fb. As in elm, node codecs take attribute codecs as
parameters, so untyped fragments such as ``["Literal", {}, ["WholeNumberLiteral",
42]]`` decode with `decode_unit`. Dictionaries are written sorted by key, as elm's
``Dict.toList`` does.

The only intended departure from elm for 3.0.0 content is the ``formatVersion``
reader, which is `morphir.ir.format_version` (elm accepts only an integer).

Decoders raise `DiagnosticError` with a location path from the decoded value.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import Any

from .. import diagnostics as d
from ..diagnostics import DiagnosticError, Location, fail
from ..format_version import (
    V3,
    V3_1,
    V3_TABLE,
    FormatVersion,
    read_document,
    write_format_version,
)
from . import literal as lit
from . import module, package
from . import type as t
from . import value as v
from .access_controlled import Access, AccessControlled
from .distribution import Distribution, Library, Specs
from .documented import Documented
from .fqname import FQName
from .name import Name
from .path import Path
from .qname import QName

type Json = Any
type Encoder[A] = Callable[[A], Json]
type Decoder[A] = Callable[[object, Location], A]

# --- Primitive helpers ---


def _expect_list(j: object, loc: Location, construct: str) -> list[object]:
    if not isinstance(j, list):
        raise fail(d.INVALID_JSON, construct, loc, f"expected an array for {construct}")
    return j


def _expect_object(j: object, loc: Location, construct: str) -> dict[str, object]:
    if not isinstance(j, dict):
        raise fail(
            d.INVALID_JSON, construct, loc, f"expected an object for {construct}"
        )
    return j


def _expect_str(j: object, loc: Location, construct: str) -> str:
    if not isinstance(j, str):
        raise fail(d.INVALID_JSON, construct, loc, f"expected a string for {construct}")
    return j


def _index(items: list[object], i: int, loc: Location, construct: str) -> object:
    if i >= len(items):
        raise fail(
            d.MISSING_MEMBER, construct, loc, f"{construct} has no element at index {i}"
        )
    return items[i]


def _field(obj: dict[str, object], key: str, loc: Location, construct: str) -> object:
    if key not in obj:
        raise fail(
            d.MISSING_MEMBER, construct, loc, f"{construct} has no member {key!r}"
        )
    return obj[key]


def _tag(j: object, loc: Location, construct: str) -> tuple[str, list[object]]:
    items = _expect_list(j, loc, construct)
    tag = _expect_str(_index(items, 0, loc, construct), (*loc, 0), construct)
    return tag, items


def _unknown(tag: str, loc: Location, construct: str) -> DiagnosticError:
    return fail(d.UNKNOWN_NODE, construct, loc, f"unknown {construct} kind {tag!r}")


def _list_of[A](
    decode: Decoder[A], j: object, loc: Location, construct: str
) -> tuple[A, ...]:
    items = _expect_list(j, loc, construct)
    return tuple(decode(item, (*loc, i)) for i, item in enumerate(items))


def _pair_list_to_dict[K, A](
    decode_key: Decoder[K],
    decode_value: Decoder[A],
    j: object,
    loc: Location,
    construct: str,
) -> dict[K, A]:
    result: dict[K, A] = {}
    for i, entry in enumerate(_expect_list(j, loc, construct)):
        here = (*loc, i)
        pair = _expect_list(entry, here, construct)
        key = decode_key(_index(pair, 0, here, construct), (*here, 0))
        result[key] = decode_value(_index(pair, 1, here, construct), (*here, 1))
    return result


def _sorted_pairs[K: tuple[Any, ...], A](
    items: dict[K, A], encode_key: Callable[[K], Json], encode_value: Encoder[A]
) -> list[Json]:
    return [
        [encode_key(key), encode_value(value)] for key, value in sorted(items.items())
    ]


# --- Morphir.Codec ---


def encode_unit(_: None) -> Json:
    """Encode elm's unit attribute as an empty object."""
    return {}


def decode_unit(_: object, __: Location = ()) -> None:
    """Decode elm's unit attribute; any JSON value is accepted, as in elm."""
    return None


# --- Name, Path, QName, FQName ---


def encode_name(name: Name) -> Json:
    return list(name)


def decode_name(j: object, loc: Location = ()) -> Name:
    words = _expect_list(j, loc, "Name")
    for i, word in enumerate(words):
        if not isinstance(word, str):
            raise fail(d.INVALID_NAME, "Name", (*loc, i), "name words must be strings")
    return Name(tuple(str(w) for w in words))


def encode_path(path: Path) -> Json:
    return [encode_name(n) for n in path]


def decode_path(j: object, loc: Location = ()) -> Path:
    return Path(_list_of(decode_name, j, loc, "Path"))


def encode_qname(qn: QName) -> Json:
    return [encode_path(qn.module_path), encode_name(qn.local_name)]


def decode_qname(j: object, loc: Location = ()) -> QName:
    items = _expect_list(j, loc, "QName")
    return QName(
        decode_path(_index(items, 0, loc, "QName"), (*loc, 0)),
        decode_name(_index(items, 1, loc, "QName"), (*loc, 1)),
    )


def encode_fqname(fqn: FQName) -> Json:
    return [
        encode_path(fqn.package_path),
        encode_path(fqn.module_path),
        encode_name(fqn.local_name),
    ]


def decode_fqname(j: object, loc: Location = ()) -> FQName:
    items = _expect_list(j, loc, "FQName")
    return FQName(
        decode_path(_index(items, 0, loc, "FQName"), (*loc, 0)),
        decode_path(_index(items, 1, loc, "FQName"), (*loc, 1)),
        decode_name(_index(items, 2, loc, "FQName"), (*loc, 2)),
    )


# --- AccessControlled, Documented ---


def encode_access_controlled[A](
    encode_value: Encoder[A],
) -> Encoder[AccessControlled[A]]:
    def encode(ac: AccessControlled[A]) -> Json:
        return {"access": ac.access.value, "value": encode_value(ac.value)}

    return encode


def decode_access_controlled[A](
    decode_value: Decoder[A],
) -> Decoder[AccessControlled[A]]:
    def decode(j: object, loc: Location = ()) -> AccessControlled[A]:
        obj = _expect_object(j, loc, "AccessControlled")
        access = _expect_str(
            _field(obj, "access", loc, "AccessControlled"),
            (*loc, "access"),
            "AccessControlled",
        )
        try:
            level = Access(access)
        except ValueError:
            raise _unknown(access, (*loc, "access"), "AccessControlled") from None
        return AccessControlled(
            level,
            decode_value(
                _field(obj, "value", loc, "AccessControlled"), (*loc, "value")
            ),
        )

    return decode


def encode_documented[A](encode_value: Encoder[A]) -> Encoder[Documented[A]]:
    def encode(doc: Documented[A]) -> Json:
        return {"doc": doc.doc, "value": encode_value(doc.value)}

    return encode


def decode_documented[A](decode_value: Decoder[A]) -> Decoder[Documented[A]]:
    """Decode ``{"doc", "value"}``, or an undocumented value with doc ``""``."""

    def decode(j: object, loc: Location = ()) -> Documented[A]:
        if isinstance(j, dict) and isinstance(j.get("doc"), str) and "value" in j:
            return Documented(str(j["doc"]), decode_value(j["value"], (*loc, "value")))
        return Documented("", decode_value(j, loc))

    return decode


# --- Literal ---


def encode_literal(literal: lit.Literal) -> Json:
    match literal:
        case lit.BoolLiteral(value):
            return ["BoolLiteral", value]
        case lit.CharLiteral(value):
            return ["CharLiteral", value]
        case lit.StringLiteral(value):
            return ["StringLiteral", value]
        case lit.WholeNumberLiteral(value):
            return ["WholeNumberLiteral", value]
        case lit.FloatLiteral(value):
            return ["FloatLiteral", value]
        case lit.DecimalLiteral(value):
            return ["DecimalLiteral", str(value)]


def decode_literal(j: object, loc: Location = ()) -> lit.Literal:
    tag, items = _tag(j, loc, "Literal")
    payload = _index(items, 1, loc, "Literal")
    here = (*loc, 1)

    def bad(message: str) -> DiagnosticError:
        return fail(d.INVALID_LITERAL, tag, here, message)

    match tag:
        case "BoolLiteral":
            if not isinstance(payload, bool):
                raise bad("BoolLiteral expects a boolean")
            return lit.BoolLiteral(payload)
        case "CharLiteral":
            if not isinstance(payload, str) or not payload:
                raise bad("CharLiteral expects a single character")
            return lit.CharLiteral(payload[0])
        case "StringLiteral":
            if not isinstance(payload, str):
                raise bad("StringLiteral expects a string")
            return lit.StringLiteral(payload)
        case "WholeNumberLiteral":
            if isinstance(payload, bool) or not isinstance(payload, int):
                raise bad("WholeNumberLiteral expects an integer")
            return lit.WholeNumberLiteral(payload)
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
            raise _unknown(tag, loc, "Literal")


# --- Type ---


def encode_type[A](encode_attributes: Encoder[A]) -> Encoder[t.Type[A]]:
    def encode(tpe: t.Type[A]) -> Json:
        a = encode_attributes(tpe.attributes)
        match tpe:
            case t.Variable(_, name):
                return ["Variable", a, encode_name(name)]
            case t.Reference(_, fqn, args):
                return ["Reference", a, encode_fqname(fqn), [encode(x) for x in args]]
            case t.Tuple(_, elements):
                return ["Tuple", a, [encode(x) for x in elements]]
            case t.Record(_, fields):
                return ["Record", a, [encode_field(f) for f in fields]]
            case t.ExtensibleRecord(_, var, fields):
                return [
                    "ExtensibleRecord",
                    a,
                    encode_name(var),
                    [encode_field(f) for f in fields],
                ]
            case t.Function(_, arg, ret):
                return ["Function", a, encode(arg), encode(ret)]
            case t.Unit(_):
                return ["Unit", a]

    def encode_field(f: t.Field[A]) -> Json:
        return {"name": encode_name(f.name), "tpe": encode(f.tpe)}

    return encode


def decode_type[A](decode_attributes: Decoder[A]) -> Decoder[t.Type[A]]:
    def decode(j: object, loc: Location = ()) -> t.Type[A]:
        tag, items = _tag(j, loc, "Type")

        def at(i: int) -> tuple[object, Location]:
            return _index(items, i, loc, tag), (*loc, i)

        attrs = decode_attributes(*at(1))
        match tag:
            case "Variable":
                return t.Variable(attrs, decode_name(*at(2)))
            case "Reference":
                return t.Reference(
                    attrs, decode_fqname(*at(2)), _list_of(decode, *at(3), "Type")
                )
            case "Tuple":
                return t.Tuple(attrs, _list_of(decode, *at(2), "Type"))
            case "Record":
                return t.Record(attrs, _list_of(decode_field, *at(2), "Field"))
            case "ExtensibleRecord":
                return t.ExtensibleRecord(
                    attrs, decode_name(*at(2)), _list_of(decode_field, *at(3), "Field")
                )
            case "Function":
                return t.Function(attrs, decode(*at(2)), decode(*at(3)))
            case "Unit":
                return t.Unit(attrs)
            case _:
                raise _unknown(tag, loc, "Type")

    def decode_field(j: object, loc: Location = ()) -> t.Field[A]:
        obj = _expect_object(j, loc, "Field")
        return t.Field(
            decode_name(_field(obj, "name", loc, "Field"), (*loc, "name")),
            decode(_field(obj, "tpe", loc, "Field"), (*loc, "tpe")),
        )

    return decode


def _encode_constructors[A](
    encode_attributes: Encoder[A],
) -> Encoder[t.Constructors[A]]:
    encode_t = encode_type(encode_attributes)

    def encode(ctors: t.Constructors[A]) -> Json:
        return _sorted_pairs(
            ctors,
            encode_name,
            lambda args: [[encode_name(n), encode_t(tp)] for n, tp in args],
        )

    return encode


def _decode_constructors[A](
    decode_attributes: Decoder[A],
) -> Decoder[t.Constructors[A]]:
    decode_t = decode_type(decode_attributes)

    def decode_arg(j: object, loc: Location) -> tuple[Name, t.Type[A]]:
        pair = _expect_list(j, loc, "ConstructorArg")
        return (
            decode_name(_index(pair, 0, loc, "ConstructorArg"), (*loc, 0)),
            decode_t(_index(pair, 1, loc, "ConstructorArg"), (*loc, 1)),
        )

    def decode_args(j: object, loc: Location) -> t.ConstructorArgs[A]:
        return _list_of(decode_arg, j, loc, "Constructor")

    def decode(j: object, loc: Location = ()) -> t.Constructors[A]:
        return _pair_list_to_dict(decode_name, decode_args, j, loc, "Constructors")

    return decode


def encode_type_specification[A](
    encode_attributes: Encoder[A],
) -> Encoder[t.Specification[A]]:
    encode_t = encode_type(encode_attributes)
    encode_ctors = _encode_constructors(encode_attributes)

    def encode(spec: t.Specification[A]) -> Json:
        params = [encode_name(p) for p in spec.type_params]
        match spec:
            case t.TypeAliasSpecification(_, tpe):
                return ["TypeAliasSpecification", params, encode_t(tpe)]
            case t.OpaqueTypeSpecification(_):
                return ["OpaqueTypeSpecification", params]
            case t.CustomTypeSpecification(_, ctors):
                return ["CustomTypeSpecification", params, encode_ctors(ctors)]
            case t.DerivedTypeSpecification(_, base, from_base, to_base):
                return [
                    "DerivedTypeSpecification",
                    params,
                    {
                        "baseType": encode_t(base),
                        "fromBaseType": encode_fqname(from_base),
                        "toBaseType": encode_fqname(to_base),
                    },
                ]

    return encode


def decode_type_specification[A](
    decode_attributes: Decoder[A],
) -> Decoder[t.Specification[A]]:
    decode_t = decode_type(decode_attributes)
    decode_ctors = _decode_constructors(decode_attributes)

    def decode(j: object, loc: Location = ()) -> t.Specification[A]:
        tag, items = _tag(j, loc, "TypeSpecification")

        def at(i: int) -> tuple[object, Location]:
            return _index(items, i, loc, tag), (*loc, i)

        match tag:
            case "TypeAliasSpecification":
                return t.TypeAliasSpecification(
                    _list_of(decode_name, *at(1), "Name"), decode_t(*at(2))
                )
            case "OpaqueTypeSpecification":
                return t.OpaqueTypeSpecification(_list_of(decode_name, *at(1), "Name"))
            case "CustomTypeSpecification":
                return t.CustomTypeSpecification(
                    _list_of(decode_name, *at(1), "Name"), decode_ctors(*at(2))
                )
            case "DerivedTypeSpecification":
                params = _list_of(decode_name, *at(1), "Name")
                config_json, config_loc = at(2)
                config = _expect_object(config_json, config_loc, tag)

                def member(key: str) -> tuple[object, Location]:
                    return _field(config, key, config_loc, tag), (*config_loc, key)

                return t.DerivedTypeSpecification(
                    params,
                    decode_t(*member("baseType")),
                    decode_fqname(*member("fromBaseType")),
                    decode_fqname(*member("toBaseType")),
                )
            case _:
                raise _unknown(tag, loc, "TypeSpecification")

    return decode


def encode_type_definition[A](
    encode_attributes: Encoder[A],
) -> Encoder[t.Definition[A]]:
    encode_t = encode_type(encode_attributes)
    encode_ctors = encode_access_controlled(_encode_constructors(encode_attributes))

    def encode(defn: t.Definition[A]) -> Json:
        params = [encode_name(p) for p in defn.type_params]
        match defn:
            case t.TypeAliasDefinition(_, tpe):
                return ["TypeAliasDefinition", params, encode_t(tpe)]
            case t.CustomTypeDefinition(_, ctors):
                return ["CustomTypeDefinition", params, encode_ctors(ctors)]

    return encode


def decode_type_definition[A](
    decode_attributes: Decoder[A],
) -> Decoder[t.Definition[A]]:
    decode_t = decode_type(decode_attributes)
    decode_ctors = decode_access_controlled(_decode_constructors(decode_attributes))

    def decode(j: object, loc: Location = ()) -> t.Definition[A]:
        tag, items = _tag(j, loc, "TypeDefinition")

        def at(i: int) -> tuple[object, Location]:
            return _index(items, i, loc, tag), (*loc, i)

        match tag:
            case "TypeAliasDefinition":
                return t.TypeAliasDefinition(
                    _list_of(decode_name, *at(1), "Name"), decode_t(*at(2))
                )
            case "CustomTypeDefinition":
                return t.CustomTypeDefinition(
                    _list_of(decode_name, *at(1), "Name"), decode_ctors(*at(2))
                )
            case _:
                raise _unknown(tag, loc, "TypeDefinition")

    return decode


# --- Value ---


def encode_pattern[A](encode_attributes: Encoder[A]) -> Encoder[v.Pattern[A]]:
    def encode(p: v.Pattern[A]) -> Json:
        a = encode_attributes(p.attributes)
        match p:
            case v.WildcardPattern(_):
                return ["WildcardPattern", a]
            case v.AsPattern(_, inner, name):
                return ["AsPattern", a, encode(inner), encode_name(name)]
            case v.TuplePattern(_, elements):
                return ["TuplePattern", a, [encode(x) for x in elements]]
            case v.ConstructorPattern(_, fqn, args):
                return [
                    "ConstructorPattern",
                    a,
                    encode_fqname(fqn),
                    [encode(x) for x in args],
                ]
            case v.EmptyListPattern(_):
                return ["EmptyListPattern", a]
            case v.HeadTailPattern(_, head, tail):
                return ["HeadTailPattern", a, encode(head), encode(tail)]
            case v.LiteralPattern(_, literal):
                return ["LiteralPattern", a, encode_literal(literal)]
            case v.UnitPattern(_):
                return ["UnitPattern", a]

    return encode


def decode_pattern[A](decode_attributes: Decoder[A]) -> Decoder[v.Pattern[A]]:
    def decode(j: object, loc: Location = ()) -> v.Pattern[A]:
        tag, items = _tag(j, loc, "Pattern")

        def at(i: int) -> tuple[object, Location]:
            return _index(items, i, loc, tag), (*loc, i)

        attrs = decode_attributes(*at(1))
        match tag:
            case "WildcardPattern":
                return v.WildcardPattern(attrs)
            case "AsPattern":
                return v.AsPattern(attrs, decode(*at(2)), decode_name(*at(3)))
            case "TuplePattern":
                return v.TuplePattern(attrs, _list_of(decode, *at(2), "Pattern"))
            case "ConstructorPattern":
                return v.ConstructorPattern(
                    attrs, decode_fqname(*at(2)), _list_of(decode, *at(3), "Pattern")
                )
            case "EmptyListPattern":
                return v.EmptyListPattern(attrs)
            case "HeadTailPattern":
                return v.HeadTailPattern(attrs, decode(*at(2)), decode(*at(3)))
            case "LiteralPattern":
                return v.LiteralPattern(attrs, decode_literal(*at(2)))
            case "UnitPattern":
                return v.UnitPattern(attrs)
            case _:
                raise _unknown(tag, loc, "Pattern")

    return decode


def encode_value[TA, VA](
    encode_type_attributes: Encoder[TA], encode_value_attributes: Encoder[VA]
) -> Encoder[v.Value[TA, VA]]:
    encode_p = encode_pattern(encode_value_attributes)

    def encode_named(fields: dict[Name, v.Value[TA, VA]]) -> Json:
        return _sorted_pairs(fields, encode_name, encode)

    def encode(val: v.Value[TA, VA]) -> Json:
        a = encode_value_attributes(val.attributes)
        match val:
            case v.LiteralValue(_, literal):
                return ["Literal", a, encode_literal(literal)]
            case v.Constructor(_, fqn):
                return ["Constructor", a, encode_fqname(fqn)]
            case v.Tuple(_, elements):
                return ["Tuple", a, [encode(x) for x in elements]]
            case v.List(_, items):
                return ["List", a, [encode(x) for x in items]]
            case v.Record(_, fields):
                return ["Record", a, encode_named(fields)]
            case v.Variable(_, name):
                return ["Variable", a, encode_name(name)]
            case v.Reference(_, fqn):
                return ["Reference", a, encode_fqname(fqn)]
            case v.Field(_, subject, name):
                return ["Field", a, encode(subject), encode_name(name)]
            case v.FieldFunction(_, name):
                return ["FieldFunction", a, encode_name(name)]
            case v.Apply(_, function, argument):
                return ["Apply", a, encode(function), encode(argument)]
            case v.Lambda(_, pattern, body):
                return ["Lambda", a, encode_p(pattern), encode(body)]
            case v.LetDefinition(_, name, defn, in_value):
                return [
                    "LetDefinition",
                    a,
                    encode_name(name),
                    encode_def(defn),
                    encode(in_value),
                ]
            case v.LetRecursion(_, defs, in_value):
                return [
                    "LetRecursion",
                    a,
                    _sorted_pairs(defs, encode_name, encode_def),
                    encode(in_value),
                ]
            case v.Destructure(_, pattern, subject, in_value):
                return [
                    "Destructure",
                    a,
                    encode_p(pattern),
                    encode(subject),
                    encode(in_value),
                ]
            case v.IfThenElse(_, cond, then_branch, else_branch):
                return [
                    "IfThenElse",
                    a,
                    encode(cond),
                    encode(then_branch),
                    encode(else_branch),
                ]
            case v.PatternMatch(_, subject, cases):
                return [
                    "PatternMatch",
                    a,
                    encode(subject),
                    [[encode_p(p), encode(body)] for p, body in cases],
                ]
            case v.UpdateRecord(_, subject, fields):
                return ["UpdateRecord", a, encode(subject), encode_named(fields)]
            case v.Unit(_):
                return ["Unit", a]

    def encode_def(defn: v.Definition[TA, VA]) -> Json:
        return _encode_value_definition(
            encode_type_attributes, encode_value_attributes, encode, defn
        )

    return encode


def decode_value[TA, VA](
    decode_type_attributes: Decoder[TA], decode_value_attributes: Decoder[VA]
) -> Decoder[v.Value[TA, VA]]:
    decode_p = decode_pattern(decode_value_attributes)

    def decode_named(j: object, loc: Location) -> dict[Name, v.Value[TA, VA]]:
        return _pair_list_to_dict(decode_name, decode, j, loc, "Value")

    def decode_def(j: object, loc: Location) -> v.Definition[TA, VA]:
        return _decode_value_definition(
            decode_type_attributes, decode_value_attributes, decode, j, loc
        )

    def decode(j: object, loc: Location = ()) -> v.Value[TA, VA]:
        tag, items = _tag(j, loc, "Value")

        def at(i: int) -> tuple[object, Location]:
            return _index(items, i, loc, tag), (*loc, i)

        attrs = decode_value_attributes(*at(1))
        match tag:
            case "Literal":
                return v.LiteralValue(attrs, decode_literal(*at(2)))
            case "Constructor":
                return v.Constructor(attrs, decode_fqname(*at(2)))
            case "Tuple":
                return v.Tuple(attrs, _list_of(decode, *at(2), "Value"))
            case "List":
                return v.List(attrs, _list_of(decode, *at(2), "Value"))
            case "Record":
                return v.Record(attrs, decode_named(*at(2)))
            case "Variable":
                return v.Variable(attrs, decode_name(*at(2)))
            case "Reference":
                return v.Reference(attrs, decode_fqname(*at(2)))
            case "Field":
                return v.Field(attrs, decode(*at(2)), decode_name(*at(3)))
            case "FieldFunction":
                return v.FieldFunction(attrs, decode_name(*at(2)))
            case "Apply":
                return v.Apply(attrs, decode(*at(2)), decode(*at(3)))
            case "Lambda":
                return v.Lambda(attrs, decode_p(*at(2)), decode(*at(3)))
            case "LetDefinition":
                return v.LetDefinition(
                    attrs, decode_name(*at(2)), decode_def(*at(3)), decode(*at(4))
                )
            case "LetRecursion":
                return v.LetRecursion(
                    attrs,
                    _pair_list_to_dict(decode_name, decode_def, *at(2), "Definition"),
                    decode(*at(3)),
                )
            case "Destructure":
                return v.Destructure(
                    attrs, decode_p(*at(2)), decode(*at(3)), decode(*at(4))
                )
            case "IfThenElse":
                return v.IfThenElse(
                    attrs, decode(*at(2)), decode(*at(3)), decode(*at(4))
                )
            case "PatternMatch":
                cases_json, cases_loc = at(3)
                cases = []
                for i, case in enumerate(_expect_list(cases_json, cases_loc, tag)):
                    here = (*cases_loc, i)
                    pair = _expect_list(case, here, "Case")
                    cases.append(
                        (
                            decode_p(_index(pair, 0, here, "Case"), (*here, 0)),
                            decode(_index(pair, 1, here, "Case"), (*here, 1)),
                        )
                    )
                return v.PatternMatch(attrs, decode(*at(2)), tuple(cases))
            case "UpdateRecord":
                return v.UpdateRecord(attrs, decode(*at(2)), decode_named(*at(3)))
            case "Unit":
                return v.Unit(attrs)
            case _:
                raise _unknown(tag, loc, "Value")

    return decode


def encode_value_specification[A](
    encode_attributes: Encoder[A],
) -> Encoder[v.Specification[A]]:
    encode_t = encode_type(encode_attributes)

    def encode(spec: v.Specification[A]) -> Json:
        return {
            "inputs": [[encode_name(n), encode_t(tp)] for n, tp in spec.inputs],
            "output": encode_t(spec.output),
        }

    return encode


def decode_value_specification[A](
    decode_attributes: Decoder[A],
) -> Decoder[v.Specification[A]]:
    decode_t = decode_type(decode_attributes)

    def decode_input(j: object, loc: Location) -> tuple[Name, t.Type[A]]:
        pair = _expect_list(j, loc, "Input")
        return (
            decode_name(_index(pair, 0, loc, "Input"), (*loc, 0)),
            decode_t(_index(pair, 1, loc, "Input"), (*loc, 1)),
        )

    def decode(j: object, loc: Location = ()) -> v.Specification[A]:
        obj = _expect_object(j, loc, "ValueSpecification")
        return v.Specification(
            _list_of(
                decode_input,
                _field(obj, "inputs", loc, "ValueSpecification"),
                (*loc, "inputs"),
                "Input",
            ),
            decode_t(
                _field(obj, "output", loc, "ValueSpecification"), (*loc, "output")
            ),
        )

    return decode


def _encode_value_definition[TA, VA](
    encode_type_attributes: Encoder[TA],
    encode_value_attributes: Encoder[VA],
    encode_body: Encoder[v.Value[TA, VA]],
    defn: v.Definition[TA, VA],
) -> Json:
    encode_t = encode_type(encode_type_attributes)
    return {
        "inputTypes": [
            [encode_name(n), encode_value_attributes(a), encode_t(tp)]
            for n, a, tp in defn.input_types
        ],
        "outputType": encode_t(defn.output_type),
        "body": encode_body(defn.body),
    }


def _decode_value_definition[TA, VA](
    decode_type_attributes: Decoder[TA],
    decode_value_attributes: Decoder[VA],
    decode_body: Decoder[v.Value[TA, VA]],
    j: object,
    loc: Location,
) -> v.Definition[TA, VA]:
    decode_t = decode_type(decode_type_attributes)
    construct = "ValueDefinition"
    obj = _expect_object(j, loc, construct)

    def decode_input(j: object, loc: Location) -> tuple[Name, VA, t.Type[TA]]:
        triple = _expect_list(j, loc, "Input")
        return (
            decode_name(_index(triple, 0, loc, "Input"), (*loc, 0)),
            decode_value_attributes(_index(triple, 1, loc, "Input"), (*loc, 1)),
            decode_t(_index(triple, 2, loc, "Input"), (*loc, 2)),
        )

    return v.Definition(
        _list_of(
            decode_input,
            _field(obj, "inputTypes", loc, construct),
            (*loc, "inputTypes"),
            "Input",
        ),
        decode_t(_field(obj, "outputType", loc, construct), (*loc, "outputType")),
        decode_body(_field(obj, "body", loc, construct), (*loc, "body")),
    )


def encode_value_definition[TA, VA](
    encode_type_attributes: Encoder[TA], encode_value_attributes: Encoder[VA]
) -> Encoder[v.Definition[TA, VA]]:
    encode_body = encode_value(encode_type_attributes, encode_value_attributes)

    def encode(defn: v.Definition[TA, VA]) -> Json:
        return _encode_value_definition(
            encode_type_attributes, encode_value_attributes, encode_body, defn
        )

    return encode


def decode_value_definition[TA, VA](
    decode_type_attributes: Decoder[TA], decode_value_attributes: Decoder[VA]
) -> Decoder[v.Definition[TA, VA]]:
    decode_body = decode_value(decode_type_attributes, decode_value_attributes)

    def decode(j: object, loc: Location = ()) -> v.Definition[TA, VA]:
        return _decode_value_definition(
            decode_type_attributes, decode_value_attributes, decode_body, j, loc
        )

    return decode


# --- Module ---


def _decode_doc(obj: dict[str, object]) -> str | None:
    doc = obj.get("doc")
    return doc if isinstance(doc, str) else None


def encode_module_specification[TA](
    encode_type_attributes: Encoder[TA],
) -> Encoder[module.Specification[TA]]:
    encode_ts = encode_documented(encode_type_specification(encode_type_attributes))
    encode_vs = encode_documented(encode_value_specification(encode_type_attributes))

    def encode(spec: module.Specification[TA]) -> Json:
        return {
            "types": _sorted_pairs(spec.types, encode_name, encode_ts),
            "values": _sorted_pairs(spec.values, encode_name, encode_vs),
            "doc": spec.doc,
        }

    return encode


def decode_module_specification[TA](
    decode_type_attributes: Decoder[TA],
) -> Decoder[module.Specification[TA]]:
    decode_ts = decode_documented(decode_type_specification(decode_type_attributes))
    decode_vs = decode_documented(decode_value_specification(decode_type_attributes))
    construct = "ModuleSpecification"

    def decode(j: object, loc: Location = ()) -> module.Specification[TA]:
        obj = _expect_object(j, loc, construct)
        return module.Specification(
            _pair_list_to_dict(
                decode_name,
                decode_ts,
                _field(obj, "types", loc, construct),
                (*loc, "types"),
                "Types",
            ),
            _pair_list_to_dict(
                decode_name,
                decode_vs,
                _field(obj, "values", loc, construct),
                (*loc, "values"),
                "Values",
            ),
            _decode_doc(obj),
        )

    return decode


def encode_module_definition[TA, VA](
    encode_type_attributes: Encoder[TA], encode_value_attributes: Encoder[VA]
) -> Encoder[module.Definition[TA, VA]]:
    encode_td = encode_access_controlled(
        encode_documented(encode_type_definition(encode_type_attributes))
    )
    encode_vd = encode_access_controlled(
        encode_documented(
            encode_value_definition(encode_type_attributes, encode_value_attributes)
        )
    )

    def encode(defn: module.Definition[TA, VA]) -> Json:
        return {
            "types": _sorted_pairs(defn.types, encode_name, encode_td),
            "values": _sorted_pairs(defn.values, encode_name, encode_vd),
            "doc": defn.doc,
        }

    return encode


def decode_module_definition[TA, VA](
    decode_type_attributes: Decoder[TA], decode_value_attributes: Decoder[VA]
) -> Decoder[module.Definition[TA, VA]]:
    decode_td = decode_access_controlled(
        decode_documented(decode_type_definition(decode_type_attributes))
    )
    decode_vd = decode_access_controlled(
        decode_documented(
            decode_value_definition(decode_type_attributes, decode_value_attributes)
        )
    )
    construct = "ModuleDefinition"

    def decode(j: object, loc: Location = ()) -> module.Definition[TA, VA]:
        obj = _expect_object(j, loc, construct)
        return module.Definition(
            _pair_list_to_dict(
                decode_name,
                decode_td,
                _field(obj, "types", loc, construct),
                (*loc, "types"),
                "Types",
            ),
            _pair_list_to_dict(
                decode_name,
                decode_vd,
                _field(obj, "values", loc, construct),
                (*loc, "values"),
                "Values",
            ),
            _decode_doc(obj),
        )

    return decode


# --- Package ---


def encode_package_specification[TA](
    encode_type_attributes: Encoder[TA],
) -> Encoder[package.Specification[TA]]:
    encode_m = encode_module_specification(encode_type_attributes)

    def encode(spec: package.Specification[TA]) -> Json:
        return {"modules": _sorted_pairs(spec.modules, encode_path, encode_m)}

    return encode


def decode_package_specification[TA](
    decode_type_attributes: Decoder[TA],
) -> Decoder[package.Specification[TA]]:
    decode_m = decode_module_specification(decode_type_attributes)
    construct = "PackageSpecification"

    def decode(j: object, loc: Location = ()) -> package.Specification[TA]:
        obj = _expect_object(j, loc, construct)
        return package.Specification(
            _pair_list_to_dict(
                decode_path,
                decode_m,
                _field(obj, "modules", loc, construct),
                (*loc, "modules"),
                "Modules",
            )
        )

    return decode


def encode_package_definition[TA, VA](
    encode_type_attributes: Encoder[TA], encode_value_attributes: Encoder[VA]
) -> Encoder[package.Definition[TA, VA]]:
    encode_m = encode_access_controlled(
        encode_module_definition(encode_type_attributes, encode_value_attributes)
    )

    def encode(defn: package.Definition[TA, VA]) -> Json:
        return {"modules": _sorted_pairs(defn.modules, encode_path, encode_m)}

    return encode


def decode_package_definition[TA, VA](
    decode_type_attributes: Decoder[TA], decode_value_attributes: Decoder[VA]
) -> Decoder[package.Definition[TA, VA]]:
    decode_m = decode_access_controlled(
        decode_module_definition(decode_type_attributes, decode_value_attributes)
    )
    construct = "PackageDefinition"

    def decode(j: object, loc: Location = ()) -> package.Definition[TA, VA]:
        obj = _expect_object(j, loc, construct)
        return package.Definition(
            _pair_list_to_dict(
                decode_path,
                decode_m,
                _field(obj, "modules", loc, construct),
                (*loc, "modules"),
                "Modules",
            )
        )

    return decode


# --- Distribution ---

_encode_typed_type = encode_type(encode_unit)
_decode_typed_type = decode_type(decode_unit)
_encode_dependency = encode_package_specification(encode_unit)
_decode_dependency = decode_package_specification(decode_unit)
_encode_library_def = encode_package_definition(encode_unit, _encode_typed_type)
_decode_library_def = decode_package_definition(decode_unit, _decode_typed_type)


_encode_specs_def = encode_package_specification(encode_unit)
_SPECS_MODULE_MEMBERS = frozenset({"types", "values", "doc"})


def _decode_specs_module(j: object, loc: Location = ()) -> module.Specification[None]:
    """Decode one of a Specs distribution's own modules, refusing other members.

    The elm-faithful module-specification decoder ignores unknown members, so a
    module definition would read as a broken specification. As in morphir-rust
    ``SpecsModuleEntry``, only ``types``, ``values`` and ``doc`` are accepted here.
    """
    obj = _expect_object(j, loc, "ModuleSpecification")
    for key in obj:
        if key not in _SPECS_MODULE_MEMBERS:
            raise fail(
                d.UNKNOWN_MEMBER,
                "ModuleSpecification",
                (*loc, key),
                "a v3 Specs distribution holds module specifications, not "
                f"definitions: unexpected member {key!r}",
            )
    return _decode_dependency_module(obj, loc)


_decode_dependency_module = decode_module_specification(decode_unit)


def _decode_specs_def(j: object, loc: Location = ()) -> package.Specification[None]:
    obj = _expect_object(j, loc, "PackageSpecification")
    return package.Specification(
        _pair_list_to_dict(
            decode_path,
            _decode_specs_module,
            _field(obj, "modules", loc, "PackageSpecification"),
            (*loc, "modules"),
            "Modules",
        )
    )


def encode_distribution(dist: Distribution) -> Json:
    """Encode a distribution as ``[kind, name, deps, def or spec]``.

    A `Library` is elm's ``["Library", name, deps, def]``; a `Specs` is
    ``["Specs", name, deps, spec]``.
    """
    match dist:
        case Library():
            return [
                "Library",
                encode_path(dist.package_name),
                _sorted_pairs(dist.dependencies, encode_path, _encode_dependency),
                _encode_library_def(dist.definition),
            ]
        case Specs():
            return [
                "Specs",
                encode_path(dist.package_name),
                _sorted_pairs(dist.dependencies, encode_path, _encode_dependency),
                _encode_specs_def(dist.specification),
            ]


def decode_distribution(j: object, loc: Location = ()) -> Distribution:
    """Decode a ``Library`` or, from format 3.1.0, a ``Specs`` distribution.

    This decoder does not see ``formatVersion``; `decode_versioned_distribution`
    refuses a ``Specs`` declared below 3.1.0.
    """
    tag, items = _tag(j, loc, "Distribution")
    if tag not in ("Library", "Specs"):
        raise fail(
            d.UNKNOWN_NODE,
            "Distribution",
            (*loc, 0),
            f"unknown distribution kind {tag!r}; format 3 has Library and, "
            "from 3.1.0, Specs",
        )

    def at(i: int) -> tuple[object, Location]:
        return _index(items, i, loc, tag), (*loc, i)

    package_name = decode_path(*at(1))
    dependencies = _pair_list_to_dict(
        decode_path, _decode_dependency, *at(2), "Dependencies"
    )
    if tag == "Specs":
        return Specs(
            package_name=package_name,
            specification=_decode_specs_def(*at(3)),
            dependencies=dependencies,
        )
    return Library(
        package_name=package_name,
        dependencies=dependencies,
        definition=_decode_library_def(*at(3)),
    )


# --- FormatVersion ---


def format_version_of(dist: Distribution) -> FormatVersion:
    """Return the lowest release that expresses ``dist``.

    A `Library` needs only 3.0.0; a `Specs` needs 3.1.0, the release that added
    it (finos/morphir decision record 0018).
    """
    return V3_1 if isinstance(dist, Specs) else V3


def encode_versioned_distribution(dist: Distribution) -> dict[str, Json]:
    """Encode ``{"formatVersion": ..., "distribution": ...}``, version first.

    The version is the lowest one that fits the content: ``3`` for a `Library`,
    ``"3.1.0"`` for a `Specs`, whatever version the input declared.
    """
    return {
        "formatVersion": write_format_version(format_version_of(dist)),
        "distribution": encode_distribution(dist),
    }


def decode_versioned_distribution(document: str | object) -> Distribution:
    """Decode a format-3 ``morphir-ir.json`` document.

    The format version is read with the shared permissive reader and must be in
    ``[3.0.0,3.2.0)``; ``4`` fails with ``unsupported_format_version_major``. A
    ``Specs`` distribution declared below 3.1.0 fails with ``specs_before_3_1``
    before its body is decoded.

    Args:
        document: JSON text or an already-decoded JSON value.

    Raises:
        DiagnosticError: On a format-version or decoding failure.
    """
    version, root = read_document(document, V3_TABLE)
    obj = _expect_object(root, (), "document")
    distribution = _field(obj, "distribution", (), "document")
    loc: Location = ("distribution",)
    tag, _ = _tag(distribution, loc, "Distribution")
    if tag == "Specs" and version < V3_1:
        raise fail(
            d.SPECS_BEFORE_3_1,
            "Specs",
            ("formatVersion",),
            f"a v3 Specs distribution needs formatVersion {V3_1} or later, "
            f"found {obj['formatVersion']!r}",
        )
    return decode_distribution(distribution, loc)


__all__ = [
    "Decoder",
    "Encoder",
    "Json",
    "decode_access_controlled",
    "decode_distribution",
    "decode_documented",
    "decode_fqname",
    "decode_literal",
    "decode_module_definition",
    "decode_module_specification",
    "decode_name",
    "decode_package_definition",
    "decode_package_specification",
    "decode_path",
    "decode_pattern",
    "decode_qname",
    "decode_type",
    "decode_type_definition",
    "decode_type_specification",
    "decode_unit",
    "decode_value",
    "decode_value_definition",
    "decode_value_specification",
    "decode_versioned_distribution",
    "encode_access_controlled",
    "encode_distribution",
    "encode_documented",
    "encode_fqname",
    "encode_literal",
    "encode_module_definition",
    "encode_module_specification",
    "encode_name",
    "encode_package_definition",
    "encode_package_specification",
    "encode_path",
    "encode_pattern",
    "encode_qname",
    "encode_type",
    "encode_type_definition",
    "encode_type_specification",
    "encode_unit",
    "encode_value",
    "encode_value_definition",
    "encode_value_specification",
    "encode_versioned_distribution",
    "format_version_of",
]
