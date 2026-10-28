# Tasks

Implementation began in PR #52 before this OpenSpec formalization. Checked items name completed work; platform qualification remains open until the Windows bootstrap is corrected and verified.

## 1. Document managed CLI installation (morphir-bj9r.1)

- [x] 1.1 Add pinned mise/uv and actual mise/pipx examples, wheel-only policy and installation guidance; verify snippet synchronization and clean released installs locally.
- [ ] 1.2 Bootstrap pipx from an explicit portable backend with correct dependency ordering; verify a clean Windows actual-pipx installation as well as the uv route and document the bootstrap.
- [x] 1.3 Document package channels, independent release tags, qualification and rollback; verify site build/link checks and navigation.

## 2. Qualify candidate installer behavior (morphir-bj9r.2)

- [x] 2.1 Validate all three candidate identities before dependency lookup, preserve exact wheel bytes, constrain dependency resolution and install offline; verify missing-native refusal and same-version candidate receipts.
- [x] 2.2 Isolate mise/Python installer state outside the checkout and qualify both installer environments; verify installed versions, v3/v4 CLI round trips and generated-model execution without Rust on PATH.
- [x] 2.3 Retain candidate/dependency digests and check identity in qualification receipts, add regression tests and a reproduction task, and verify the installed qualification script against local and Linux CI candidates.

## 3. Gate platform and WASM publication (morphir-bj9r.3)

- [x] 3.1 Add installer checks to the existing Build category and path selector; verify focused selector/aggregate regressions and actionlint.
- [x] 3.2 Require the advertised release matrix before CLI publication, reuse compatible Linux evidence and consume published native wheels for CLI tags; verify workflow dependencies and the manual run's refusal to publish.
- [x] 3.3 Reject a well-formed incorrect WASM checksum and seal/check final release asset names; verify the negative checksum regression and a changed-asset receipt refusal.
- [ ] 3.4 Complete current-candidate qualification on Linux x86_64/aarch64, macOS arm64/x86_64 and Windows x86_64 with both installers; retain successful platform receipts and confirm unavailable required evidence prevents promotion.

## 4. Verify integrated delivery (morphir-bj9r.4)

- [x] 4.1 Run code quality, BDD, installed examples and site checks; record actual local results and the initial current-code CI run.
- [x] 4.2 Validate both OpenSpec changes strictly, browser-check their designs and keep bead states consistent; verify the proposal separates completed installer work from unstarted process work.
- [ ] 4.3 Push the final PR candidate and retain its CI/review/platform qualification evidence; reassess the provisional build assessment using actual results and verify all changes are synchronized remotely.

## Workflow follow-up

- Merge and publish only under maintainer approval covering those actions.
- Sync and archive this completed change after delivery review; leave the process/current-MEP proposal open until separately applied.
