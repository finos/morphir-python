# Python API reference

Import the public compiler API from `morphir_tools.python`. It loads the native
compiler lazily when you compile or generate. The private bridge module is not
an application API. See the [complete example](python-compiler.md#use-the-python-api)
and [installation requirements](installation.md) first.

## Operations

| Operation | Result |
| --- | --- |
| `compile_sources(sources, *, package, exposed_modules=None, ir_version=IrVersion.V3)` | `CompileResult` |
| `generate_python(distribution)` | `GenerateResult` |
| `native_compiler()` | `NativeCompilerInfo` |

`sources` is a sequence of `SourceDocument(path, text)`. Paths are relative module
paths with `/` separators. Compilation reads source text statically. `package`
is a Morphir package identity; exposure uses module paths. `IrVersion.V3` is the
default; `IrVersion.V4` is draft.

## Immutable results and diagnostics

`CompileResult` is `CompiledV3 | CompiledV4 | CompileFailure`. A success has a
version-specific `distribution` and `warnings`. `GenerateResult` is
`Generated | GenerationFailure`; success contains ordered `GeneratedArtifact`
values with `path` and `text`. `LibraryModel` identifies supported input models.

`CompilerDiagnostic` has `code`, `severity`, `message`, optional `source` and
`ir_path`. `Severity` distinguishes error, warning, info and hint. A
`SourceLocation` contains the `path`, `start` and `end` `SourcePosition` values.
Positions use zero-based lines and UTF-16 characters. `render()` formats a
human-readable location; use fields and codes in application logic.

`NativeCompilerUnavailable` reports a missing or incompatible installation.
`NativeCompilerError` reports an internal compiler failure.
`EXPECTED_BRIDGE_API` and `EXPECTED_NATIVE_VERSION` describe the private package
pair expected by this CLI release. They are diagnostic information, not knobs
to override a version mismatch.

## Checked signatures

This reference is synchronized from the candidate public exports. The declared
release examples verify that their used signatures work against the released
pair. The reference check fails if a public export disappears from this page
or its signature snapshot changes without updating the source.

<!-- reference: api -->
```text
EXPECTED_BRIDGE_API
EXPECTED_NATIVE_VERSION
CompileFailure(diagnostics: 'tuple[CompilerDiagnostic, ...]') -> None
CompileResult
CompiledV3(distribution: 'v3_dist.Library', warnings: 'tuple[CompilerDiagnostic, ...]' = ()) -> None
CompiledV4(distribution: 'v4_dist.LibraryDistribution', warnings: 'tuple[CompilerDiagnostic, ...]' = ()) -> None
CompilerDiagnostic(code: 'str', severity: 'Severity', message: 'str', source: 'SourceLocation | None' = None, ir_path: 'tuple[str | int, ...]' = ()) -> None
GenerateResult
Generated(artifacts: 'tuple[GeneratedArtifact, ...]', warnings: 'tuple[CompilerDiagnostic, ...]' = ()) -> None
GeneratedArtifact(path: 'str', text: 'str') -> None
GenerationFailure(diagnostics: 'tuple[CompilerDiagnostic, ...]') -> None
IrVersion(*values)
LibraryModel
NativeCompilerError
NativeCompilerInfo(version: 'str', bridge_api: 'int', compiler_version: 'str') -> None
NativeCompilerUnavailable
Severity(*values)
SourceDocument(path: 'str', text: 'str') -> None
SourceLocation(path: 'str', start: 'SourcePosition', end: 'SourcePosition') -> None
SourcePosition(line: 'int', character: 'int') -> None
compile_sources(sources: 'Iterable[SourceDocument]', *, package: 'str', exposed_modules: 'Sequence[str] | None' = None, ir_version: 'IrVersion' = <IrVersion.V3: '3'>) -> 'CompileResult'
generate_python(distribution: 'LibraryModel | object') -> 'GenerateResult'
native_compiler() -> 'NativeCompilerInfo'
```
<!-- /reference -->
