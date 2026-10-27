r"""Compile Python to Morphir IR and generate Python from Morphir IR.

This is the typed, in-process API behind ``morphir-python compile`` and
``morphir-python generate``. A native compiler does the work; callers need
neither Rust nor a separate Morphir executable, and the native compiler loads
only when one of these functions is first called.

Example:
    >>> from morphir_tools.python import SourceDocument, compile_sources
    >>> from morphir_tools.python import CompiledV3, generate_python
    >>> source = SourceDocument(
    ...     "rules.py",
    ...     "def choose(flag: bool, a: int, b: int) -> int:\n"
    ...     "    return a if flag else b\n",
    ... )
    >>> compiled = compile_sources([source], package="acme/example")
    >>> isinstance(compiled, CompiledV3)
    True
    >>> generated = generate_python(compiled.distribution)
    >>> [artifact.path for artifact in generated.artifacts]
    ['rules.py']
"""

from ._api import compile_sources, generate_python, native_compiler
from ._bridge import EXPECTED_BRIDGE_API, EXPECTED_NATIVE_VERSION
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
    NativeCompilerUnavailable,
    Severity,
    SourceDocument,
    SourceLocation,
    SourcePosition,
)

__all__ = [
    "EXPECTED_BRIDGE_API",
    "EXPECTED_NATIVE_VERSION",
    "CompileFailure",
    "CompileResult",
    "CompiledV3",
    "CompiledV4",
    "CompilerDiagnostic",
    "GenerateResult",
    "Generated",
    "GeneratedArtifact",
    "GenerationFailure",
    "IrVersion",
    "LibraryModel",
    "NativeCompilerError",
    "NativeCompilerInfo",
    "NativeCompilerUnavailable",
    "Severity",
    "SourceDocument",
    "SourceLocation",
    "SourcePosition",
    "compile_sources",
    "generate_python",
    "native_compiler",
]
