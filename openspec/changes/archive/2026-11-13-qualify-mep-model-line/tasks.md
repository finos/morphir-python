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

- [x] 4.1 Open the PR and get CI green; check and handle each review finding. PR [#80](https://github.com/finos/morphir-python/pull/80) merged as `560a6503b8ffcab87ea667391579b747757bec0d`; its review fixes and green candidate CI are recorded in [the delivery comment](https://github.com/finos/morphir-python/pull/80#issuecomment-6553253719), and merged-main CI [41296468946](https://github.com/finos/morphir-python/actions/runs/41296468946) passed.
- [x] 4.2 Run the Release workflow manually on the candidate branch; verify every required job passes and no release is published. Run [41267831018](https://github.com/finos/morphir-python/actions/runs/41267831018) at `d70053aebb222b1796cb80fb3f7c3b8619ae1f37` succeeded; every publication job was skipped.
- [x] 4.3 Record the approved merge and published `extension/python/v0.6.0` assets, verify the WASM, descriptor and checksum bytes, and reconcile published-module host evidence by exact identity with the tested dry run. Publication [41300584158](https://github.com/finos/morphir-python/actions/runs/41300584158) succeeded at `560a6503b8ffcab87ea667391579b747757bec0d`. See the delivery close-out below for the narrower evidence claim and provenance follow-up.
- [x] 4.4 Publish a separate 0.6.0 release record and digest pins in `docs/extension-0.6.0.md` and `site/releases/python-0.6.0.json`, register the page in site navigation, and verify documentation checks. Preserve the original 0.5.0 recipe, `site/integrations.json` and committed host receipt as historical evidence rather than changing their bound inputs.

## Delivery close-out, 2026-11-13

- The release WASM SHA-256 is `ce0cba07f0395ff8179b42eb021ade05c68197f69b8e9c0c8bc369d2a035727c`, exactly the dry-run WASM that passed 32 of 32 MoonBit model-line rows. Published module evidence is carried forward by byte identity. No new post-release MoonBit run or blanket published-process qualification is claimed.
- The descriptor SHA-256 is `83db8a9203844585d00601457a8e1e348bd2b517f0c4dc4524faaadd8c43479f`, and the checksum-file SHA-256 is `e5fd91b19d1b3ad0f09ec0e54a69add31fd557835964dfb571f2cfcd5dabf096`. All checked assets match the published `SHA256SUMS`; `bundle-host.json` binds the released WASM and descriptor to successful Rust-host v3/v4 operations and installed-integrity refusal.
- The original 4.3 plan overclaimed attestation delivery: the release workflow had no producer, and GitHub attestation verification for the WASM returns 404. Signed provenance is explicitly deferred to [#89](https://github.com/finos/morphir-python/issues/89); checksums and MCK reports are not called attestations.
- The original 4.4 pin-retargeting plan would invalidate the preserved 0.5.0 documentation receipt. Its replacement is the separate 0.6.0 release record and pins, without altering that historical recipe or verifier.
- PR #87 subsequently removed retired MEP 0.1 from the 0.6.2 guest code. The archived delta's Ion-only scenario is reconciled with that current policy; historical 0.6.0 artifacts and their dual-protocol claims remain unchanged. The two negotiation scenarios are synced into the main model-transport spec.
- Beads reconciliation is pending [#90](https://github.com/finos/morphir-python/issues/90). The local shared tracker cannot find this epic or its release group, and its existing unresolved merge conflict prevents pull. No record was falsely closed, no conflict was overridden, and no Windows `bd dolt push` was run.
- Close-out validation passes the change's strict validation before archive, all 13 remaining active-change/main-spec checks after archive, snippet synchronization, the three portable documentation tests, all four installed Python examples, five Windows-native CLI commands, decoded IR equality and generated-code execution. The POSIX-shell recipe itself remains a Linux CI check. The preserved host receipt matches every canonical Git input, and every new release pin matches its downloaded asset and the published checksum list.

## Workflow follow-up

- Archive the delivered change with this documentation close-out; merge remains subject to maintainer approval. Keep #89 and #90 open until their separate acceptance criteria are met.
- Damian's main session moves the finos/morphir bundle pins in a separate PR.
