# Proposal

## Why

The Python compiler currently exposes a WASM MEP guest advertising legacy `0.1`, while the canonical upstream contract is `0.2.0-draft.1`. Users need a process alternative sharing the compiler and an explicit path to the newer contract, rather than a transport change that leaves its model methods unsupported.

## What Changes

- Add a native Rust `morphir-python-extension --stdio` guest around the existing compiler and SDK session endpoint, without a Python runtime dependency.
- Preserve the WASM guest, extension identity, source subset, diagnostics and legacy `0.1` operations.
- Add exact `0.2.0-draft.1` negotiation and bilateral model transport admission, initially for the `morphir-ir`/`morphir-json` profile with the compiler's supported IR v3/v4 Library models.
- Implement bounded, integrity-checked model envelopes and compileModel/generateModel adapters for the admitted tuples. Refuse unsupported profiles and guarantees explicitly; rich Ion transport is not advertised by this initial increment.
- Publish and qualify both runtime choices, with accurate platform/runtime descriptors and host compatibility documentation. Qualify each documented host route independently.

## Capabilities

### New Capabilities

- `python/model-transport`: New-draft negotiation, complete model tuples, envelope integrity and Python compiler adapters with explicit unsupported-profile refusals.

### Modified Capabilities

- `python/extension`: Shared WASM/process compiler behavior, bounded process sessions and qualified dual-runtime distribution.

## Beads

- **Tracked by**: `morphir-5hxy`
- **Prerequisites**: `morphir-4wrx` (published SDK0.4.0, completed), `morphir-av8s` (approved separate upstream Python JSON executable MCK profile, finos/morphir#1109).
- **Related**: `morphir-bj9r` (mise/pipx CLI installation and release assurance), `morphir-ukvn.5.98` (MoonBit Extism qualification context).

## Impact

A qualified published SDK pin covering canonical numeric/string wire IDs, Rust compiler adapters and a process guest entry point, extension metadata/claims, platform release packaging, MEP conformance fixtures and host documentation. The canonical reference is finos/morphir `c552dac801f23f2b2b566d29e08780723498ce36`, `spec/mep/README.md` and `model-transport.md`. Package, protocol, model envelope and IR versions remain independent. A Python CLI stdio wrapper, additional Python syntax, rich Ion preservation, cancellation/progress and performance claims are outside this increment. Upstream host changes require their own repository work; unqualified routes must remain labeled unsupported.
