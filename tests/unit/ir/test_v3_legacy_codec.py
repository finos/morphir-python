"""Tests for the legacy format 1 and 2 decoders (capability ir/v3).

The JSON spellings come from morphir-elm at bc99af69: ``*/CodecV1.elm`` for
format 1, and for format 2 the codecs before commit 02aa36af, whose value and
pattern tags survive as ``Value/CodecV2.elm`` in that commit.
"""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from morphir.ir import diagnostics as d
from morphir.ir import v3
from morphir.ir.diagnostics import DiagnosticError
from morphir.ir.migrate import v3_to_v4
from morphir.ir.v3 import codec, codec_v1, codec_v2, module, package
from morphir.ir.v3 import literal as lit
from morphir.ir.v3 import type as t
from morphir.ir.v3 import value as v
from morphir.ir.v3.access_controlled import private, public
from morphir.ir.v3.documented import Documented
from morphir.ir.v3.fqname import fqn
from morphir.ir.v3.name import Name, from_string
from morphir.ir.v3.path import from_string as path_from_string

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "ir" / "legacy"
RENTALS_1 = FIXTURES / "elm-rentals-format-1.json"
RENTALS_2 = FIXTURES / "elm-rentals-format-2.json"

FQ = [[["morphir"], ["s", "d", "k"]], [["basics"]], ["int"]]
INT_FQN = fqn("Morphir.SDK", "Basics", "Int")
INT = t.Reference(None, INT_FQN)
INT_1 = ["reference", {}, FQ, []]
INT_3 = ["Reference", {}, FQ, []]
UNIT_V = ["unit", {}]
WILD = ["wildcard_pattern", {}]
DEF_1 = {
    "inputTypes": [[["a"], {}, ["unit", {}]]],
    "outputType": ["unit", {}],
    "body": UNIT_V,
}
DEF_2 = {
    "inputTypes": [[["a"], {}, ["Unit", {}]]],
    "outputType": ["Unit", {}],
    "body": UNIT_V,
}
DEF = v.Definition(((("a",), None, t.Unit(None)),), t.Unit(None), v.Unit(None))


def n(text: str) -> Name:
    return from_string(text)


def codes(fn, j) -> tuple[str, ...]:  # type: ignore[no-untyped-def]
    with pytest.raises(DiagnosticError) as info:
        fn(j)
    return info.value.codes


decode_type_1 = codec_v1.decode_type(codec.decode_unit)
decode_pattern_1 = codec_v1.decode_pattern(codec.decode_unit)
decode_value_1 = codec_v1.decode_value(codec.decode_unit, codec.decode_unit)
decode_pattern_2 = codec_v2.decode_pattern(codec.decode_unit)
decode_value_2 = codec_v2.decode_value(codec.decode_unit, codec.decode_unit)


class TestFormat1Literals:
    @pytest.mark.parametrize(
        ("j", "expected"),
        [
            (["bool_literal", True], lit.BoolLiteral(True)),
            (["char_literal", "x"], lit.CharLiteral("x")),
            (["string_literal", "s"], lit.StringLiteral("s")),
            (["int_literal", 42], lit.WholeNumberLiteral(42)),
            (["float_literal", 1.5], lit.FloatLiteral(1.5)),
            (["decimal_literal", "1.25"], lit.DecimalLiteral(Decimal("1.25"))),
        ],
    )
    def test_tags(self, j: object, expected: lit.Literal) -> None:
        assert codec_v1.decode_literal(j) == expected

    @pytest.mark.parametrize(
        ("j", "code"),
        [
            (["BoolLiteral", True], d.UNKNOWN_NODE),
            (["whole_number_literal", 1], d.UNKNOWN_NODE),
            (["int_literal", "1"], d.INVALID_LITERAL),
            ([], d.MISSING_MEMBER),
        ],
    )
    def test_errors(self, j: object, code: str) -> None:
        assert codes(codec_v1.decode_literal, j) == (code,)


class TestFormat1Types:
    @pytest.mark.parametrize(
        ("j", "expected"),
        [
            (["variable", {}, ["a"]], t.Variable(None, ("a",))),
            (
                ["reference", {}, FQ, [["variable", {}, ["a"]]]],
                t.Reference(None, INT_FQN, (t.Variable(None, ("a",)),)),
            ),
            (["tuple", {}, [INT_1, INT_1]], t.Tuple(None, (INT, INT))),
            (["record", {}, [[["a"], INT_1]]], t.Record(None, (t.Field(("a",), INT),))),
            (
                ["extensible_record", {}, ["r"], [[["a"], INT_1]]],
                t.ExtensibleRecord(None, ("r",), (t.Field(("a",), INT),)),
            ),
            (["function", {}, INT_1, INT_1], t.Function(None, INT, INT)),
            (["unit", {}], t.Unit(None)),
        ],
    )
    def test_tags(self, j: object, expected: t.Type[None]) -> None:
        assert decode_type_1(j) == expected

    @pytest.mark.parametrize(
        ("j", "code"),
        [
            (["Variable", {}, ["a"]], d.UNKNOWN_NODE),
            (["record", {}, [{"name": ["a"], "tpe": INT_1}]], d.INVALID_JSON),
            (["variable", {}], d.MISSING_MEMBER),
        ],
    )
    def test_errors(self, j: object, code: str) -> None:
        assert codes(decode_type_1, j) == (code,)

    def test_specifications(self) -> None:
        decode = codec_v1.decode_type_specification(codec.decode_unit)
        assert decode(
            ["type_alias_specification", [["a"]], INT_1]
        ) == t.TypeAliasSpecification((("a",),), INT)
        assert decode(["opaque_type_specification", []]) == t.OpaqueTypeSpecification(
            ()
        )
        assert decode(
            ["custom_type_specification", [], [[["foo"], [[["x"], INT_1]]]]]
        ) == t.CustomTypeSpecification((), {("foo",): ((("x",), INT),)})
        config = {"baseType": INT_1, "fromBaseType": FQ, "toBaseType": FQ}
        assert decode(
            ["derived_type_specification", [], config]
        ) == t.DerivedTypeSpecification((), INT, INT_FQN, INT_FQN)

    def test_derived_type_uses_the_decoder_spelling(self) -> None:
        # elm CodecV1 encodes "DerivedTypeSpecification" but decodes only
        # "derived_type_specification"; the decoder is what reads files.
        decode = codec_v1.decode_type_specification(codec.decode_unit)
        config = {"baseType": INT_1, "fromBaseType": FQ, "toBaseType": FQ}
        assert codes(decode, ["DerivedTypeSpecification", [], config]) == (
            d.UNKNOWN_NODE,
        )
        assert codes(decode, ["derived_type_specification", [], {}]) == (
            d.MISSING_MEMBER,
        )

    def test_definitions(self) -> None:
        decode = codec_v1.decode_type_definition(codec.decode_unit)
        assert decode(["type_alias_definition", [], INT_1]) == t.TypeAliasDefinition(
            (), INT
        )
        assert decode(
            ["custom_type_definition", [], ["private", [[["foo"], []]]]]
        ) == t.CustomTypeDefinition((), private({("foo",): ()}))
        assert codes(decode, ["TypeAliasDefinition", [], INT_1]) == (d.UNKNOWN_NODE,)


class TestFormat1Wrappers:
    def test_access_controlled_is_a_tagged_array(self) -> None:
        decode = codec_v1.decode_access_controlled(decode_type_1)
        assert decode(["public", INT_1]) == public(INT)
        assert decode(["private", INT_1]) == private(INT)

    @pytest.mark.parametrize(
        ("j", "code"),
        [
            ({"access": "Public", "value": INT_1}, d.INVALID_JSON),
            (["Public", INT_1], d.UNKNOWN_NODE),
            (["public"], d.MISSING_MEMBER),
        ],
    )
    def test_access_controlled_errors(self, j: object, code: str) -> None:
        decode = codec_v1.decode_access_controlled(decode_type_1)
        assert codes(decode, j) == (code,)

    def test_documented_is_a_pair_or_bare(self) -> None:
        decode = codec_v1.decode_documented(decode_type_1)
        assert decode(["doc", INT_1]) == Documented("doc", INT)
        assert decode(INT_1) == Documented("", INT)
        assert decode(UNIT_V) == Documented("", t.Unit(None))

    def test_documented_reports_both_alternatives(self) -> None:
        decode = codec_v1.decode_documented(decode_type_1)
        assert codes(decode, ["doc", ["bogus", {}]]) == (
            d.UNKNOWN_NODE,
            d.UNKNOWN_NODE,
        )
        assert codes(decode, {"doc": "x"}) == (d.INVALID_JSON,)


PATTERNS: list[tuple[object, v.Pattern[None]]] = [
    (WILD, v.WildcardPattern(None)),
    (
        ["as_pattern", {}, WILD, ["x"]],
        v.AsPattern(None, v.WildcardPattern(None), n("x")),
    ),
    (["tuple_pattern", {}, [WILD]], v.TuplePattern(None, (v.WildcardPattern(None),))),
    (
        ["constructor_pattern", {}, FQ, [WILD]],
        v.ConstructorPattern(None, INT_FQN, (v.WildcardPattern(None),)),
    ),
    (["empty_list_pattern", {}], v.EmptyListPattern(None)),
    (
        ["head_tail_pattern", {}, WILD, WILD],
        v.HeadTailPattern(None, v.WildcardPattern(None), v.WildcardPattern(None)),
    ),
    (["unit_pattern", {}], v.UnitPattern(None)),
]

U = v.Unit(None)
VALUES: list[tuple[object, v.Value[None, None]]] = [
    (["constructor", {}, FQ], v.Constructor(None, INT_FQN)),
    (["tuple", {}, [UNIT_V]], v.Tuple(None, (U,))),
    (["list", {}, [UNIT_V]], v.List(None, (U,))),
    (["record", {}, [[["a"], UNIT_V]]], v.Record(None, {("a",): U})),
    (["variable", {}, ["x"]], v.Variable(None, ("x",))),
    (["reference", {}, FQ], v.Reference(None, INT_FQN)),
    (["field", {}, UNIT_V, ["a"]], v.Field(None, U, ("a",))),
    (["field_function", {}, ["a"]], v.FieldFunction(None, ("a",))),
    (["apply", {}, UNIT_V, UNIT_V], v.Apply(None, U, U)),
    (["lambda", {}, WILD, UNIT_V], v.Lambda(None, v.WildcardPattern(None), U)),
    (
        ["destructure", {}, WILD, UNIT_V, UNIT_V],
        v.Destructure(None, v.WildcardPattern(None), U, U),
    ),
    (["if_then_else", {}, UNIT_V, UNIT_V, UNIT_V], v.IfThenElse(None, U, U, U)),
    (
        ["pattern_match", {}, UNIT_V, [[WILD, UNIT_V]]],
        v.PatternMatch(None, U, ((v.WildcardPattern(None), U),)),
    ),
    (
        ["update_record", {}, UNIT_V, [[["a"], UNIT_V]]],
        v.UpdateRecord(None, U, {("a",): U}),
    ),
    (UNIT_V, U),
]


class TestFormat1Values:
    @pytest.mark.parametrize(("j", "expected"), PATTERNS)
    def test_pattern_tags(self, j: object, expected: v.Pattern[None]) -> None:
        assert decode_pattern_1(j) == expected

    def test_literal_pattern_uses_format_1_literals(self) -> None:
        j = ["literal_pattern", {}, ["int_literal", 1]]
        assert decode_pattern_1(j) == v.LiteralPattern(None, lit.WholeNumberLiteral(1))

    @pytest.mark.parametrize("j", [["WildcardPattern", {}], ["bogus_pattern", {}]])
    def test_unknown_pattern(self, j: object) -> None:
        assert codes(decode_pattern_1, j) == (d.UNKNOWN_NODE,)

    @pytest.mark.parametrize(("j", "expected"), VALUES)
    def test_value_tags(self, j: object, expected: v.Value[None, None]) -> None:
        assert decode_value_1(j) == expected

    def test_literal_value_uses_format_1_literals(self) -> None:
        j = ["literal", {}, ["bool_literal", True]]
        assert decode_value_1(j) == v.LiteralValue(None, lit.BoolLiteral(True))

    def test_let_definitions_use_format_1_types(self) -> None:
        assert decode_value_1(
            ["let_definition", {}, ["x"], DEF_1, UNIT_V]
        ) == v.LetDefinition(None, ("x",), DEF, U)
        assert decode_value_1(
            ["let_recursion", {}, [[["x"], DEF_1]], UNIT_V]
        ) == v.LetRecursion(None, {("x",): DEF}, U)

    @pytest.mark.parametrize(
        ("j", "code"),
        [
            (["Literal", {}, ["bool_literal", True]], d.UNKNOWN_NODE),
            (["literal", {}, ["BoolLiteral", True]], d.UNKNOWN_NODE),
            (["let_definition", {}, ["x"], DEF_2, UNIT_V], d.UNKNOWN_NODE),
            (["pattern_match", {}, UNIT_V, [[WILD]]], d.MISSING_MEMBER),
            (["apply", {}, UNIT_V], d.MISSING_MEMBER),
        ],
    )
    def test_value_errors(self, j: object, code: str) -> None:
        assert codes(decode_value_1, j) == (code,)

    def test_typed_value_attributes(self) -> None:
        decode = codec_v1.decode_value(codec.decode_unit, decode_type_1)
        assert decode(["variable", INT_1, ["x"]]) == v.Variable(INT, ("x",))

    def test_value_specification_and_definition(self) -> None:
        spec = codec_v1.decode_value_specification(codec.decode_unit)
        assert spec({"inputs": [[["a"], INT_1]], "output": INT_1}) == (
            v.Specification(((("a",), INT),), INT)
        )
        defn = codec_v1.decode_value_definition(codec.decode_unit, codec.decode_unit)
        assert defn(DEF_1) == DEF
        assert codes(defn, {"inputTypes": [], "outputType": INT_1}) == (
            d.MISSING_MEMBER,
        )


MODULE_SPEC_1 = {
    "types": [[["t"], ["a type", ["opaque_type_specification", []]]]],
    "values": [[["f"], {"inputs": [], "output": INT_1}]],
}
MODULE_DEF_1 = {
    "types": [[["t"], ["public", ["a type", ["type_alias_definition", [], INT_1]]]]],
    "values": [[["f"], ["private", DEF_1]]],
}
MODULE_SPEC = module.Specification(
    {("t",): Documented("a type", t.OpaqueTypeSpecification(()))},
    {("f",): Documented("", v.Specification((), INT))},
)
MODULE_DEF: module.Definition[None, None] = module.Definition(
    {("t",): public(Documented("a type", t.TypeAliasDefinition((), INT)))},
    {("f",): private(Documented("", DEF))},
)


class TestFormat1Packages:
    def test_module_specification(self) -> None:
        decode = codec_v1.decode_module_specification(codec.decode_unit)
        assert decode(MODULE_SPEC_1) == MODULE_SPEC

    def test_module_doc_is_not_read(self) -> None:
        decode = codec_v1.decode_module_specification(codec.decode_unit)
        assert decode({**MODULE_SPEC_1, "doc": "ignored"}).doc is None
        decode_def = codec_v1.decode_module_definition(
            codec.decode_unit, codec.decode_unit
        )
        assert decode_def({**MODULE_DEF_1, "doc": "ignored"}).doc is None

    def test_module_definition(self) -> None:
        decode = codec_v1.decode_module_definition(codec.decode_unit, codec.decode_unit)
        assert decode(MODULE_DEF_1) == MODULE_DEF
        assert codes(decode, {"types": []}) == (d.MISSING_MEMBER,)

    def test_package_specification_uses_name_and_spec(self) -> None:
        decode = codec_v1.decode_package_specification(codec.decode_unit)
        j = {"modules": [{"name": [["a"]], "spec": MODULE_SPEC_1}]}
        assert decode(j) == package.Specification({(("a",),): MODULE_SPEC})
        assert codes(decode, {"modules": [[[["a"]], MODULE_SPEC_1]]}) == (
            d.INVALID_JSON,
        )

    def test_package_definition_uses_name_and_def(self) -> None:
        decode = codec_v1.decode_package_definition(
            codec.decode_unit, codec.decode_unit
        )
        j = {"modules": [{"name": [["a"]], "def": ["public", MODULE_DEF_1]}]}
        assert decode(j) == package.Definition({(("a",),): public(MODULE_DEF)})
        assert codes(decode, {"modules": [{"name": [["a"]]}]}) == (d.MISSING_MEMBER,)

    def test_distribution(self) -> None:
        j = ["library", [["p"]], [], {"modules": []}]
        assert codec_v1.decode_distribution(j) == v3.Library(
            path_from_string("P"), package.Definition()
        )
        assert codes(codec_v1.decode_distribution, ["Library", [], [], {}]) == (
            d.UNKNOWN_NODE,
        )

    def test_distribution_with_dependency(self) -> None:
        spec = {"modules": [{"name": [["a"]], "spec": MODULE_SPEC_1}]}
        j = ["library", [["p"]], [[[["dep"]], spec]], {"modules": []}]
        lib = codec_v1.decode_distribution(j)
        assert lib.dependencies == {
            path_from_string("Dep"): package.Specification({(("a",),): MODULE_SPEC})
        }

    def test_versioned_distribution(self) -> None:
        j = {"formatVersion": 1, "distribution": ["library", [], [], {"modules": []}]}
        assert codec_v1.decode_versioned_distribution(j) == v3.Library(
            path_from_string(""), package.Definition()
        )

    @pytest.mark.parametrize("version", [2, 3, "3.0.0", 4])
    def test_versioned_distribution_refuses_other_formats(
        self, version: object
    ) -> None:
        j = {"formatVersion": version, "distribution": []}
        assert codes(codec_v1.decode_versioned_distribution, j) == (
            d.UNSUPPORTED_FORMAT_VERSION_MAJOR,
        )

    def test_versioned_distribution_needs_a_distribution(self) -> None:
        assert codes(codec_v1.decode_versioned_distribution, {"formatVersion": 1}) == (
            d.MISSING_MEMBER,
        )


class TestFormat2:
    @pytest.mark.parametrize(("j", "expected"), PATTERNS)
    def test_pattern_tags_are_snake_case(
        self, j: object, expected: v.Pattern[None]
    ) -> None:
        assert decode_pattern_2(j) == expected

    @pytest.mark.parametrize(("j", "expected"), VALUES)
    def test_value_tags_are_snake_case(
        self, j: object, expected: v.Value[None, None]
    ) -> None:
        assert decode_value_2(j) == expected

    def test_literals_and_types_are_format_3(self) -> None:
        assert decode_value_2(["literal", {}, ["BoolLiteral", True]]) == v.LiteralValue(
            None, lit.BoolLiteral(True)
        )
        assert decode_pattern_2(
            ["literal_pattern", {}, ["WholeNumberLiteral", 1]]
        ) == v.LiteralPattern(None, lit.WholeNumberLiteral(1))
        assert decode_value_2(
            ["let_definition", {}, ["x"], DEF_2, UNIT_V]
        ) == v.LetDefinition(None, ("x",), DEF, U)
        decode = codec_v2.decode_value(
            codec.decode_unit, codec.decode_type(codec.decode_unit)
        )
        assert decode(["variable", INT_3, ["x"]]) == v.Variable(INT, ("x",))

    @pytest.mark.parametrize(
        "j",
        [
            ["Literal", {}, ["BoolLiteral", True]],
            ["literal", {}, ["bool_literal", True]],
            ["let_definition", {}, ["x"], DEF_1, UNIT_V],
        ],
    )
    def test_other_spellings_are_refused(self, j: object) -> None:
        assert codes(decode_value_2, j) == (d.UNKNOWN_NODE,)

    def test_value_definition(self) -> None:
        decode = codec_v2.decode_value_definition(codec.decode_unit, codec.decode_unit)
        assert decode(DEF_2) == DEF

    def test_module_and_package_definition(self) -> None:
        module_def = {
            "types": [
                [
                    ["t"],
                    {
                        "access": "Public",
                        "value": {
                            "doc": "a type",
                            "value": ["TypeAliasDefinition", [], INT_3],
                        },
                    },
                ]
            ],
            "values": [[["f"], {"access": "Private", "value": DEF_2}]],
            "doc": "a module",
        }
        decode_module = codec_v2.decode_module_definition(
            codec.decode_unit, codec.decode_unit
        )
        expected = module.Definition(MODULE_DEF.types, MODULE_DEF.values, "a module")
        assert decode_module(module_def) == expected
        decode_package = codec_v2.decode_package_definition(
            codec.decode_unit, codec.decode_unit
        )
        j = {"modules": [[[["a"]], {"access": "Public", "value": module_def}]]}
        assert decode_package(j) == package.Definition({(("a",),): public(expected)})

    def test_distribution(self) -> None:
        j = ["Library", [["p"]], [], {"modules": []}]
        assert codec_v2.decode_distribution(j) == v3.Library(
            path_from_string("P"), package.Definition()
        )
        assert codes(codec_v2.decode_distribution, ["library", [], [], {}]) == (
            d.UNKNOWN_NODE,
        )

    def test_versioned_distribution(self) -> None:
        j = {"formatVersion": 2, "distribution": ["Library", [], [], {"modules": []}]}
        assert codec_v2.decode_versioned_distribution(json.dumps(j)) == v3.Library(
            path_from_string(""), package.Definition()
        )

    @pytest.mark.parametrize("version", [1, 3, 4])
    def test_versioned_distribution_refuses_other_formats(self, version: int) -> None:
        j = {"formatVersion": version, "distribution": []}
        assert codes(codec_v2.decode_versioned_distribution, j) == (
            d.UNSUPPORTED_FORMAT_VERSION_MAJOR,
        )


class TestElmFixtures:
    """The morphir-elm rentals example, written once as format 1 and once as 2."""

    def test_format_1_decodes(self) -> None:
        lib = codec_v1.decode_versioned_distribution(RENTALS_1.read_text())
        assert lib.package_name == path_from_string("Morphir.Example.App")
        assert list(lib.definition.modules) == [path_from_string("Rentals")]

    def test_format_2_decodes(self) -> None:
        lib = codec_v2.decode_versioned_distribution(RENTALS_2.read_text())
        assert lib.package_name == path_from_string("Morphir.Example.App")

    def test_both_formats_hold_the_same_model(self) -> None:
        assert codec_v1.decode_versioned_distribution(
            RENTALS_1.read_text()
        ) == codec_v2.decode_versioned_distribution(RENTALS_2.read_text())

    @pytest.mark.parametrize(
        ("reader", "fixture"),
        [
            (codec_v1.decode_versioned_distribution, RENTALS_1),
            (codec_v2.decode_versioned_distribution, RENTALS_2),
        ],
    )
    def test_legacy_gives_a_3_0_0_library_never_specs(self, reader, fixture) -> None:  # type: ignore[no-untyped-def]
        lib = reader(fixture.read_text())
        assert isinstance(lib, v3.Library)
        assert not isinstance(lib, v3.Specs)
        document = codec.encode_versioned_distribution(lib)
        assert document["formatVersion"] == 3

    def test_upgrade_writes_format_3(self) -> None:
        lib = codec_v1.decode_versioned_distribution(RENTALS_1.read_text())
        document = codec.encode_versioned_distribution(lib)
        assert document["formatVersion"] == 3
        assert codec.decode_versioned_distribution(document) == lib

    def test_upgrade_continues_to_v4(self) -> None:
        lib = codec_v2.decode_versioned_distribution(RENTALS_2.read_text())
        assert v3_to_v4(lib).value.package.name is not None

    @pytest.mark.parametrize("fixture", [RENTALS_1, RENTALS_2])
    def test_format_3_reader_still_refuses_legacy(self, fixture: Path) -> None:
        assert codes(codec.decode_versioned_distribution, fixture.read_text()) == (
            d.UNSUPPORTED_FORMAT_VERSION_MAJOR,
        )
