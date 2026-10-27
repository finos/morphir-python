"""Value and pattern decoders with the snake_case tags of formats 1 and 2.

morphir-elm wrote value and pattern tags in snake_case (``"let_definition"``,
``"wildcard_pattern"``) in formats 1 and 2, and in TitleCase from format 3
(commit 02aa36af). The node shapes did not change. Literals and types inside
values did change between format 1 and format 2, so each decoder here takes the
literal decoder and the type decoder of its format.

Port of the decoders in ``Value/CodecV1.elm`` (morphir-elm bc99af69) and in
``Value/CodecV2.elm`` (morphir-elm 02aa36af, removed in 7cb7b300).
"""

from __future__ import annotations

from ..diagnostics import Location
from . import literal as lit
from . import type as t
from . import value as v
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
)
from .name import Name


def decode_pattern[A](
    decode_literal: Decoder[lit.Literal], decode_attributes: Decoder[A]
) -> Decoder[v.Pattern[A]]:
    """Build a snake_case pattern decoder (elm ``decodePattern``)."""

    def decode(j: object, loc: Location = ()) -> v.Pattern[A]:
        tag, items = _tag(j, loc, "Pattern")

        def at(i: int) -> tuple[object, Location]:
            return _index(items, i, loc, tag), (*loc, i)

        match tag:
            case "wildcard_pattern":
                return v.WildcardPattern(decode_attributes(*at(1)))
            case "as_pattern":
                return v.AsPattern(
                    decode_attributes(*at(1)), decode(*at(2)), decode_name(*at(3))
                )
            case "tuple_pattern":
                return v.TuplePattern(
                    decode_attributes(*at(1)), _list_of(decode, *at(2), "Pattern")
                )
            case "constructor_pattern":
                return v.ConstructorPattern(
                    decode_attributes(*at(1)),
                    decode_fqname(*at(2)),
                    _list_of(decode, *at(3), "Pattern"),
                )
            case "empty_list_pattern":
                return v.EmptyListPattern(decode_attributes(*at(1)))
            case "head_tail_pattern":
                return v.HeadTailPattern(
                    decode_attributes(*at(1)), decode(*at(2)), decode(*at(3))
                )
            case "literal_pattern":
                return v.LiteralPattern(
                    decode_attributes(*at(1)), decode_literal(*at(2))
                )
            case "unit_pattern":
                return v.UnitPattern(decode_attributes(*at(1)))
            case _:
                raise _unknown(tag, loc, "Pattern")

    return decode


def decode_value_definition[TA, VA](
    decode_type: Decoder[t.Type[TA]],
    decode_value_attributes: Decoder[VA],
    decode_body: Decoder[v.Value[TA, VA]],
) -> Decoder[v.Definition[TA, VA]]:
    """Build a decoder for ``{"inputTypes", "outputType", "body"}``."""
    construct = "ValueDefinition"

    def decode_input(j: object, loc: Location) -> tuple[Name, VA, t.Type[TA]]:
        triple = _expect_list(j, loc, "Input")
        return (
            decode_name(_index(triple, 0, loc, "Input"), (*loc, 0)),
            decode_value_attributes(_index(triple, 1, loc, "Input"), (*loc, 1)),
            decode_type(_index(triple, 2, loc, "Input"), (*loc, 2)),
        )

    def decode(j: object, loc: Location = ()) -> v.Definition[TA, VA]:
        obj = _expect_object(j, loc, construct)
        return v.Definition(
            _list_of(
                decode_input,
                _field(obj, "inputTypes", loc, construct),
                (*loc, "inputTypes"),
                "Input",
            ),
            decode_type(
                _field(obj, "outputType", loc, construct), (*loc, "outputType")
            ),
            decode_body(_field(obj, "body", loc, construct), (*loc, "body")),
        )

    return decode


def decode_value[TA, VA](
    decode_literal: Decoder[lit.Literal],
    decode_type: Decoder[t.Type[TA]],
    decode_value_attributes: Decoder[VA],
) -> Decoder[v.Value[TA, VA]]:
    """Build a snake_case value decoder (elm ``decodeValue``).

    Args:
        decode_literal: The literal decoder of the format.
        decode_type: The decoder for the types inside value definitions.
        decode_value_attributes: The decoder for value and pattern attributes.
    """
    decode_p = decode_pattern(decode_literal, decode_value_attributes)

    def decode_named(j: object, loc: Location) -> dict[Name, v.Value[TA, VA]]:
        return _pair_list_to_dict(decode_name, decode, j, loc, "Value")

    def decode_case(j: object, loc: Location) -> tuple[v.Pattern[VA], v.Value[TA, VA]]:
        pair = _expect_list(j, loc, "Case")
        return (
            decode_p(_index(pair, 0, loc, "Case"), (*loc, 0)),
            decode(_index(pair, 1, loc, "Case"), (*loc, 1)),
        )

    def decode(j: object, loc: Location = ()) -> v.Value[TA, VA]:
        tag, items = _tag(j, loc, "Value")

        def at(i: int) -> tuple[object, Location]:
            return _index(items, i, loc, tag), (*loc, i)

        def attrs() -> VA:
            return decode_value_attributes(*at(1))

        match tag:
            case "literal":
                return v.LiteralValue(attrs(), decode_literal(*at(2)))
            case "constructor":
                return v.Constructor(attrs(), decode_fqname(*at(2)))
            case "tuple":
                return v.Tuple(attrs(), _list_of(decode, *at(2), "Value"))
            case "list":
                return v.List(attrs(), _list_of(decode, *at(2), "Value"))
            case "record":
                return v.Record(attrs(), decode_named(*at(2)))
            case "variable":
                return v.Variable(attrs(), decode_name(*at(2)))
            case "reference":
                return v.Reference(attrs(), decode_fqname(*at(2)))
            case "field":
                return v.Field(attrs(), decode(*at(2)), decode_name(*at(3)))
            case "field_function":
                return v.FieldFunction(attrs(), decode_name(*at(2)))
            case "apply":
                return v.Apply(attrs(), decode(*at(2)), decode(*at(3)))
            case "lambda":
                return v.Lambda(attrs(), decode_p(*at(2)), decode(*at(3)))
            case "let_definition":
                return v.LetDefinition(
                    attrs(), decode_name(*at(2)), decode_def(*at(3)), decode(*at(4))
                )
            case "let_recursion":
                return v.LetRecursion(
                    attrs(),
                    _pair_list_to_dict(decode_name, decode_def, *at(2), "Definition"),
                    decode(*at(3)),
                )
            case "destructure":
                return v.Destructure(
                    attrs(), decode_p(*at(2)), decode(*at(3)), decode(*at(4))
                )
            case "if_then_else":
                return v.IfThenElse(
                    attrs(), decode(*at(2)), decode(*at(3)), decode(*at(4))
                )
            case "pattern_match":
                return v.PatternMatch(
                    attrs(), decode(*at(2)), _list_of(decode_case, *at(3), "Case")
                )
            case "update_record":
                return v.UpdateRecord(attrs(), decode(*at(2)), decode_named(*at(3)))
            case "unit":
                return v.Unit(attrs())
            case _:
                raise _unknown(tag, loc, "Value")

    decode_def = decode_value_definition(decode_type, decode_value_attributes, decode)
    return decode
