# Proposal

## Why

Every Morphir extension must be on the latest MEP, `0.2.0-draft.1`. The Python extension `0.5.0` already declares it, with `0.1` kept, and serves `morphir.frontend.compileModel` and `morphir.backend.generateModel` for the tuples `morphir-ir` / `morphir-json` / envelope `0.1.0-draft.1` / IR `3.0.0` and `4.0.0`. Three gaps remain. No test shows the guest agreeing on JSON when the host's default is Ion but the host also offers JSON (the negotiation rule that finos/morphir-gleam#31 tests). The model operations have no golden outputs. The MoonBit worker host (finos/morphir-moonbit `main`) qualified Python `0.4.1` and `0.4.2` on MEP `0.1` only, not the model line.

## What Changes

- Add session tests: host that prefers Ion but also offers JSON; host that offers only Ion; compile admission that does not grant generation; wrong envelope version in each direction; the process executable serving both model operations and stopping by itself.
- Add golden outputs for `compileModel` (envelope and exact payload bytes) and `generateModel` (artifacts) for IR `3.0.0` and `4.0.0`, through a real negotiated session.
- Add the host-default scenario to `python/model-transport`.
- Qualify the candidate on the MoonBit worker host from the native and npm CLIs: `extension describe`, `compile` and `generate` on the model line with a contract `0.2.0` pin, recompile of generated sources, and worker shutdown. Repeat the existing `0.1`-only suite for `0.4.1` and `0.4.2`.
- Release `extension/python/v0.6.0` with the current dependencies (Ruff `0.0.20`). No protocol, claim or tuple changes. No Ion.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `python/model-transport`: the admission requirement gains a scenario for a host whose default format the guest does not serve.

## Beads

- **Tracked by**: `morphir-ukvn.1.6.9`
- **Related**: `morphir-5hxy` (delivered the model line in `0.5.0`); `morphir-1q2c` (MEP spec: model-format default and required rule); `morphir-hv6m` (MCK check of model-format selection order); `morphir-ukvn.5.64.36.7` (MoonBit worker host qualification of published extensions).

## Impact

Tests and golden files in `rust/crates/morphir-python-binding` and `rust/crates/morphir-python-extension`, the compiler crate version (`0.6.0`), `.gitattributes` and pre-commit excludes for byte-exact golden files, and the extension documentation after release. finos/morphir keeps its `extension/python/v0.4.2` pin; its bundle pins move in a separate PR. Merge and tag need maintainer approval.

## Delivery close-out

PR #80 merged as `560a6503b8ffcab87ea667391579b747757bec0d` and extension 0.6.0 was published on 2026-11-01. The successful manual dry run and published WASM have the same digest, so the recorded 32-row MoonBit run applies to the same module bytes. This is evidence reuse, not a new post-release run or qualification of every published process executable.

The close-out adds a separate 0.6.0 release page and digest pins while preserving the byte-bound 0.5.0 host recipe. It syncs the negotiation scenarios against the later 0.6.2 decision to refuse retired MEP 0.1, without changing historical releases. The release workflow did not produce the attestations anticipated in the original plan; future signed provenance is tracked in [#89](https://github.com/finos/morphir-python/issues/89). Shared Beads reconciliation is blocked by its existing merge conflict and tracked in [#90](https://github.com/finos/morphir-python/issues/90). Archival records this delivered scope and these explicit follow-ups.
