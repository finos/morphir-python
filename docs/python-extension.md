# The morphir-python Morphir extension

The `morphir-python` extension lets a Morphir host, such as the Rust `morphir`
CLI, compile Python with `morphir compile --language python` and generate Python
with `morphir generate --target python`. It is the
[`morphir-python-binding`](../rust/crates/morphir-python-binding/README.md)
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

Extension `0.4.2` pairs with `morphir-python==0.0.4` and
`morphir-python-native==0.1.1`. The native API reports compiler version `0.4.2`.
Use `0.4.2` or later with hosts that require an explicit multi-document claim;
`0.4.1` omits that claim.

The declaration is in [`rust/extension.toml`](../rust/extension.toml).

## Install a release bundle

A release contains the WASM guest, its `.sha256` file and a version-2 release
descriptor. Publishing it needs Morphir CLI `0.4.0-beta.7` or later. Rename the
descriptor to `release.json` before you publish it:

```console
gh release download extension/python/v<version> --repo finos/morphir-python --dir python-bundle
mv python-bundle/morphir-python-binding-<version>.release.json python-bundle/release.json
morphir extension repository init .morphir/python-index
morphir extension repository add python-local --directory .morphir/python-index
morphir extension repository publish python-local --bundle python-bundle
morphir extension repository verify python-local
morphir extension install --repository python-local morphir-python
```

Installation verifies the WASM digest and records its capability claims. The CLI
shows WASM claims as `unchecked`: it records the claims the guest declared and
does not probe them. After installation, compilation and generation work
offline.

## Compile and generate

Create a project with `src/acme/models.py` and `src/acme/rules.py` (see the
[Python compiler guide](python-compiler.md#use-the-python-api) for supported
Python) and this `morphir.toml`:

```toml
[project]
name = "acme/example"
version = "0.1.0"
source_directory = "src"

[frontend]
language = "python"
emit_parse_stage = false
```

Then run:

```console
morphir compile --language python --input src --ir-version 3.0.0 --output compiled
morphir generate --target python --input compiled/morphir-ir.json --output generated
```

Omit `--ir-version`, or use `4`, for draft IR v4.

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
