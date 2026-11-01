# Tasks

Qualification receipts for 3.1 and 3.2 (finos/morphir-moonbit `main` 40623b8, macOS arm64) are on bead `morphir-ukvn.1.6.9.3`: the `0.1` suite passed 32 of 32 rows, and the candidate model line passed 32 of 32 rows for the WASM and process guests from both CLIs. The host refuses IR 3 on the model line; see design.html, Risks.

## 1. Test negotiation, golden outputs and refusals (morphir-ukvn.1.6.9.1)

- [x] 1.1 Add session tests for an Ion-preferring host that also offers JSON, an Ion-only host, compile-only admission and a wrong envelope version; verify `cargo test -p morphir-python-binding --test model_session` passes.
- [x] 1.2 Add golden outputs for `compileModel` and `generateModel` for IR `3.0.0` and `4.0.0` through a negotiated session, with byte-exact payload files kept out of line-ending conversion and end-of-file hooks; verify `cargo test -p morphir-python-binding --test model_golden` passes and each payload file's SHA-256 equals its envelope digest.
- [x] 1.3 Add a process test that runs both model operations in a `0.2.0-draft.1` session and checks that the process stops by itself; verify `cargo test -p morphir-python-extension` passes.

## 2. Specify and document (morphir-ukvn.1.6.9.2)

- [x] 2.1 Add the host-default and Ion-only scenarios to `python/model-transport`; verify `openspec validate qualify-mep-model-line --strict` passes.
- [x] 2.2 Set the compiler crate version to `0.6.0`; verify `mise run rust:check` and `mise run check` pass.

## 3. Qualify on the MoonBit worker host (morphir-ukvn.1.6.9.3)

- [x] 3.1 Repeat the `0.1`-only Python suite of finos/morphir-moonbit `main` (`mise run test:cli-extism-python`) for `0.4.1` and `0.4.2`; verify every row passes from the native and npm CLIs.
- [x] 3.2 Run `extension describe`, model-line `compile` (IR 4), `generate`, recompile and a consumer check of the generated Python for the candidate WASM with a contract `0.2.0` pin from the native and npm CLIs; verify protocol `0.2.0-draft.1`, the JSON tuple, equal outputs across CLIs and `exited-after-exit` worker shutdown, and record the receipt on the epic bead.

## 4. Release (morphir-ukvn.1.6.9.4)

- [ ] 4.1 Open the PR and get CI green; check and handle each review finding.
- [ ] 4.2 Run the Release workflow manually on the candidate branch; verify every required job passes and no release is published.
- [ ] 4.3 After maintainer approval, merge, push `extension/python/v0.6.0` at the reviewed commit and verify the published assets, attestations, `release.json` descriptors and `.sha256` files; requalify the published WASM on the MoonBit worker host.
- [ ] 4.4 Point the extension documentation and `site/integrations.json` at `0.6.0` with its published digests; verify `mise run docs:test`.

## Workflow follow-up

- Archive the change after the release and the documentation update merge.
- Damian's main session moves the finos/morphir bundle pins in a separate PR.
