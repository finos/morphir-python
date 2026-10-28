# Install Morphir Python

Use CPython 3.14. For command-line use, mise manages the interpreter and an
isolated CLI environment for you. For Python application development, install
the packages into your application's environment.

## Install the CLI with mise

With [mise](https://mise.jdx.dev/getting-started.html) installed, copy this into
your project's `mise.toml`:

<!-- example: examples/install/mise-uv.toml -->
```toml
[tools]
python = "3.14"
uv = "0.12.10"
"pypi:morphir-python" = { version = "0.1.0", uvx_args = "--no-build" }
```
<!-- /example -->

Then run:

```bash
mise trust
mise install
mise exec -- morphir-python --help
```

This uses mise's `pypi:` backend with uv, installs the published package from
PyPI, and exposes `morphir-python`. `--no-build` refuses source distributions:
the native compiler must have a compatible wheel, so installation never needs
a Rust toolchain. This does not install from a GitHub source checkout or a
standalone executable archive. GitHub Releases also retain the CLI wheel and
source archive; see [the release process](releasing.md).

To use actual pipx instead of uv, use this alternative `mise.toml`:

<!-- example: examples/install/mise-pipx.toml -->
```toml
[tools]
python = "3.14"
pipx = "1.18.4"
"pipx:morphir-python" = { version = "0.1.0", python = "3.14", uvx = false, pipx_args = "--pip-args='--only-binary=:all:'" }
```
<!-- /example -->

Run the same three commands above. `uvx = false` selects pipx, `python = "3.14"`
on the tool selects its interpreter, and `--only-binary=:all:` enforces the same
wheel-only policy. Choose one configuration. `pipx:` and `pypi:` are accepted
backend names, but mise treats them as separate installed tools. The
[mise backend documentation](https://mise.jdx.dev/dev-tools/backends/pypi.html)
explains these options.

For a global installation, put the chosen entries in your global mise
configuration, normally `~/.config/mise/config.toml` on macOS/Linux, then run
`mise install`. `mise config ls` shows the configuration files in use. With mise shell
activation enabled, run `morphir-python` directly. Without shell activation,
`mise exec -- morphir-python ...` works from a directory using the configuration.
The CLI's environment is separate from your project's Python dependencies.

The examples require mise 2026.10.20 or later. The versions are intentionally
pinned; update the CLI version when adopting another release. Pinning the CLI
does not freeze every transitive dependency. The version-only examples use the
installer flags above; they do not claim a fully locked dependency graph.

## Install Python packages

Choose a package according to what your application needs.

| Package | Install for | What it installs |
| --- | --- | --- |
| `morphir` | IR models, codecs, migration and SDK functions | No third-party runtime dependencies |
| `morphir-python` | The CLI and `morphir_tools.python` compiler API | `morphir`, Typer and an exact compatible native compiler |
| `morphir-python-native` | Compiler implementation dependency | Installed automatically by `morphir-python` |

The released quickstarts use `morphir-python==0.1.0`, `morphir==0.1.0` and
`morphir-python-native==0.1.1`. The core and CLI have independent versions.

```bash
python3.14 -m venv .venv
. .venv/bin/activate
python -m pip install --only-binary=:all: morphir==0.1.0 morphir-python==0.1.0
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
python -m pip install morphir==0.1.0
```

The [IR and SDK examples](library.md) work without the native compiler. Installing
the library does not install the CLI. The SDK functions are normal Python
functions; the compiler accepts a narrower [source subset](python-compiler.md#supported-python).

## Released and development examples

The site tracks the repository's main branch. Examples labeled **Released** run
against the exact qualified packages above. IR v4 remains a draft upstream.
Core 0.1.0 includes the compact canonical v4 writer and the explicit `Spelling`
option. Examples labeled **Development** require wheels built from the source
revision under test; their manifest and receipts identify those prerequisites.

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

For mise, check `mise which morphir-python` and run with `mise exec --` if the
command is absent from your shell. If its managed interpreter was removed or
replaced, reinstall with `mise install --force pypi:morphir-python` or the
`pipx:` name you configured. A wheel-only refusal is an explicit unsupported
environment, not an instruction to install Rust.
