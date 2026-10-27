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
from morphir.ir.v4 import codec, module, package
from morphir.ir.v4 import incompleteness as inc
from morphir.ir.v4 import type as t
from morphir.ir.v4 import type_def as td
from morphir.ir.v4 import value as v
from morphir.ir.v4.access_controlled import Public
from morphir.ir.v4.distribution import LibraryDistribution, PackageInfo
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
