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
