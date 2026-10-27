"""Tests for the compact v4 spellings that the draft v4 reader accepts.

The finos/morphir v4 JSON profile at the pinned commit says that readers MUST
accept every spelling the v4 JSON Schema marks as valid. Each case gives a
compact (or legacy) spelling and the expanded spelling that the writer emits.
The reader must give the same model for both, and the writer must give the
expanded spelling back. Kit case ids name the finos/morphir case a test follows.
"""

from __future__ import annotations

import json
import math
from decimal import Decimal
from pathlib import Path as FilePath
from typing import Any

import pytest

from morphir.ir import diagnostics as d
from morphir.ir import v3
from morphir.ir.diagnostics import DiagnosticError
from morphir.ir.format_version import parse_json
from morphir.ir.v3 import codec as v3_codec
from morphir.ir.v4 import codec, module
from morphir.ir.v4 import document as doc
from morphir.ir.v4 import literal as lit
from morphir.ir.v4 import type as t
from morphir.ir.v4 import type_def as td
from morphir.ir.v4 import type_spec as ts
from morphir.ir.v4 import value as v
from morphir.ir.v4.access_controlled import Private, Public
from morphir.ir.v4.distribution import (
    ApplicationDistribution,
    EntryPointKind,
    LibraryDistribution,
)
from morphir.ir.v4.documented import Documented
from morphir.ir.v4.fqname import FQName
from morphir.ir.v4.name import Name
from morphir.ir.v4.path import Path

FIXTURES = FilePath(__file__).resolve().parents[2] / "fixtures" / "ir"
COMPILER = FIXTURES / "python-compiler"
UPSTREAM = FIXTURES / "v4"

Json = Any


def n(*words: str) -> Name:
    return Name(words)


def p(*names: Name) -> Path:
    return Path(names)


SDK = p(n("morphir"), n("s", "d", "k"))
TA = t.TypeAttributes()
VA = v.ValueAttributes()


def sdk(mod: str, local: str) -> FQName:
    return FQName(SDK, p(n(mod)), n(*local.split("-")))


INT = t.Reference(TA, sdk("basics", "int"))
FLOAT = t.Reference(TA, sdk("basics", "float"))
BOOL = t.Reference(TA, sdk("basics", "bool"))
STRING = t.Reference(TA, sdk("string", "string"))


def fail_codes(fn: Any, *args: Any) -> tuple[str, ...]:
    with pytest.raises(DiagnosticError) as info:
        fn(*args)
    return info.value.codes


def fail_location(fn: Any, *args: Any) -> tuple[str | int, ...]:
    with pytest.raises(DiagnosticError) as info:
        fn(*args)
    return info.value.diagnostics[0].location


# --- Expanded spellings, as the writer emits them ---


def x_ref(fqname: str, *args: Json) -> Json:
    body: dict[str, Json] = {"fqname": fqname}
    if args:
        body["args"] = list(args)
    return {"Reference": body}


def x_var(name: str) -> Json:
    return {"Variable": {"name": name}}


def x_lit(kind: str, value: Json) -> Json:
    return {"Literal": {"literal": {kind: value}}}


X_INT = x_ref("morphir/SDK:basics#int")
X_STRING = x_ref("morphir/SDK:string#string")
X_WILD: Json = {"WildcardPattern": {}}
X_AS_X = {"AsPattern": {"pattern": X_WILD, "name": "x"}}
SDK_ARRAY = [["morphir"], ["s", "d", "k"]]


class TestNames:
    """Kit names-0001 to names-0008: legacy word arrays are valid input."""

    @pytest.mark.parametrize(
        ("legacy", "words"),
        [
            (["value", "in", "u", "s", "d"], ("value", "in", "u", "s", "d")),
            (["a"], ("a",)),
            (["item", "2"], ("item", "2")),
            (["f", "r", "2052", "a"], ("f", "r", "2052", "a")),
        ],
    )
    def test_legacy_name_array(self, legacy: list[str], words: tuple[str, ...]) -> None:
        name = codec.decode_name(legacy)
        assert name == n(*words)
        assert codec.decode_name(codec.encode_name(name)) == name

    @pytest.mark.parametrize(
        "bad", [[], ["Value"], ["value-in"], [1], ["a", None], [["a"]]]
    )
    def test_invalid_legacy_name_array(self, bad: list[object]) -> None:
        assert fail_codes(codec.decode_name, bad) == (d.INVALID_NAME,)

    def test_name_must_be_a_string_or_array(self) -> None:
        assert fail_codes(codec.decode_name, 7) == (d.INVALID_JSON,)

    def test_legacy_path_arrays(self) -> None:
        assert codec.decode_path(SDK_ARRAY) == SDK
        assert codec.decode_path(["morphir", "SDK"]) == SDK
        assert fail_codes(codec.decode_path, []) == (d.INVALID_NAME,)

    def test_legacy_fqname_arrays(self) -> None:
        expected = sdk("list", "map")
        assert codec.decode_fqname([SDK_ARRAY, [["list"]], ["map"]]) == expected
        assert codec.decode_fqname(["morphir/SDK", "list", "map"]) == expected
        assert fail_codes(codec.decode_fqname, ["morphir/SDK", "list"]) == (
            d.INVALID_JSON,
        )
        assert fail_codes(codec.decode_fqname, 3) == (d.INVALID_JSON,)


TYPE_CASES: list[tuple[str, Json, Json]] = [
    ("variable-bare", "a", x_var("a")),
    ("variable-wrapped-name", {"Variable": "a"}, x_var("a")),
    ("variable-wrapped-legacy", {"Variable": ["a"]}, x_var("a")),
    ("variable-expanded", {"Variable": {"attributes": {}, "name": "a"}}, x_var("a")),
    ("reference-bare", "morphir/SDK:basics#int", X_INT),
    ("reference-wrapped", {"Reference": "morphir/SDK:basics#int"}, X_INT),
    (
        "reference-empty-args",
        {"Reference": {"fqname": "morphir/SDK:basics#int", "args": []}},
        X_INT,
    ),
    (
        "reference-attributes",
        {"Reference": {"attributes": {}, "fqname": "morphir/SDK:basics#int"}},
        X_INT,
    ),
    (
        "reference-array",
        {"Reference": ["morphir/SDK:list#list", "a"]},
        x_ref("morphir/SDK:list#list", x_var("a")),
    ),
    (
        "reference-array-two-args",
        {
            "Reference": [
                "morphir/SDK:dict#dict",
                "morphir/SDK:string#string",
                "morphir/SDK:basics#int",
            ]
        },
        x_ref("morphir/SDK:dict#dict", X_STRING, X_INT),
    ),
    (
        "reference-array-legacy-fqname",
        {"Reference": [[SDK_ARRAY, [["list"]], ["list"]], "a"]},
        x_ref("morphir/SDK:list#list", x_var("a")),
    ),
    (
        "reference-expanded-object-args",
        {"Reference": {"fqname": "morphir/SDK:list#list", "args": ["a"]}},
        x_ref("morphir/SDK:list#list", x_var("a")),
    ),
    (
        "tuple-bare",
        ["morphir/SDK:basics#int", "morphir/SDK:string#string"],
        {"Tuple": {"elements": [X_INT, X_STRING]}},
    ),
    ("tuple-bare-empty", [], {"Tuple": {"elements": []}}),
    (
        "tuple-wrapped",
        {"Tuple": ["morphir/SDK:basics#int", "a"]},
        {"Tuple": {"elements": [X_INT, x_var("a")]}},
    ),
    (
        "tuple-expanded",
        {"Tuple": {"attributes": {}, "elements": ["a"]}},
        {"Tuple": {"elements": [x_var("a")]}},
    ),
    (
        "record",
        {
            "Record": {
                "fields": {
                    "name": "morphir/SDK:string#string",
                    "age": "morphir/SDK:basics#int",
                }
            }
        },
        {"Record": {"fields": {"name": X_STRING, "age": X_INT}}},
    ),
    (
        "extensible-record",
        {
            "ExtensibleRecord": {
                "attributes": {},
                "variable": "r",
                "fields": {"email": "morphir/SDK:string#string"},
            }
        },
        {"ExtensibleRecord": {"variable": "r", "fields": {"email": X_STRING}}},
    ),
    (
        "function",
        {
            "Function": {
                "parameterType": "morphir/SDK:basics#int",
                "returnType": "morphir/SDK:string#string",
            }
        },
        {"Function": {"parameterType": X_INT, "returnType": X_STRING}},
    ),
    ("unit-expanded", {"Unit": {"attributes": {}}}, {"Unit": {}}),
    (
        "empty-constraints",
        {"Variable": {"attributes": {"constraints": {}}, "name": "a"}},
        x_var("a"),
    ),
]


class TestTypeSpellings:
    @pytest.mark.parametrize(
        ("compact", "expanded"),
        [(c, e) for _, c, e in TYPE_CASES],
        ids=[i for i, _, _ in TYPE_CASES],
    )
    def test_compact_reads_as_expanded(self, compact: Json, expanded: Json) -> None:
        decoded = codec.decode_type(compact)
        assert decoded == codec.decode_type(expanded)
        assert codec.encode_type(decoded) == expanded

    def test_compact_model(self) -> None:
        assert codec.decode_type("morphir/SDK:basics#int") == INT
        assert codec.decode_type("comparable") == t.Variable(TA, n("comparable"))
        assert codec.decode_type(["a", "morphir/SDK:basics#float"]) == t.Tuple(
            TA, [t.Variable(TA, n("a")), FLOAT]
        )

    @pytest.mark.parametrize(
        ("bad", "code"),
        [
            # A bare string at type position is an FQName or a lowercase variable.
            ("Int", d.INVALID_NAME),
            ("value-in-USD", d.INVALID_NAME),
            ("1a", d.INVALID_NAME),
            ("morphir/SDK:basics", d.INVALID_NAME),
            (42, d.INVALID_JSON),
            (True, d.INVALID_JSON),
            (None, d.INVALID_JSON),
            # A Reference array is an FQName and at least one argument.
            ({"Reference": ["morphir/SDK:list#list"]}, d.INVALID_JSON),
            ({"Reference": ["morphir/SDK", "list", "list"]}, d.INVALID_NAME),
            ({"Reference": 4}, d.INVALID_JSON),
            ({"Variable": 4}, d.INVALID_JSON),
            ({"Tuple": "a"}, d.INVALID_JSON),
            # v3 tagged arrays and type-level holes are not v4 type expressions.
            (["Reference", {}, "morphir/SDK:basics#int"], d.UNKNOWN_NODE),
            ({"Draft": {}}, d.UNKNOWN_NODE),
            # Legacy-window spellings are not valid in the pinned schema.
            ({"Record": {"name": "morphir/SDK:string#string"}}, d.UNKNOWN_MEMBER),
            ({"Function": {"arg": "a", "result": "a"}}, d.UNKNOWN_MEMBER),
            ({"Variable": {"attrs": {}, "name": "a"}}, d.UNKNOWN_MEMBER),
            # Kit types-0012.
            (
                {"Variable": {"attributes": {"constraints": 5}, "name": "a"}},
                d.INVALID_JSON,
            ),
            (
                {"Variable": {"attributes": {"colour": "red"}, "name": "a"}},
                d.UNKNOWN_MEMBER,
            ),
            (
                {"Variable": {"attributes": {"constraints": {"x": 1}}, "name": "a"}},
                d.UNKNOWN_MEMBER,
            ),
        ],
    )
    def test_invalid_spellings(self, bad: Json, code: str) -> None:
        assert fail_codes(codec.decode_type, bad) == (code,)

    def test_failure_is_located(self) -> None:
        bad = {"Record": {"fields": {"street": "Street"}}}
        assert fail_location(codec.decode_type, bad) == ("Record", "fields", "street")


LITERAL_CASES: list[tuple[str, Json, lit.Literal]] = [
    ("integer-expanded", {"IntegerLiteral": {"value": 42}}, lit.IntegerLiteral(42)),
    ("whole-number", {"WholeNumberLiteral": {"value": 42}}, lit.IntegerLiteral(42)),
    ("bool-expanded", {"BoolLiteral": {"value": True}}, lit.BoolLiteral(True)),
    ("char-expanded", {"CharLiteral": {"value": "a"}}, lit.CharLiteral("a")),
    ("astral-char", {"CharLiteral": "\U0001f600"}, lit.CharLiteral("\U0001f600")),
    ("string-expanded", {"StringLiteral": {"value": "x"}}, lit.StringLiteral("x")),
    ("float-expanded", {"FloatLiteral": {"value": 4.0}}, lit.FloatLiteral(4.0)),
    # Kit values-0046 and values-0047: unknown members beside value are ignored.
    (
        "float-unknown-member",
        {"FloatLiteral": {"future": True, "value": 4.0}},
        lit.FloatLiteral(4.0),
    ),
    (
        "integer-unknown-member",
        {"IntegerLiteral": {"future": True, "value": 42}},
        lit.IntegerLiteral(42),
    ),
    (
        "decimal-expanded",
        {"DecimalLiteral": {"value": "10.50"}},
        lit.DecimalLiteral(Decimal("10.50")),
    ),
    # Kit patterns-and-literals-0005: a document has no {"value": ..} spelling.
    (
        "document-value-member",
        {"DocumentLiteral": {"value": 1}},
        lit.DocumentLiteral(doc.DocObject({"value": doc.DocInt(1)})),
    ),
    # Kit patterns-and-literals-0019 and 0020: arbitrary precision.
    (
        "big-integer",
        {"IntegerLiteral": 18446744073709551616},
        lit.IntegerLiteral(18446744073709551616),
    ),
    (
        "big-negative-integer",
        {"IntegerLiteral": -9223372036854775809},
        lit.IntegerLiteral(-9223372036854775809),
    ),
]


class TestLiteralSpellings:
    @pytest.mark.parametrize(
        ("spelling", "expected"),
        [(s, e) for _, s, e in LITERAL_CASES],
        ids=[i for i, _, _ in LITERAL_CASES],
    )
    def test_literal_spelling(self, spelling: Json, expected: lit.Literal) -> None:
        assert codec.decode_literal(spelling) == expected

    @pytest.mark.parametrize("lexeme", ["-0.00", "1e-7", ".5", "12.", "+3", "10.50"])
    def test_decimal_lexemes(self, lexeme: str) -> None:
        decoded = codec.decode_literal({"DecimalLiteral": lexeme})
        assert decoded == lit.DecimalLiteral(Decimal(lexeme))

    @pytest.mark.parametrize(
        "bad",
        [
            # Kit patterns-and-literals-0016.
            {"DecimalLiteral": "ten"},
            {"DecimalLiteral": ""},
            {"DecimalLiteral": "1_000"},
            {"DecimalLiteral": "NaN"},
            {"DecimalLiteral": " 1"},
            {"DecimalLiteral": "1\n"},
            {"DecimalLiteral": 10.5},
            {"IntegerLiteral": {}},
            {"IntegerLiteral": {"value": 1.5}},
            {"FloatLiteral": math.inf},
            {"FloatLiteral": {"value": math.nan}},
            {"FloatLiteral": 10**400},
            {"CharLiteral": {"value": "ab"}},
        ],
    )
    def test_invalid_literals(self, bad: Json) -> None:
        assert fail_codes(codec.decode_literal, bad) == (d.INVALID_LITERAL,)


VALUE_CASES: list[tuple[str, Json, Json]] = [
    # Decision 0009: bare scalars and arrays at value position.
    ("bare-integer", 42, x_lit("IntegerLiteral", 42)),
    ("bare-negative-integer", -7, x_lit("IntegerLiteral", -7)),
    ("bare-bool", True, x_lit("BoolLiteral", True)),
    ("bare-float", 4.0, x_lit("FloatLiteral", 4.0)),
    ("bare-variable", "x", x_var("x")),
    ("bare-legacy-free-name", "value-in-USD", x_var("value-in-USD")),
    (
        "bare-reference",
        "morphir/SDK:basics#add",
        {"Reference": {"fqname": "morphir/SDK:basics#add"}},
    ),
    (
        "bare-list",
        [1, 2, 3],
        {"List": {"items": [x_lit("IntegerLiteral", i) for i in (1, 2, 3)]}},
    ),
    ("bare-empty-list", [], {"List": {"items": []}}),
    (
        "bare-list-of-names",
        ["x", "y"],
        {"List": {"items": [x_var("x"), x_var("y")]}},
    ),
    # Literal wrapper forms (kit values-0025).
    ("literal-integer", {"Literal": 42}, x_lit("IntegerLiteral", 42)),
    ("literal-float", {"Literal": 4.5}, x_lit("FloatLiteral", 4.5)),
    ("literal-bool", {"Literal": False}, x_lit("BoolLiteral", False)),
    ("literal-string", {"Literal": "a"}, x_lit("StringLiteral", "a")),
    ("literal-typed", {"Literal": {"IntegerLiteral": 42}}, x_lit("IntegerLiteral", 42)),
    (
        "literal-typed-value",
        {"Literal": {"IntegerLiteral": {"value": 42}}},
        x_lit("IntegerLiteral", 42),
    ),
    (
        "literal-whole-number",
        {"Literal": {"WholeNumberLiteral": 42}},
        x_lit("IntegerLiteral", 42),
    ),
    (
        "literal-expanded-direct",
        {"Literal": {"attributes": {}, "literal": 42}},
        x_lit("IntegerLiteral", 42),
    ),
    (
        "literal-expanded-string",
        {"Literal": {"literal": "a"}},
        x_lit("StringLiteral", "a"),
    ),
    (
        "literal-expanded-typed",
        {"Literal": {"attributes": {}, "literal": {"IntegerLiteral": 42}}},
        x_lit("IntegerLiteral", 42),
    ),
    (
        "literal-document",
        {"Literal": {"DocumentLiteral": {"a": [1, None]}}},
        x_lit("DocumentLiteral", {"a": [1, None]}),
    ),
    # Constructor, Variable, Reference and FieldFunction compact payloads.
    (
        "constructor",
        {"Constructor": "morphir/SDK:maybe#just"},
        {"Constructor": {"fqname": "morphir/SDK:maybe#just"}},
    ),
    (
        "constructor-legacy-fqname",
        {"Constructor": [SDK_ARRAY, [["maybe"]], ["just"]]},
        {"Constructor": {"fqname": "morphir/SDK:maybe#just"}},
    ),
    (
        "constructor-expanded",
        {"Constructor": {"attributes": {}, "fqname": "morphir/SDK:maybe#just"}},
        {"Constructor": {"fqname": "morphir/SDK:maybe#just"}},
    ),
    ("variable", {"Variable": "x"}, x_var("x")),
    ("variable-legacy", {"Variable": ["my", "x"]}, x_var("my-x")),
    ("variable-expanded", {"Variable": {"attributes": {}, "name": "x"}}, x_var("x")),
    (
        "reference",
        {"Reference": "morphir/SDK:basics#add"},
        {"Reference": {"fqname": "morphir/SDK:basics#add"}},
    ),
    (
        "reference-legacy",
        {"Reference": ["morphir/SDK", "basics", "add"]},
        {"Reference": {"fqname": "morphir/SDK:basics#add"}},
    ),
    ("field-function", {"FieldFunction": "name"}, {"FieldFunction": {"name": "name"}}),
    (
        "field-function-expanded",
        {"FieldFunction": {"attributes": {}, "name": "name"}},
        {"FieldFunction": {"name": "name"}},
    ),
    # Tuple and List wrappers (kit values-0029, values-0031).
    (
        "tuple",
        {"Tuple": [{"Variable": "x"}, 1]},
        {"Tuple": {"elements": [x_var("x"), x_lit("IntegerLiteral", 1)]}},
    ),
    (
        "tuple-object",
        {"Tuple": {"elements": ["x", 1]}},
        {"Tuple": {"elements": [x_var("x"), x_lit("IntegerLiteral", 1)]}},
    ),
    (
        "list",
        {"List": [1, 2]},
        {"List": {"items": [x_lit("IntegerLiteral", 1), x_lit("IntegerLiteral", 2)]}},
    ),
    (
        "list-object",
        {"List": {"attributes": {}, "items": [1]}},
        {"List": {"items": [x_lit("IntegerLiteral", 1)]}},
    ),
    # Expanded nodes whose children are compact.
    (
        "if-then-else",
        {"IfThenElse": {"condition": True, "then": 1, "else": 2}},
        {
            "IfThenElse": {
                "condition": x_lit("BoolLiteral", True),
                "then": x_lit("IntegerLiteral", 1),
                "else": x_lit("IntegerLiteral", 2),
            }
        },
    ),
    (
        "apply",
        {"Apply": {"function": "morphir/SDK:basics#negate", "argument": 1}},
        {
            "Apply": {
                "function": {"Reference": {"fqname": "morphir/SDK:basics#negate"}},
                "argument": x_lit("IntegerLiteral", 1),
            }
        },
    ),
    (
        "field",
        {"Field": {"target": "record", "name": "field-name"}},
        {"Field": {"target": x_var("record"), "name": "field-name"}},
    ),
    (
        "record",
        {"Record": {"fields": {"name": "x", "age": 25}}},
        {
            "Record": {
                "fields": {"name": x_var("x"), "age": x_lit("IntegerLiteral", 25)}
            }
        },
    ),
    (
        "update-record",
        {"UpdateRecord": {"target": "record", "fields": {"name": {"Literal": "new"}}}},
        {
            "UpdateRecord": {
                "target": x_var("record"),
                "fields": {"name": x_lit("StringLiteral", "new")},
            }
        },
    ),
    (
        "lambda",
        {"Lambda": {"pattern": X_AS_X, "body": "x"}},
        {"Lambda": {"pattern": X_AS_X, "body": x_var("x")}},
    ),
    (
        "let-definition",
        {
            "LetDefinition": {
                "name": "x",
                "definition": {
                    "ExpressionBody": {
                        "inputTypes": {},
                        "outputType": "morphir/SDK:basics#int",
                        "body": 1,
                    }
                },
                "in": "x",
            }
        },
        {
            "LetDefinition": {
                "name": "x",
                "definition": {
                    "ExpressionBody": {
                        "inputTypes": {},
                        "outputType": X_INT,
                        "body": x_lit("IntegerLiteral", 1),
                    }
                },
                "in": x_var("x"),
            }
        },
    ),
    (
        "let-recursion",
        {
            "LetRecursion": {
                "definitions": {
                    "f": {
                        "ExpressionBody": {
                            "inputTypes": {"a": "a"},
                            "outputType": "a",
                            "body": "f",
                        }
                    }
                },
                "in": "f",
            }
        },
        {
            "LetRecursion": {
                "definitions": {
                    "f": {
                        "ExpressionBody": {
                            "inputTypes": {"a": x_var("a")},
                            "outputType": x_var("a"),
                            "body": x_var("f"),
                        }
                    }
                },
                "in": x_var("f"),
            }
        },
    ),
    (
        "destructure",
        {"Destructure": {"pattern": [X_AS_X, X_WILD], "value": "pair", "in": "x"}},
        {
            "Destructure": {
                "pattern": {"TuplePattern": {"patterns": [X_AS_X, X_WILD]}},
                "value": x_var("pair"),
                "in": x_var("x"),
            }
        },
    ),
    (
        "pattern-match",
        {
            "PatternMatch": {
                "value": "x",
                "cases": [
                    {"pattern": {"LiteralPattern": 0}, "body": True},
                    {"pattern": X_WILD, "body": False},
                ],
            }
        },
        {
            "PatternMatch": {
                "value": x_var("x"),
                "cases": [
                    {
                        "pattern": {
                            "LiteralPattern": {"literal": {"IntegerLiteral": 0}}
                        },
                        "body": x_lit("BoolLiteral", True),
                    },
                    {"pattern": X_WILD, "body": x_lit("BoolLiteral", False)},
                ],
            }
        },
    ),
    (
        "hole",
        {
            "Hole": {
                "reason": {"UnresolvedReference": {"target": "my-org/project:m#gone"}},
                "expectedType": "morphir/SDK:string#string",
            }
        },
        {
            "Hole": {
                "reason": {"UnresolvedReference": {"target": "my-org/project:m#gone"}},
                "expectedType": X_STRING,
            }
        },
    ),
    ("unit-expanded", {"Unit": {"attributes": {}}}, {"Unit": {}}),
]


class TestValueSpellings:
    @pytest.mark.parametrize(
        ("compact", "expanded"),
        [(c, e) for _, c, e in VALUE_CASES],
        ids=[i for i, _, _ in VALUE_CASES],
    )
    def test_compact_reads_as_expanded(self, compact: Json, expanded: Json) -> None:
        decoded = codec.decode_value(compact)
        assert decoded == codec.decode_value(expanded)
        assert codec.encode_value(decoded) == expanded

    def test_compact_model(self) -> None:
        assert codec.decode_value(42) == v.LiteralValue(VA, lit.IntegerLiteral(42))
        assert codec.decode_value("x") == v.Variable(VA, n("x"))
        assert codec.decode_value({"Literal": "a"}) == v.LiteralValue(
            VA, lit.StringLiteral("a")
        )

    @pytest.mark.parametrize(
        ("bad", "code"),
        [
            # Decision 0009, rule 3: a bare string is a name, never a string literal.
            ("hello world", d.INVALID_NAME),
            ("value-in-Usd", d.INVALID_NAME),
            ("a:b", d.INVALID_NAME),
            (None, d.INVALID_JSON),
            ({"Literal": None}, d.INVALID_LITERAL),
            ({"Literal": [1]}, d.INVALID_LITERAL),
            ({"Literal": {"attributes": {}}}, d.MISSING_MEMBER),
            ({"Literal": {"literal": 1, "extra": 2}}, d.UNKNOWN_MEMBER),
            ({"Literal": {"literal": None}}, d.INVALID_LITERAL),
            ({"Tuple": "x"}, d.INVALID_JSON),
            ({"List": 1}, d.INVALID_JSON),
            ({"Constructor": 1}, d.INVALID_JSON),
            ({"Constructor": ["morphir/SDK", "maybe"]}, d.INVALID_JSON),
            ({"FieldFunction": 1}, d.INVALID_JSON),
            ({"Record": {"name": "x"}}, d.UNKNOWN_MEMBER),
            (
                {"IfThenElse": {"condition": True, "thenBranch": 1, "elseBranch": 2}},
                d.UNKNOWN_MEMBER,
            ),
            # Kit values-0042 and a v3 tagged array.
            ({"Native": {"fqname": "morphir/SDK:basics#add"}}, d.UNKNOWN_NODE),
            (["Variable", {}, ["x"]], d.UNKNOWN_NODE),
            ({"IntegerLiteral": 42}, d.UNKNOWN_NODE),
        ],
    )
    def test_invalid_spellings(self, bad: Json, code: str) -> None:
        assert fail_codes(codec.decode_value, bad) == (code,)

    def test_documented_let_definition_has_no_slot(self) -> None:
        bad = {
            "LetDefinition": {
                "name": "x",
                "definition": {
                    "doc": "one",
                    "ExpressionBody": {
                        "inputTypes": {},
                        "outputType": "a",
                        "body": 1,
                    },
                },
                "in": "x",
            }
        }
        assert fail_codes(codec.decode_value, bad) == (d.UNKNOWN_MEMBER,)
        assert fail_location(codec.decode_value, bad) == (
            "LetDefinition",
            "definition",
            "doc",
        )


class TestNumbersByLexeme:
    """Decision 0009, rule 2: a bare number's kind follows its lexeme."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("0", lit.IntegerLiteral(0)),
            ("-7", lit.IntegerLiteral(-7)),
            ("0.0", lit.FloatLiteral(0.0)),
            ("4.0", lit.FloatLiteral(4.0)),
            ("1e3", lit.FloatLiteral(1000.0)),
            ("4E0", lit.FloatLiteral(4.0)),
            ("-0.5", lit.FloatLiteral(-0.5)),
            (
                "123456789012345678901234567890",
                lit.IntegerLiteral(int("123456789012345678901234567890")),
            ),
        ],
    )
    def test_bare_number_in_a_document(self, text: str, expected: lit.Literal) -> None:
        body = {"ExpressionBody": {"inputTypes": {}, "outputType": "a", "body": "@"}}
        root = {
            "formatVersion": 4,
            "distribution": {
                "Library": {
                    "packageName": "a",
                    "def": {
                        "modules": {
                            "m": {"Public": {"values": {"v": {"Public": body}}}}
                        }
                    },
                }
            },
        }
        document = json.dumps(root).replace('"@"', text)
        dist = codec.decode_versioned_distribution(document)
        assert isinstance(dist, LibraryDistribution)
        mod = dist.definition.modules[p(n("m"))].value
        defn = mod.values[n("v")].value.value
        assert isinstance(defn, v.Definition)
        assert defn.body == v.LiteralValue(VA, expected)

    def test_json_parser_keeps_the_lexeme_kind(self) -> None:
        parsed = parse_json("[0, 0.0, 1e3, 18446744073709551616]")
        assert isinstance(parsed, list)
        assert [type(x) for x in parsed] == [int, float, float, int]
        assert parsed[3] == 18446744073709551616

    def test_out_of_range_float_is_refused(self) -> None:
        assert fail_codes(codec.decode_value, json.loads("1e400")) == (
            d.INVALID_LITERAL,
        )
        assert fail_codes(codec.decode_value, {"Literal": math.nan}) == (
            d.INVALID_LITERAL,
        )


PATTERN_CASES: list[tuple[str, Json, Json]] = [
    (
        "tuple-bare",
        [X_WILD, X_AS_X],
        {"TuplePattern": {"patterns": [X_WILD, X_AS_X]}},
    ),
    (
        "tuple-wrapped",
        {"TuplePattern": [X_WILD]},
        {"TuplePattern": {"patterns": [X_WILD]}},
    ),
    (
        "tuple-expanded",
        {
            "TuplePattern": {
                "attributes": {},
                "patterns": [
                    {
                        "AsPattern": {
                            "attributes": {},
                            "pattern": {"WildcardPattern": {"attributes": {}}},
                            "name": "x",
                        }
                    }
                ],
            }
        },
        {"TuplePattern": {"patterns": [X_AS_X]}},
    ),
    (
        "literal-bare-integer",
        {"LiteralPattern": 42},
        {"LiteralPattern": {"literal": {"IntegerLiteral": 42}}},
    ),
    (
        "literal-bare-string",
        {"LiteralPattern": "a"},
        {"LiteralPattern": {"literal": {"StringLiteral": "a"}}},
    ),
    (
        "literal-bare-float",
        {"LiteralPattern": 0.5},
        {"LiteralPattern": {"literal": {"FloatLiteral": 0.5}}},
    ),
    (
        "literal-typed",
        {"LiteralPattern": {"CharLiteral": "c"}},
        {"LiteralPattern": {"literal": {"CharLiteral": "c"}}},
    ),
    (
        "literal-expanded-direct",
        {"LiteralPattern": {"attributes": {}, "literal": True}},
        {"LiteralPattern": {"literal": {"BoolLiteral": True}}},
    ),
    (
        "nullary-expanded",
        {"EmptyListPattern": {"attributes": {}}},
        {"EmptyListPattern": {}},
    ),
    (
        "as-legacy-name",
        {"AsPattern": {"pattern": X_WILD, "name": ["x"]}},
        X_AS_X,
    ),
    (
        "constructor-legacy-fqname",
        {
            "ConstructorPattern": {
                "fqname": ["morphir/SDK", "maybe", "just"],
                "patterns": [[X_WILD, X_WILD]],
            }
        },
        {
            "ConstructorPattern": {
                "fqname": "morphir/SDK:maybe#just",
                "patterns": [{"TuplePattern": {"patterns": [X_WILD, X_WILD]}}],
            }
        },
    ),
]


class TestPatternSpellings:
    @pytest.mark.parametrize(
        ("compact", "expanded"),
        [(c, e) for _, c, e in PATTERN_CASES],
        ids=[i for i, _, _ in PATTERN_CASES],
    )
    def test_compact_reads_as_expanded(self, compact: Json, expanded: Json) -> None:
        decoded = codec.decode_pattern(compact)
        assert decoded == codec.decode_pattern(expanded)
        assert codec.encode_pattern(decoded) == expanded

    @pytest.mark.parametrize(
        ("bad", "code"),
        [
            # Kit patterns-and-literals-0007.
            ({"LiteralPattern": {"DocumentLiteral": {"name": "A"}}}, d.INVALID_LITERAL),
            (
                {"LiteralPattern": {"literal": {"DocumentLiteral": 1}}},
                d.INVALID_LITERAL,
            ),
            ({"LiteralPattern": None}, d.INVALID_LITERAL),
            # The schema has no bare scalar or bare literal at pattern position.
            ("x", d.INVALID_JSON),
            (42, d.INVALID_JSON),
            ({"IntegerLiteral": 42}, d.UNKNOWN_NODE),
            (["WildcardPattern", {}], d.UNKNOWN_NODE),
            ({"TuplePattern": "x"}, d.INVALID_JSON),
        ],
    )
    def test_invalid_spellings(self, bad: Json, code: str) -> None:
        assert fail_codes(codec.decode_pattern, bad) == (code,)


CTORS: ts.Constructors = {
    n("just"): [(n("value"), t.Variable(TA, n("a")))],
    n("nothing"): [],
}
ALIAS_DEF = td.TypeAliasDefinition([], STRING)
ALIAS_JSON = {"typeParams": [], "typeExp": "morphir/SDK:string#string"}
BODY = v.Definition([], INT, v.Variable(VA, n("x")))
BODY_JSON = {"inputTypes": {}, "outputType": "morphir/SDK:basics#int", "body": "x"}


class TestDefinitionSpellings:
    def test_constructor_spellings(self) -> None:
        # Kit definitions-0003 and the schema's legacy Constructors array.
        compact = {"just": [["value", "a"]], "nothing": []}
        legacy = [["just", [[["value"], "a"]]], ["nothing", []]]
        assert codec._decode_constructors(compact, ()) == CTORS
        assert codec._decode_constructors(legacy, ()) == CTORS
        assert list(codec._decode_constructors(legacy, ())) == [n("just"), n("nothing")]

    @pytest.mark.parametrize(
        ("bad", "code"),
        [
            ([["just", []], ["just", []]], d.DUPLICATE_MEMBER),
            ([["just"]], d.INVALID_JSON),
            ([["just", [["value"]]]], d.INVALID_JSON),
            (["just"], d.INVALID_JSON),
            (7, d.INVALID_JSON),
        ],
    )
    def test_invalid_constructors(self, bad: Json, code: str) -> None:
        assert fail_codes(codec._decode_constructors, bad, ()) == (code,)

    @pytest.mark.parametrize(
        ("spelling", "expected"),
        [
            (
                ["TypeAliasDefinition", ["a"], "a"],
                td.TypeAliasDefinition([n("a")], t.Variable(TA, n("a"))),
            ),
            (
                [
                    "CustomTypeDefinition",
                    ["a"],
                    {
                        "access": "Public",
                        "value": {"just": [["value", "a"]], "nothing": []},
                    },
                ],
                td.CustomTypeDefinition([n("a")], Public(CTORS)),
            ),
            (
                [
                    "CustomTypeDefinition",
                    ["a"],
                    {"private": {"just": [["value", "a"]], "nothing": []}},
                ],
                td.CustomTypeDefinition([n("a")], Private(CTORS)),
            ),
            (
                {
                    "CustomTypeDefinition": {
                        "typeParams": [["a"]],
                        "constructors": [["just", [["value", "a"]]], ["nothing", []]],
                    }
                },
                td.CustomTypeDefinition([n("a")], Public(CTORS)),
            ),
        ],
    )
    def test_type_definition_spellings(
        self, spelling: Json, expected: td.Definition
    ) -> None:
        assert codec.decode_type_definition(spelling) == expected

    @pytest.mark.parametrize(
        ("spelling", "expected"),
        [
            # Kit definitions-0002.
            (["OpaqueTypeSpecification", []], ts.OpaqueTypeSpecification([])),
            (
                [
                    "TypeAliasSpecification",
                    ["a"],
                    {"Reference": ["morphir/SDK:list#list", "a"]},
                ],
                ts.TypeAliasSpecification(
                    [n("a")],
                    t.Reference(TA, sdk("list", "list"), [t.Variable(TA, n("a"))]),
                ),
            ),
            (
                [
                    "CustomTypeSpecification",
                    ["a"],
                    {"just": [["value", "a"]], "nothing": []},
                ],
                ts.CustomTypeSpecification([n("a")], CTORS),
            ),
            (
                [
                    "DerivedTypeSpecification",
                    [],
                    {
                        "baseType": "morphir/SDK:string#string",
                        "fromBaseType": "my/pkg:m#from-string",
                        "toBaseType": ["my/pkg", "m", "to-string"],
                    },
                ],
                ts.DerivedTypeSpecification(
                    [],
                    ts.DerivedTypeSpecificationDetails(
                        STRING,
                        FQName(p(n("my"), n("pkg")), p(n("m")), n("from", "string")),
                        FQName(p(n("my"), n("pkg")), p(n("m")), n("to", "string")),
                    ),
                ),
            ),
        ],
    )
    def test_legacy_type_specification_arrays(
        self, spelling: Json, expected: ts.Specification
    ) -> None:
        assert codec.decode_type_specification(spelling) == expected

    @pytest.mark.parametrize(
        ("bad", "code"),
        [
            (["OpaqueTypeSpecification"], d.INVALID_JSON),
            (["TypeAliasSpecification", [], "a", "extra"], d.INVALID_JSON),
            (["Nope", []], d.UNKNOWN_NODE),
            ([], d.UNKNOWN_NODE),
            (["DerivedTypeSpecification", [], {"baseType": "a"}], d.MISSING_MEMBER),
        ],
    )
    def test_invalid_legacy_specification_arrays(self, bad: Json, code: str) -> None:
        assert fail_codes(codec.decode_type_specification, bad) == (code,)

    @pytest.mark.parametrize(
        "bad",
        [
            ["TypeAliasDefinition", []],
            ["IncompleteTypeDefinition", [], {"Draft": {}}],
            ["CustomTypeDefinition", [], {"access": "Public", "value": {}, "x": 1}],
        ],
    )
    def test_invalid_legacy_definition_arrays(self, bad: Json) -> None:
        with pytest.raises(DiagnosticError):
            codec.decode_type_definition(bad)

    def test_value_specification_spellings(self) -> None:
        expected = v.Specification([(n("a"), INT), (n("b"), INT)], INT)
        canonical = {
            "inputs": {"a": "morphir/SDK:basics#int", "b": "morphir/SDK:basics#int"},
            "output": "morphir/SDK:basics#int",
        }
        # Kit definitions-0004: the legacy inputs array.
        legacy = {
            "inputs": [
                ["a", "morphir/SDK:basics#int"],
                [["b"], "morphir/SDK:basics#int"],
            ],
            "output": "morphir/SDK:basics#int",
        }
        assert codec.decode_value_specification(canonical) == expected
        assert codec.decode_value_specification(legacy) == expected
        # Kit definitions-0029: inputs may be omitted.
        no_inputs = v.Specification([], INT)
        assert (
            codec.decode_value_specification({"output": "morphir/SDK:basics#int"})
            == no_inputs
        )
        assert fail_codes(
            codec.decode_value_specification, {"inputs": [["a"]], "output": "a"}
        ) == (d.INVALID_JSON,)
        repeated = {"inputs": [["a", "a"], ["a", "a"]], "output": "a"}
        assert fail_codes(codec.decode_value_specification, repeated) == (
            d.DUPLICATE_MEMBER,
        )
        assert fail_location(codec.decode_value_specification, repeated) == (
            "inputs",
            1,
        )

    def test_module_specification_doc_spellings(self) -> None:
        # Kit definitions-0010: doc flattened beside the members, or nested.
        spec = v.Specification([(n("a"), INT)], INT)
        members = {
            "inputs": {"a": "morphir/SDK:basics#int"},
            "output": "morphir/SDK:basics#int",
        }
        flat = {"types": {}, "values": {"add": {"doc": "Adds", **members}}}
        nested = {"types": {}, "values": {"add": {"doc": "Adds", "value": members}}}
        expected = module.Specification(values={n("add"): Documented("Adds", spec)})
        assert codec.decode_module_specification(flat) == expected
        assert codec.decode_module_specification(nested) == expected

    def test_type_specification_doc_is_flattened(self) -> None:
        flat = {"types": {"t": {"doc": "A type", "OpaqueTypeSpecification": {}}}}
        expected = module.Specification(
            types={n("t"): Documented("A type", ts.OpaqueTypeSpecification([]))}
        )
        assert codec.decode_module_specification(flat) == expected

    @pytest.mark.parametrize(
        "entry",
        [
            # Kit definitions-0006 (canonical) and definitions-0001.
            {"Public": {"doc": "D", "TypeAliasDefinition": ALIAS_JSON}},
            {"access": "Public", "doc": "D", "TypeAliasDefinition": ALIAS_JSON},
            {
                "access": "Public",
                "doc": "D",
                "value": {"TypeAliasDefinition": ALIAS_JSON},
            },
            {
                "access": "Public",
                "value": {"doc": "D", "TypeAliasDefinition": ALIAS_JSON},
            },
            {"Public": {"doc": "D", "value": {"TypeAliasDefinition": ALIAS_JSON}}},
            {"pub": {"doc": "D", "TypeAliasDefinition": ALIAS_JSON}},
            {"public": {"doc": "D", "TypeAliasDefinition": ALIAS_JSON}},
            {"access": "pub", "doc": "D", "TypeAliasDefinition": ALIAS_JSON},
            {
                "access": "public",
                "doc": "D",
                "value": ["TypeAliasDefinition", [], "morphir/SDK:string#string"],
            },
        ],
    )
    def test_public_type_definition_entries(self, entry: Json) -> None:
        mod = codec.decode_module_definition({"types": {"t": entry}})
        assert mod.types == {n("t"): Public(Documented("D", ALIAS_DEF))}

    @pytest.mark.parametrize(
        "entry",
        [
            # Kit definitions-0017.
            {"Private": {"TypeAliasDefinition": ALIAS_JSON}},
            {"private": {"TypeAliasDefinition": ALIAS_JSON}},
            {"access": "Private", "TypeAliasDefinition": ALIAS_JSON},
            {"access": "private", "value": {"TypeAliasDefinition": ALIAS_JSON}},
        ],
    )
    def test_private_type_definition_entries(self, entry: Json) -> None:
        mod = codec.decode_module_definition({"types": {"t": entry}})
        assert mod.types == {n("t"): Private(Documented(None, ALIAS_DEF))}

    @pytest.mark.parametrize(
        ("entry", "expected"),
        [
            # Kit definitions-0018 and definitions-0019.
            (
                {"Public": {"doc": "Adds", "ExpressionBody": BODY_JSON}},
                Public(Documented("Adds", BODY)),
            ),
            (
                {"access": "Public", "doc": "Adds", "ExpressionBody": BODY_JSON},
                Public(Documented("Adds", BODY)),
            ),
            (
                {"access": "Private", "ExpressionBody": BODY_JSON},
                Private(Documented(None, BODY)),
            ),
            (
                {"private": {"ExpressionBody": BODY_JSON}},
                Private(Documented(None, BODY)),
            ),
        ],
    )
    def test_value_definition_entries(self, entry: Json, expected: object) -> None:
        mod = codec.decode_module_definition({"values": {"v": entry}})
        assert mod.values == {n("v"): expected}

    @pytest.mark.parametrize(
        ("entry", "code", "location"),
        [
            # Kit definitions-0031.
            (
                {"priv": {"TypeAliasDefinition": ALIAS_JSON}},
                d.UNKNOWN_NODE,
                ("types", "t"),
            ),
            (
                {"access": "priv", "TypeAliasDefinition": ALIAS_JSON},
                d.UNKNOWN_NODE,
                ("types", "t", "access"),
            ),
            (
                {"access": 1, "TypeAliasDefinition": ALIAS_JSON},
                d.UNKNOWN_NODE,
                ("types", "t", "access"),
            ),
            # Kit definitions-0028.
            (
                {"Public": {"doc": ["a", "b"], "TypeAliasDefinition": ALIAS_JSON}},
                d.INVALID_JSON,
                ("types", "t", "Public", "doc"),
            ),
            # The legacy-window wrapper without doc is not valid in the schema.
            (
                {"Public": {"value": {"TypeAliasDefinition": ALIAS_JSON}}},
                d.UNKNOWN_NODE,
                ("types", "t", "Public", "value"),
            ),
            # Documentation given twice.
            (
                {
                    "Public": {
                        "doc": "a",
                        "value": {"doc": "b", "TypeAliasDefinition": ALIAS_JSON},
                    }
                },
                d.DUPLICATE_MEMBER,
                ("types", "t", "Public", "value", "doc"),
            ),
            ({"access": "Public"}, d.MISSING_MEMBER, ("types", "t")),
            ({"Public": {"doc": "a"}}, d.UNKNOWN_NODE, ("types", "t", "Public")),
            # Kit definitions-0023.
            (
                {"Public": {"TypeAliasDefinition": {"annotations": [], **ALIAS_JSON}}},
                d.UNKNOWN_MEMBER,
                ("types", "t", "Public", "TypeAliasDefinition", "annotations"),
            ),
        ],
    )
    def test_invalid_definition_entries(
        self, entry: Json, code: str, location: tuple[str | int, ...]
    ) -> None:
        bad = {"types": {"t": entry}}
        assert fail_codes(codec.decode_module_definition, bad) == (code,)
        assert fail_location(codec.decode_module_definition, bad) == location

    @pytest.mark.parametrize(
        "entry",
        [
            {"Public": {"types": {}, "values": {}}},
            {"pub": {"types": {}, "values": {}}},
            {"access": "Public", "value": {"types": {}, "values": {}}},
            {"access": "Public", "types": {}, "values": {}},
            {"access": "public", "doc": "M", "types": {}},
        ],
    )
    def test_package_module_entries(self, entry: Json) -> None:
        decoded = codec.decode_package_definition({"modules": {"m": entry}})
        mod = decoded.modules[p(n("m"))]
        assert isinstance(mod, Public)
        assert mod.value.types == {}

    def test_flattened_module_keeps_doc(self) -> None:
        entry = {"access": "Private", "doc": "M", "values": {}}
        decoded = codec.decode_package_definition({"modules": {"m": entry}})
        assert decoded.modules[p(n("m"))] == Private(module.Definition(doc="M"))

    def test_flattened_module_rejects_unknown_members(self) -> None:
        entry = {"access": "Public", "value": {}, "types": {}}
        bad = {"modules": {"m": entry}}
        assert fail_codes(codec.decode_package_definition, bad) == (d.UNKNOWN_MEMBER,)

    def test_distribution_legacy_names(self) -> None:
        document = {
            "formatVersion": 4,
            "distribution": {
                "Application": {
                    "packageName": [["acme"], ["example"]],
                    "entryPoints": {
                        "start": {
                            "target": [["acme", "example"], "main", "run"],
                            "kind": "main",
                        }
                    },
                }
            },
        }
        dist = codec.decode_versioned_distribution(document)
        assert isinstance(dist, ApplicationDistribution)
        assert dist.package.name == p(n("acme"), n("example"))
        entry = dist.entry_points[n("start")]
        assert entry.target == FQName(
            p(n("acme"), n("example")), p(n("main")), n("run")
        )
        assert entry.kind is EntryPointKind.Main


def load(path: FilePath) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def library(path: FilePath) -> LibraryDistribution:
    dist = codec.decode_versioned_distribution(path.read_text(encoding="utf-8"))
    assert isinstance(dist, LibraryDistribution)
    return dist


def module_of(dist: LibraryDistribution, name: str) -> module.Definition:
    entry = dist.definition.modules[p(n(name))]
    assert isinstance(entry, Public)
    return entry.value


def body_of(mod: module.Definition, name: str) -> v.Value:
    entry = mod.values[n(*name.split("-"))]
    assert isinstance(entry, Public)
    defn = entry.value.value
    assert isinstance(defn, v.Definition)
    return defn.body


ACME = p(n("acme"), n("example"))


def acme(local: str) -> t.Type:
    return t.Reference(TA, FQName(ACME, p(n("models")), n(*local.split("-"))))


def float_lit(x: float) -> v.Value:
    return v.LiteralValue(VA, lit.FloatLiteral(x))


class TestCompilerOutput:
    """The compact output of morphir-python-binding 0.4.0 / morphir-core 0.2.0."""

    def test_modules_fixture(self) -> None:
        dist = library(COMPILER / "modules-v4.json")
        assert dist.package.name == ACME
        assert list(dist.definition.modules) == [p(n("models")), p(n("rules"))]

        models = module_of(dist, "models")
        assert list(models.types) == [
            n("address"),
            n("application"),
            n("decision"),
            n("labeled", "point"),
            n("point"),
        ]
        address = models.types[n("address")]
        assert address == Public(
            Documented(
                None,
                td.TypeAliasDefinition(
                    [],
                    t.Record(
                        TA,
                        [t.Field(n("street"), STRING), t.Field(n("zip", "code"), INT)],
                    ),
                ),
            )
        )
        decision = models.types[n("decision")].value.value
        assert isinstance(decision, td.CustomTypeDefinition)
        assert isinstance(decision.constructors, Public)
        ctors = decision.constructors.value
        assert list(ctors) == [n("pending"), n("approved")]
        assert ctors[n("pending")] == []
        assert ctors[n("approved")] == [
            (n("amount"), FLOAT),
            (n("address"), acme("address")),
        ]
        point = models.types[n("point")].value.value
        assert point == td.TypeAliasDefinition([], t.Tuple(TA, [FLOAT, FLOAT]))

        located = models.values[n("located")].value.value
        assert isinstance(located, v.Definition)
        assert [(name, tpe) for name, _, tpe in located.input_types] == [
            (n("flag"), BOOL),
            (n("location"), acme("point")),
        ]
        assert located.output_type == acme("labeled-point")
        assert located.body == v.IfThenElse(
            VA,
            v.Variable(VA, n("flag")),
            v.Tuple(
                VA,
                [
                    v.Variable(VA, n("location")),
                    v.LiteralValue(VA, lit.StringLiteral("known")),
                ],
            ),
            v.Tuple(
                VA,
                [
                    v.Tuple(VA, [float_lit(0.0), float_lit(0.0)]),
                    v.LiteralValue(VA, lit.StringLiteral("unknown")),
                ],
            ),
        )
        rules = module_of(dist, "rules")
        assert list(rules.values) == [n("origin"), n("select", "decision")]
        assert body_of(rules, "origin") == v.Tuple(VA, [float_lit(0.0), float_lit(0.0)])

    def test_adt_fixture(self) -> None:
        dist = library(COMPILER / "adt-v4.json")
        models = module_of(dist, "models")
        assert list(models.values) == [
            n("choose"),
            n("classify"),
            n("expression"),
            n("guarded"),
            n("located"),
            n("make", "point"),
            n("nested"),
        ]
        less_than = v.Reference(VA, sdk("basics", "less-than"))
        classify = body_of(models, "classify")
        assert isinstance(classify, v.IfThenElse)
        assert classify.condition == v.Apply(
            VA,
            v.Apply(VA, less_than, v.Variable(VA, n("value"))),
            v.LiteralValue(VA, lit.IntegerLiteral(0)),
        )
        assert classify.then_branch == v.LiteralValue(VA, lit.StringLiteral("negative"))
        assert isinstance(classify.else_branch, v.IfThenElse)
        expression = body_of(models, "expression")
        assert expression == v.IfThenElse(
            VA, v.Variable(VA, n("flag")), float_lit(-1.5), float_lit(2.5)
        )
        assert body_of(models, "make-point") == v.Tuple(
            VA, [v.Variable(VA, n("x")), v.Variable(VA, n("y"))]
        )

    @pytest.mark.parametrize("name", ["modules-v4.json", "adt-v4.json"])
    def test_fixture_round_trips_through_the_expanded_writer(self, name: str) -> None:
        dist = library(COMPILER / name)
        encoded = codec.encode_versioned_distribution(dist)
        assert codec.decode_versioned_distribution(json.dumps(encoded)) == dist
        assert encoded != load(COMPILER / name)

    def test_v3_twin_decodes(self) -> None:
        text = (COMPILER / "modules-v3.json").read_text(encoding="utf-8")
        dist = v3_codec.decode_versioned_distribution(text)
        assert isinstance(dist, v3.Library)
        assert [list(m) for m in dist.definition.modules] == [
            [("models",)],
            [("rules",)],
        ]


class TestUpstreamExamples:
    """The finos/morphir v4 examples at the pinned commit."""

    def test_books_and_records(self) -> None:
        dist = library(UPSTREAM / "finos-books-and-records-example.json")
        mod = module_of_path(dist, p(n("books", "and", "records")))
        assert mod.doc is not None and mod.doc.startswith("Books and Records")
        book = mod.types[n("book")].value.value
        model = p(n("morphir"), n("reference"), n("model"))
        records = p(n("books", "and", "records"))
        assert book == td.TypeAliasDefinition(
            [],
            t.Reference(
                TA,
                sdk("dict", "dict"),
                [
                    t.Reference(TA, FQName(model, records, n("product", "i", "d"))),
                    t.Reference(TA, FQName(model, records, n("deal"))),
                ],
            ),
        )
        deal_event = mod.types[n("deal", "event")].value.value
        assert isinstance(deal_event, td.CustomTypeDefinition)
        assert next(iter(deal_event.constructors.value)) == n("deal", "opened")
        basics = dist.dependencies[SDK].modules[p(n("basics"))]
        assert basics.types[n("int")] == Documented(
            None, ts.OpaqueTypeSpecification([])
        )

    def test_complete_example_hits_the_name_model_gap(self) -> None:
        text = (UPSTREAM / "finos-complete-example.json").read_text(encoding="utf-8")
        with pytest.raises(DiagnosticError) as info:
            codec.decode_versioned_distribution(text)
        assert info.value.codes == (d.INVALID_NAME,)
        assert info.value.diagnostics[0].location == (
            "distribution",
            "Library",
            "def",
            "modules",
            "u-s/f-r-2052-a/data-tables",
        )

    def test_complete_example_decodes_once_the_name_is_representable(self) -> None:
        text = (UPSTREAM / "finos-complete-example.json").read_text(encoding="utf-8")
        dist = library_from_text(text.replace("u-s/f-r-2052-a", "US/FR-2052-a"))
        mod = module_of_path(
            dist, p(n("u", "s"), n("f", "r", "2052", "a"), n("data", "tables"))
        )
        assert mod.doc == "Data tables module for regulatory reporting"
        total = mod.values[n("calculate", "total")]
        assert isinstance(total, Public)
        defn = total.value.value
        assert isinstance(defn, v.Definition)
        assert defn.body == float_lit(0.0)
        listing = dist.dependencies[SDK].modules[p(n("list"))]
        map_spec = listing.values[n("map")].value
        assert [name for name, _ in map_spec.inputs] == [n("f"), n("list")]


def library_from_text(text: str) -> LibraryDistribution:
    dist = codec.decode_versioned_distribution(text)
    assert isinstance(dist, LibraryDistribution)
    return dist


def module_of_path(dist: LibraryDistribution, path: Path) -> module.Definition:
    entry = dist.definition.modules[path]
    assert isinstance(entry, Public)
    return entry.value


@pytest.mark.parametrize("text", [":#int", "morphir/sdk:#int", ":basics#int"])
def test_fqname_strings_need_package_and_module_paths(text: str) -> None:
    # The schema's FQNameString pattern requires a segment in each path.
    with pytest.raises(DiagnosticError):
        codec.decode_fqname(text)
    with pytest.raises(DiagnosticError):
        codec.decode_type(text)


def test_a_decimal_beyond_the_decimal_range_is_a_diagnostic() -> None:
    # The lexeme is valid, but Python's Decimal cannot represent the exponent.
    with pytest.raises(DiagnosticError) as error:
        codec.decode_literal({"DecimalLiteral": "1e999999999999999999999999999"})
    assert error.value.codes == (d.INVALID_LITERAL,)
