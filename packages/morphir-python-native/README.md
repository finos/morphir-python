# morphir-python-native

Read the [documentation site](https://finos.github.io/morphir-python/) for
[installation](https://finos.github.io/morphir-python/docs/installation/),
[API examples](https://finos.github.io/morphir-python/docs/python-compiler/) and
[CLI workflows](https://finos.github.io/morphir-python/docs/quickstart/).

The native compiler behind the `morphir-python` tools. It contains a private
CPython extension module built from the Rust `morphir-python-binding` compiler
with [PyO3](https://pyo3.rs) and [Maturin](https://www.maturin.rs).

Do not import this package directly. Install `morphir-python` and use the typed
API in `morphir_tools.python` or the `morphir-python compile` and
`morphir-python generate` commands. Each `morphir-python` release requires one
exact version of this distribution and checks it before first use.

Wheels need no Rust toolchain. Building from the source archive needs Rust 1.98
or later; see the [repository guide](https://github.com/finos/morphir-python/blob/main/docs/python-compiler.md).
