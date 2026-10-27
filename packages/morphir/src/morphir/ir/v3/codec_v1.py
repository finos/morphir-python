"""Read-only JSON decoders for morphir-elm IR format 1, into the 3.0.0 model.

Port of the decoders in morphir-elm ``src/Morphir/IR/*/CodecV1.elm`` at commit
bc99af69, which morphir-elm still uses to read ``"formatVersion": 1``. As in elm,
format 1 decodes into the same model as format 3.0.0, so decoding is the upgrade:
encode the result with `morphir.ir.v3.codec` to write format 3. The encoders are
not ported, because no writer emits format 1.

Format 1 differs from format 3.0.0 only in these spellings:

- every tag is snake_case: ``"library"``, ``"public"``, ``"variable"``,
  ``"custom_type_definition"``, ``"let_definition"``, ``"wildcard_pattern"``;
- literal tags are ``"bool_literal"``, ``"char_literal"``, ``"string_literal"``,
  ``"int_literal"``, ``"float_literal"`` and ``"decimal_literal"``;
- access control is ``["public", x]``, documentation is ``[doc, x]`` or the bare
  ``x``, and a record field type is ``[name, type]``;
- package modules are ``{"name", "spec"}`` and ``{"name", "def"}`` objects;
- modules have no ``doc``; a ``doc`` member is ignored, as in elm.

Names, paths, and qualified names are spelled as in format 3.0.0; use the
`morphir.ir.v3.codec` decoders for them. elm's ``encodeSpecification`` writes a
derived type as ``"DerivedTypeSpecification"`` but ``decodeSpecification`` reads
only ``"derived_type_specification"``; this decoder follows the elm decoder.
"""

from __future__ import annotations

from .. import diagnostics as d
from ..diagnostics import DiagnosticError, Location, fail
from ..format_version import LegacyFormat, read_legacy_document
from . import _legacy_value, module, package
from . import literal as lit
from . import type as t
from . import value as v
from .access_controlled import Access, AccessControlled
from .codec import (
    Decoder,
    _expect_list,
    _expect_object,
    _field,
    _index,
    _list_of,
    _pair_list_to_dict,
    _tag,
    _unknown,
    decode_fqname,
    decode_name,
    decode_path,
    decode_unit,
)
from .codec import decode_literal as decode_literal_3
from .distribution import Library
from .documented import Documented
from .name import Name
from .path import Path

# --- Literal ---

_LITERAL_TAGS = {
    "bool_literal": "BoolLiteral",
    "char_literal": "CharLiteral",
    "string_literal": "StringLiteral",
    "int_literal": "WholeNumberLiteral",
    "float_literal": "FloatLiteral",
    "decimal_literal": "DecimalLiteral",
}


def decode_literal(j: object, loc: Location = ()) -> lit.Literal:
    """Decode a format-1 literal; the payloads are checked as in format 3.0.0."""
    tag, items = _tag(j, loc, "Literal")
    title = _LITERAL_TAGS.get(tag)
    if title is None:
        raise _unknown(tag, loc, "Literal")
    return decode_literal_3([title, *items[1:]], loc)


# --- AccessControlled, Documented ---


_ACCESS = {"public": Access.PUBLIC, "private": Access.PRIVATE}


def decode_access_controlled[A](
    decode_value: Decoder[A],
) -> Decoder[AccessControlled[A]]:
    """Decode ``["public", x]`` or ``["private", x]``."""

    def decode(j: object, loc: Location = ()) -> AccessControlled[A]:
        tag, items = _tag(j, loc, "AccessControlled")
        access = _ACCESS.get(tag)
        if access is None:
            raise _unknown(tag, loc, "AccessControlled")
        return AccessControlled(
            access, decode_value(_index(items, 1, loc, tag), (*loc, 1))
        )

    return decode


def decode_documented[A](decode_value: Decoder[A]) -> Decoder[Documented[A]]:
    """Decode ``[doc, x]``, or an undocumented ``x`` with doc ``""``.

    As elm's ``Decode.oneOf``, the pair is tried first. When both readings fail,
    the error holds the diagnostics of both.
    """

    def decode(j: object, loc: Location = ()) -> Documented[A]:
        if isinstance(j, list) and len(j) > 1 and isinstance(j[0], str):
            try:
                return Documented(j[0], decode_value(j[1], (*loc, 1)))
            except DiagnosticError as pair_error:
                try:
                    return Documented("", decode_value(j, loc))
                except DiagnosticError as bare_error:
                    raise DiagnosticError(
                        *pair_error.diagnostics, *bare_error.diagnostics
                    ) from None
        return Documented("", decode_value(j, loc))

    return decode


# --- Type ---


def decode_type[A](decode_attributes: Decoder[A]) -> Decoder[t.Type[A]]:
    """Build a format-1 type decoder (elm ``decodeType``)."""

    def decode(j: object, loc: Location = ()) -> t.Type[A]:
        tag, items = _tag(j, loc, "Type")

        def at(i: int) -> tuple[object, Location]:
            return _index(items, i, loc, tag), (*loc, i)

        def attrs() -> A:
            return decode_attributes(*at(1))

        match tag:
            case "variable":
                return t.Variable(attrs(), decode_name(*at(2)))
            case "reference":
                return t.Reference(
                    attrs(), decode_fqname(*at(2)), _list_of(decode, *at(3), "Type")
                )
            case "tuple":
                return t.Tuple(attrs(), _list_of(decode, *at(2), "Type"))
            case "record":
                return t.Record(attrs(), _list_of(decode_field, *at(2), "Field"))
            case "extensible_record":
                return t.ExtensibleRecord(
                    attrs(),
                    decode_name(*at(2)),
                    _list_of(decode_field, *at(3), "Field"),
                )
            case "function":
                return t.Function(attrs(), decode(*at(2)), decode(*at(3)))
            case "unit":
                return t.Unit(attrs())
            case _:
                raise _unknown(tag, loc, "Type")

    def decode_field(j: object, loc: Location = ()) -> t.Field[A]:
        pair = _expect_list(j, loc, "Field")
        return t.Field(
            decode_name(_index(pair, 0, loc, "Field"), (*loc, 0)),
            decode(_index(pair, 1, loc, "Field"), (*loc, 1)),
        )

    return decode


def _decode_constructors[A](
    decode_t: Decoder[t.Type[A]],
) -> Decoder[t.Constructors[A]]:
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


def decode_type_specification[A](
    decode_attributes: Decoder[A],
) -> Decoder[t.Specification[A]]:
    """Build a format-1 type specification decoder."""
    decode_t = decode_type(decode_attributes)
    decode_ctors = _decode_constructors(decode_t)

    def decode(j: object, loc: Location = ()) -> t.Specification[A]:
        tag, items = _tag(j, loc, "TypeSpecification")

        def at(i: int) -> tuple[object, Location]:
            return _index(items, i, loc, tag), (*loc, i)

        def params() -> tuple[Name, ...]:
            return _list_of(decode_name, *at(1), "Name")

        match tag:
            case "type_alias_specification":
                return t.TypeAliasSpecification(params(), decode_t(*at(2)))
            case "opaque_type_specification":
                return t.OpaqueTypeSpecification(params())
            case "custom_type_specification":
                return t.CustomTypeSpecification(params(), decode_ctors(*at(2)))
            case "derived_type_specification":
                config_json, config_loc = at(2)
                config = _expect_object(config_json, config_loc, tag)

                def member(key: str) -> tuple[object, Location]:
                    return _field(config, key, config_loc, tag), (*config_loc, key)

                return t.DerivedTypeSpecification(
                    params(),
                    decode_t(*member("baseType")),
                    decode_fqname(*member("fromBaseType")),
                    decode_fqname(*member("toBaseType")),
                )
            case _:
                raise _unknown(tag, loc, "TypeSpecification")

    return decode


def decode_type_definition[A](
    decode_attributes: Decoder[A],
) -> Decoder[t.Definition[A]]:
    """Build a format-1 type definition decoder."""
    decode_t = decode_type(decode_attributes)
    decode_ctors = decode_access_controlled(_decode_constructors(decode_t))

    def decode(j: object, loc: Location = ()) -> t.Definition[A]:
        tag, items = _tag(j, loc, "TypeDefinition")

        def at(i: int) -> tuple[object, Location]:
            return _index(items, i, loc, tag), (*loc, i)

        match tag:
            case "type_alias_definition":
                return t.TypeAliasDefinition(
                    _list_of(decode_name, *at(1), "Name"), decode_t(*at(2))
                )
            case "custom_type_definition":
                return t.CustomTypeDefinition(
                    _list_of(decode_name, *at(1), "Name"), decode_ctors(*at(2))
                )
            case _:
                raise _unknown(tag, loc, "TypeDefinition")

    return decode


# --- Value ---


def decode_pattern[A](decode_attributes: Decoder[A]) -> Decoder[v.Pattern[A]]:
    """Build a format-1 pattern decoder."""
    return _legacy_value.decode_pattern(decode_literal, decode_attributes)


def decode_value[TA, VA](
    decode_type_attributes: Decoder[TA], decode_value_attributes: Decoder[VA]
) -> Decoder[v.Value[TA, VA]]:
    """Build a format-1 value decoder."""
    return _legacy_value.decode_value(
        decode_literal, decode_type(decode_type_attributes), decode_value_attributes
    )


def decode_value_specification[A](
    decode_attributes: Decoder[A],
) -> Decoder[v.Specification[A]]:
    """Build a decoder for ``{"inputs", "output"}`` with format-1 types."""
    decode_t = decode_type(decode_attributes)
    construct = "ValueSpecification"

    def decode_input(j: object, loc: Location) -> tuple[Name, t.Type[A]]:
        pair = _expect_list(j, loc, "Input")
        return (
            decode_name(_index(pair, 0, loc, "Input"), (*loc, 0)),
            decode_t(_index(pair, 1, loc, "Input"), (*loc, 1)),
        )

    def decode(j: object, loc: Location = ()) -> v.Specification[A]:
        obj = _expect_object(j, loc, construct)
        return v.Specification(
            _list_of(
                decode_input,
                _field(obj, "inputs", loc, construct),
                (*loc, "inputs"),
                "Input",
            ),
            decode_t(_field(obj, "output", loc, construct), (*loc, "output")),
        )

    return decode


def decode_value_definition[TA, VA](
    decode_type_attributes: Decoder[TA], decode_value_attributes: Decoder[VA]
) -> Decoder[v.Definition[TA, VA]]:
    """Build a format-1 value definition decoder."""
    return _legacy_value.decode_value_definition(
        decode_type(decode_type_attributes),
        decode_value_attributes,
        decode_value(decode_type_attributes, decode_value_attributes),
    )


# --- Module ---


def _named[A](
    decode_entry: Decoder[A],
    obj: dict[str, object],
    key: str,
    loc: Location,
    construct: str,
) -> dict[Name, A]:
    return _pair_list_to_dict(
        decode_name,
        decode_entry,
        _field(obj, key, loc, construct),
        (*loc, key),
        key.capitalize(),
    )


def decode_module_specification[TA](
    decode_type_attributes: Decoder[TA],
) -> Decoder[module.Specification[TA]]:
    """Build a format-1 module specification decoder; ``doc`` is always None."""
    decode_ts = decode_documented(decode_type_specification(decode_type_attributes))
    decode_vs = decode_documented(decode_value_specification(decode_type_attributes))

    def decode(j: object, loc: Location = ()) -> module.Specification[TA]:
        construct = "ModuleSpecification"
        obj = _expect_object(j, loc, construct)
        return module.Specification(
            _named(decode_ts, obj, "types", loc, construct),
            _named(decode_vs, obj, "values", loc, construct),
        )

    return decode


def decode_module_definition[TA, VA](
    decode_type_attributes: Decoder[TA], decode_value_attributes: Decoder[VA]
) -> Decoder[module.Definition[TA, VA]]:
    """Build a format-1 module definition decoder; ``doc`` is always None."""
    decode_td = decode_access_controlled(
        decode_documented(decode_type_definition(decode_type_attributes))
    )
    decode_vd = decode_access_controlled(
        decode_documented(
            decode_value_definition(decode_type_attributes, decode_value_attributes)
        )
    )

    def decode(j: object, loc: Location = ()) -> module.Definition[TA, VA]:
        construct = "ModuleDefinition"
        obj = _expect_object(j, loc, construct)
        return module.Definition(
            _named(decode_td, obj, "types", loc, construct),
            _named(decode_vd, obj, "values", loc, construct),
        )

    return decode


# --- Package ---


def _modules[A](
    decode_module: Decoder[A], member: str, j: object, loc: Location, construct: str
) -> dict[Path, A]:
    obj = _expect_object(j, loc, construct)
    result: dict[Path, A] = {}
    entries = _field(obj, "modules", loc, construct)
    for i, entry in enumerate(_expect_list(entries, (*loc, "modules"), "Modules")):
        here = (*loc, "modules", i)
        named = _expect_object(entry, here, "Module")
        name = decode_path(_field(named, "name", here, "Module"), (*here, "name"))
        result[name] = decode_module(
            _field(named, member, here, "Module"), (*here, member)
        )
    return result


def decode_package_specification[TA](
    decode_type_attributes: Decoder[TA],
) -> Decoder[package.Specification[TA]]:
    """Build a decoder for ``{"modules": [{"name", "spec"}]}``."""
    decode_m = decode_module_specification(decode_type_attributes)

    def decode(j: object, loc: Location = ()) -> package.Specification[TA]:
        return package.Specification(
            _modules(decode_m, "spec", j, loc, "PackageSpecification")
        )

    return decode


def decode_package_definition[TA, VA](
    decode_type_attributes: Decoder[TA], decode_value_attributes: Decoder[VA]
) -> Decoder[package.Definition[TA, VA]]:
    """Build a decoder for ``{"modules": [{"name", "def": ["public", ...]}]}``."""
    decode_m = decode_access_controlled(
        decode_module_definition(decode_type_attributes, decode_value_attributes)
    )

    def decode(j: object, loc: Location = ()) -> package.Definition[TA, VA]:
        return package.Definition(
            _modules(decode_m, "def", j, loc, "PackageDefinition")
        )

    return decode


# --- Distribution ---

_decode_dependency = decode_package_specification(decode_unit)
_decode_library_def = decode_package_definition(decode_unit, decode_type(decode_unit))


def decode_distribution(j: object, loc: Location = ()) -> Library:
    """Decode ``["library", name, dependencies, definition]``."""
    tag, items = _tag(j, loc, "Distribution")
    if tag != "library":
        raise fail(
            d.UNKNOWN_NODE,
            "Distribution",
            (*loc, 0),
            f"unknown distribution kind {tag!r}; format 1 has only library",
        )

    def at(i: int) -> tuple[object, Location]:
        return _index(items, i, loc, tag), (*loc, i)

    return Library(
        package_name=decode_path(*at(1)),
        dependencies=_pair_list_to_dict(
            decode_path, _decode_dependency, *at(2), "Dependencies"
        ),
        definition=_decode_library_def(*at(3)),
    )


def decode_versioned_distribution(document: str | object) -> Library:
    """Decode a ``"formatVersion": 1`` document into the format 3.0.0 model.

    Args:
        document: JSON text or an already-decoded JSON value.

    Raises:
        DiagnosticError: With ``unsupported_format_version_major`` for any format
            other than 1, or with a decoding diagnostic.
    """
    root = read_legacy_document(document, LegacyFormat.V1)
    return decode_distribution(
        _field(root, "distribution", (), "document"), ("distribution",)
    )


__all__ = [
    "decode_access_controlled",
    "decode_distribution",
    "decode_documented",
    "decode_literal",
    "decode_module_definition",
    "decode_module_specification",
    "decode_package_definition",
    "decode_package_specification",
    "decode_pattern",
    "decode_type",
    "decode_type_definition",
    "decode_type_specification",
    "decode_value",
    "decode_value_definition",
    "decode_value_specification",
    "decode_versioned_distribution",
]
