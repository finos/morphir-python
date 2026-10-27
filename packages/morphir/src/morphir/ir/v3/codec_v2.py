"""Read-only JSON decoders for morphir-elm IR format 2, into the 3.0.0 model.

morphir-elm wrote format 2 from commit 8e0e729d (2021-10-08) to commit 02aa36af
(2023-05-18). Format 3 changed one thing: value and pattern tags went from
snake_case (``"let_definition"``, ``"wildcard_pattern"``) to TitleCase. Every
other shape, including TitleCase literals and types, ``{"access", "value"}``,
``{"doc", "value"}``, and ``[path, module]`` package entries, is the format 3.0.0
shape, so this module reuses `morphir.ir.v3.codec` for everything except values,
patterns, and the containers that hold them.

The value and pattern decoders port ``Value/CodecV2.elm`` from morphir-elm commit
02aa36af. morphir-elm removed that module in commit 7cb7b300, and today refuses
format 2; reading it here is a deliberate divergence, so that old files can be
upgraded. As in elm, format 2 decodes into the format 3.0.0 model; encode the
result with `morphir.ir.v3.codec` to write format 3. No writer emits format 2.

The finos/morphir v2 schema documentation says that format 2 literals stay
snake_case. morphir-elm wrote them in TitleCase from the first format-2 commit
(e742a620), and morphir-elm is normative.
"""

from __future__ import annotations

from .. import diagnostics as d
from ..diagnostics import Location, fail
from ..format_version import LegacyFormat, read_legacy_document
from . import _legacy_value, module, package
from . import value as v
from .codec import (
    Decoder,
    _expect_object,
    _field,
    _index,
    _pair_list_to_dict,
    _tag,
    decode_access_controlled,
    decode_documented,
    decode_literal,
    decode_name,
    decode_package_specification,
    decode_path,
    decode_type,
    decode_type_definition,
    decode_unit,
)
from .codec import _decode_doc as decode_module_doc
from .distribution import Library


def decode_pattern[A](decode_attributes: Decoder[A]) -> Decoder[v.Pattern[A]]:
    """Build a format-2 pattern decoder: snake_case tags, format-3 literals."""
    return _legacy_value.decode_pattern(decode_literal, decode_attributes)


def decode_value[TA, VA](
    decode_type_attributes: Decoder[TA], decode_value_attributes: Decoder[VA]
) -> Decoder[v.Value[TA, VA]]:
    """Build a format-2 value decoder: snake_case tags, format-3 types and literals."""
    return _legacy_value.decode_value(
        decode_literal, decode_type(decode_type_attributes), decode_value_attributes
    )


def decode_value_definition[TA, VA](
    decode_type_attributes: Decoder[TA], decode_value_attributes: Decoder[VA]
) -> Decoder[v.Definition[TA, VA]]:
    """Build a format-2 value definition decoder."""
    return _legacy_value.decode_value_definition(
        decode_type(decode_type_attributes),
        decode_value_attributes,
        decode_value(decode_type_attributes, decode_value_attributes),
    )


def decode_module_definition[TA, VA](
    decode_type_attributes: Decoder[TA], decode_value_attributes: Decoder[VA]
) -> Decoder[module.Definition[TA, VA]]:
    """Build a format-2 module definition decoder, with the optional ``doc``."""
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
            decode_module_doc(obj),
        )

    return decode


def decode_package_definition[TA, VA](
    decode_type_attributes: Decoder[TA], decode_value_attributes: Decoder[VA]
) -> Decoder[package.Definition[TA, VA]]:
    """Build a decoder for ``{"modules": [[path, {"access", "value"}]]}``."""
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


_decode_dependency = decode_package_specification(decode_unit)
_decode_library_def = decode_package_definition(decode_unit, decode_type(decode_unit))


def decode_distribution(j: object, loc: Location = ()) -> Library:
    """Decode ``["Library", name, dependencies, definition]``."""
    tag, items = _tag(j, loc, "Distribution")
    if tag != "Library":
        raise fail(
            d.UNKNOWN_NODE,
            "Distribution",
            (*loc, 0),
            f"unknown distribution kind {tag!r}; format 2 has only Library",
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
    """Decode a ``"formatVersion": 2`` document into the format 3.0.0 model.

    Args:
        document: JSON text or an already-decoded JSON value.

    Raises:
        DiagnosticError: With ``unsupported_format_version_major`` for any format
            other than 2, or with a decoding diagnostic.
    """
    root = read_legacy_document(document, LegacyFormat.V2)
    return decode_distribution(
        _field(root, "distribution", (), "document"), ("distribution",)
    )


__all__ = [
    "decode_distribution",
    "decode_module_definition",
    "decode_package_definition",
    "decode_pattern",
    "decode_value",
    "decode_value_definition",
    "decode_versioned_distribution",
]
