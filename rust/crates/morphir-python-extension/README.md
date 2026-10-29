# Morphir Python process guest

This crate runs the shared Python compiler as a native MEP process. It has no
CPython or PyO3 dependency, and the executable needs no user Rust toolchain.
Source is parsed statically and is never imported or executed.

Development build and entry point:

```bash
cargo build --manifest-path rust/Cargo.toml --release -p morphir-python-extension
./rust/target/release/morphir-python-extension --stdio
```

With no arguments the executable also serves stdio, matching the canonical
native bundler and installed process launcher. `--stdio` is an explicit alias;
`--help` prints usage and exits.

In stdio mode stdout contains only Content-Length-framed UTF-8 JSON-RPC.
Headers are bounded to 8 KiB and complete bodies to 16 MiB. Lengths count bytes;
unknown headers are ignored and duplicate lengths are refused. A damaged frame
ends the connection. Invalid JSON in an otherwise valid frame gets a parse-error
response and the next framed request can recover. Notifications get no response;
`morphir.exit` ends the process. Each process owns its SDK protocol session.

The host owns deadlines and process cleanup. A native process has ordinary OS
rights; choosing it does not provide a WASM sandbox.

The current development build advertises legacy MEP 0.1. Exact-draft discovery
and model transport wait for the qualified published SDK prerequisite and
conformance checks. Platform archives and installation recipes are still under
development. The retained WASM release remains the qualified installation route.

## Stage a development bundle

From a clean candidate checkout, build the release executable and run the pinned
Morphir CLI's native bundler through the packaging helper:

```bash
python -m scripts.process_extension \
  --executable rust/target/release/morphir-python-extension \
  --output .dev/process-bundle \
  --commit "$(git rev-parse HEAD)" \
  --report .dev/qualification/process-package.json \
  --host-check
```

On Windows the executable path ends in `.exe`. The helper selects an explicit
supported target, verifies the pinned CLI archive and stages a versioned raw
executable, its checksum and canonical `release.json`. It records the canonical
default argument list, explicit `--stdio` alias, executable mode, source commit,
Cargo lock digest, bundler identity, exact artifact bytes and live claims in the
separate report. Receipts are not additional members of the canonical bundle.

`--host-check` requires the development Python environment with the matching
native compiler. It publishes into a temporary local repository, installs into
an isolated Morphir home, deletes the repository and runs offline v3/v4
compile/generate/recompile comparisons against the Python API. This legacy route
check does not qualify the new MEP draft. Platform release builds, new-draft
qualification and promotion gates remain in progress.
