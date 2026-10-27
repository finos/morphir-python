"""Tests for the upstream v4 constructs (change align-ir-v4-with-upstream).

Expected JSON is the expanded form of the finos/morphir kit cases at the pinned
commit; the case id is named in each test.
"""

from __future__ import annotations

import pytest

from morphir.ir import diagnostics as d
from morphir.ir import v4
from morphir.ir.diagnostics import DiagnosticError
from morphir.ir.migrate import Err, v4_to_v3
from morphir.ir.v4 import annotation as ann
from morphir.ir.v4 import codec, module, package
from morphir.ir.v4 import incompleteness as inc
from morphir.ir.v4 import type as t
from morphir.ir.v4 import type_def as td
from morphir.ir.v4 import type_spec as ts
from morphir.ir.v4 import value as v
from morphir.ir.v4.access_controlled import Public
from morphir.ir.v4.distribution import (
    LibraryDistribution,
    PackageInfo,
    SpecsDistribution,
)
from morphir.ir.v4.documented import Documented
from morphir.ir.v4.fqname import FQName
from morphir.ir.v4.name import Name
from morphir.ir.v4.path import Path


def n(*words: str) -> Name:
    return Name(words)


def p(*names: Name) -> Path:
    return Path(names)


TA = t.TypeAttributes()
SDK = p(n("morphir"), n("s", "d", "k"))
INT = t.Reference(TA, FQName(SDK, p(n("basics")), n("int")))
STRING = t.Reference(TA, FQName(SDK, p(n("string")), n("string")))
INT_JSON = {"Reference": {"fqname": "morphir/SDK:basics#int"}}
STRING_JSON = {"Reference": {"fqname": "morphir/SDK:string#string"}}
MISSING = FQName(p(n("my", "org"), n("project")), p(n("module")), n("missing"))
TYPED = v.ValueAttributes(inferred_type=INT)


def fail_codes(fn, *args) -> tuple[str, ...]:  # type: ignore[no-untyped-def]
    with pytest.raises(DiagnosticError) as info:
        fn(*args)
    return info.value.codes


def library(
    *,
    types: dict[Name, td.Definition] | None = None,
    values: dict[Name, v.ValueDefinitionBody] | None = None,
) -> LibraryDistribution:
    mod = module.Definition(
        types={k: Public(Documented("doc", x)) for k, x in (types or {}).items()},
        values={k: Public(Documented("doc", x)) for k, x in (values or {}).items()},
    )
    return LibraryDistribution(
        PackageInfo(p(n("my"), n("pkg"))),
        package.Definition({p(n("app")): Public(mod)}),
    )


def downgrade_errors(lib: LibraryDistribution) -> list[tuple[str, str, str]]:
    result = v4_to_v3(lib)
    assert isinstance(result, Err)
    return [
        (x.code, x.construct, "/".join(map(str, x.location)))
        for x in result.diagnostics
    ]


class TestIncompleteness:
    def test_exported_from_v4(self) -> None:
        assert v4.Incompleteness is inc.Incompleteness
        assert v4.HoleReason is inc.HoleReason

    def test_type_mismatch_hole_definitions_0014(self) -> None:
        defn = td.IncompleteTypeDefinition(
            [n("a")],
            inc.HoleIncompleteness(inc.TypeMismatch("morphir/SDK:basics#int", "s")),
        )
        expected = {
            "IncompleteTypeDefinition": {
                "typeParams": ["a"],
                "incompleteness": {
                    "Hole": {
                        "reason": {
                            "TypeMismatch": {
                                "expected": "morphir/SDK:basics#int",
                                "found": "s",
                            }
                        }
                    }
                },
            }
        }
        assert codec.encode_type_definition(defn) == expected
        assert codec.decode_type_definition(expected) == defn

    def test_draft_with_partial_type_definitions_0015(self) -> None:
        defn = td.IncompleteTypeDefinition([], inc.DraftIncompleteness(), INT)
        expected = {
            "IncompleteTypeDefinition": {
                "typeParams": [],
                "incompleteness": {"Draft": {}},
                "partialTypeExp": INT_JSON,
            }
        }
        assert codec.encode_type_definition(defn) == expected
        assert codec.decode_type_definition(expected) == defn

    def test_hole_keeps_partial_body_definitions_0024(self) -> None:
        defn = td.IncompleteTypeDefinition(
            [], inc.HoleIncompleteness(inc.UnresolvedReference(MISSING), INT)
        )
        expected = {
            "IncompleteTypeDefinition": {
                "typeParams": [],
                "incompleteness": {
                    "Hole": {
                        "reason": {
                            "UnresolvedReference": {
                                "target": "my-org/project:module#missing"
                            }
                        },
                        "partialBody": INT_JSON,
                    }
                },
            }
        }
        assert codec.encode_type_definition(defn) == expected
        assert codec.decode_type_definition(expected) == defn

    def test_deleted_during_refactor_reason(self) -> None:
        hole = v.Hole(TYPED, inc.DeletedDuringRefactor("tx-42"), INT)
        encoded = codec.encode_value(hole)
        assert encoded["Hole"]["reason"] == {
            "DeletedDuringRefactor": {"tx-id": "tx-42"}
        }
        assert codec.decode_value(encoded) == hole

    def test_draft_is_not_a_hole_reason_definitions_0026(self) -> None:
        bad = {
            "IncompleteTypeDefinition": {
                "typeParams": [],
                "incompleteness": {"Hole": {"reason": {"Draft": {}}}},
            }
        }
        assert fail_codes(codec.decode_type_definition, bad) == (d.UNKNOWN_NODE,)

    def test_reason_must_be_an_object(self) -> None:
        bad = {"Hole": {"reason": "Draft"}}
        assert fail_codes(codec.decode_value, bad) == (d.INVALID_JSON,)

    def test_incomplete_type_definition_does_not_downgrade(self) -> None:
        defn = td.IncompleteTypeDefinition([], inc.DraftIncompleteness())
        errors = downgrade_errors(library(types={n("t"): defn}))
        assert errors == [
            (
                d.UNSUPPORTED_V4_DOWNGRADE,
                "IncompleteTypeDefinition",
                "distribution/modules/app/types/t/IncompleteTypeDefinition",
            )
        ]


INPUTS_INT = [(n("a"), INT), (n("b"), INT)]
X_JSON = {"Variable": {"attributes": {"inferredType": INT_JSON}, "name": "x"}}


class TestDefinitionBodies:
    def test_exported_from_v4(self) -> None:
        assert v4.ValueDefinitionBody is v.ValueDefinitionBody
        assert v4.NativeBody is v.NativeBody

    def test_native_body_definitions_0009(self) -> None:
        body = v.NativeBody(INPUTS_INT, INT, v.NativeInfo(v.Arithmetic()))
        expected = {
            "NativeBody": {
                "inputTypes": {"a": INT_JSON, "b": INT_JSON},
                "outputType": INT_JSON,
                "nativeInfo": {"hint": {"Arithmetic": {}}},
            }
        }
        assert codec.encode_value_definition(body) == expected
        assert codec.decode_value_definition(expected) == body

    @pytest.mark.parametrize(
        "hint",
        [
            v.Comparison(),
            v.StringOp(),
            v.CollectionOp(),
            v.PlatformSpecific("wasm"),
        ],
        ids=lambda h: type(h).__name__,
    )
    def test_native_hints_round_trip(self, hint: v.NativeHint) -> None:
        body = v.NativeBody([], INT, v.NativeInfo(hint))
        assert (
            codec.decode_value_definition(codec.encode_value_definition(body)) == body
        )

    def test_platform_specific_names_its_platform_definitions_0030(self) -> None:
        bad = {
            "NativeBody": {
                "inputTypes": {},
                "outputType": INT_JSON,
                "nativeInfo": {"hint": {"PlatformSpecific": {}}},
            }
        }
        assert fail_codes(codec.decode_value_definition, bad) == (d.MISSING_MEMBER,)

    def test_external_body_definitions_0007(self) -> None:
        body = v.ExternalBody(
            [(n("msg"), STRING)],
            INT,
            [v.ExternalBinding("javascript", "console.log")],
        )
        expected = {
            "ExternalBody": {
                "inputTypes": {"msg": STRING_JSON},
                "outputType": INT_JSON,
                "externals": [
                    {"targetPlatform": "javascript", "externalName": "console.log"}
                ],
            }
        }
        assert codec.encode_value_definition(body) == expected
        assert codec.decode_value_definition(expected) == body

    def test_external_body_with_fallback_definitions_0008(self) -> None:
        body = v.ExternalBody(
            [(n("x"), INT)],
            INT,
            [
                v.ExternalBinding("erlang", "math:abs"),
                v.ExternalBinding("javascript", "Math.abs"),
            ],
            v.Variable(TYPED, n("x")),
        )
        encoded = codec.encode_value_definition(body)
        assert encoded["ExternalBody"]["body"] == X_JSON
        assert codec.decode_value_definition(encoded) == body

    def test_duplicate_platform_is_refused(self) -> None:
        bindings = [v.ExternalBinding("js", "a"), v.ExternalBinding("js", "b")]
        body = v.ExternalBody([], INT, bindings)
        assert fail_codes(codec.encode_value_definition, body) == (d.DUPLICATE_MEMBER,)
        bad = {
            "ExternalBody": {
                "inputTypes": {},
                "outputType": INT_JSON,
                "externals": [
                    {"targetPlatform": "js", "externalName": "a"},
                    {"targetPlatform": "js", "externalName": "b"},
                ],
            }
        }
        assert fail_codes(codec.decode_value_definition, bad) == (d.DUPLICATE_MEMBER,)

    def test_external_body_needs_a_binding(self) -> None:
        body = v.ExternalBody([], INT, [])
        assert fail_codes(codec.encode_value_definition, body) == (d.INVALID_JSON,)
        bad = {
            "ExternalBody": {"inputTypes": {}, "outputType": INT_JSON, "externals": []}
        }
        assert fail_codes(codec.decode_value_definition, bad) == (d.INVALID_JSON,)

    def test_incomplete_body_definitions_0016(self) -> None:
        body = v.IncompleteBody(
            [(n("x"), INT)],
            inc.HoleIncompleteness(inc.DeletedDuringRefactor("tx-42")),
            INT,
        )
        expected = {
            "IncompleteBody": {
                "inputTypes": {"x": INT_JSON},
                "outputType": INT_JSON,
                "incompleteness": {
                    "Hole": {"reason": {"DeletedDuringRefactor": {"tx-id": "tx-42"}}}
                },
            }
        }
        assert codec.encode_value_definition(body) == expected
        assert codec.decode_value_definition(expected) == body

    def test_incomplete_body_keeps_partial_value_definitions_0025(self) -> None:
        body = v.IncompleteBody(
            [], inc.DraftIncompleteness(), INT, v.Variable(TYPED, n("x"))
        )
        encoded = codec.encode_value_definition(body)
        assert encoded["IncompleteBody"]["partialBody"] == X_JSON
        assert codec.decode_value_definition(encoded) == body
        no_output = v.IncompleteBody([], inc.DraftIncompleteness())
        encoded = codec.encode_value_definition(no_output)
        assert "outputType" not in encoded["IncompleteBody"]
        assert codec.decode_value_definition(encoded) == no_output

    def test_let_binding_holds_any_body(self) -> None:
        native = v.NativeBody([], INT, v.NativeInfo(v.Arithmetic()))
        let = v.LetDefinition(TYPED, n("f"), native, v.Variable(TYPED, n("f")))
        assert codec.decode_value(codec.encode_value(let)) == let

    def test_library_mixing_bodies_round_trips(self) -> None:
        lib = library(
            values={
                n("native"): v.NativeBody([], INT, v.NativeInfo(v.Arithmetic())),
                n("expr"): v.Definition([], INT, v.Unit(TYPED)),
            }
        )
        document = codec.encode_versioned_distribution(lib)
        assert codec.decode_versioned_distribution(document) == lib

    def test_new_bodies_do_not_downgrade(self) -> None:
        native = v.NativeBody([], INT, v.NativeInfo(v.Arithmetic()))
        external = v.ExternalBody([], INT, [v.ExternalBinding("js", "f")])
        incomplete = v.IncompleteBody([], inc.DraftIncompleteness())
        let = v.Definition(
            [], INT, v.LetDefinition(TYPED, n("g"), native, v.Unit(TYPED))
        )
        lib = library(
            values={
                n("n"): native,
                n("e"): external,
                n("i"): incomplete,
                n("l"): let,
            }
        )
        values = "distribution/modules/app/values"
        assert downgrade_errors(lib) == [
            (d.UNSUPPORTED_V4_DOWNGRADE, "NativeBody", f"{values}/n/NativeBody"),
            (d.UNSUPPORTED_V4_DOWNGRADE, "ExternalBody", f"{values}/e/ExternalBody"),
            (
                d.UNSUPPORTED_V4_DOWNGRADE,
                "IncompleteBody",
                f"{values}/i/IncompleteBody",
            ),
            (
                d.UNSUPPORTED_V4_DOWNGRADE,
                "NativeBody",
                f"{values}/l/body/LetDefinition/definition/NativeBody",
            ),
        ]

    def test_input_drop_walks_external_fallback(self) -> None:
        from morphir.ir.migrate import drop_input_attributes

        inner = v.Definition(
            [(n("y"), v.ValueAttributes(inferred_type=STRING), INT)],
            INT,
            v.Unit(TYPED),
        )
        fallback = v.LetDefinition(TYPED, n("g"), inner, v.Unit(TYPED))
        external = v.ExternalBody([], INT, [v.ExternalBinding("js", "f")], fallback)
        result = drop_input_attributes(library(values={n("e"): external}))
        assert [w.location[-1] for w in result.warnings] == ["y"]
        codec.encode_versioned_distribution(result.value)


ANNOTATIONS = p(n("annotations"))
ORG = p(n("my", "org"), n("project"))


def anno(local: str) -> FQName:
    return FQName(ORG, ANNOTATIONS, n(local))


def lit_string(text: str) -> v.Value:
    from morphir.ir.v4 import literal

    return v.LiteralValue(v.ValueAttributes(), literal.StringLiteral(text))


class TestAnnotations:
    def test_exported_from_v4(self) -> None:
        assert v4.Annotation is ann.Annotation

    def test_type_specification_annotations_definitions_0020(self) -> None:
        spec = ts.TypeAliasSpecification(
            [],
            STRING,
            [
                ann.CompactAnnotation(anno("deprecated"), "Use user-v2 instead"),
                ann.StructuredAnnotation(
                    anno("since"),
                    [
                        ann.PositionalArgument(lit_string("1.2.0")),
                        ann.NamedArgument(n("reason"), lit_string("renamed")),
                    ],
                ),
                ann.StructuredAnnotation(anno("internal")),
            ],
        )
        string_literal = {"literal": {"StringLiteral": "1.2.0"}}
        expected = {
            "TypeAliasSpecification": {
                "annotations": [
                    "my-org/project:annotations#deprecated:Use user-v2 instead",
                    {
                        "name": "my-org/project:annotations#since",
                        "arguments": [
                            {"Literal": string_literal},
                            {
                                "name": "reason",
                                "value": {
                                    "Literal": {"literal": {"StringLiteral": "renamed"}}
                                },
                            },
                        ],
                    },
                    {"name": "my-org/project:annotations#internal"},
                ],
                "typeParams": [],
                "typeExp": STRING_JSON,
            }
        }
        encoded = codec.encode_type_specification(spec)
        assert encoded == expected
        assert next(iter(encoded["TypeAliasSpecification"])) == "annotations"
        assert codec.decode_type_specification(expected) == spec

    def test_empty_arguments_read_as_structured(self) -> None:
        j = {
            "OpaqueTypeSpecification": {
                "annotations": [
                    {"name": "my-org/project:annotations#internal", "arguments": []}
                ]
            }
        }
        spec = codec.decode_type_specification(j)
        assert spec == ts.OpaqueTypeSpecification(
            [], [ann.StructuredAnnotation(anno("internal"))]
        )

    def test_compact_text_starts_after_first_colon_after_hash(self) -> None:
        j = {
            "OpaqueTypeSpecification": {
                "annotations": ["my-org/project:annotations#version:1.0.0:rc"]
            }
        }
        spec = codec.decode_type_specification(j)
        assert spec.annotations == [ann.CompactAnnotation(anno("version"), "1.0.0:rc")]

    def test_value_specification_definitions_0021(self) -> None:
        spec = v.Specification(
            [(n("x"), INT)], INT, [ann.CompactAnnotation(anno("pure"))]
        )
        expected = {
            "annotations": ["my-org/project:annotations#pure"],
            "inputs": {"x": INT_JSON},
            "output": INT_JSON,
        }
        assert codec.encode_value_specification(spec) == expected
        assert codec.decode_value_specification(expected) == spec

    def test_module_specification_definitions_0022(self) -> None:
        spec = module.Specification(
            doc="The domain module",
            annotations=[ann.CompactAnnotation(anno("stable"))],
        )
        expected = {
            "annotations": ["my-org/project:annotations#stable"],
            "types": {},
            "values": {},
            "doc": "The domain module",
        }
        encoded = codec.encode_module_specification(spec)
        assert encoded == expected
        assert list(encoded) == ["annotations", "types", "values", "doc"]
        assert codec.decode_module_specification(expected) == spec

    def test_no_annotations_writes_no_member(self) -> None:
        spec = ts.OpaqueTypeSpecification([])
        assert codec.encode_type_specification(spec) == {
            "OpaqueTypeSpecification": {"typeParams": []}
        }

    def test_definition_carries_no_annotations_definitions_0023(self) -> None:
        bad = {
            "TypeAliasDefinition": {
                "annotations": [],
                "typeParams": [],
                "typeExp": STRING_JSON,
            }
        }
        assert fail_codes(codec.decode_type_definition, bad) == (d.UNKNOWN_MEMBER,)

    def test_annotations_do_not_downgrade(self) -> None:
        spec = module.Specification(
            types={
                n("t"): Documented(
                    "doc",
                    ts.OpaqueTypeSpecification(
                        [], [ann.CompactAnnotation(anno("internal"))]
                    ),
                )
            },
            values={
                n("f"): Documented(
                    "doc",
                    v.Specification([], INT, [ann.CompactAnnotation(anno("pure"))]),
                )
            },
            annotations=[ann.CompactAnnotation(anno("stable"))],
        )
        lib = library()
        lib = LibraryDistribution(
            lib.package,
            lib.definition,
            {p(n("dep")): package.Specification({p(n("m")): spec})},
        )
        deps = "distribution/dependencies/dep/m"
        assert downgrade_errors(lib) == [
            (d.UNSUPPORTED_V4_DOWNGRADE, "Annotations", f"{deps}/annotations"),
            (d.UNSUPPORTED_V4_DOWNGRADE, "Annotations", f"{deps}/types/t/annotations"),
            (
                d.UNSUPPORTED_V4_DOWNGRADE,
                "Annotations",
                f"{deps}/values/f/annotations",
            ),
        ]

    def test_specs_distribution_with_annotations_round_trips(self) -> None:
        spec = module.Specification(annotations=[ann.CompactAnnotation(anno("x"))])
        specs = SpecsDistribution(
            PackageInfo(p(n("my"), n("pkg"))),
            package.Specification({p(n("m")): spec}),
        )
        document = codec.encode_versioned_distribution(specs)
        assert codec.decode_versioned_distribution(document) == specs


class TestUnion:
    def test_exported_from_v4(self) -> None:
        assert t.Union in v4.Type.__args__  # type: ignore[attr-defined]

    def test_union_round_trips(self) -> None:
        union = t.Union(TA, [STRING, INT])
        expected = {"Union": {"alternatives": [STRING_JSON, INT_JSON]}}
        assert codec.encode_type(union) == expected
        assert codec.decode_type(expected) == union

    def test_order_duplicates_nesting_and_attributes_are_kept(self) -> None:
        attrs = t.TypeAttributes(source=t.SourceLocation(1, 1, 1, 9))
        union = t.Union(attrs, [INT, t.Union(TA, [STRING, INT]), INT])
        encoded = codec.encode_type(union)
        assert "attributes" in encoded["Union"]
        assert codec.decode_type(encoded) == union

    @pytest.mark.parametrize("alternatives", [[], [INT]], ids=["empty", "singleton"])
    def test_fewer_than_two_alternatives_are_refused(
        self, alternatives: list[t.Type]
    ) -> None:
        union = t.Union(TA, alternatives)
        assert fail_codes(codec.encode_type, union) == (d.INVALID_JSON,)
        bad = {"Union": {"alternatives": [codec.encode_type(x) for x in alternatives]}}
        assert fail_codes(codec.decode_type, bad) == (d.INVALID_JSON,)

    def test_map_attributes_keeps_order_and_duplicates(self) -> None:
        union = t.Union(TA, [INT, STRING, INT])
        src = t.TypeAttributes(source=t.SourceLocation(1, 1, 1, 1))
        mapped = t.map_attributes(union, lambda _: src)
        assert isinstance(mapped, t.Union)
        assert mapped.attributes == src
        assert [type(x).__name__ for x in mapped.alternatives] == ["Reference"] * 3
        assert all(x.attributes == src for x in mapped.alternatives)

    def test_union_does_not_downgrade(self) -> None:
        defn = td.TypeAliasDefinition([], t.Union(TA, [STRING, INT]))
        errors = downgrade_errors(library(types={n("t"): defn}))
        assert errors == [
            (
                d.UNSUPPORTED_V4_DOWNGRADE,
                "Union",
                "distribution/modules/app/types/t/Union",
            )
        ]


class TestDeprecated:
    @pytest.mark.parametrize(
        ("cls", "replacement"),
        [(v.Native, "NativeBody"), (v.External, "ExternalBody")],
    )
    def test_value_nodes_name_their_replacement(
        self, cls: type, replacement: str
    ) -> None:
        doc = cls.__doc__ or ""
        assert "Deprecated" in doc
        assert replacement in doc

    def test_type_constraints_are_deprecated(self) -> None:
        from morphir.ir.v4.type_constraints import TypeConstraints

        assert "Deprecated" in (TypeConstraints.__doc__ or "")


class TestInputDropCoverage:
    def test_walks_incomplete_partial_body_and_keeps_native(self) -> None:
        from morphir.ir.migrate import drop_input_attributes

        inner = v.Definition(
            [(n("y"), v.ValueAttributes(inferred_type=STRING), INT)],
            INT,
            v.Unit(TYPED),
        )
        partial = v.LetDefinition(TYPED, n("g"), inner, v.Unit(TYPED))
        incomplete = v.IncompleteBody([], inc.DraftIncompleteness(), None, partial)
        native = v.NativeBody([], INT, v.NativeInfo(v.Arithmetic()))
        lib = library(values={n("i"): incomplete, n("n"): native})
        result = drop_input_attributes(lib)
        assert [w.location[-1] for w in result.warnings] == ["y"]
        mod = result.value.definition.modules[p(n("app"))]
        assert mod.value.values[n("n")].value.value == native

    def test_application_distribution(self) -> None:
        from morphir.ir.migrate import drop_input_attributes
        from morphir.ir.v4.distribution import ApplicationDistribution

        defn = v.Definition(
            [(n("x"), v.ValueAttributes(inferred_type=STRING), INT)],
            INT,
            v.Unit(TYPED),
        )
        lib = library(values={n("main"): defn})
        app = ApplicationDistribution(lib.package, lib.definition)
        result = drop_input_attributes(app)
        assert isinstance(result.value, ApplicationDistribution)
        assert len(result.warnings) == 1


def attributed_let() -> v.Value:
    inner = v.Definition(
        [(n("y"), v.ValueAttributes(inferred_type=STRING), INT)], INT, v.Unit(TYPED)
    )
    return v.LetDefinition(TYPED, n("g"), inner, v.Unit(TYPED))


def annotated_spec() -> module.Specification:
    def structured(name: str) -> ann.StructuredAnnotation:
        return ann.StructuredAnnotation(
            anno(name),
            [
                ann.PositionalArgument(attributed_let()),
                ann.NamedArgument(n("k"), attributed_let()),
            ],
        )

    return module.Specification(
        types={
            n("t"): Documented(
                "doc", ts.OpaqueTypeSpecification([], [structured("type")])
            )
        },
        values={
            n("f"): Documented("doc", v.Specification([], INT, [structured("value")]))
        },
        annotations=[ann.CompactAnnotation(anno("stable")), structured("module")],
    )


class TestInputDropInSpecifications:
    def test_specs_distribution_annotation_arguments(self) -> None:
        from morphir.ir.migrate import drop_input_attributes

        specs = SpecsDistribution(
            PackageInfo(p(n("my"), n("pkg"))),
            package.Specification({p(n("m")): annotated_spec()}),
        )
        with pytest.raises(DiagnosticError):
            codec.encode_versioned_distribution(specs)
        result = drop_input_attributes(specs)
        assert len(result.warnings) == 6
        assert {w.location[:3] for w in result.warnings} == {
            ("distribution", "modules", "m")
        }
        codec.encode_versioned_distribution(result.value)

    def test_library_dependency_specifications(self) -> None:
        from morphir.ir.migrate import drop_input_attributes

        lib = library()
        lib = LibraryDistribution(
            lib.package,
            lib.definition,
            {p(n("dep")): package.Specification({p(n("m")): annotated_spec()})},
        )
        result = drop_input_attributes(lib)
        assert len(result.warnings) == 6
        assert all(
            w.location[:3] == ("distribution", "dependencies", "dep")
            for w in result.warnings
        )
        codec.encode_versioned_distribution(result.value)

    def test_application_dependency_definitions(self) -> None:
        from morphir.ir.migrate import drop_input_attributes
        from morphir.ir.v4.distribution import ApplicationDistribution

        dep = library(values={n("f"): v.Definition([], INT, attributed_let())})
        app = ApplicationDistribution(
            dep.package, package.Definition(), {p(n("dep")): dep.definition}
        )
        result = drop_input_attributes(app)
        assert [w.location[:3] for w in result.warnings] == [
            ("distribution", "dependencies", "dep")
        ]
        codec.encode_versioned_distribution(result.value)
