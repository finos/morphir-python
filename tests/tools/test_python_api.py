"""Tests for the typed Python compiler API (capability python/compiler)."""

from __future__ import annotations

import dataclasses
import json
import threading
from pathlib import Path

import pytest

from morphir.ir.v3 import codec as v3_codec
from morphir.ir.v3 import distribution as v3_dist
from morphir.ir.v4 import distribution as v4_dist
from morphir_tools import python as api
from morphir_tools.python import diagnostics as codes

V3_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ir" / "v3"

MODELS = """\
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Pending:
    pass

@dataclass(frozen=True)
class Approved:
    amount: float

type Decision = Pending | Approved

type Point = tuple[float, float]
"""

RULES = """\
from __future__ import annotations
from collections.abc import Callable
from .models import Decision, Point

def choose(flag: bool, first: Decision, second: Decision) -> Decision:
    if flag:
        return first
    else:
        return second

def origin() -> Point:
    return (0.0, 0.0)

def apply_twice(step: Callable[[int], int], value: int) -> int:
    return step(step(value))

def add_one(value: int) -> int:
    return apply_twice(lambda item: item, value)
"""

SOURCES = (
    api.SourceDocument("acme/models.py", MODELS),
    api.SourceDocument("acme/rules.py", RULES),
)


def module_access(library: v3_dist.Library) -> dict[str, str]:
    return {
        "/".join("-".join(name) for name in path): module.access.value
        for path, module in library.definition.modules.items()
    }


def compile_ok(
    sources: tuple[api.SourceDocument, ...] = SOURCES,
    **options: object,
) -> api.CompiledV3 | api.CompiledV4:
    result = api.compile_sources(sources, package="acme/example", **options)  # type: ignore[arg-type]
    assert not isinstance(result, api.CompileFailure), result
    return result


class TestCompile:
    def test_defaults_to_a_v3_library(self) -> None:
        result = compile_ok()
        assert isinstance(result, api.CompiledV3)
        assert isinstance(result.distribution, v3_dist.Library)
        assert result.warnings == ()
        assert set(module_access(result.distribution)) == {"acme/models", "acme/rules"}

    def test_explicit_v4_returns_the_v4_model(self) -> None:
        result = compile_ok(ir_version=api.IrVersion.V4)
        assert isinstance(result, api.CompiledV4)
        assert isinstance(result.distribution, v4_dist.LibraryDistribution)

    def test_exposure_selects_public_modules(self) -> None:
        result = compile_ok(exposed_modules=("acme/models",))
        assert isinstance(result, api.CompiledV3)
        assert module_access(result.distribution) == {
            "acme/models": "Public",
            "acme/rules": "Private",
        }

    def test_empty_exposure_differs_from_omitted_exposure(self) -> None:
        result = compile_ok(exposed_modules=())
        assert isinstance(result, api.CompiledV3)
        assert set(module_access(result.distribution).values()) == {"Private"}

    def test_syntax_error_is_a_located_failure(self) -> None:
        result = api.compile_sources(
            (api.SourceDocument("broken.py", "def broken(:\n"),), package="acme/x"
        )
        assert isinstance(result, api.CompileFailure)
        (diagnostic,) = result.diagnostics
        assert diagnostic.code == codes.PY_SYNTAX
        assert diagnostic.severity is api.Severity.ERROR
        assert diagnostic.source is not None
        assert diagnostic.source.path == "broken.py"
        assert diagnostic.source.start.line == 0
        assert diagnostic.render().startswith("PY002 at broken.py:1:")

    @pytest.mark.parametrize(
        "text",
        [
            "count = 1\n",
            "import os\n",
            "from pathlib import Path\nPath('owned.txt').write_text('x')\n",
        ],
    )
    def test_unsupported_constructs_fail_without_a_model(
        self, text: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = api.compile_sources(
            (api.SourceDocument("bad.py", text),), package="acme/x"
        )
        assert isinstance(result, api.CompileFailure)
        assert not hasattr(result, "distribution")
        assert result.diagnostics[0].severity is api.Severity.ERROR
        assert result.diagnostics[0].code in {codes.PY_UNSUPPORTED, codes.PY_NAME}
        assert list(tmp_path.iterdir()) == []

    def test_source_permutations_give_equal_models(self) -> None:
        first = compile_ok()
        second = compile_ok(tuple(reversed(SOURCES)))
        assert first == second

    def test_concurrent_calls_are_independent(self) -> None:
        expected = {
            version: compile_ok(ir_version=version) for version in api.IrVersion
        }
        failures: list[str] = []

        def work(version: api.IrVersion) -> None:
            for _ in range(5):
                if compile_ok(ir_version=version) != expected[version]:
                    failures.append(version.value)

        threads = [
            threading.Thread(target=work, args=(version,))
            for version in list(api.IrVersion) * 4
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        assert failures == []

    def test_invalid_options_are_rejected_before_compiling(self) -> None:
        with pytest.raises(ValueError, match="package"):
            api.compile_sources(SOURCES, package="")
        with pytest.raises(ValueError, match="duplicate"):
            api.compile_sources(SOURCES + SOURCES[:1], package="acme/x")


class TestResultTypes:
    def test_results_are_frozen(self) -> None:
        result = compile_ok()
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.warnings = ()  # type: ignore[misc]
        with pytest.raises(dataclasses.FrozenInstanceError):
            SOURCES[0].text = ""  # type: ignore[misc]

    def test_failure_cannot_be_empty(self) -> None:
        with pytest.raises(ValueError):
            api.CompileFailure(())
        with pytest.raises(ValueError):
            api.GenerationFailure(())

    def test_success_cannot_hold_errors(self) -> None:
        error = api.CompilerDiagnostic(
            code="PY004", severity=api.Severity.ERROR, message="no"
        )
        with pytest.raises(ValueError):
            api.Generated(artifacts=(), warnings=(error,))


class TestGenerate:
    @pytest.mark.parametrize("version", list(api.IrVersion))
    def test_generates_one_artifact_per_module(self, version: api.IrVersion) -> None:
        compiled = compile_ok(ir_version=version)
        generated = api.generate_python(compiled.distribution)
        assert isinstance(generated, api.Generated), generated
        assert [artifact.path for artifact in generated.artifacts] == [
            "acme/models.py",
            "acme/rules.py",
        ]
        rules = generated.artifacts[1].text
        assert "def choose(" in rules
        assert "lambda" in rules

    @pytest.mark.parametrize("version", list(api.IrVersion))
    def test_generated_python_recompiles_to_the_same_model(
        self, version: api.IrVersion
    ) -> None:
        compiled = compile_ok(ir_version=version)
        generated = api.generate_python(compiled.distribution)
        assert isinstance(generated, api.Generated)
        sources = tuple(
            api.SourceDocument(artifact.path, artifact.text)
            for artifact in generated.artifacts
        )
        assert compile_ok(sources, ir_version=version) == compiled

    def test_specs_distribution_is_rejected(self) -> None:
        specs = v3_codec.decode_versioned_distribution(
            (V3_FIXTURES / "mck-distributions-0011-specs.json").read_text()
        )
        assert isinstance(specs, v3_dist.Specs)
        result = api.generate_python(specs)
        assert isinstance(result, api.GenerationFailure)
        assert result.diagnostics[0].code == codes.UNSUPPORTED_DISTRIBUTION

    def test_unsupported_value_is_a_compiler_diagnostic(self) -> None:
        library = v3_codec.decode_versioned_distribution(
            (V3_FIXTURES / "elm-simpleValueTree.json").read_text()
        )
        result = api.generate_python(library)
        assert isinstance(result, api.GenerationFailure)
        assert result.diagnostics[0].code.startswith("PY")


class TestNativeCompatibility:
    def test_reports_the_installed_native_compiler(self) -> None:
        info = api.native_compiler()
        assert info.version == api.EXPECTED_NATIVE_VERSION
        assert info.bridge_api == api.EXPECTED_BRIDGE_API
        assert info.compiler_version

    def test_rejects_a_mismatched_native_version(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from morphir_tools.python import _bridge

        monkeypatch.setattr(_bridge, "EXPECTED_NATIVE_VERSION", "9.9.9")
        _bridge.load.cache_clear()
        try:
            with pytest.raises(api.NativeCompilerUnavailable, match=r"9\.9\.9"):
                api.compile_sources(SOURCES, package="acme/example")
        finally:
            monkeypatch.undo()
            _bridge.load.cache_clear()

    def test_rejects_a_mismatched_bridge_revision(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from morphir_tools.python import _bridge

        monkeypatch.setattr(_bridge, "EXPECTED_BRIDGE_API", 999)
        _bridge.load.cache_clear()
        try:
            with pytest.raises(api.NativeCompilerUnavailable, match="999"):
                api.native_compiler()
        finally:
            monkeypatch.undo()
            _bridge.load.cache_clear()

    def test_internal_errors_raise(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from morphir_tools.python import _bridge

        class Broken:
            @staticmethod
            def compile(request: str) -> str:
                return json.dumps(
                    {"success": False, "diagnostics": [], "internalError": "boom"}
                )

        monkeypatch.setattr(_bridge, "module", lambda: Broken)
        with pytest.raises(api.NativeCompilerError, match="boom"):
            api.compile_sources(SOURCES, package="acme/example")
