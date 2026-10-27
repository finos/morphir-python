"""Tests for the v4 package layout and the draft v4 JSON codec (capability ir/v4)."""

import importlib
import json
from decimal import Decimal

import pytest

import morphir.ir as ir
from morphir.ir import diagnostics as d
from morphir.ir import v4
from morphir.ir.diagnostics import DiagnosticError
from morphir.ir.v4 import codec, module, package
from morphir.ir.v4 import document as doc
from morphir.ir.v4 import incompleteness as inc
from morphir.ir.v4 import literal as lit
from morphir.ir.v4 import type as t
from morphir.ir.v4 import type_def as td
from morphir.ir.v4 import type_spec as ts
from morphir.ir.v4 import value as v
from morphir.ir.v4.access_controlled import Private, Public
from morphir.ir.v4.distribution import (
    ApplicationDistribution,
    EntryPoint,
    EntryPointKind,
    LibraryDistribution,
    PackageInfo,
    SpecsDistribution,
)
from morphir.ir.v4.documented import Documented
from morphir.ir.v4.fqname import FQName
from morphir.ir.v4.name import Name
from morphir.ir.v4.path import Path
from morphir.ir.v4.type_constraints import TypeConstraints

SHIMMED = [
    "access_controlled",
    "decorations",
    "distribution",
    "document",
    "documented",
    "fqname",
    "json",
    "literal",
    "meta",
    "module",
    "name",
    "package",
    "path",
    "qname",
    "ref",
    "type_constraints",
    "type_def",
    "type_spec",
    "type",
    "value",
]


def n(*words: str) -> Name:
    return Name(words)


def p(*names: Name) -> Path:
    return Path(names)


PKG = p(n("my"), n("pkg"))
INT = t.Reference(
    t.TypeAttributes(),
    FQName(p(n("morphir"), n("s", "d", "k")), p(n("basics")), n("int")),
)
TA = t.TypeAttributes()


def typed(tpe: t.Type = INT) -> v.ValueAttributes:
    return v.ValueAttributes(inferred_type=tpe)


def fail_codes(fn, *args) -> tuple[str, ...]:  # type: ignore[no-untyped-def]
    with pytest.raises(DiagnosticError) as info:
        fn(*args)
    return info.value.codes


def sample_definition() -> package.Definition:
    a = n("a")
    va = typed()
    unit = v.Unit(va)
    fq = FQName(PKG, p(n("main")), n("f"))
    patterns: list[v.Pattern] = [
        v.WildcardPattern(va),
        v.AsPattern(va, v.WildcardPattern(va), a),
        v.TuplePattern(va, [v.UnitPattern(va)]),
        v.ConstructorPattern(va, fq, [v.EmptyListPattern(va)]),
        v.HeadTailPattern(va, v.WildcardPattern(va), v.EmptyListPattern(va)),
        v.LiteralPattern(va, lit.IntegerLiteral(1)),
    ]
    inner = v.Definition([(a, typed(), INT)], INT, unit)
    body = v.LetDefinition(
        va,
        a,
        inner,
        v.LetRecursion(
            va,
            {n("g"): inner},
            v.PatternMatch(
                va,
                v.Tuple(va, [unit, v.List(va, [unit])]),
                [(pat, v.Lambda(va, pat, unit)) for pat in patterns],
            ),
        ),
    )
    values: list[v.Value] = [
        body,
        v.LiteralValue(va, lit.DecimalLiteral(Decimal("1.5"))),
        v.LiteralValue(va, lit.FloatLiteral(2.5)),
        v.LiteralValue(va, lit.StringLiteral("s")),
        v.LiteralValue(va, lit.CharLiteral("c")),
        v.LiteralValue(va, lit.BoolLiteral(True)),
        v.Constructor(va, fq),
        v.Record(va, [(n("x"), unit)]),
        v.Variable(va, a),
        v.Reference(va, fq),
        v.Field(va, unit, n("x")),
        v.FieldFunction(va, n("x")),
        v.Apply(va, unit, unit),
        v.Destructure(va, v.WildcardPattern(va), unit, unit),
        v.IfThenElse(va, unit, unit, unit),
        v.UpdateRecord(va, unit, [(n("x"), unit)]),
    ]
    fields = [t.Field(n("x"), INT)]
    types: list[t.Type] = [
        t.Variable(TA, a),
        t.Reference(TA, fq, [INT]),
        t.Tuple(TA, [INT]),
        t.Record(TA, fields),
        t.ExtensibleRecord(TA, a, fields),
        t.Function(TA, INT, INT),
        t.Unit(TA),
    ]
    ctors: ts.Constructors = {n("just"): [(a, t.Variable(TA, a))], n("none"): []}
    mod = module.Definition(
        types={
            n("alias"): Public(
                Documented("An alias.", td.TypeAliasDefinition([], INT))
            ),
            n("maybe"): Private(
                Documented(None, td.CustomTypeDefinition([a], Public(ctors)))
            ),
            n("hidden"): Public(
                Documented(None, td.CustomTypeDefinition([], Private({})))
            ),
        },
        values={
            n("v", str(i)): Public(Documented("doc", v.Definition([], INT, x)))
            for i, x in enumerate(values)
        }
        | {
            n("t", str(i)): Private(
                Documented(None, v.Definition([(a, typed(tp), tp)], tp, unit))
            )
            for i, tp in enumerate(types)
        },
        doc="Main module.",
    )
    return package.Definition({p(n("main")): Public(mod)})


def sample_specification() -> package.Specification:
    a = n("a")
    return package.Specification(
        {
            p(n("basics")): module.Specification(
                types={
                    n("int"): Documented(None, ts.OpaqueTypeSpecification([])),
                    n("alias"): Documented("d", ts.TypeAliasSpecification([a], INT)),
                    n("custom"): Documented(
                        None, ts.CustomTypeSpecification([], {n("c"): [(a, INT)]})
                    ),
                    n("derived"): Documented(
                        None,
                        ts.DerivedTypeSpecification(
                            [],
                            ts.DerivedTypeSpecificationDetails(
                                INT,
                                FQName(PKG, p(n("m")), n("from")),
                                FQName(PKG, p(n("m")), n("to")),
                            ),
                        ),
                    ),
                },
                values={n("add"): Documented(None, v.Specification([(a, INT)], INT))},
            )
        }
    )


def round_trip(dist):  # type: ignore[no-untyped-def]
    text = json.dumps(codec.encode_versioned_distribution(dist))
    return codec.decode_versioned_distribution(text)


class TestLayout:
    @pytest.mark.parametrize("name", SHIMMED)
    def test_shim_exports_same_objects(self, name: str) -> None:
        shim = importlib.import_module(f"morphir.ir.{name}")
        real = importlib.import_module(f"morphir.ir.v4.{name}")
        for attr in shim.__all__:
            assert getattr(shim, attr) is getattr(real, attr)

    def test_root_reexports_v4(self) -> None:
        assert ir.Name is v4.Name
        assert ir.LibraryDistribution is v4.LibraryDistribution
        for attr in ir.__all__:
            if hasattr(v4, attr) and attr not in ("module", "package"):
                assert getattr(ir, attr) is getattr(v4, attr)

    def test_v3_and_v4_are_distinct(self) -> None:
        from morphir.ir import v3

        assert v3.Name is not ir.Name
        assert v3.Library is not ir.LibraryDistribution

    def test_package_version_is_optional(self) -> None:
        assert PackageInfo(PKG).version is None
        assert PackageInfo(PKG, "1.0.0").version == "1.0.0"


class TestNames:
    @pytest.mark.parametrize(
        ("words", "text"),
        [
            (("value", "in", "u", "s", "d"), "value-in-USD"),
            (("a",), "a"),
            (("f", "r", "2052", "a"), "FR-2052-a"),
            (("item", "2"), "item-2"),
            (("s", "d", "k"), "SDK"),
        ],
    )
    def test_canonical_spelling(self, words: tuple[str, ...], text: str) -> None:
        assert codec.encode_name(Name(words)) == text
        assert codec.decode_name(text) == words

    @pytest.mark.parametrize(
        "text", ["value-in-Usd", "value-in-(usd)", "A", "B2B", "USD-EUR", "a-b", ""]
    )
    def test_unrepresentable_names(self, text: str) -> None:
        assert fail_codes(codec.decode_name, text) == (d.INVALID_NAME,)

    def test_encode_rejects_bad_words(self) -> None:
        assert fail_codes(codec.encode_name, Name(("Bad",))) == (d.INVALID_NAME,)
        assert fail_codes(codec.encode_name, Name(())) == (d.INVALID_NAME,)

    def test_paths_and_fqnames(self) -> None:
        sdk = p(n("morphir"), n("s", "d", "k"))
        assert codec.encode_path(sdk) == "morphir/SDK"
        assert codec.decode_path("morphir/SDK") == sdk
        assert codec.decode_path("") == ()
        f = FQName(sdk, p(n("list")), n("map"))
        assert codec.encode_fqname(f) == "morphir/SDK:list#map"
        assert codec.decode_fqname("morphir/SDK:list#map") == f
        assert fail_codes(codec.decode_fqname, "morphir/SDK.list.map") == (
            d.INVALID_NAME,
        )
        assert fail_codes(codec.decode_name, ["legacy"]) == (d.INVALID_JSON,)


class TestRoundTrip:
    def test_library(self) -> None:
        lib = LibraryDistribution(
            PackageInfo(PKG, "1.2.0"),
            sample_definition(),
            {p(n("morphir"), n("s", "d", "k")): sample_specification()},
        )
        decoded = round_trip(lib)
        assert decoded == LibraryDistribution(
            PackageInfo(PKG), lib.definition, lib.dependencies
        )

    def test_specs(self) -> None:
        specs = SpecsDistribution(PackageInfo(PKG), sample_specification())
        assert round_trip(specs) == specs

    def test_application(self) -> None:
        target = FQName(PKG, p(n("main")), n("run"))
        app = ApplicationDistribution(
            PackageInfo(PKG),
            sample_definition(),
            {p(n("dep")): package.Definition()},
            {
                n("startup"): EntryPoint(
                    target, EntryPointKind.Main, Documented(None, "Go")
                ),
                n("job"): EntryPoint(target, EntryPointKind.Job),
            },
        )
        assert round_trip(app) == app

    def test_attributes_and_hole(self) -> None:
        src_t = t.SourceLocation(1, 2, 3, 4)
        src_v = v.SourceLocation(1, 2, 3, 4)
        ext = {FQName(PKG, p(n("m")), n("tag")): {"k": [1]}}
        tpe = t.Unit(t.TypeAttributes(source=src_t, extensions=ext))
        assert codec.decode_type(codec.encode_type(tpe)) == tpe
        attrs = v.ValueAttributes(source=src_v, inferred_type=tpe, extensions=ext)
        hole = v.Hole(attrs, inc.TypeMismatch("a", "b"), INT)
        assert codec.decode_value(codec.encode_value(hole)) == hole
        bare = v.Hole(v.ValueAttributes(), inc.DeletedDuringRefactor("tx"), None)
        assert codec.decode_value(codec.encode_value(bare)) == bare

    def test_document_literal(self) -> None:
        value = doc.DocObject(
            {
                "a": doc.DocArray(
                    [
                        doc.DocNull(),
                        doc.DocBool(True),
                        doc.DocInt(1),
                        doc.DocFloat(1.5),
                        doc.DocString("s"),
                    ]
                )
            }
        )
        literal = lit.DocumentLiteral(value)
        assert codec.decode_literal(codec.encode_literal(literal)) == literal

    def test_whole_number_literal_is_read_as_integer(self) -> None:
        assert codec.decode_literal({"WholeNumberLiteral": 3}) == lit.IntegerLiteral(3)

    def test_envelope_shape(self) -> None:
        lib = LibraryDistribution(PackageInfo(PKG, "9.9.9"), package.Definition())
        encoded = codec.encode_versioned_distribution(lib)
        assert list(encoded) == ["formatVersion", "distribution"]
        assert encoded["formatVersion"] == 4
        assert encoded["distribution"] == {
            "Library": {
                "packageName": "my/pkg",
                "dependencies": {},
                "def": {"modules": {}},
            }
        }
        assert "9.9.9" not in json.dumps(encoded)

    def test_string_version_is_accepted(self) -> None:
        text = '{"distribution": {"Library": {"packageName": "a"}}, "formatVersion": "4.0.0"}'
        decoded = codec.decode_versioned_distribution(text)
        assert decoded == LibraryDistribution(
            PackageInfo(p(n("a"))), package.Definition()
        )

    def test_draft_notice_names_pin(self) -> None:
        assert codec.FINOS_MORPHIR_PIN in codec.DRAFT_NOTICE
        assert "draft" in (codec.__doc__ or "").lower()
        assert codec.FINOS_MORPHIR_PIN in (v4.__doc__ or "")


class TestDecodeFailures:
    def test_unknown_node(self) -> None:
        err = pytest.raises(DiagnosticError, codec.decode_type, {"Union": {}}).value
        assert err.codes == (d.UNKNOWN_NODE,)
        assert err.diagnostics[0].location == ("Union",)

    def test_compact_spelling_is_not_guessed(self) -> None:
        assert fail_codes(codec.decode_type, "morphir/SDK:basics#int") == (
            d.INVALID_JSON,
        )
        assert fail_codes(codec.decode_type, {"Unit": {}, "Tuple": {}}) == (
            d.UNKNOWN_NODE,
        )

    def test_unknown_member(self) -> None:
        bad = {"Variable": {"name": "a", "annotations": []}}
        assert fail_codes(codec.decode_type, bad) == (d.UNKNOWN_MEMBER,)

    def test_missing_member(self) -> None:
        assert fail_codes(
            codec.decode_value, {"Apply": {"function": {"Unit": {}}}}
        ) == (d.MISSING_MEMBER,)

    def test_duplicate_member(self) -> None:
        text = (
            '{"formatVersion": 4, "distribution": {"Library": '
            '{"packageName": "a", "packageName": "b"}}}'
        )
        assert fail_codes(codec.decode_versioned_distribution, text) == (
            d.DUPLICATE_MEMBER,
        )

    def test_unknown_distribution_kind_and_root_member(self) -> None:
        doc_ = {"formatVersion": 4, "distribution": {"Component": {}}}
        assert fail_codes(codec.decode_versioned_distribution, doc_) == (
            d.UNKNOWN_NODE,
        )
        doc_ = {"formatVersion": 4, "distribution": {}, "extra": 1}
        assert fail_codes(codec.decode_versioned_distribution, doc_) == (
            d.UNKNOWN_MEMBER,
        )

    def test_v3_is_refused(self) -> None:
        assert fail_codes(
            codec.decode_versioned_distribution, {"formatVersion": 3}
        ) == (d.UNSUPPORTED_FORMAT_VERSION_MAJOR,)

    def test_unknown_definition_body(self) -> None:
        other = {"MacroBody": {"inputTypes": {}, "outputType": {"Unit": {}}}}
        assert fail_codes(codec.decode_value_definition, other) == (d.UNKNOWN_NODE,)
        native = {"NativeBody": {"inputTypes": {}, "outputType": {"Unit": {}}}}
        assert fail_codes(codec.decode_value_definition, native) == (d.MISSING_MEMBER,)

    @pytest.mark.parametrize(
        "bad",
        [
            {"BoolLiteral": 1},
            {"CharLiteral": "ab"},
            {"StringLiteral": 1},
            {"IntegerLiteral": 1.5},
            {"FloatLiteral": "x"},
            {"DecimalLiteral": 1},
            {"DecimalLiteral": "x"},
        ],
    )
    def test_invalid_literals(self, bad: dict[str, object]) -> None:
        assert fail_codes(codec.decode_literal, bad) == (d.INVALID_LITERAL,)

    def test_unknown_literal(self) -> None:
        assert fail_codes(codec.decode_literal, {"Nope": 1}) == (d.UNKNOWN_NODE,)

    def test_access_entry_point_and_source(self) -> None:
        bad_access = {"modules": {"m": {"Protected": {}}}}
        assert fail_codes(codec.decode_package_definition, bad_access) == (
            d.UNKNOWN_NODE,
        )
        bad_ctor_access = {
            "CustomTypeDefinition": {
                "typeParams": [],
                "constructors": {},
                "access": "x",
            }
        }
        assert fail_codes(codec.decode_type_definition, bad_ctor_access) == (
            d.UNKNOWN_NODE,
        )
        bad_kind = {
            "Application": {
                "packageName": "a",
                "entryPoints": {"e": {"target": "a:b#c", "kind": "daemon"}},
            }
        }
        assert fail_codes(codec.decode_distribution, bad_kind) == (d.UNKNOWN_NODE,)
        bad_source = {
            "Unit": {
                "attributes": {
                    "source": {
                        "startLine": "1",
                        "startColumn": 1,
                        "endLine": 1,
                        "endColumn": 1,
                    }
                }
            }
        }
        assert fail_codes(codec.decode_type, bad_source) == (d.INVALID_JSON,)
        bad_ctor = {"c": [["a"]]}
        assert fail_codes(codec._decode_constructors, bad_ctor, ()) == (d.INVALID_JSON,)


class TestEncodeFailures:
    @pytest.mark.parametrize(
        "node",
        [
            v.Native(v.ValueAttributes(), FQName(PKG, p(n("m")), n("f")), None),
            v.External(v.ValueAttributes(), "f", "js"),
        ],
    )
    def test_native_and_external_have_no_spelling(self, node: v.Value) -> None:
        err = pytest.raises(DiagnosticError, codec.encode_value, node).value
        assert err.codes == (d.NO_V4_SPELLING,)
        assert err.diagnostics[0].construct == type(node).__name__

    def test_duplicate_record_field(self) -> None:
        unit = v.Unit(v.ValueAttributes())
        record = v.Record(v.ValueAttributes(), [(n("x"), unit), (n("x"), unit)])
        assert fail_codes(codec.encode_value, record) == (d.DUPLICATE_MEMBER,)
        rtype = t.Record(TA, [t.Field(n("x"), INT), t.Field(n("x"), INT)])
        assert fail_codes(codec.encode_type, rtype) == (d.DUPLICATE_MEMBER,)

    def test_constraints_have_no_spelling(self) -> None:
        tpe = t.Unit(t.TypeAttributes(constraints=TypeConstraints()))
        assert fail_codes(codec.encode_type, tpe) == (d.NO_V4_SPELLING,)

    def test_input_attributes_beyond_declared_type(self) -> None:
        unit = v.Unit(v.ValueAttributes())
        defn = v.Definition([(n("a"), typed(t.Unit(TA)), INT)], INT, unit)
        assert fail_codes(codec.encode_value_definition, defn) == (d.NO_V4_SPELLING,)
