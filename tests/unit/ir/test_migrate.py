"""Tests for v3 <-> v4 migrations (capability ir/migrate)."""

import dataclasses
from decimal import Decimal
from pathlib import Path

import pytest

from morphir.ir import diagnostics as d
from morphir.ir import v3
from morphir.ir.migrate import Err, Ok, v3_to_v4, v4_to_v3
from morphir.ir.v3 import codec as v3_codec
from morphir.ir.v3 import literal as lit3
from morphir.ir.v3 import package as pkg3
from morphir.ir.v3 import type as t3
from morphir.ir.v3 import value as val3
from morphir.ir.v4 import document as doc4
from morphir.ir.v4 import literal as lit4
from morphir.ir.v4 import module as mod4
from morphir.ir.v4 import package as pkg4
from morphir.ir.v4 import type as t4
from morphir.ir.v4 import type_def as td4
from morphir.ir.v4 import type_spec as ts4
from morphir.ir.v4 import value as v4
from morphir.ir.v4.access_controlled import Private, Public
from morphir.ir.v4.distribution import (
    ApplicationDistribution,
    LibraryDistribution,
    PackageInfo,
    SpecsDistribution,
)
from morphir.ir.v4.documented import Documented
from morphir.ir.v4.fqname import FQName
from morphir.ir.v4.name import Name
from morphir.ir.v4.path import Path as IRPath
from morphir.ir.v4.type_constraints import TypeConstraints

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "ir" / "v3"
FIXTURE_FILES = sorted(FIXTURES.glob("*.json"))


def load(path: Path) -> v3.Library:
    return v3_codec.decode_versioned_distribution(path.read_text(encoding="utf-8"))


def n(*words: str) -> Name:
    return Name(words)


PKG = IRPath((n("my"), n("pkg")))
INT = t4.Reference(
    t4.TypeAttributes(),
    FQName(IRPath((n("morphir"), n("s", "d", "k"))), IRPath((n("basics"),)), n("int")),
)
TYPED = v4.ValueAttributes(inferred_type=INT)


def library(
    body: v4.Value | None = None,
    *,
    version: str | None = None,
    value_doc: str | None = "doc",
    inputs: list[tuple[Name, v4.ValueAttributes, t4.Type]] | None = None,
    types: dict[Name, object] | None = None,
) -> LibraryDistribution:
    defn = v4.Definition(inputs or [], INT, body or v4.Unit(TYPED))
    mod = mod4.Definition(
        types=types or {},  # type: ignore[arg-type]
        values={n("main"): Public(Documented(value_doc, defn))},
    )
    return LibraryDistribution(
        PackageInfo(PKG, version),
        pkg4.Definition({IRPath((n("app"),)): Public(mod)}),
    )


def errors(result: object) -> list[tuple[str, str]]:
    assert isinstance(result, Err)
    return [(x.code, x.construct) for x in result.diagnostics]


class TestForward:
    @pytest.mark.parametrize("path", FIXTURE_FILES, ids=lambda p: p.name)
    def test_round_trip_is_semantically_equal(self, path: Path) -> None:
        lib = load(path)
        up = v3_to_v4(lib, package_version="1.2.0")
        assert isinstance(up, Ok)
        assert up.warnings == ()
        back = v4_to_v3(up.value)
        assert isinstance(back, Ok)
        assert back.value == lib
        assert [w.code for w in back.warnings] == [d.PACKAGE_VERSION_DROPPED]

    def test_values_carry_inferred_type(self) -> None:
        lib = load(FIXTURES / "elm-simpleValueTree.json")
        result = v3_to_v4(lib)
        assert isinstance(result, Ok)
        assert result.value.package.version is None
        for mod in result.value.definition.modules.values():
            for value in mod.value.values.values():
                body = value.value.value.body
                assert body.attributes.inferred_type is not None
                assert body.attributes.source is None
                assert body.attributes.extensions == {}

    def test_whole_number_becomes_integer(self) -> None:
        u = t3.Unit(None)
        body = val3.LiteralValue(u, lit3.WholeNumberLiteral(7))
        defn = val3.Definition((), u, body)
        mod = v3.module.Definition(
            values={
                v3.Name(("x",)): v3.access_controlled.public(v3.Documented("", defn))
            }
        )
        lib = v3.Library(
            v3.Path((v3.Name(("p",)),)),
            pkg3.Definition(
                {v3.Path((v3.Name(("m",)),)): v3.access_controlled.private(mod)}
            ),
        )
        result = v3_to_v4(lib)
        assert isinstance(result, Ok)
        module = result.value.definition.modules[IRPath((n("m"),))]
        assert isinstance(module, Private)
        migrated = module.value.values[n("x")].value.value.body
        assert isinstance(migrated, v4.LiteralValue)
        assert migrated.literal == lit4.IntegerLiteral(7)


class TestReverse:
    def test_compatible_library_downgrades(self) -> None:
        literals: list[lit4.Literal] = [
            lit4.BoolLiteral(True),
            lit4.CharLiteral("c"),
            lit4.StringLiteral("s"),
            lit4.IntegerLiteral(1),
            lit4.FloatLiteral(1.5),
            lit4.DecimalLiteral(Decimal("2.5")),
        ]
        body = v4.Tuple(TYPED, [v4.LiteralValue(TYPED, x) for x in literals])
        result = v4_to_v3(library(body, inputs=[(n("a"), TYPED, INT)]))
        assert isinstance(result, Ok)
        assert result.warnings == ()

    def test_package_version_dropped_warning(self) -> None:
        result = v4_to_v3(library(version="1.2.0"))
        assert isinstance(result, Ok)
        assert [w.code for w in result.warnings] == [d.PACKAGE_VERSION_DROPPED]

    @pytest.mark.parametrize(
        ("dist", "kind"),
        [
            (SpecsDistribution(PackageInfo(PKG), pkg4.Specification()), "Specs"),
            (
                ApplicationDistribution(PackageInfo(PKG), pkg4.Definition()),
                "Application",
            ),
        ],
    )
    def test_specs_and_application_do_not_downgrade(
        self, dist: object, kind: str
    ) -> None:
        assert errors(v4_to_v3(dist)) == [(d.UNSUPPORTED_V4_DOWNGRADE, kind)]  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "node",
        [
            v4.Hole(TYPED, None, None),
            v4.Native(TYPED, FQName(PKG, IRPath(()), n("f")), None),
            v4.External(TYPED, "f", "js"),
            v4.LiteralValue(TYPED, lit4.DocumentLiteral(doc4.DocNull())),
        ],
    )
    def test_v4_only_nodes(self, node: v4.Value) -> None:
        found = errors(v4_to_v3(library(node)))
        construct = (
            "DocumentLiteral"
            if isinstance(node, v4.LiteralValue)
            else type(node).__name__
        )
        assert found == [(d.UNSUPPORTED_V4_DOWNGRADE, construct)]
        assert isinstance(v4_to_v3(library(node)), Err)
        result = v4_to_v3(library(node))
        assert isinstance(result, Err)
        assert result.diagnostics[0].location[:2] == ("distribution", "modules")

    def test_missing_inferred_type_on_value_pattern_and_input(self) -> None:
        bare = v4.ValueAttributes()
        body = v4.Lambda(TYPED, v4.WildcardPattern(bare), v4.Unit(bare))
        found = errors(v4_to_v3(library(body, inputs=[(n("a"), bare, INT)])))
        assert found == [
            (d.MISSING_INFERRED_TYPE, "ValueDefinitionInput"),
            (d.MISSING_INFERRED_TYPE, "WildcardPattern"),
            (d.MISSING_INFERRED_TYPE, "Unit"),
        ]

    def test_semantic_type_attributes(self) -> None:
        sources = [
            t4.TypeAttributes(source=t4.SourceLocation(1, 1, 1, 2)),
            t4.TypeAttributes(constraints=TypeConstraints()),
            t4.TypeAttributes(extensions={FQName(PKG, IRPath(()), n("x")): 1}),
        ]
        for attrs in sources:
            typed = v4.ValueAttributes(inferred_type=t4.Unit(attrs))
            assert errors(v4_to_v3(library(v4.Unit(typed)))) == [
                (d.UNSUPPORTED_ATTRIBUTES_DOWNGRADE, "TypeAttributes")
            ]

    def test_value_extensions(self) -> None:
        attrs = dataclasses.replace(
            TYPED, extensions={FQName(PKG, IRPath(()), n("x")): 1}
        )
        assert errors(v4_to_v3(library(v4.Unit(attrs)))) == [
            (d.UNSUPPORTED_ATTRIBUTES_DOWNGRADE, "Unit")
        ]

    def test_missing_member_documentation(self) -> None:
        assert errors(v4_to_v3(library(value_doc=None))) == [
            (d.UNSUPPORTED_DOCUMENTATION_DOWNGRADE, "ValueDefinition")
        ]
        types = {n("t"): Public(Documented(None, td4.TypeAliasDefinition([], INT)))}
        assert errors(v4_to_v3(library(types=types))) == [
            (d.UNSUPPORTED_DOCUMENTATION_DOWNGRADE, "TypeDefinition")
        ]

    def test_every_failure_is_collected_in_one_pass(self) -> None:
        body = v4.Apply(
            TYPED, v4.Hole(TYPED, None, None), v4.Unit(v4.ValueAttributes())
        )
        found = errors(v4_to_v3(library(body, value_doc=None)))
        assert {code for code, _ in found} == {
            d.UNSUPPORTED_DOCUMENTATION_DOWNGRADE,
            d.UNSUPPORTED_V4_DOWNGRADE,
            d.MISSING_INFERRED_TYPE,
        }

    def test_source_locations_need_opt_in(self) -> None:
        attrs = dataclasses.replace(TYPED, source=v4.SourceLocation(1, 1, 1, 5))
        dist = library(v4.Unit(attrs))
        assert errors(v4_to_v3(dist)) == [(d.UNSUPPORTED_ATTRIBUTES_DOWNGRADE, "Unit")]
        result = v4_to_v3(dist, drop_source_locations=True)
        assert isinstance(result, Ok)
        assert [w.code for w in result.warnings] == [d.SOURCE_LOCATION_DROPPED]

    def test_invalid_classic_name(self) -> None:
        assert errors(v4_to_v3(library(v4.Variable(TYPED, n("Bad"))))) == [
            (d.INVALID_NAME, "Name")
        ]

    def test_duplicate_record_fields(self) -> None:
        unit = v4.Unit(TYPED)
        body = v4.Record(TYPED, [(n("x"), unit), (n("x"), unit)])
        assert errors(v4_to_v3(library(body))) == [(d.DUPLICATE_MEMBER, "Record")]

    def test_hand_built_library_with_every_node_downgrades(self) -> None:
        a = n("a")
        u = v4.Unit(TYPED)
        f = FQName(PKG, IRPath((n("app"),)), n("f"))
        ta = t4.TypeAttributes()
        pats: list[v4.Pattern] = [
            v4.WildcardPattern(TYPED),
            v4.AsPattern(TYPED, v4.UnitPattern(TYPED), a),
            v4.TuplePattern(TYPED, [v4.EmptyListPattern(TYPED)]),
            v4.ConstructorPattern(TYPED, f, []),
            v4.HeadTailPattern(
                TYPED, v4.WildcardPattern(TYPED), v4.WildcardPattern(TYPED)
            ),
            v4.LiteralPattern(TYPED, lit4.IntegerLiteral(1)),
        ]
        inner = v4.Definition([], INT, u)
        body = v4.LetDefinition(
            TYPED,
            a,
            inner,
            v4.LetRecursion(
                TYPED,
                {a: inner},
                v4.PatternMatch(
                    TYPED,
                    v4.List(TYPED, [v4.Constructor(TYPED, f), v4.Reference(TYPED, f)]),
                    [(x, v4.Destructure(TYPED, x, u, u)) for x in pats],
                ),
            ),
        )
        extra = v4.IfThenElse(
            TYPED,
            v4.Field(TYPED, u, a),
            v4.FieldFunction(TYPED, a),
            v4.UpdateRecord(TYPED, v4.Variable(TYPED, a), [(a, u)]),
        )
        fields = [t4.Field(a, INT)]
        types: list[t4.Type] = [
            t4.Variable(ta, a),
            t4.Tuple(ta, [INT]),
            t4.Record(ta, fields),
            t4.ExtensibleRecord(ta, a, fields),
            t4.Function(ta, INT, INT),
            t4.Unit(ta),
        ]
        ctors: ts4.Constructors = {a: [(a, INT)]}
        type_defs = {
            n("alias"): Public(Documented("d", td4.TypeAliasDefinition([a], types[0]))),
            n("custom"): Private(
                Documented("d", td4.CustomTypeDefinition([], Private(ctors)))
            ),
        }
        dist = library(v4.Apply(TYPED, body, extra), types=type_defs)
        dist = dataclasses.replace(
            dist,
            dependencies={
                PKG: pkg4.Specification(
                    {
                        IRPath((n("m"),)): mod4.Specification(
                            types={
                                n("o"): Documented("", ts4.OpaqueTypeSpecification([])),
                                n("al"): Documented(
                                    "", ts4.TypeAliasSpecification([], types[1])
                                ),
                                n("c"): Documented(
                                    "", ts4.CustomTypeSpecification([], ctors)
                                ),
                                n("dr"): Documented(
                                    "",
                                    ts4.DerivedTypeSpecification(
                                        [],
                                        ts4.DerivedTypeSpecificationDetails(
                                            types[2], f, f
                                        ),
                                    ),
                                ),
                            },
                            values={
                                n("v", str(i)): Documented(
                                    "", v4.Specification([(a, x)], x)
                                )
                                for i, x in enumerate(types)
                            },
                        )
                    }
                )
            },
        )
        result = v4_to_v3(dist)
        assert isinstance(result, Ok), result
        up = v3_to_v4(result.value)
        assert isinstance(up, Ok)
        again = v4_to_v3(up.value)
        assert isinstance(again, Ok)
        assert again.value == result.value
