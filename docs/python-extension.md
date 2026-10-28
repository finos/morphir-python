# The morphir-python Morphir extension

The `morphir-python` extension lets a Morphir host, such as the Rust `morphir`
CLI, compile Python with `morphir compile --language python` and generate Python
with `morphir generate --target python`. It is the
[`morphir-python-binding`](https://github.com/finos/morphir-python/blob/main/rust/crates/morphir-python-binding/README.md)
compiler built as a WebAssembly guest that speaks the Morphir extension protocol
(MEP). It is the same compiler that the `morphir-python` Python package runs
natively, so both give the same IR and the same diagnostic codes.

This repository builds and releases the extension. Bundles up to
`extension/python/v0.4.0` were released from
[finos/morphir-rust](https://github.com/finos/morphir-rust/releases) and remain
available there.

| Identity | Value |
| --- | --- |
| Extension ID | `morphir-python` |
| Short ID and release tag | `python`, `extension/python/v<version>` |
| Language | `python` (`.py`) |
| Target | `python` |
| IR versions | `3`, `4` |
| MEP version | `0.1` |
| Multiple source documents | `multiDocument: true`, from `0.4.2` |

Extension `0.4.2` pairs with `morphir-python==0.1.0` and
`morphir-python-native==0.1.1`, qualified with `morphir==0.1.0`.
The native API reports compiler version `0.4.2`.
Use `0.4.2` or later with hosts that require an explicit multi-document claim;
`0.4.1` omits that claim.

The declaration is in [`rust/extension.toml`](https://github.com/finos/morphir-python/blob/main/rust/extension.toml).

## Install the qualified release bundle

This recipe uses **finos/morphir 0.4.0-beta.10** and Python extension **0.4.1**.
Use the Rust product CLI, not the MoonBit executable of the same name. The
[compatibility guide](compatibility.md) explains the difference. CPython is not
needed to run the installed WASM guest.

For a reproducible setup from this checkout, `python3 scripts/docs_hosts.py
prepare` downloads the pinned CLI and bundle, verifies the release archive and
both bundle file SHA-256 digests, renames the descriptor to `release.json`, and
prints the absolute `MORPHIR_HOST` and `PYTHON_BUNDLE` paths. Pins live in
[site/integrations.json](https://github.com/finos/morphir-python/blob/main/site/integrations.json)
and [rust/extension.toml](https://github.com/finos/morphir-python/blob/main/rust/extension.toml).
Run the printed `--version` command and check it reports 0.4.0-beta.10.

For manual acquisition, download the 0.4.1 `.wasm`, `.wasm.sha256` and `.release.json` assets
from the [extension release](https://github.com/finos/morphir-python/releases/tag/extension/python/v0.4.1).
Verify the SHA-256 values in the pin file before using them, then rename the
`.release.json` descriptor to `release.json` in the same bundle directory.
The WASM digest is
`a04722e16115667fc7c332177805dcb049aef563afcee0e5f80c5fea302f5b4e`.
The descriptor digest is
`6cebee18b70e75da90f1cd187f24c8185ddde2565bb7c8e5049e21bbcccf0bb3`.
The host release has platform-specific archives; use the declared target and
hash rather than an unversioned executable from PATH.

## Install, discover and invoke

Use a fresh project directory with the `src/acme/` model files from the
[quickstart](quickstart.md), then set `MORPHIR_HOST` and `PYTHON_BUNDLE` to those
verified absolute paths. This POSIX-shell recipe creates an isolated Morphir
home, publishes to a local index, installs the bundle and checks discovery
before compiling. It is the exact recipe run by documentation qualification.

<!-- example: examples/extension.sh -->
```bash
#!/usr/bin/env bash
set -euo pipefail
# MORPHIR_HOST is the verified finos/morphir 0.4.0-beta.10 executable.
# PYTHON_BUNDLE is the verified 0.4.1 bundle directory containing release.json.
: "${MORPHIR_HOST:?Set the verified Rust-host executable path}"
: "${PYTHON_BUNDLE:?Set the verified bundle directory}"
"$MORPHIR_HOST" --version
export MORPHIR_HOME="$PWD/.morphir-home"
"$MORPHIR_HOST" extension repository init .morphir/python-index
"$MORPHIR_HOST" extension repository add python-local --directory .morphir/python-index
"$MORPHIR_HOST" extension repository publish python-local --bundle "$PYTHON_BUNDLE"
"$MORPHIR_HOST" extension repository verify python-local
"$MORPHIR_HOST" extension install --repository python-local morphir-python
"$MORPHIR_HOST" extension list
cat > morphir.toml <<'TOML'
[project]
name = "acme/example"
version = "0.1.0"
source_directory = "src"

[frontend]
language = "python"
emit_parse_stage = false
TOML
"$MORPHIR_HOST" compile --language python --input src --ir-version 3.0.0 --output compiled
"$MORPHIR_HOST" generate --target python --input compiled/morphir-ir.json --output host-generated
"$MORPHIR_HOST" compile --language python --input host-generated --ir-version 3.0.0 --output host-rebuilt
```
<!-- /example -->

The installed extension supplies the `python` frontend and target. Compilation
writes `compiled/morphir-ir.json`; generation writes the two modules beneath
`host-generated/acme/`. Recompilation checks equivalent IR. For this CLI,
omitting `--ir-version`, or selecting `4`, requests draft v4. The Python CLI
instead defaults to v3, so recipes state the version explicitly.

Installation records capability claims as `unchecked`; the runtime compile and
generate checks provide execution evidence. The existing bundle qualifier also
removes the local index, blocks network access and repeats v3/v4 round trips.
Use `python3 scripts/docs_hosts.py qualify` to repeat the displayed workflow and
offline checks. Receipts record pins, file hashes, host identity, checker and
input digest. Download failure never counts as a passing qualification.

## Build a development bundle

From the repository root:

```console
mise install
mise run install
mise run extension:bundle
```

This task:

1. builds the release WASM guest and validates it with `wasm-tools`;
2. packages it with finos/morphir-rust's canonical WASM packager
   (`scripts/package_extension.py`), run unchanged at the revision pinned in
   `rust/extension.toml`, so the bundle has the same descriptor format as
   earlier releases. The finos/morphir `morphir extension bundle` command packages
   native process extensions only;
3. downloads the Morphir CLI version pinned in `rust/extension.toml`, checks its
   SHA-256 digest, publishes and installs the bundle into a new Morphir home,
   deletes the repository, blocks network access, and compiles, generates and
   recompiles a two-module model in IR v3 and v4;
4. checks that the IR from the extension equals the IR from the Python API for
   the same sources.

The bundle is written to `.morphir/build/extensions/python/`, and JSON receipts
with every digest are written to `.dev/qualification/`. A bundle built from a
clean checkout records its commit as `gitCommit`; a bundle from a modified
checkout does not.

CI runs this task when the compiler, the declaration or the bundle tooling
changes, and uploads the bundle as `morphir-python-extension-bundle`.
