# The morphir-python Morphir extension

The `morphir-python` extension lets a Morphir host, such as the Rust `morphir`
CLI, compile Python with `morphir compile --language python` and generate Python
with `morphir generate --target python`. It is the
[`morphir-python-binding`](https://github.com/finos/morphir-python/blob/main/rust/crates/morphir-python-binding/README.md)
compiler built as a WebAssembly guest or a standalone process speaking the
Morphir extension protocol (MEP). It is the same compiler that the Python package runs
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
| Published 0.5.0 MEP versions | `0.2.0-draft.1`, `0.1` |
| Multiple source documents | `multiDocument: true`, from `0.4.2` |

Extension `0.5.0` pairs with `morphir-python==0.1.2` and
`morphir-python-native==0.1.2`, using published Rust SDK `0.4.0`.
The bridge API remains revision `1`; core `morphir==0.1.1` includes the updated
documentation metadata.

Historical extension `0.4.2` pairs with `morphir-python==0.1.0`,
`morphir-python-native==0.1.1` and `morphir==0.1.0`; its compiler version is
`0.4.2`. Use `0.4.2` or later with hosts that require an explicit multi-document
claim; `0.4.1` omits that claim.

## Model protocol in release 0.5.0

Package, protocol, envelope, claims and IR versions identify different contracts:

| Contract | Value |
| --- | --- |
| Compiler / extension package | `0.5.0` |
| Rust extension SDK dependency | exactly `0.4.0` from crates.io |
| MEP offers | exact `0.2.0-draft.1` and legacy `0.1` |
| Model envelope | exact `0.1.0-draft.1` |
| Claim set | `0.1.0-draft.2` |
| Model profile / codec | `morphir-ir` / `morphir-json` |
| Semantic IR | `3.0.0` or `4.0.0`, Library distributions |

The host must offer complete operation/profile/codec/envelope/IR tuples through
`modelTransport` during initialization. The guest selects only their intersection
and the lower value of each limit. Both `morphir.frontend.compileModel` and
`morphir.backend.generateModel` support each stated IR version. The static limits
are 12 MiB encoded content, 8 MiB decoded content, depth 128 and 100,000 nodes.
Session capabilities remain fixed after initialization. Legacy sessions use
`compile`/`generate` and cannot call model methods. Other MEP drafts do not match.

Numeric and string request IDs retain their type and value. Unsupported Ion
profiles or evidence, required guarantees, and Specs/Application generation are
refused explicitly. No rich-model preservation or automatic codec fallback is
advertised.

The shared executable MCK's separate `python-json-library-v1` profile qualifies
the supported JSON subset. Its fixed expectations and existing MoonBit rich-Ion
profile remain independent. WASM qualification uses the pinned Rust Extism host
adapter; raw request and response bodies pass unchanged to the guest. This ABI
handles requests only, so notification silence and exit describe the adapter and
guest route, not notification delivery inside the WASM guest.

The declaration is in [`rust/extension.toml`](https://github.com/finos/morphir-python/blob/main/rust/extension.toml).
The released host recipe below uses legacy MEP `0.1`. For new-draft protocol
checks, use the [source-pinned MCK](releasing.md#qualify-both-extension-runtimes)
recorded in the release evidence.

## Install the qualified release bundle

This recipe uses **finos/morphir 0.4.0-beta.10** and Python extension **0.5.0**.
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

For manual acquisition, download the 0.5.0 `.wasm`, `.wasm.sha256` and `.release.json` assets
from the [extension release](https://github.com/finos/morphir-python/releases/tag/extension/python/v0.5.0).
Verify the SHA-256 values in the pin file before using them, then rename the
`.release.json` descriptor to `release.json` in the same bundle directory.
The WASM digest is
`791d6cc60f442b1088b291e9aed4f2740a38b0f0cc920f5f7418735c2b88aeb6`.
The descriptor digest is
`a78df591623388a95f3f7f8f7465422cee3dd4f6d86a64224d2a02291d8a81b3`.
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
# PYTHON_BUNDLE is the verified 0.5.0 bundle directory containing release.json.
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

## Download and choose a runtime

Release `0.5.0` provides both WASM and process bundles on
[GitHub Releases](https://github.com/finos/morphir-python/releases/tag/extension/python/v0.5.0).
The process executable is a MEP guest for the finos/morphir host. The
`morphir-python` CLI continues to use its pinned native Python wheel through the
[mise/pipx installation](python-compiler.md); choosing an extension runtime does
not configure that CLI.

Use two separate canonical bundle directories and named local repositories.
The WASM bundle contains its `.wasm`, checksum and `release.json`. The process
bundle contains the raw executables, their checksums and its own `release.json`.
The canonical repository writer refuses a bundle mixing both runtimes.
The process bundle includes Linux x86_64/ARM64, macOS x86_64/ARM64 and Windows
x86_64. Installation chooses the matching platform and refuses an absent one.

The release includes five raw executables and checksums, a separately named
process descriptor, `morphir-python-extension-VERSION.tar.gz`, source-bound
qualification receipts and `SHA256SUMS`. The archive contains the complete
canonical process bundle, with `release.json` and executable permissions. Its
payloads match the raw assets. Raw MCK reports, their saved rechecks, runtime
switching evidence and host timing samples are retained alongside the bundles.

With the [GitHub CLI](https://cli.github.com/) installed, run this in a fresh
directory using Bash, `shasum` and `tar`. Download all assets before checking
`SHA256SUMS`; it covers the qualification evidence as well as the bundles.

<!-- example: examples/install/extension-bundles.sh -->
```bash
#!/usr/bin/env bash
set -euo pipefail
VERSION=0.5.0
gh release download "extension/python/v$VERSION" \
  --repo finos/morphir-python --dir python-extension-assets
(cd python-extension-assets && shasum -a 256 -c SHA256SUMS)
mkdir python-wasm python-process
cp "python-extension-assets/morphir-python-binding-$VERSION.wasm" \
  "python-extension-assets/morphir-python-binding-$VERSION.wasm.sha256" python-wasm/
cp "python-extension-assets/morphir-python-binding-$VERSION.release.json" \
  python-wasm/release.json
tar -xzf "python-extension-assets/morphir-python-extension-$VERSION.tar.gz" \
  -C python-process
export WASM_BUNDLE="$(cd python-wasm && pwd)"
export PROCESS_BUNDLE="$(cd python-process && pwd)"
```
<!-- /example -->

The qualification workflow runs installation and runtime-switching checks
against this extracted archive. Both directories above contain version `0.5.0`.
Historical `0.4.2` bundles remain available from their original release.

Set `WASM_BUNDLE` and `PROCESS_BUNDLE` to those unmodified directories. With
`MORPHIR_HOST` pointing at the pinned host described above, an isolated trial is:

```bash
export MORPHIR_HOME="$(mktemp -d)"
VERSION=0.5.0
"$MORPHIR_HOST" extension repository init ./wasm-repository
"$MORPHIR_HOST" extension repository init ./process-repository
"$MORPHIR_HOST" extension repository add python-wasm --directory ./wasm-repository
"$MORPHIR_HOST" extension repository add python-process --directory ./process-repository
"$MORPHIR_HOST" extension repository publish python-wasm --bundle "$WASM_BUNDLE"
"$MORPHIR_HOST" extension repository publish python-process --bundle "$PROCESS_BUNDLE"
"$MORPHIR_HOST" extension install morphir-python --repository python-wasm --version "$VERSION"

# Switch the active provider in this isolated Morphir home.
"$MORPHIR_HOST" extension uninstall morphir-python
"$MORPHIR_HOST" extension install morphir-python --repository python-process --version "$VERSION"
```

The repository selects the runtime; this host has no `--runtime` installation
flag. It permits one active `morphir-python` provider per home. Uninstall it
before installing the other runtime from its explicit repository. Compile and
generate commands remain the same. The process guest starts in stdio mode with
no arguments; `--stdio` is also accepted by hosts configured to pass it.
Installation restores executable permissions, so the Morphir host can launch a
downloaded raw executable without a user Rust toolchain or Python interpreter.
A process has ordinary OS rights; WASM uses the host's Extism isolation.

The developer [Rust host checker](https://github.com/finos/morphir-python/tree/main/tools/extension-qualification)
pins the upstream host source and tests actual WASM/process bytes independently
of the installation recipe. It verifies legacy v3/v4 operations, diagnostic
parity, orderly shutdown and process timeout cleanup. Its timing runner retains
fresh-guest startup and compile/generate samples for small and larger inputs,
including the machine, build profile, input and artifact identities. These
observations do not establish newer-draft conformance or a general speed claim.

The release-assembly check runs this switch in both directions with fresh
project caches, compares v3/v4 IR and generated-file digests, rejects an actual
foreign-only bundle, and checks that changing installed bytes causes a digest
refusal before compilation. Each platform's own bundle qualifier also checks
installed-byte integrity. These are legacy-route checks. The separate executable
MCK qualification covers the new MEP draft and its model operations. Promotion
must retain and verify both kinds of evidence for the candidate being released.

To verify already built candidates without rebuilding them:

```bash
python -m scripts.qualify_runtime --wasm "$WASM_BUNDLE" \
  --process "$PROCESS_BUNDLE" --report .dev/qualification/runtime-choice.json
```

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
   the same sources;
5. requires digest refusal when installed bytes are changed in a fresh project,
   then restores the original artifact.

The bundle is written to `.morphir/build/extensions/python/`, and JSON receipts
with every digest are written to `.dev/qualification/`. A bundle built from a
clean checkout records its commit as `gitCommit`; a bundle from a modified
checkout does not.

CI runs this task when the compiler, the declaration or the bundle tooling
changes, and uploads the bundle as `morphir-python-extension-bundle`.
