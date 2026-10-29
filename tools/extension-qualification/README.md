# Source-pinned Rust host qualification

This developer-only executable exercises the actual WASM and native process
guest bytes through `morphir-host` and `morphir-host-native` at
`d51daa8aea7ae09ae295ff254d72b27770c64104`. It uses the upstream Extism and
process channels directly. Process launches have an empty environment and do
not use Python or a Rust launcher.

The Git dependencies are isolated in this tool's Cargo workspace. The compiler
and Python packages continue to depend on published crates. A source-built host
does not remove the compiler's published SDK prerequisite.

Build once, then supply the exact candidate artifacts:

```bash
cargo build --locked --release --manifest-path tools/extension-qualification/Cargo.toml \
  --target-dir .dev/host-qualification-target

.dev/host-qualification-target/release/morphir-python-host-qualification \
  path/to/guest.wasm path/to/morphir-python-extension \
  .dev/qualification/rust-host.json
```

The checker owns temporary copies, verifies their hashes, and restores only
the process copy's executable permission if artifact transfer removed it. It
initializes each runtime using legacy MEP `0.1`, then checks IR v3/v4 compilation,
generation, recompilation, unsupported-source diagnostics, matching results,
and orderly shutdown. The process route must leave no running child, unread
stdout, or stderr. An actual guest request with a 1 ms host deadline must fail
with a timeout and leave the child reaped. The timeout can occur during
initialization or during the intentionally large compile request.

The JSON result binds the checker binary, artifacts, inputs, Rust toolchain and
host revision. This legacy interoperability check is separate from the pinned
executable MCK guest suite. It cannot establish the newer MEP draft, negotiated
model transport, canonical conformance, installed-byte integrity or platform
coverage. Those have their own required checks.

## Repeat timing observations

```bash
python3 -m scripts.benchmark_extension \
  --checker .dev/host-qualification-target/release/morphir-python-host-qualification \
  --wasm path/to/guest.wasm --process path/to/morphir-python-extension \
  --output .dev/qualification/runtime-timings --samples 5
```

The destination must be new. The runner retains both Python inputs, every raw
checker result and log, hashes, the machine description, and nanosecond samples
with min/median/max in `timings.json`. Workloads contain one record/one function
and 200 records/100 typed conditional functions. Alphabetic identifiers fit
both supported IR naming formats. Every sample still verifies semantic and
diagnostic parity and process cleanup.

Each sample starts a fresh checker process and fresh guests. Guest startup
includes initialization and, for WASM, module compilation. OS caches are not
cleared. Operations run in a fixed session order: v3 types, v3 values, v4 types,
v4 values. Later operations reuse the guest session. WASM runs before process,
so the report records that order and makes no general speed claim. Whole-checker
wall time includes both runtimes, validation, timeout cleanup and report I/O;
it is not a per-runtime startup measurement.

The checker also accepts two optional source paths after `REPORT`, for the
type-only and type/value cases respectively. The benchmark uses these to keep
the measured inputs reproducible. Inputs must compile and roundtrip in both
advertised IR versions.

## Bridge the real WASM guest to the shared MCK

The same build produces `mep_wasm_host`, a transport adapter for the upstream
`morphir mck mep guest-run` executable. It forwards request bodies unchanged to
the actual Extism guest's `handle` export and returns its exact response bytes.
The adapter contains no conformance expectations or adjudication logic.

```bash
"$MCK" --no-banner mck mep guest-run --kit "$PYTHON_JSON_KIT" \
  --host "$PWD/.dev/host-qualification-target/release/mep_wasm_host" \
  --host-arg "$WASM_GUEST" --identity-file "$WASM_GUEST" \
  --identity-file "$PWD/rust/Cargo.lock" \
  --identity-file "$PWD/tools/extension-qualification/Cargo.lock" \
  --identity-file "$PWD/tools/extension-qualification/src/bin/mep_wasm_host.rs" \
  --report "$PWD/.dev/qualification/mck-wasm.json"
"$MCK" --no-banner mck mep report-check --kit "$PYTHON_JSON_KIT" \
  "$PWD/.dev/qualification/mck-wasm.json"
```

Use an explicitly pinned shared MCK source/binary and its matching
`python-json-library-v1` kit. Supply absolute guest paths. Process qualification
can pass the raw executable directly as `--host`, without this adapter.
The saved report records the actual host executable, arguments, guest bytes,
checker, corpus, identities and observations. Its canonical recheck requires
the same checker and all recorded identity paths while they are available.

The release producers automate this through `scripts.mep_tool` and
`scripts.qualify_mep`. Each producer rechecks its saved report locally before
uploading it. The Linux collector verifies the source/artifact/report identities
and successful producer receipt from the same workflow run; it does not rewrite
foreign filesystem paths or claim to re-run their filesystem recheck. See the
[release contract](../../docs/releasing.md#qualify-both-extension-runtimes).

Extism exposes a requests-only `handle` ABI. As in the pinned upstream
`ExtismChannel`, notifications are not forwarded; an exit notification closes
the bridge and unloads the guest. Those lifecycle observations qualify this
adapter/guest pair, rather than claiming guest notification delivery. Process
session tests exercise actual native guest notification handling separately.
