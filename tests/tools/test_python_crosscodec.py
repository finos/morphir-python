"""The Rust compiler and the Python codecs agree on the supported mapping."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from morphir.ir import diagnostics as d
from morphir.ir import format_version as fv
from morphir.ir.migrate import Err, v3_to_v4, v4_to_v3
from morphir.ir.v3 import distribution as v3_dist
from morphir.ir.v4 import codec as v4_codec
from morphir.ir.v4 import distribution as v4_dist
from morphir_python_native import _native
from morphir_tools import python as api
from morphir_tools.python import diagnostics as codes

if TYPE_CHECKING:
    from collections.abc import Mapping

    import pytest

NUMBERS = """\
from __future__ import annotations
type Pair = tuple[tuple[int, int], float]

def nest(a: int, b: int, c: float) -> Pair:
    return ((a, b), c)

def big() -> int:
    return 123456789012345678901234567890
"""

SAMPLE = Path(__file__).resolve().parents[1] / "fixtures" / "python" / "loans"
UPSTREAM_V4 = Path(__file__).resolve().parents[1] / "fixtures" / "ir" / "v4"


def sample() -> list[api.SourceDocument]:
    return [
        api.SourceDocument(p.relative_to(SAMPLE).as_posix(), p.read_text())
        for p in sorted(SAMPLE.rglob("*.py"))
    ]


def compiled(
    sources: list[api.SourceDocument], version: api.IrVersion
) -> api.CompiledV3 | api.CompiledV4:
    result = api.compile_sources(sources, package="acme/example", ir_version=version)
    assert not isinstance(result, api.CompileFailure), result
    return result


def texts(result: api.GenerateResult) -> dict[str, str]:
    assert isinstance(result, api.Generated), result
    return {artifact.path: artifact.text for artifact in result.artifacts}


class TestNumbersAndTuples:
    def test_v4_keeps_arbitrary_integers_and_nested_tuples(self) -> None:
        source = [api.SourceDocument("numbers.py", NUMBERS)]
        first = compiled(source, api.IrVersion.V4)
        encoded = fv.dump_json(
            v4_codec.encode_versioned_distribution(first.distribution)  # type: ignore[arg-type]
        )
        assert "123456789012345678901234567890" in encoded
        generated = texts(api.generate_python(first.distribution))
        assert "return 123456789012345678901234567890" in generated["numbers.py"]
        assert "type Pair = tuple[tuple[int, int], float]" in generated["numbers.py"]
        again = compiled(
            [api.SourceDocument("numbers.py", generated["numbers.py"])],
            api.IrVersion.V4,
        )
        assert again == first

    def test_v3_rejects_integers_beyond_its_range(self) -> None:
        result = api.compile_sources(
            [api.SourceDocument("numbers.py", NUMBERS)], package="acme/example"
        )
        assert isinstance(result, api.CompileFailure)
        assert result.diagnostics[0].code == codes.PY_UNSUPPORTED
        assert "64-bit" in result.diagnostics[0].message


class TestIndependentlyAuthoredIr:
    def test_python_encoded_v4_generates_like_rust_encoded_v4(self) -> None:
        # The compiler writes compact v4; generate_python sends the Python
        # codec's expanded spelling of the same model.
        direct = compiled(sample(), api.IrVersion.V4)
        native = json.loads(
            json.loads(
                _native.compile(
                    json.dumps(
                        {
                            "package": "acme/example",
                            "sources": [
                                {"path": d.path, "text": d.text} for d in sample()
                            ],
                            "exposedModules": None,
                            "irVersion": "4",
                        }
                    )
                )
            )["ir"]
        )
        expanded = v4_codec.encode_versioned_distribution(
            direct.distribution,  # type: ignore[arg-type]
            spelling=v4_codec.Spelling.EXPANDED,
        )
        assert native != expanded
        assert v4_codec.decode_versioned_distribution(native) == direct.distribution
        from_compact = api.generate_python(
            v4_codec.decode_versioned_distribution(json.dumps(native))
        )
        assert texts(from_compact) == texts(api.generate_python(direct.distribution))

    def test_migrated_typed_v3_values_are_rejected_explicitly(self) -> None:
        # v3_to_v4 keeps inferred types as value attributes, which the compiler
        # cannot yet carry into Python; it says so instead of dropping them.
        classic = compiled(sample(), api.IrVersion.V3)
        assert isinstance(classic.distribution, v3_dist.Library)
        result = api.generate_python(v3_to_v4(classic.distribution).value)
        assert isinstance(result, api.GenerationFailure)
        assert result.diagnostics[0].code == codes.PY_UNSUPPORTED
        assert "attributes" in result.diagnostics[0].message

    def test_downgrading_compiler_v4_is_refused_explicitly(self) -> None:
        # v3 members need documentation strings that compiler v4 output lacks.
        draft = compiled(sample(), api.IrVersion.V4)
        assert isinstance(draft.distribution, v4_dist.LibraryDistribution)
        result = v4_to_v3(draft.distribution)
        assert isinstance(result, Err)
        found = {item.code for item in result.diagnostics}
        assert d.UNSUPPORTED_DOCUMENTATION_DOWNGRADE in found
        assert found <= {
            d.UNSUPPORTED_DOCUMENTATION_DOWNGRADE,
            d.MISSING_INFERRED_TYPE,
        }

    def test_an_upstream_example_outside_the_subset_is_diagnosed(self) -> None:
        upstream = v4_codec.decode_versioned_distribution(
            (UPSTREAM_V4 / "finos-books-and-records-example.json").read_text()
        )
        result = api.generate_python(upstream)
        assert isinstance(result, api.GenerationFailure)
        assert result.diagnostics[0].code.startswith("PY")


class TestNoSilentDropping:
    def test_documentation_is_rejected_not_dropped(self) -> None:
        draft = compiled(sample(), api.IrVersion.V4)
        document = v4_codec.encode_versioned_distribution(
            draft.distribution  # type: ignore[arg-type]
        )
        modules = document["distribution"]["Library"]["def"]["modules"]
        types = next(iter(modules.values()))["Public"]["types"]
        name, definition = next(iter(types.items()))
        access, body = next(iter(definition.items()))
        types[name] = {access: {"doc": "Documented in IR only.", **body}}
        documented = v4_codec.decode_versioned_distribution(json.dumps(document))
        result = api.generate_python(documented)
        assert isinstance(result, api.GenerationFailure), result
        assert result.diagnostics[0].code == codes.PY_UNSUPPORTED


class TestWarnings:
    def test_warnings_stay_with_a_successful_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from morphir_tools.python import _bridge

        real = _bridge.module()

        class Warns:
            @staticmethod
            def compile(request: str) -> str:
                output: Mapping[str, object] = json.loads(real.compile(request))
                return json.dumps(
                    {
                        **output,
                        "diagnostics": [
                            {
                                "severity": "warning",
                                "code": codes.PY_PARSE_STAGE,
                                "message": "parse-stage output is unavailable",
                                "location": None,
                            }
                        ],
                    }
                )

        monkeypatch.setattr(_bridge, "module", lambda: Warns)
        result = api.compile_sources(sample(), package="acme/example")
        assert isinstance(result, api.CompiledV3)
        (warning,) = result.warnings
        assert warning.severity is api.Severity.WARNING
        assert warning.code == codes.PY_PARSE_STAGE
