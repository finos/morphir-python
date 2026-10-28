# Compile Python to Morphir IR and generate Python

`morphir-python` compiles a supported subset of Python to Morphir IR, and
generates Python from Morphir IR. It does both in process, through a native
compiler that installs automatically with the package. You do not need Rust or a
separate Morphir executable.

The [released installation guide](installation.md) records the tested package
pair. This page also notes development-only codec behavior where it differs.

The compiler is the Rust crate
[`morphir-python-binding`](https://github.com/finos/morphir-python/blob/main/rust/crates/morphir-python-binding/README.md). The
same crate is the `morphir-python` Morphir extension, so the Python API, the CLI,
native Rust callers and Morphir extension hosts give the same results and the
same diagnostic codes.

## Install

```console
pip install morphir-python
```

This installs three distributions:

| Distribution | Contents | Runtime dependencies |
| --- | --- | --- |
| `morphir` | IR models, codecs and the Morphir SDK | none |
| `morphir-python-native` | private native compiler module | none |
| `morphir-python` | the `morphir-python` CLI and `morphir_tools.python` | `morphir`, one exact `morphir-python-native` version, Typer |

Install only `morphir` when you need the IR and SDK without the compiler.

Prebuilt `morphir-python-native` wheels are qualified for CPython 3.14 on:

| Platform | Wheel tag |
| --- | --- |
| Linux x86_64, glibc 2.28 or later | `manylinux_2_28_x86_64` |
| Linux aarch64, glibc 2.28 or later | `manylinux_2_28_aarch64` |
| macOS 11 or later, Apple silicon | `macosx_11_0_arm64` |
| macOS 10.12 or later, Intel | `macosx_10_12_x86_64` |
| Windows x86_64 | `win_amd64` |

The wheels use the CPython stable ABI (`cp314-abi3`). The free-threaded
interpreter (`python3.14t`) is not qualified. On other platforms `pip` builds the
compiler from the source archive, which needs Rust 1.98 or later; see
[Build from source](#build-from-source).

## Use the Python API

<!-- example: examples/compiler_api.py -->
```python
"""Compile source strings and generate typed artifacts in memory."""

from morphir_tools.python import (
    CompiledV3,
    CompileFailure,
    Generated,
    SourceDocument,
    compile_sources,
    generate_python,
)

models = SourceDocument(
    "acme/models.py",
    """\
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Pending:
    pass

@dataclass(frozen=True)
class Approved:
    amount: float

type Decision = Pending | Approved
""",
)
rules = SourceDocument(
    "acme/rules.py",
    """\
from __future__ import annotations
from .models import Decision

def choose(flag: bool, first: Decision, second: Decision) -> Decision:
    if flag:
        return first
    else:
        return second
""",
)

compiled = compile_sources([models, rules], package="acme/example")
if isinstance(compiled, CompileFailure):
    for diagnostic in compiled.diagnostics:
        print(diagnostic.severity.value, diagnostic.render())
    raise SystemExit(1)
assert isinstance(compiled, CompiledV3)

generated = generate_python(compiled.distribution)
assert isinstance(generated, Generated)
for artifact in generated.artifacts:
    print(artifact.path)
```
<!-- /example -->

`compile_sources` takes the source documents of one package, its Morphir
package name, and two options:

- `exposed_modules`: module paths to make public, such as `("acme/models",)`.
  `None`, the default, makes every module public. An empty tuple makes every
  module private.
- `ir_version`: `IrVersion.V3` (the default, stable format 3.0.0) or
  `IrVersion.V4` (draft format 4.0.0).

It returns one of three frozen types:

| Result | Contents |
| --- | --- |
| `CompiledV3` | `distribution`, a `morphir.ir.v3.distribution.Library`, and `warnings` |
| `CompiledV4` | `distribution`, a `morphir.ir.v4.distribution.LibraryDistribution`, and `warnings` |
| `CompileFailure` | `diagnostics`, at least one, and no model |

`generate_python` takes a v3 `Library` or a v4 `LibraryDistribution`, for example
one read with `morphir.ir.v3.codec.decode_versioned_distribution`. It returns
`Generated`, with one `GeneratedArtifact(path, text)` per module in path order,
or `GenerationFailure`. A Specs or Application distribution fails with
`unsupported_distribution`. Convert legacy formats 1 and 2 with
`morphir-python ir convert` first.

Generation reads both v4 spellings, the compact one the compiler and other
Morphir tools write and the expanded one the Python codec writes. Two limits
apply:

- IR v3 integer literals must fit in 64 bits. Compile to v4 for larger integers;
  v4 keeps them exactly.
- Generation does not yet accept v4 values that carry attributes. A v4 model
  that `morphir.ir.migrate.v3_to_v4` made from typed v3 IR keeps the inferred
  types as attributes, so generation rejects it with `PY004`. Generate from the
  v3 model instead. Empty documentation, which such a model also carries, is
  accepted; documentation text is rejected rather than dropped.

The order of the source documents does not change the result. Calls hold no
shared state, so several threads can compile at the same time; the compiler runs
without holding Python's global interpreter lock.

### Diagnostics

Each `CompilerDiagnostic` has a `code`, a `severity` (`Severity.ERROR`,
`WARNING`, `INFO` or `HINT`), a `message`, and either a `source` location
(path, zero-based line and UTF-16 character) or an `ir_path` into the IR
document. A success can carry warnings; a failure never carries a model.

| Code | Meaning |
| --- | --- |
| `PY001` | Unsupported request or option |
| `PY002` | Python syntax error, with a source range |
| `PY003` | Invalid name or naming collision |
| `PY004` | Unsupported declaration, annotation or IR feature |
| `PY005` | IR decoding or serialization, or generated syntax failure |
| `PY006` | Parse-stage output was requested but is unavailable |
| `unsupported_distribution` | Generation received a Specs or Application distribution |

IR reading and writing failures keep their `morphir.ir.diagnostics` codes, such
as `unknown_node`. The constants are in `morphir_tools.python.diagnostics`.

Two exceptions report installation problems, not problems in your model:
`NativeCompilerUnavailable` when the native compiler is missing or its version
does not match this release, and `NativeCompilerError` for an internal compiler
failure, which is a bug to report.

## Use the CLI

```console
morphir-python compile src --package acme/example --output model.json
morphir-python ir inspect model.json
morphir-python generate model.json --output-dir generated
morphir-python compile generated --package acme/example --output rebuilt.json
```

`compile SOURCE` accepts one `.py` file or a directory. A directory is read
recursively in sorted order; hidden directories, `__pycache__` and symbolic links
are skipped. A file's path relative to the source root gives its module name:
`src/acme/rules.py` becomes module `acme/rules`. A single file uses its parent
directory as the root.

| Option | Meaning |
| --- | --- |
| `--package NAME` | Morphir package name. Required. |
| `--output FILE` | Where to write the IR document. Required. |
| `--ir-version v3\|v4` | IR version to write; `v3` by default. `v4` prints a draft notice. |
| `--expose MODULE` | Module to make public. Repeat it for more modules. Without it every module is public. |

`generate FILE --output-dir DIRECTORY` reads a format 3.0 or draft v4 Library
and writes one Python module per Morphir module, keeping the module directories.
The output directory must not exist or must be empty, and must not be a symbolic
link. All files are written to a staging directory next to it and moved into
place together, so a failure leaves no partial output.

Both commands write diagnostics to standard error as
`error: CODE at LOCATION: MESSAGE`, and exit with 1 on failure. Warnings are
printed as `warning: ...` and do not change the exit code. A failed compilation
leaves an existing output file unchanged.

To make the generated modules importable, put the output directory on Python's
import path. The generated code needs no Morphir package at run time.

## Supported Python

The compiler accepts this subset of Python 3.12 and later, in both IR versions:

- frozen dataclasses as records, and named unions of dataclasses
  (`type Decision = Pending | Approved`) as custom types;
- fixed tuples and non-generic `type` aliases of tuples;
- scalar fields (`int`, `float`, `str`, `bool`), same-package references and
  unary `Callable[[A], B]` types;
- annotated pure functions whose bodies return through `if`/`elif`/`else`
  branches or conditional expressions, with literals, comparisons, typed calls
  and unary lambdas;
- absolute and relative imports between modules of the same package.

Anything else is rejected with a diagnostic, never compiled partially. This
includes assignments, loops, methods, defaults, containers, optional fields,
boolean operators, other imports, and constructor calls inside functions. The
[compiler README](https://github.com/finos/morphir-python/blob/main/rust/crates/morphir-python-binding/README.md#current-boundary)
lists the exact boundary.

Compilation reads source text only. It never imports or runs the source, and
generation never runs the generated code.

A compile, generate and recompile round trip keeps module access, references,
type definitions and function behavior. It does not keep comments, formatting or
equivalent spellings of the same expression.

## Build from source

Contributors build everything from a checkout with [mise](https://mise.jdx.dev):

```console
mise install          # Python 3.14, uv, Rust 1.98.1 and wasm-tools
mise run install      # builds morphir-python-native into .venv with Maturin
mise run check        # Python checks
mise run rust:check   # Rust format, lint and tests
```

To build only the native wheel, run
`uvx --from maturin==1.15.0 maturin build --release` in
`packages/morphir-python-native`. Its source archive contains the whole Rust
workspace it needs, so `pip install morphir_python_native-*.tar.gz` works without
a checkout when Rust is on `PATH`.

## Handle a model error

This example reports `PY004 error rules.py` for unsupported assignment.

<!-- example: examples/diagnostics.py -->
```python
"""Handle an unsupported model without exceptions or partial output."""

from morphir_tools.python import CompileFailure, SourceDocument, compile_sources

result = compile_sources(
    [SourceDocument("rules.py", "answer = 42\n")], package="acme/example"
)
assert isinstance(result, CompileFailure)
diagnostic = result.diagnostics[0]
assert diagnostic.code == "PY004"
assert diagnostic.source is not None
assert diagnostic.source.path == "rules.py"
print(diagnostic.code, diagnostic.severity.value, diagnostic.source.path)
```
<!-- /example -->
