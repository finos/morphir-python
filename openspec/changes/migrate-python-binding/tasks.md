# Tasks

Implement against `design.html` and the three delta specs. Follow TDD within each behavior group; claim its bead before work and close it only with passing checks and commit evidence. Keep the A2 final-delivery dependency on the epic. Actual publication and live provider promotion require maintainer approval and are listed under workflow follow-up.

## 1. Move and qualify the standalone Rust compiler (morphir-ukvn.1.6.1)

- [x] 1.1 Select and record the current upstream morphir-rust source revision, reconcile changes since inspected `f4298d0`, and inventory the crate, fixture consumers, release selectors and parent CLI provider references; verify the recorded file inventory and existing binding tests against that revision.
- [x] 1.2 Move the compiler, examples, fixtures, acceptance tests and support documentation into `rust/crates/morphir-python-binding`; add the Rust workspace and lockfile using resolvable published core/SDK versions or one documented exact git revision; verify `cargo metadata --locked` and absence of sibling-checkout dependencies.
- [x] 1.3 Preserve the native Rust API, MEP identity, Ruff pins and current v3/v4 subset; verify migrated unit/integration, Gherkin acceptance and doc tests, Cargo formatting/clippy, and a release WASM build without CPython linking.
- [x] 1.4 Add the documented external Rust usage example and build prerequisites; verify an independent temporary Cargo consumer can compile and generate through the declared dependency without morphir-rust source paths or Python development libraries.

## 2. Expose the compiler through a typed in-process Python API (morphir-ukvn.1.6.2)

- [x] 2.1 Add failing public API tests for in-memory documents, package/exposure options, v3 default and explicit v4, diagnostics and generated artifacts; implement the isolated `morphir-python-native` PyO3 bridge calling the existing compiler traits, following the pinned Tokenizers example in the design; verify owned request extraction, detached Rust execution without Python callbacks, concurrent request isolation, and that compiler-only native/WASM builds still omit PyO3.
- [x] 2.2 Add frozen result/source/artifact types and `morphir_tools.python.compile_sources` and `generate_python`; decode and encode only with existing versioned Python library APIs; verify strict mypy/pyright checks on the new public API and result states that cannot combine failure with successful model data.
- [x] 2.3 Add cross-codec tests for ADTs, nested tuples, imports, visibility, unary higher-order functions, arbitrary integers and independently authored IR in both versions; verify normalized round trips, deterministic source permutations and explicit unsupported model/attribute diagnostics without silent migration.
- [x] 2.4 Preserve language diagnostic codes, severities and available source locations, and document API examples and subset limits; verify warnings survive success, failure has no partial model, submitted code never executes, and documentation examples run through the public API; verify native stubs match installed extension exports/signatures and public typed examples pass both type checkers.

## 3. Package the native compiler for Python users (morphir-ukvn.1.6.3)

- [x] 3.1 Add the Maturin native distribution with a qualified pinned PyO3/Maturin pair, private module, stubs, `py.typed`, licenses and explicit version identity, using the pinned Pydantic packaging example in the design; verify wheel contents and agreement between compiled-module identity, distribution metadata and release inputs while both existing distributions remain on Hatch.
- [x] 3.2 Add an exact qualified native dependency to each tools release and uv workspace wiring, keeping core dependencies empty and compiler loading lazy; verify expected native version/bridge API revision checks, clear rejection of deliberately mismatched installations, library-only installation and existing `ir inspect`/`ir convert` tests without initializing the native compiler.
- [x] 3.3 Produce the native source archive with all referenced Rust workspace files; verify building and installing its wheel in a clean directory with no source checkout or sibling repository available, then run an installed API round trip; compare the included build inputs and archive-only qualification with the pinned Polars example in the design.
- [x] 3.4 Document the qualified CPython/platform matrix, wheel-only installation and contributor source builds; verify clean wheelhouse installation of core, native and tools with Rust absent from PATH and record the exact artifacts used; audit the declared Linux baseline and bundled shared libraries, prohibit build-host-specific CPU assumptions in portable wheels, and run installed import/API checks on declared deployment targets.

## 4. Add Python compile and generate CLI commands (morphir-ukvn.1.6.4)

- [x] 4.1 Add compile tests and implement file/directory discovery, required package, repeated exposure selections and version options through the public API; verify deterministic module identities, local import resolution and `ir inspect` on written v3/v4 models.
- [x] 4.2 Add generate tests and implement shared IR decoding plus API generation into an absent/empty output directory; verify nested modules, importable output, unsupported distribution/node diagnostics and parity with API codes.
- [x] 4.3 Stage complete output before publication and render I/O failures consistently; verify injected write failures, late-module rejection, preservation of existing compile files, refusal of nonempty directories and artifact path/collision/symlink checks.
- [x] 4.4 Add behave scenarios and user-facing CLI/API documentation for compile/generate/recompile; verify both versions, visibility settings and executable conditional/tuple/closure behavior in a separate process, plus all existing CLI regression tests.

## 5. Qualify scoped CI and independently owned extension bundles (morphir-ukvn.1.6.5)

- [x] 5.1 Add mise tasks and scoped Python, Rust/native and bundle checks following the current common-layout contract; verify selector tests for documentation-only, native-only, compiler, shared dependency and workflow changes, plus aggregate failure/cancellation/missing-result handling.
- [x] 5.2 Build one compatible artifact per target/ABI and reuse it for clean-install tests; verify no consumer rebuilds its input and preserve existing lint/typecheck/coverage/BDD/release checks, with runtime and cache observations recorded rather than estimated savings.
- [x] 5.3 Build and package the WASM extension here with the canonical `morphir extension bundle` command against pinned tools; verify claims, checksums, source provenance and initialization/compile/generate/recompile through an isolated offline MEP host for both IR versions.
- [x] 5.4 Add nonpublishing release qualification for the advertised wheel platforms, source archive and extension bundle, independent version/tag validation and exact-artifact promotion inputs; verify workflow syntax and refusal of failed/skipped/missing/mismatched candidate evidence, then document the approval and native-before-tools publication order.

## 6. Measure native and Python integration costs (morphir-ukvn.1.6.6)

- [x] 6.1 Add a reproducible benchmark command with fixed fixtures and scale parameters, comparing native Rust, bridge, public API and CLI at matched target versions; verify warmup/repetition metadata, separate startup and JSON/codec costs, and recorded toolchains/build profile/input sizes.
- [x] 6.2 Run release-build samples and record medians/spread in an HTML report with raw results in the local output directory; verify conclusions distinguish parsing-only `ast.parse` measurements from full compilation and make no Rust-versus-Python compiler claim without an equivalent implementation.

## 7. Remove the old provider and prepare ecosystem cutover (morphir-ukvn.1.6.7)

- [x] 7.1 Prepare a coordinated morphir-rust feature branch removing the crate, workspace membership and Python release/CI registrations; move compiler-owned tests here and replace former-directory fixture includes with independent host fixtures or a pinned replacement provider; verify affected workspace tests, CI selector tests and no references that require the deleted directory.
- [x] 7.2 Prepare finos/morphir provider/discovery, provenance, integration fixture and pin updates as required by the current registry implementation; verify the isolated extension install selects the bundle built here and offline ecosystem CLI round trips pass without the old Python crate.
- [ ] 7.3 Run final repository quality gates, installed Python API/CLI proofs and standalone Rust/native/WASM proofs for the coordinated revisions; verify recorded model equivalence, artifact digests and target-repository checks, and preserve unrelated sibling-checkout work.
- [ ] 7.4 Record reviewable commit ranges, qualification receipts, rollback steps and outstanding A2/release dependencies in beads; verify all implementation task evidence is linked and the epic remains open until approved publication and live provider cutover have actually satisfied its acceptance conditions.

## Workflow follow-up

- Present the exact qualified artifacts and coordinated repository changes for maintainer release/merge approval. Publish the native dependency and extension bundle before dependent tools or registry promotion; preserve historical releases.
- Verify live `morphir extension install morphir-python` fetches from finos/morphir-python and the published Python packages install and round trip without Rust. Record release URLs, digests and merged revisions before closing A4 and relink relevant compiler backlog work to this repository.
- Archive this OpenSpec change after implementation and the applicable review process; adjust HTML asset paths for the archive location, update the epic spec id and sync beads.
