"""Compile Python sources to Morphir IR and generate Python from IR."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from morphir.ir import format_version as fv
from morphir.ir.diagnostics import DiagnosticError
from morphir.ir.v3 import codec as v3_codec
from morphir.ir.v3 import distribution as v3_dist
from morphir.ir.v4 import codec as v4_codec
from morphir.ir.v4 import distribution as v4_dist

from . import _bridge
from . import diagnostics as codes

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping, Sequence

from ._types import (
    CompiledV3,
    CompiledV4,
    CompileFailure,
    CompilerDiagnostic,
    CompileResult,
    Generated,
    GeneratedArtifact,
    GenerateResult,
    GenerationFailure,
    IrVersion,
    LibraryModel,
    NativeCompilerError,
    NativeCompilerInfo,
    Severity,
    SourceDocument,
    SourceLocation,
    SourcePosition,
)


def native_compiler() -> NativeCompilerInfo:
    """Load the native compiler and report its identity.

    Raises:
        NativeCompilerUnavailable: When it is missing or incompatible.
    """
    return _bridge.load()


def compile_sources(
    sources: Iterable[SourceDocument],
    *,
    package: str,
    exposed_modules: Sequence[str] | None = None,
    ir_version: IrVersion = IrVersion.V3,
) -> CompileResult:
    """Compile Python source documents to a Morphir IR Library.

    The sources are parsed statically: nothing is imported or executed. The
    order of ``sources`` does not affect the result.

    Args:
        sources: The documents of one package, with paths relative to its root.
        package: The Morphir package name, such as ``"acme/example"``.
        exposed_modules: Module paths to make public, such as
            ``("acme/models",)``. ``None`` exposes every module; an empty
            sequence exposes none.
        ir_version: The IR version to write. Defaults to stable v3.

    Returns:
        A `CompiledV3` or `CompiledV4` holding the decoded Library, or a
        `CompileFailure` with at least one diagnostic and no model.

    Raises:
        ValueError: When ``package`` is empty or two documents share a path.
        NativeCompilerUnavailable: When the native compiler is missing or
            incompatible.
        NativeCompilerError: When the native compiler fails internally.
    """
    documents = sorted(sources, key=lambda document: document.path)
    if not package:
        raise ValueError("package must name a Morphir package")
    paths = [document.path for document in documents]
    if len(set(paths)) != len(paths):
        raise ValueError("source documents contain a duplicate path")
    request = {
        "package": package,
        "sources": [{"path": d.path, "text": d.text} for d in documents],
        "exposedModules": None if exposed_modules is None else list(exposed_modules),
        "irVersion": ir_version.value,
    }
    output = _call(_bridge.module().compile, json.dumps(request))
    diagnostics = _diagnostics(output)
    ir = output.get("ir")
    if not output.get("success") or not isinstance(ir, str):
        return CompileFailure(diagnostics or (_missing_diagnostic(),))
    try:
        if ir_version is IrVersion.V3:
            classic = v3_codec.decode_versioned_distribution(ir)
            if isinstance(classic, v3_dist.Library):
                return CompiledV3(classic, diagnostics)
        else:
            draft = v4_codec.decode_versioned_distribution(ir)
            if isinstance(draft, v4_dist.LibraryDistribution):
                return CompiledV4(draft, diagnostics)
    except DiagnosticError as error:
        return CompileFailure(_ir_diagnostics(error))
    raise NativeCompilerError("the native compiler returned a non-Library model")


def generate_python(distribution: LibraryModel | object) -> GenerateResult:
    """Generate Python modules from a v3 or draft v4 Library model.

    Args:
        distribution: A `morphir.ir.v3.distribution.Library` or
            `morphir.ir.v4.distribution.LibraryDistribution`. Specs and
            Application distributions are rejected with a diagnostic.

    Returns:
        `Generated` with one artifact per module, in path order, or a
        `GenerationFailure` with at least one diagnostic and no artifacts.

    Raises:
        NativeCompilerUnavailable: When the native compiler is missing or
            incompatible.
        NativeCompilerError: When the native compiler fails internally.
    """
    try:
        match distribution:
            case v3_dist.Library():
                document = v3_codec.encode_versioned_distribution(distribution)
            case v4_dist.LibraryDistribution():
                document = v4_codec.encode_versioned_distribution(distribution)
            case _:
                kind = type(distribution).__name__
                return GenerationFailure(
                    (
                        CompilerDiagnostic(
                            codes.UNSUPPORTED_DISTRIBUTION,
                            Severity.ERROR,
                            "Python generation needs a Library distribution, "
                            f"not {kind}",
                        ),
                    )
                )
    except DiagnosticError as error:
        return GenerationFailure(_ir_diagnostics(error))
    output = _call(_bridge.module().generate, fv.dump_json(document))
    diagnostics = _diagnostics(output)
    raw = output.get("artifacts")
    if not output.get("success") or not isinstance(raw, list):
        return GenerationFailure(diagnostics or (_missing_diagnostic(),))
    artifacts = tuple(
        sorted(
            (
                GeneratedArtifact(str(item["path"]), str(item["content"]))
                for item in cast("list[Mapping[str, object]]", raw)
            ),
            key=lambda artifact: artifact.path,
        )
    )
    return Generated(artifacts, diagnostics)


def _call(function: Callable[[str], str], argument: str) -> Mapping[str, object]:
    output = cast("Mapping[str, object]", json.loads(function(argument)))
    internal = output.get("internalError")
    if internal is not None:
        raise NativeCompilerError(str(internal))
    return output


def _missing_diagnostic() -> CompilerDiagnostic:
    return CompilerDiagnostic(
        codes.PY_SERIALIZATION,
        Severity.ERROR,
        "the native compiler failed without a diagnostic",
    )


def _diagnostics(output: Mapping[str, object]) -> tuple[CompilerDiagnostic, ...]:
    items = cast("list[Mapping[str, object]]", output.get("diagnostics") or [])
    return tuple(_diagnostic(item) for item in items)


def _diagnostic(item: Mapping[str, object]) -> CompilerDiagnostic:
    location = cast("Mapping[str, object] | None", item.get("location"))
    source = None
    if location is not None:
        start = cast("Mapping[str, int]", location["start"])
        end = cast("Mapping[str, int]", location["end"])
        source = SourceLocation(
            str(location["path"]),
            SourcePosition(start["line"], start["character"]),
            SourcePosition(end["line"], end["character"]),
        )
    return CompilerDiagnostic(
        code=str(item.get("code") or codes.PY_SERIALIZATION),
        severity=Severity(str(item["severity"])),
        message=str(item["message"]),
        source=source,
    )


def _ir_diagnostics(error: DiagnosticError) -> tuple[CompilerDiagnostic, ...]:
    return tuple(
        CompilerDiagnostic(
            code=item.code,
            severity=Severity.ERROR,
            message=item.message,
            ir_path=item.location,
        )
        for item in error.diagnostics
    )
