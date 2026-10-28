"""The v4 writer: compact canonical spelling, flattened documentation, selection.

The compact forms follow morphir-core 0.2.0, the reference writer at the same
finos/morphir v4 JSON profile (``serde_v4.rs``): a node without attributes is
written in its shortest schema-valid form, a node with attributes keeps the
expanded spelling with ``attributes`` first, and ``doc`` is flattened first
beside the documented node (decision 0010).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from morphir.ir import diagnostics as d
from morphir.ir.diagnostics import DiagnosticError
from morphir.ir.v4 import codec
from morphir.ir.v4 import literal as lit
from morphir.ir.v4 import type as t
from morphir.ir.v4 import value as v
from morphir.ir.v4.codec import Spelling
from morphir.ir.v4.fqname import FQName
from morphir.ir.v4.name import Name
from morphir.ir.v4.path import Path as IrPath

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "ir"
COMPILER = FIXTURES / "python-compiler"
UPSTREAM = FIXTURES / "v4"

INT = FQName(
    IrPath((Name(("morphir",)), Name(("s", "d", "k")))),
    IrPath((Name(("basics",)),)),
    Name(("int",)),
)
LIST = FQName(INT.package_path, IrPath((Name(("list",)),)), Name(("list",)))
NO_TYPE = t.TypeAttributes()
NO_VALUE = v.ValueAttributes()
LOCATED = t.TypeAttributes(source=t.SourceLocation(1, 2, 3, 4))


def name(*words: str) -> Name:
    return Name(words)


@pytest.mark.parametrize("fixture", ["modules-v4.json", "adt-v4.json"])
def test_compiler_output_re_encodes_byte_for_byte(fixture: str) -> None:
    text = (COMPILER / fixture).read_text()
    original = json.loads(text)
    encoded = codec.encode_versioned_distribution(
        codec.decode_versioned_distribution(text)
    )
    assert json.dumps(encoded) == json.dumps(original)


@pytest.mark.parametrize("fixture", ["modules-v4", "adt-v4"])
def test_expanded_spelling_is_unchanged(fixture: str) -> None:
    # The golden files hold the writer's output before the compact spelling.
    model = codec.decode_versioned_distribution(
        (COMPILER / f"{fixture}.json").read_text()
    )
    golden = json.loads((COMPILER / f"{fixture}.expanded.json").read_text())
    encoded = codec.encode_versioned_distribution(model, spelling=Spelling.EXPANDED)
    assert json.dumps(encoded) == json.dumps(golden)


@pytest.mark.parametrize(
    ("tpe", "expected"),
    [
        (t.Variable(NO_TYPE, name("a")), "a"),
        (t.Reference(NO_TYPE, INT, []), "morphir/SDK:basics#int"),
        (
            t.Reference(NO_TYPE, LIST, [t.Variable(NO_TYPE, name("a"))]),
            {"Reference": ["morphir/SDK:list#list", "a"]},
        ),
        (
            t.Tuple(NO_TYPE, [t.Reference(NO_TYPE, INT, []), t.Unit(NO_TYPE)]),
            {"Tuple": ["morphir/SDK:basics#int", {"Unit": {}}]},
        ),
        (
            t.Function(
                NO_TYPE, t.Variable(NO_TYPE, name("a")), t.Reference(NO_TYPE, INT, [])
            ),
            {
                "Function": {
                    "parameterType": "a",
                    "returnType": "morphir/SDK:basics#int",
                }
            },
        ),
        (
            t.Record(NO_TYPE, [t.Field(name("count"), t.Reference(NO_TYPE, INT, []))]),
            {"Record": {"fields": {"count": "morphir/SDK:basics#int"}}},
        ),
    ],
)
def test_compact_type_forms(tpe: t.Type, expected: Any) -> None:
    assert codec.encode_type(tpe) == expected
    assert codec.decode_type(codec.encode_type(tpe)) == tpe


def test_a_type_with_attributes_keeps_the_expanded_spelling() -> None:
    located = t.Reference(LOCATED, INT, [t.Variable(NO_TYPE, name("a"))])
    encoded = codec.encode_type(located)
    assert list(encoded["Reference"]) == ["attributes", "fqname", "args"]
    assert encoded["Reference"]["args"] == ["a"]
    assert codec.decode_type(encoded) == located


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            v.LiteralValue(NO_VALUE, lit.IntegerLiteral(42)),
            {"Literal": {"IntegerLiteral": 42}},
        ),
        (
            v.LiteralValue(NO_VALUE, lit.StringLiteral("x")),
            {"Literal": {"StringLiteral": "x"}},
        ),
        (v.Variable(NO_VALUE, name("flag")), {"Variable": "flag"}),
        (v.Reference(NO_VALUE, INT), {"Reference": "morphir/SDK:basics#int"}),
        (v.Constructor(NO_VALUE, INT), {"Constructor": "morphir/SDK:basics#int"}),
        (v.FieldFunction(NO_VALUE, name("count")), {"FieldFunction": "count"}),
        (
            v.Tuple(NO_VALUE, [v.Variable(NO_VALUE, name("a")), v.Unit(NO_VALUE)]),
            {"Tuple": [{"Variable": "a"}, {"Unit": {}}]},
        ),
        (
            v.List(NO_VALUE, [v.LiteralValue(NO_VALUE, lit.BoolLiteral(True))]),
            {"List": [{"Literal": {"BoolLiteral": True}}]},
        ),
        (
            v.Apply(
                NO_VALUE, v.Reference(NO_VALUE, INT), v.Variable(NO_VALUE, name("a"))
            ),
            {
                "Apply": {
                    "function": {"Reference": "morphir/SDK:basics#int"},
                    "argument": {"Variable": "a"},
                }
            },
        ),
    ],
)
def test_compact_value_forms(value: v.Value, expected: Any) -> None:
    assert codec.encode_value(value) == expected
    assert codec.decode_value(codec.encode_value(value)) == value


def test_compact_pattern_forms() -> None:
    pattern = v.TuplePattern(
        NO_VALUE,
        [
            v.LiteralPattern(NO_VALUE, lit.IntegerLiteral(1)),
            v.WildcardPattern(NO_VALUE),
        ],
    )
    encoded = codec.encode_pattern(pattern)
    assert encoded == {
        "TuplePattern": [
            {"LiteralPattern": {"IntegerLiteral": 1}},
            {"WildcardPattern": {}},
        ]
    }
    assert codec.decode_pattern(encoded) == pattern


def test_a_value_with_attributes_keeps_the_expanded_spelling() -> None:
    typed = v.ValueAttributes(inferred_type=t.Reference(NO_TYPE, INT, []))
    value = v.Variable(typed, name("a"))
    encoded = codec.encode_value(value)
    assert list(encoded["Variable"]) == ["attributes", "name"]
    assert encoded["Variable"]["attributes"]["inferredType"] == "morphir/SDK:basics#int"
    assert codec.decode_value(encoded) == value


COMPACT_TAGS = {
    "Literal",
    "Variable",
    "Reference",
    "Constructor",
    "FieldFunction",
    "Tuple",
    "List",
    "TuplePattern",
    "LiteralPattern",
}


def compact_nodes(json_value: Any, path: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    """Paths of wrappers whose payload is not an expanded object."""
    found: list[tuple[Any, ...]] = []
    if isinstance(json_value, dict):
        for key, item in json_value.items():
            if (
                key in COMPACT_TAGS
                and len(json_value) == 1
                and not isinstance(item, dict)
            ):
                found.append((*path, key))
            found.extend(compact_nodes(item, (*path, key)))
    elif isinstance(json_value, list):
        for index, item in enumerate(json_value):
            found.extend(compact_nodes(item, (*path, index)))
    return found


@pytest.mark.parametrize(
    "fixture",
    [
        COMPILER / "modules-v4.json",
        COMPILER / "adt-v4.json",
        UPSTREAM / "finos-books-and-records-example.json",
    ],
)
def test_expanded_output_has_no_compact_node(fixture: Path) -> None:
    model = codec.decode_versioned_distribution(fixture.read_text())
    expanded = codec.encode_versioned_distribution(model, spelling=Spelling.EXPANDED)
    assert compact_nodes(expanded) == []
    compact = codec.encode_versioned_distribution(model)
    assert compact_nodes(compact) != []
    assert codec.decode_versioned_distribution(json.dumps(expanded)) == model
    assert codec.decode_versioned_distribution(json.dumps(compact)) == model


def test_the_selection_applies_only_to_its_call() -> None:
    tpe = t.Reference(NO_TYPE, INT, [])
    assert codec.encode_type(tpe, spelling=Spelling.EXPANDED) == {
        "Reference": {"fqname": "morphir/SDK:basics#int"}
    }
    assert codec.encode_type(tpe) == "morphir/SDK:basics#int"


def test_documentation_is_flattened_first() -> None:
    document = json.loads((COMPILER / "modules-v4.json").read_text())
    modules = document["distribution"]["Library"]["def"]["modules"]
    point = modules["models"]["Public"]["types"]["point"]["Public"]
    modules["models"]["Public"]["types"]["point"]["Public"] = {
        "doc": "A point.",
        **point,
    }
    choose = modules["rules"]["Public"]["values"]["select-decision"]["Public"]
    modules["rules"]["Public"]["values"]["select-decision"]["Public"] = {
        "value": choose,
        "doc": "Choose one.",
    }
    model = codec.decode_versioned_distribution(json.dumps(document))
    for spelling in Spelling:
        encoded = codec.encode_versioned_distribution(model, spelling=spelling)
        documented = [
            node for node in _objects(encoded) if "doc" in node and "types" not in node
        ]
        assert len(documented) == 2
        for node in documented:
            # Decision 0010: `doc` first, beside the node's own members.
            assert next(iter(node)) == "doc"
            assert "value" not in node
        assert codec.decode_versioned_distribution(json.dumps(encoded)) == model


def _objects(json_value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(json_value, dict):
        found.append(json_value)
        for item in json_value.values():
            found.extend(_objects(item))
    elif isinstance(json_value, list):
        for item in json_value:
            found.extend(_objects(item))
    return found


def test_a_documented_node_that_is_not_an_object_is_refused() -> None:
    def encode_string(value: str, _loc: tuple[Any, ...]) -> Any:
        return value

    run = codec._encode_documented(encode_string)
    from morphir.ir.v4.documented import Documented

    with pytest.raises(DiagnosticError) as error:
        run(Documented("text", "not an object"), ())
    assert error.value.codes == (d.NO_V4_SPELLING,)
