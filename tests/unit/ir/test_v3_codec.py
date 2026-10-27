"""Tests for the v3 model and its morphir-elm format-3 codecs (capability ir/v3)."""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from morphir.ir import diagnostics as d
from morphir.ir import v3
from morphir.ir.diagnostics import DiagnosticError
from morphir.ir.v3 import codec, module, package
from morphir.ir.v3 import literal as lit
from morphir.ir.v3 import type as t
from morphir.ir.v3 import value as v
from morphir.ir.v3.access_controlled import Access, private, public
from morphir.ir.v3.documented import Documented
from morphir.ir.v3.fqname import FQName, fqn
from morphir.ir.v3.name import Name, from_string, to_camel_case, to_list
from morphir.ir.v3.path import Path as IRPath
from morphir.ir.v3.path import from_list as path_from_list
from morphir.ir.v3.path import from_string as path_from_string
from morphir.ir.v3.path import to_list as path_to_list
from morphir.ir.v3.qname import QName

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "ir" / "v3"
FIXTURE_FILES = sorted(FIXTURES.glob("*.json"))
KIT_SPECS = FIXTURES / "mck-distributions-0011-specs.json"
RUST_SPECS = FIXTURES / "rust-classic-specs-transport.json"

INT = t.Reference(None, fqn("Morphir.SDK", "Basics", "Int"))


def n(text: str) -> Name:
    return from_string(text)


def decode_error(fn, j) -> DiagnosticError:  # type: ignore[no-untyped-def]
    with pytest.raises(DiagnosticError) as info:
        fn(j)
    return info.value


class TestNames:
    def test_from_string_splits_like_elm(self) -> None:
        assert from_string("valueInUSD") == ("value", "in", "u", "s", "d")
        assert from_string("fr_2052a") == ("fr", "2052", "a")

    def test_helpers(self) -> None:
        assert to_list(n("fooBar")) == ["foo", "bar"]
        assert to_camel_case(n("foo_bar")) == "fooBar"
        assert to_camel_case(Name(())) == ""
        p = path_from_string("Morphir.SDK")
        assert p == (("morphir",), ("s", "d", "k"))
        assert path_to_list(path_from_list([n("a")])) == [("a",)]

    def test_name_codec(self) -> None:
        assert codec.encode_name(n("fooBar")) == ["foo", "bar"]
        assert codec.decode_name(["foo", "bar"]) == ("foo", "bar")
        assert decode_error(codec.decode_name, ["a", 1]).codes == (d.INVALID_NAME,)

    def test_qname_and_fqname(self) -> None:
        qn = QName(path_from_string("A.B"), n("c"))
        assert codec.decode_qname(codec.encode_qname(qn)) == qn
        f = fqn("Morphir.SDK", "Basics", "Int")
        assert codec.encode_fqname(f) == [
            [["morphir"], ["s", "d", "k"]],
            [["basics"]],
            ["int"],
        ]
        assert codec.decode_fqname(codec.encode_fqname(f)) == f
        assert decode_error(codec.decode_fqname, [[], []]).codes == (d.MISSING_MEMBER,)


class TestModel:
    def test_library_has_no_package_version(self) -> None:
        lib = v3.Library(path_from_string("My.Pkg"), package.Definition())
        assert not hasattr(lib, "package_version")
        assert not hasattr(lib, "version")

    def test_library_with_typed_values(self) -> None:
        body: v.Value[None, t.Type[None]] = v.LiteralValue(
            INT, lit.WholeNumberLiteral(1)
        )
        defn = v.Definition((), INT, body)
        mod = module.Definition(values={n("one"): public(Documented("", defn))})
        lib = v3.Library(
            path_from_string("My.Pkg"),
            package.Definition({path_from_string("Main"): public(mod)}),
            {path_from_string("Morphir.SDK"): package.Specification()},
        )
        stored = lib.definition.modules[path_from_string("Main")].value
        assert stored.values[n("one")].value.value.body.attributes == INT

    def test_v3_classes_are_distinct_from_v4(self) -> None:
        from morphir.ir import v4

        assert v3.Name is not v4.Name
        assert v3.FQName is not v4.FQName
        assert v.Apply is not v4.value.Apply

    def test_access_helpers(self) -> None:
        assert private(1).access is Access.PRIVATE


class TestNodeCodecs:
    def test_untyped_literal_fragment(self) -> None:
        decode = codec.decode_value(codec.decode_unit, codec.decode_unit)
        fragment = ["Literal", {}, ["WholeNumberLiteral", 42]]
        value = decode(fragment)
        assert value == v.LiteralValue(None, lit.WholeNumberLiteral(42))
        encode = codec.encode_value(codec.encode_unit, codec.encode_unit)
        assert encode(value) == fragment

    @pytest.mark.parametrize(
        "literal",
        [
            lit.BoolLiteral(True),
            lit.CharLiteral("x"),
            lit.StringLiteral("hi"),
            lit.WholeNumberLiteral(-3),
            lit.FloatLiteral(1.5),
            lit.DecimalLiteral(Decimal("1.25")),
        ],
    )
    def test_literal_round_trip(self, literal: lit.Literal) -> None:
        assert codec.decode_literal(codec.encode_literal(literal)) == literal

    @pytest.mark.parametrize(
        "bad",
        [
            ["BoolLiteral", 1],
            ["CharLiteral", ""],
            ["StringLiteral", 1],
            ["WholeNumberLiteral", 1.5],
            ["WholeNumberLiteral", True],
            ["FloatLiteral", "x"],
            ["DecimalLiteral", 1],
            ["DecimalLiteral", "abc"],
        ],
    )
    def test_invalid_literal(self, bad: list[object]) -> None:
        assert decode_error(codec.decode_literal, bad).codes == (d.INVALID_LITERAL,)

    def test_float_literal_accepts_integer_json(self) -> None:
        assert codec.decode_literal(["FloatLiteral", 2]) == lit.FloatLiteral(2.0)

    def test_unknown_literal(self) -> None:
        err = decode_error(codec.decode_literal, ["NopeLiteral", 1])
        assert err.codes == (d.UNKNOWN_NODE,)

    def test_every_type_node_round_trips(self) -> None:
        enc = codec.encode_type(codec.encode_unit)
        dec = codec.decode_type(codec.decode_unit)
        a = n("a")
        field = t.Field(n("x"), t.Variable(None, a))
        types: list[t.Type[None]] = [
            t.Variable(None, a),
            t.Reference(None, fqn("P", "M", "T"), (t.Unit(None),)),
            t.Tuple(None, (t.Unit(None), t.Variable(None, a))),
            t.Record(None, (field,)),
            t.ExtensibleRecord(None, a, (field,)),
            t.Function(None, t.Unit(None), t.Unit(None)),
            t.Unit(None),
        ]
        for tpe in types:
            assert dec(enc(tpe)) == tpe

    def test_unknown_type_kind(self) -> None:
        dec = codec.decode_type(codec.decode_unit)
        err = decode_error(dec, ["Union", {}])
        assert err.codes == (d.UNKNOWN_NODE,)
        assert err.diagnostics[0].construct == "Type"

    def test_type_specifications_and_definitions(self) -> None:
        enc_s = codec.encode_type_specification(codec.encode_unit)
        dec_s = codec.decode_type_specification(codec.decode_unit)
        enc_d = codec.encode_type_definition(codec.encode_unit)
        dec_d = codec.decode_type_definition(codec.decode_unit)
        params = (n("a"),)
        ctors: t.Constructors[None] = {
            n("b"): (),
            n("a"): ((n("x"), t.Unit(None)),),
        }
        specs: list[t.Specification[None]] = [
            t.TypeAliasSpecification(params, t.Unit(None)),
            t.OpaqueTypeSpecification(params),
            t.CustomTypeSpecification(params, ctors),
            t.DerivedTypeSpecification(
                (), t.Unit(None), fqn("P", "M", "from"), fqn("P", "M", "to")
            ),
        ]
        for spec in specs:
            assert dec_s(enc_s(spec)) == spec
        encoded = enc_s(t.CustomTypeSpecification(params, ctors))
        assert [c[0] for c in encoded[2]] == [["a"], ["b"]]
        defs: list[t.Definition[None]] = [
            t.TypeAliasDefinition(params, t.Unit(None)),
            t.CustomTypeDefinition(params, private(ctors)),
        ]
        for defn in defs:
            assert dec_d(enc_d(defn)) == defn
        assert decode_error(dec_s, ["X", []]).codes == (d.UNKNOWN_NODE,)
        assert decode_error(dec_d, ["X", []]).codes == (d.UNKNOWN_NODE,)

    def test_every_value_and_pattern_node_round_trips(self) -> None:
        enc = codec.encode_value(codec.encode_unit, codec.encode_unit)
        dec = codec.decode_value(codec.decode_unit, codec.decode_unit)
        x = n("x")
        u: v.Value[None, None] = v.Unit(None)
        f = fqn("P", "M", "f")
        patterns: list[v.Pattern[None]] = [
            v.WildcardPattern(None),
            v.AsPattern(None, v.WildcardPattern(None), x),
            v.TuplePattern(None, (v.UnitPattern(None),)),
            v.ConstructorPattern(None, f, (v.EmptyListPattern(None),)),
            v.EmptyListPattern(None),
            v.HeadTailPattern(None, v.WildcardPattern(None), v.EmptyListPattern(None)),
            v.LiteralPattern(None, lit.BoolLiteral(False)),
            v.UnitPattern(None),
        ]
        defn = v.Definition(((x, None, t.Unit(None)),), t.Unit(None), u)
        values: list[v.Value[None, None]] = [
            v.LiteralValue(None, lit.StringLiteral("s")),
            v.Constructor(None, f),
            v.Tuple(None, (u, u)),
            v.List(None, (u,)),
            v.Record(None, {x: u}),
            v.Variable(None, x),
            v.Reference(None, f),
            v.Field(None, u, x),
            v.FieldFunction(None, x),
            v.Apply(None, u, u),
            v.LetDefinition(None, x, defn, u),
            v.LetRecursion(None, {x: defn}, u),
            v.IfThenElse(None, u, u, u),
            v.PatternMatch(None, u, tuple((p, u) for p in patterns)),
            v.UpdateRecord(None, u, {x: u}),
            u,
        ]
        values += [v.Lambda(None, p, u) for p in patterns]
        values += [v.Destructure(None, p, u, u) for p in patterns]
        for value in values:
            assert dec(enc(value)) == value

    def test_unknown_value_and_pattern(self) -> None:
        dec = codec.decode_value(codec.decode_unit, codec.decode_unit)
        assert decode_error(dec, ["Hole", {}]).codes == (d.UNKNOWN_NODE,)
        dec_p = codec.decode_pattern(codec.decode_unit)
        assert decode_error(dec_p, ["NopePattern", {}]).codes == (d.UNKNOWN_NODE,)

    def test_decode_errors_are_located(self) -> None:
        dec = codec.decode_value(codec.decode_unit, codec.decode_unit)
        err = decode_error(dec, ["Apply", {}, ["Unit", {}], ["Bogus", {}]])
        assert err.diagnostics[0].location == (3,)
        err = decode_error(dec, ["Apply", {}, ["Unit", {}]])
        assert err.codes == (d.MISSING_MEMBER,)
        assert decode_error(dec, "Unit").codes == (d.INVALID_JSON,)
        assert decode_error(dec, [1]).codes == (d.INVALID_JSON,)
        assert decode_error(dec, ["Tuple", {}, {}]).codes == (d.INVALID_JSON,)

    def test_value_specification_and_definition(self) -> None:
        enc_s = codec.encode_value_specification(codec.encode_unit)
        dec_s = codec.decode_value_specification(codec.decode_unit)
        spec = v.Specification(((n("a"), t.Unit(None)),), t.Unit(None))
        assert dec_s(enc_s(spec)) == spec
        assert decode_error(dec_s, {"inputs": []}).codes == (d.MISSING_MEMBER,)
        assert decode_error(dec_s, []).codes == (d.INVALID_JSON,)
        enc_d = codec.encode_value_definition(codec.encode_unit, codec.encode_unit)
        dec_d = codec.decode_value_definition(codec.decode_unit, codec.decode_unit)
        defn = v.Definition(((n("a"), None, t.Unit(None)),), t.Unit(None), v.Unit(None))
        assert dec_d(enc_d(defn)) == defn

    def test_documented_and_access(self) -> None:
        enc = codec.encode_access_controlled(codec.encode_documented(codec.encode_name))
        dec = codec.decode_access_controlled(codec.decode_documented(codec.decode_name))
        item = public(Documented("doc", n("a")))
        assert dec(enc(item)) == item
        undocumented = codec.decode_documented(codec.decode_name)(["a"])
        assert undocumented == Documented("", ("a",))
        bad = {"access": "Protected", "value": ["a"]}
        assert decode_error(dec, bad).codes == (d.UNKNOWN_NODE,)
        assert decode_error(dec, {"value": ["a"]}).codes == (d.MISSING_MEMBER,)

    def test_module_doc_is_optional(self) -> None:
        dec = codec.decode_module_definition(codec.decode_unit, codec.decode_unit)
        assert dec({"types": [], "values": []}).doc is None
        assert dec({"types": [], "values": [], "doc": "hi"}).doc == "hi"
        enc = codec.encode_module_specification(codec.encode_unit)
        dec_s = codec.decode_module_specification(codec.decode_unit)
        spec = module.Specification(
            types={n("t"): Documented("", t.OpaqueTypeSpecification(()))},
            values={n("v"): Documented("", v.Specification((), t.Unit(None)))},
            doc="m",
        )
        assert dec_s(enc(spec)) == spec


class TestVersionedDistribution:
    @pytest.mark.parametrize("path", FIXTURE_FILES, ids=lambda p: p.name)
    def test_golden_fixture_round_trips(self, path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        dist = codec.decode_versioned_distribution(text)
        encoded = codec.encode_versioned_distribution(dist)
        assert next(iter(encoded)) == "formatVersion"
        assert encoded["formatVersion"] == (
            3 if isinstance(dist, v3.Library) else "3.1.0"
        )
        assert codec.decode_versioned_distribution(json.dumps(encoded)) == dist
        assert encoded == json.loads(text)

    def test_fixture_is_inspectable_without_migration(self) -> None:
        lib = codec.decode_versioned_distribution(
            (FIXTURES / "elm-simpleValueTree.json").read_text()
        )
        assert isinstance(lib, v3.Library)
        assert isinstance(lib.package_name, IRPath)
        for mod in lib.definition.modules.values():
            for value in mod.value.values.values():
                assert isinstance(value.value.value, v.Definition)

    def test_string_version_reads_and_writes_integer(self) -> None:
        text = (FIXTURES / "elm-base.json").read_text()
        doc = json.loads(text)
        doc["formatVersion"] = "3.0.0"
        lib = codec.decode_versioned_distribution(json.dumps(doc))
        assert codec.encode_versioned_distribution(lib)["formatVersion"] == 3

    def test_v4_is_refused(self) -> None:
        err = decode_error(
            codec.decode_versioned_distribution,
            '{"formatVersion": 4, "distribution": {}}',
        )
        assert err.codes == (d.UNSUPPORTED_FORMAT_VERSION_MAJOR,)
        assert "4.0.0" in str(err)
        assert "only 3.0.x and 3.1.x" in str(err)

    def test_unknown_distribution_tag(self) -> None:
        doc = {"formatVersion": 3, "distribution": ["Application", [], [], {}]}
        err = decode_error(codec.decode_versioned_distribution, doc)
        assert err.codes == (d.UNKNOWN_NODE,)
        assert err.diagnostics[0].location == ("distribution", 0)
        assert "'Application'" in str(err)
        assert "Library" in str(err)
        assert "Specs" in str(err)

    def test_missing_distribution(self) -> None:
        err = decode_error(codec.decode_versioned_distribution, {"formatVersion": 3})
        assert err.codes == (d.MISSING_MEMBER,)

    def test_fqname_type(self) -> None:
        assert isinstance(fqn("a", "b", "c"), FQName)


def specs_doc(version: object, modules: object = None) -> dict[str, object]:
    return {
        "formatVersion": version,
        "distribution": [
            "Specs",
            [["my"], ["pkg"]],
            [],
            {"modules": [] if modules is None else modules},
        ],
    }


class TestSpecs:
    def test_kit_case_decodes(self) -> None:
        dist = codec.decode_versioned_distribution(KIT_SPECS.read_text())
        assert isinstance(dist, v3.Specs)
        assert dist.package_name == path_from_string("my.pkg")
        assert dist.dependencies == {}
        basics = dist.specification.modules[path_from_string("basics")]
        assert basics.doc == "Basics."
        assert basics.types[n("int")] == Documented("", t.OpaqueTypeSpecification(()))
        assert basics.values == {}

    def test_kit_case_encodes_to_its_canonical_json(self) -> None:
        dist = codec.decode_versioned_distribution(KIT_SPECS.read_text())
        assert codec.encode_versioned_distribution(dist) == json.loads(
            KIT_SPECS.read_text()
        )

    def test_dependencies_decode_as_for_a_library(self) -> None:
        dist = codec.decode_versioned_distribution(RUST_SPECS.read_text())
        assert isinstance(dist, v3.Specs)
        assert dist.dependencies == {
            IRPath((Name(("morphir",)), Name(("s", "d", "k")))): (
                package.Specification()
            )
        }

    def test_specs_is_written_as_3_1_0(self) -> None:
        dist = v3.Specs(path_from_string("my.pkg"), package.Specification())
        encoded = codec.encode_versioned_distribution(dist)
        assert encoded == specs_doc("3.1.0")
        assert list(encoded) == ["formatVersion", "distribution"]

    @pytest.mark.parametrize("version", ["3.1.0", "3.1.7"])
    def test_specs_reads_at_every_3_1_release(self, version: str) -> None:
        dist = codec.decode_versioned_distribution(specs_doc(version))
        assert isinstance(dist, v3.Specs)

    @pytest.mark.parametrize("version", [3, "3", "3.0.0", "3.0.1"])
    def test_specs_before_3_1_is_refused(self, version: object) -> None:
        err = decode_error(codec.decode_versioned_distribution, specs_doc(version))
        assert err.codes == (d.SPECS_BEFORE_3_1,)
        diagnostic = err.diagnostics[0]
        assert diagnostic.construct == "Specs"
        assert diagnostic.location == ("formatVersion",)
        assert "3.1.0 or later" in diagnostic.message

    def test_specs_version_is_checked_before_the_body(self) -> None:
        doc = specs_doc(3, modules="not a list")
        err = decode_error(codec.decode_versioned_distribution, doc)
        assert err.codes == (d.SPECS_BEFORE_3_1,)

    @pytest.mark.parametrize("version", [3, "3.0.0", "3.1.0"])
    def test_library_reads_at_every_supported_3_x(self, version: object) -> None:
        doc = json.loads((FIXTURES / "elm-base.json").read_text())
        doc["formatVersion"] = version
        dist = codec.decode_versioned_distribution(doc)
        assert isinstance(dist, v3.Library)
        assert codec.encode_versioned_distribution(dist)["formatVersion"] == 3

    def test_module_definition_in_specs_is_refused(self) -> None:
        definition = {
            "access": "Public",
            "value": {"types": [], "values": [], "doc": "Basics."},
        }
        doc = specs_doc("3.1.0", [[[["basics"]], definition]])
        err = decode_error(codec.decode_versioned_distribution, doc)
        assert d.UNKNOWN_MEMBER in err.codes
        diagnostic = err.diagnostics[0]
        assert diagnostic.code == d.UNKNOWN_MEMBER
        assert diagnostic.location == ("distribution", 3, "modules", 0, 1, "access")
        assert "specifications, not definitions" in diagnostic.message

    def test_extra_member_in_specs_module_is_refused(self) -> None:
        spec = {"types": [], "values": [], "doc": None, "extra": 1}
        doc = specs_doc("3.1.0", [[[["basics"]], spec]])
        err = decode_error(codec.decode_versioned_distribution, doc)
        assert err.codes == (d.UNKNOWN_MEMBER,)

    def test_specs_module_needs_types_and_values(self) -> None:
        doc = specs_doc("3.1.0", [[[["basics"]], {"values": []}]])
        err = decode_error(codec.decode_versioned_distribution, doc)
        assert err.codes == (d.MISSING_MEMBER,)

    def test_specs_module_must_be_an_object(self) -> None:
        doc = specs_doc("3.1.0", [[[["basics"]], []]])
        err = decode_error(codec.decode_versioned_distribution, doc)
        assert err.codes == (d.INVALID_JSON,)

    def test_dependency_modules_keep_the_elm_reading(self) -> None:
        doc = json.loads(RUST_SPECS.read_text())
        dependency = {"types": [], "values": [], "doc": None, "extra": 1}
        doc["distribution"][2][0][1]["modules"] = [[[["basics"]], dependency]]
        dist = codec.decode_versioned_distribution(doc)
        assert isinstance(dist, v3.Specs)

    def test_unversioned_specs_round_trips(self) -> None:
        dist = codec.decode_versioned_distribution(RUST_SPECS.read_text())
        assert codec.decode_distribution(codec.encode_distribution(dist)) == dist
