"""Immutable inputs and results of the Python compiler API."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from morphir.ir.v3 import distribution as v3_dist
from morphir.ir.v4 import distribution as v4_dist


class IrVersion(Enum):
    """The Morphir IR version a compilation writes."""

    V3 = "3"
    """Stable format 3.0.0."""
    V4 = "4"
    """Draft format 4.0.0."""


class Severity(Enum):
    """How serious a compiler diagnostic is."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"


@dataclass(frozen=True)
class SourceDocument:
    """One Python source file to compile.

    Attributes:
        path: Path relative to the source root, with ``/`` separators, such as
            ``"acme/rules.py"``. It decides the Morphir module name.
        text: The complete source text. It is parsed, never imported or run.
    """

    path: str
    text: str


@dataclass(frozen=True)
class SourcePosition:
    """A zero-based line and UTF-16 character offset in a source document."""

    line: int
    character: int


@dataclass(frozen=True)
class SourceLocation:
    """A half-open range in one source document."""

    path: str
    start: SourcePosition
    end: SourcePosition


@dataclass(frozen=True)
class CompilerDiagnostic:
    """A problem reported by compilation or generation.

    Attributes:
        code: Stable code from `morphir_tools.python.diagnostics` or
            `morphir.ir.diagnostics`.
        severity: How serious the problem is.
        message: Human-readable explanation. Callers must not parse it.
        source: The source range, when the problem is in a source document.
        ir_path: Path from the IR document root, when the problem is in IR.
    """

    code: str
    severity: Severity
    message: str
    source: SourceLocation | None = None
    ir_path: tuple[str | int, ...] = ()

    def render(self) -> str:
        """Render as ``severity code at location: message`` for terminal output."""
        if self.source is not None:
            start = self.source.start
            where = f"{self.source.path}:{start.line + 1}:{start.character + 1}"
        elif self.ir_path:
            where = "/".join(str(part) for part in self.ir_path)
        else:
            where = "<request>"
        return f"{self.severity.value} {self.code} at {where}: {self.message}"


def _warnings_only(diagnostics: tuple[CompilerDiagnostic, ...]) -> None:
    if any(item.severity is Severity.ERROR for item in diagnostics):
        raise ValueError("a successful result cannot carry error diagnostics")


def _not_empty(diagnostics: tuple[CompilerDiagnostic, ...]) -> None:
    if not diagnostics:
        raise ValueError("a failure needs at least one diagnostic")


@dataclass(frozen=True)
class CompiledV3:
    """A successful compilation to a format 3.0.0 Library."""

    distribution: v3_dist.Library
    warnings: tuple[CompilerDiagnostic, ...] = ()

    def __post_init__(self) -> None:
        _warnings_only(self.warnings)


@dataclass(frozen=True)
class CompiledV4:
    """A successful compilation to a draft format 4.0.0 Library."""

    distribution: v4_dist.LibraryDistribution
    warnings: tuple[CompilerDiagnostic, ...] = ()

    def __post_init__(self) -> None:
        _warnings_only(self.warnings)


@dataclass(frozen=True)
class CompileFailure:
    """A compilation that produced no model."""

    diagnostics: tuple[CompilerDiagnostic, ...]

    def __post_init__(self) -> None:
        _not_empty(self.diagnostics)


type CompileResult = CompiledV3 | CompiledV4 | CompileFailure


@dataclass(frozen=True)
class GeneratedArtifact:
    """One generated Python module.

    Attributes:
        path: Path relative to the output root, with ``/`` separators.
        text: The module source.
    """

    path: str
    text: str


@dataclass(frozen=True)
class Generated:
    """Successful generation: every module of the input Library."""

    artifacts: tuple[GeneratedArtifact, ...]
    warnings: tuple[CompilerDiagnostic, ...] = ()

    def __post_init__(self) -> None:
        _warnings_only(self.warnings)


@dataclass(frozen=True)
class GenerationFailure:
    """A generation that produced no artifacts."""

    diagnostics: tuple[CompilerDiagnostic, ...]

    def __post_init__(self) -> None:
        _not_empty(self.diagnostics)


type GenerateResult = Generated | GenerationFailure

type LibraryModel = v3_dist.Library | v4_dist.LibraryDistribution
"""A Library model that generation accepts."""


@dataclass(frozen=True)
class NativeCompilerInfo:
    """Identity of the loaded native compiler.

    Attributes:
        version: Version of the ``morphir-python-native`` distribution and module.
        bridge_api: Revision of the private bridge contract.
        compiler_version: Version of the linked ``morphir-python-binding`` crate.
    """

    version: str
    bridge_api: int
    compiler_version: str


class NativeCompilerUnavailable(ImportError):  # noqa: N818 - reads as a state
    """The native compiler is missing or incompatible with this release."""


class NativeCompilerError(RuntimeError):
    """The native compiler failed internally; this is a bug, not a user error."""
