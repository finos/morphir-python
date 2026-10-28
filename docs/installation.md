# Install Morphir Python

Use CPython 3.14. Choose a package according to what your application needs.

| Package | Install for | What it installs |
| --- | --- | --- |
| `morphir` | IR models, codecs, migration and SDK functions | No third-party runtime dependencies |
| `morphir-python` | The CLI and `morphir_tools.python` compiler API | `morphir`, Typer and an exact compatible native compiler |
| `morphir-python-native` | Compiler implementation dependency | Installed automatically by `morphir-python` |

The released quickstarts use `morphir-python==0.0.3`, `morphir==0.0.2` and
`morphir-python-native==0.1.0`. The core and CLI have independent versions.

```bash
python3.14 -m venv .venv
. .venv/bin/activate
python -m pip install --only-binary=:all: morphir==0.0.2 morphir-python==0.0.3
morphir-python --help
```

On Windows, activate with `.venv\Scripts\Activate.ps1` in PowerShell.
The `--only-binary` option makes a missing wheel fail explicitly instead of
attempting to build Rust. You do not need a Rust toolchain for these wheels.
See the [CLI quickstart](quickstart.md) next.

## Supported compiler wheels

The native compiler uses the CPython 3.14 stable ABI. Qualified wheels cover
Linux x86_64 and aarch64 with glibc 2.28 or later, macOS arm64 on 11 or later,
macOS x86_64 on 10.12 or later, and Windows x86_64. Free-threaded CPython and
other platforms are unqualified. A source installation on another platform
requires Rust 1.98 or later and is distinct from the wheel-only quickstart.

## Use only the library

```bash
python -m pip install morphir==0.0.2
```

The [IR and SDK examples](library.md) work without the native compiler. Installing
the library does not install the CLI. The SDK functions are normal Python
functions; the compiler accepts a narrower [source subset](python-compiler.md#supported-python).

## Released and development examples

The site tracks the repository's main branch. Examples labeled **Released** run
against the pinned published packages. Examples labeled **Development** require
wheels built from the source revision under test. In particular, the current
compact-v4 writer and `Spelling` option are development features after core
0.0.2. IR v4 remains a draft upstream even when its codec is released.

For a development installation, follow [build from source](python-compiler.md#build-from-source).
Keep the CLI/native pair together. An incompatible private bridge raises
`NativeCompilerUnavailable`; reinstall the CLI and its dependencies rather than
importing or calling the private native module directly.

## Troubleshoot installation

If pip reports no matching wheel, check Python version, architecture, libc and
whether the interpreter is free-threaded. If `morphir-python` cannot be found,
activate the environment and check its `bin` or `Scripts` directory. A model error
such as `PY004` is a compiler diagnostic; reinstalling packages will not make
unsupported syntax compile.
