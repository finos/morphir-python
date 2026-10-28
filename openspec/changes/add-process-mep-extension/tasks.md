# Tasks

This change is being applied. SDK 0.4.0 is published and the separate upstream Python JSON MCK profile is merged. All implementation and candidate qualification tasks are complete. Landing and approved component publication remain in progress.

## 1. Negotiate current and legacy MEP (morphir-5hxy.1)

- [x] 1.1 Resolve the SDK 0.3.0 numeric-only wire ID gap with a qualified published SDK pin, linking an upstream prerequisite if needed; add explicit legacy `0.1` and exact `0.2.0-draft.1` offers using the pinned SDK's session helpers; verify numeric/string ID preservation, both handshakes, incompatible drafts and unchanged legacy compile/generate behavior.
- [x] 1.2 Add bilateral complete-tuple and limit negotiation without widening static claims; verify cross-product, unadvertised method, unsupported guarantee and legacy-session refusals.
- [x] 1.3 Document independent MEP, envelope, IR, claims and package versions; verify the capability reference matches live discovery and initialized sessions.

## 2. Adapt supported model envelopes (morphir-5hxy.2)

- [x] 2.1 Implement bounded canonical JSON model-envelope admission using SDK helpers; verify base64, byte length, hash, critical fields, semantic IR version and size-limit negative cases.
- [x] 2.2 Adapt compileModel/generateModel for admitted JSON-profile v3/v4 Library tuples through the shared compiler; verify compile/generate/recompile semantics and diagnostic parity with legacy operations.
- [x] 2.3 Refuse unadvertised Ion profiles, unsupported distributions and guarantees without lossy fallback; test these refusals and document the initial support matrix.

## 3. Serve native stdio sessions (morphir-5hxy.3)

- [x] 3.1 Add the thin Rust process guest and documented `morphir-python-extension --stdio` entry point; verify it builds and executes without CPython/PyO3 or a user Rust toolchain.
- [x] 3.2 Implement bounded Content-Length framing around the SDK session; test Unicode byte lengths, partial/truncated messages, duplicate/invalid lengths, overflow, invalid UTF-8/JSON and header/body limits.
- [x] 3.3 Preserve request IDs, notification silence, fixed session capabilities, shutdown/exit and protocol-only stdout; verify a real multi-request process test and document stderr and supervision behavior.

## 4. Distribute both runtime choices (morphir-5hxy.4)

- [x] 4.1 Build process artifacts for each advertised platform and retain the WASM artifact; verify both use the shared compiler and produce matching supported results and diagnostics.
- [x] 4.2 Stage canonical runtime/platform/mode/argument/digest/claim descriptors and source receipts with pinned tooling; verify host readers, installed-byte integrity, offline activation and explicit unsupported-platform refusal.
- [x] 4.3 Add release assurance and runtime-selection documentation alongside each artifact producer, including exact native/CLI pairing where affected; verify missing or mismatched evidence blocks promotion and historical WASM assets remain available.

## 5. Qualify host interoperability (morphir-5hxy.5)

- [x] 5.1 Run the pinned executable MEP guest suite for both runtimes and protocol offers, including supported model operations and negative admission; retain source/artifact-bound conformance receipts.
- [x] 5.2 Qualify the concrete Rust host process and WASM routes using a pinned compatible release or source build; verify initialization, v3/v4 operations, parity, timeout and child cleanup with a clean child environment.
- [x] 5.3 Test documented MoonBit routes independently, record prerequisite upstream work for any unsupported path and publish only evidenced compatibility claims; verify documentation recipes against the specified host revisions.
- [x] 5.4 Measure representative cold-start and compile/generate workloads for process and WASM without making an unmeasured speed claim; retain the reproducible inputs, toolchain and timing report.

## Workflow follow-up

- All 16 implementation tasks are complete. Full candidate [40726356123](https://github.com/finos/morphir-python/actions/runs/40726356123) succeeded at `bce5d859b524edf452b3031e2e2e56fc32f4da71`. The five process platforms and portable WASM each pass 91 canonical observations and saved rechecks, totaling 546 observations. All transferred receipts were independently checked locally against current source, helper, corpus, checker, lockfile, artifact and claim identities.
- Exact native `0.1.2` / CLI `0.1.1` pairing and compiler/extension `0.5.0` are qualified. Every process producer passes installed offline operation and full structured diagnostic parity with the Python API. Windows imports only allowed OS runtimes. The extracted process archive passes runtime switching, installed-byte integrity and unsupported-platform refusal.
- Final promotion stages 39 assets plus `SHA256SUMS`. Local audit verifies every final checksum, all 11 canonical process archive members, payload hashes, executable modes and all six raw MCK report/recheck pairs. A real four-platform input set is refused for missing Intel evidence. Historical WASM releases `0.4.0` and `0.4.2` remain available with their recorded digests.
- Source-pinned Rust host checks and ten fresh timing samples for small/medium workloads pass on the actual candidate bytes. Raw inputs, reports and toolchain/build identities are retained in the candidate and final host-evidence archive. No general performance claim is made. MoonBit routes remain unsupported at the documented pin with checked limitations.
- SDK `0.4.0` publication and the separate upstream Python JSON MCK profile are complete. The Windows checker build passes with short scoped Cargo storage and explicit parent/submodule Git settings; real source changes are still refused. No corpus change or integrity exception was accepted.
- Main specs are synced. All merges and admin bypass are approved. The maintainer approved native `0.1.2`, CLI `0.1.1` and extension `0.5.0` at merge `f2032e3adaf72854a3907dc092e8abb757f08b4a`.
- Native [40758932916](https://github.com/finos/morphir-python/actions/runs/40758932916) published all five wheels and the source archive. Every PyPI file matches its qualified workflow artifact and checksum exactly. Extension [40758936256](https://github.com/finos/morphir-python/actions/runs/40758936256) is qualifying the approved source.
- CLI [40764461472](https://github.com/finos/morphir-python/actions/runs/40764461472) correctly refused publication: the current core `0.1.0` wheel differs from PyPI after documentation-site metadata edits. Direct comparison confirms identical runtime sources and changes only to `METADATA` and `RECORD`. No CLI files were published. Bug `morphir-5hxy.6` prepares core `0.1.1` and CLI `0.1.2`; preserve the failed `python-v0.1.1` tag and the strict byte-identity guard. Corrected publication requires approval for the new tags and source after qualification.
- Keep this change active until publication and final verification; archive afterward. Do not treat staged assets as published releases.
