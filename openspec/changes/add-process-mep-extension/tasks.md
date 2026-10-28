# Tasks

This change is being applied. The published SDK prerequisite is tracked in morphir-4wrx and finos/morphir-rust#316. Python process/model implementation tasks remain incomplete.

## 1. Negotiate current and legacy MEP (morphir-5hxy.1)

- [ ] 1.1 Resolve the SDK 0.3.0 numeric-only wire ID gap with a qualified published SDK pin, linking an upstream prerequisite if needed; add explicit legacy `0.1` and exact `0.2.0-draft.1` offers using the pinned SDK's session helpers; verify numeric/string ID preservation, both handshakes, incompatible drafts and unchanged legacy compile/generate behavior.
- [ ] 1.2 Add bilateral complete-tuple and limit negotiation without widening static claims; verify cross-product, unadvertised method, unsupported guarantee and legacy-session refusals.
- [ ] 1.3 Document independent MEP, envelope, IR, claims and package versions; verify the capability reference matches live discovery and initialized sessions.

## 2. Adapt supported model envelopes (morphir-5hxy.2)

- [ ] 2.1 Implement bounded canonical JSON model-envelope admission using SDK helpers; verify base64, byte length, hash, critical fields, semantic IR version and size-limit negative cases.
- [ ] 2.2 Adapt compileModel/generateModel for admitted JSON-profile v3/v4 Library tuples through the shared compiler; verify compile/generate/recompile semantics and diagnostic parity with legacy operations.
- [ ] 2.3 Refuse unadvertised Ion profiles, unsupported distributions and guarantees without lossy fallback; test these refusals and document the initial support matrix.

## 3. Serve native stdio sessions (morphir-5hxy.3)

- [ ] 3.1 Add the thin Rust process guest and documented `morphir-python-extension --stdio` entry point; verify it builds and executes without CPython/PyO3 or a user Rust toolchain.
- [ ] 3.2 Implement bounded Content-Length framing around the SDK session; test Unicode byte lengths, partial/truncated messages, duplicate/invalid lengths, overflow, invalid UTF-8/JSON and header/body limits.
- [ ] 3.3 Preserve request IDs, notification silence, fixed session capabilities, shutdown/exit and protocol-only stdout; verify a real multi-request process test and document stderr and supervision behavior.

## 4. Distribute both runtime choices (morphir-5hxy.4)

- [ ] 4.1 Build process artifacts for each advertised platform and retain the WASM artifact; verify both use the shared compiler and produce matching supported results and diagnostics.
- [ ] 4.2 Stage canonical runtime/platform/mode/argument/digest/claim descriptors and source receipts with pinned tooling; verify host readers, installed-byte integrity, offline activation and explicit unsupported-platform refusal.
- [ ] 4.3 Add release assurance and runtime-selection documentation alongside each artifact producer, including exact native/CLI pairing where affected; verify missing or mismatched evidence blocks promotion and historical WASM assets remain available.

## 5. Qualify host interoperability (morphir-5hxy.5)

- [ ] 5.1 Run the pinned executable MEP guest suite for both runtimes and protocol offers, including supported model operations and negative admission; retain source/artifact-bound conformance receipts.
- [ ] 5.2 Qualify the concrete Rust host process and WASM routes using a pinned compatible release or source build; verify initialization, v3/v4 operations, parity, timeout and child cleanup with a clean child environment.
- [ ] 5.3 Test documented MoonBit routes independently, record prerequisite upstream work for any unsupported path and publish only evidenced compatibility claims; verify documentation recipes against the specified host revisions.
- [ ] 5.4 Measure representative cold-start and compile/generate workloads for process and WASM without making an unmeasured speed claim; retain the reproducible inputs, toolchain and timing report.

## Workflow follow-up

- Implementation requires separately applying this proposal after review.
- Merge, tags and publication require maintainer approval; sync/archive only after implementation and qualification are complete.
