# Tasks

Implement the contracts in `specs/docs/` using the decisions in `design.html`. Scope is current-support documentation; MoonBit Extism implementation remains a separate proposal. Prefer one implementation PR if practical.

## 1. Establish Telescope site and local preview (morphir-ukvn.9.1)

- [x] 1.1 Add pinned Telescope 0.2.1 archive/version/checksum setup metadata and `site:setup`; verify clean Linux x64 and macOS arm64 installation without a Telescope checkout or MoonBit compiler and document other platform limits.
- [x] 1.2 Add `site/site.json`, landing page, navigation and static assets with `/morphir-python/` deployment configuration; verify installation, API, CLI, integration and contributor sections are reachable and templates/planning/generated files are absent from navigation and search.
- [x] 1.3 Add `site:build`, `site:check` and `site:serve` tasks and a contributor guide; verify the documented sequence builds/checks/serves at `/` and `/morphir-python/`, preserves prior output on validation failure and reports a deliberately broken fragment.
- [x] 1.4 Add browser smoke coverage for desktop and 360px, light/dark themes, keyboard focus, navigation, search and code copying; verify no page-level overflow and retain screenshots/results for the candidate.
- [x] 1.5 Record the foundation/version/limitations in `docs/site-foundation.md`; link Telescope's existing tutorial intent when durable, and report any confirmed reusable blocker upstream with reproduction and acceptance criteria. Verify each remaining gap has a linked report or an explicit non-blocking consumer workaround.

- [x] 1.6 Match morphir-moonbit revision bd3adc52 colors and landing design using an attributed theme and Python example; verify both themes, desktop/mobile layouts, canonical source, base paths and atomic failure preservation, report the Telescope customization gap upstream and verify the published site after merge.

## 2. Publish verified Python API and CLI examples (morphir-ukvn.9.2)

- [x] 2.1 Add canonical multi-module model, compiler API and CLI recipe sources under `examples/`, with a prerequisite/result manifest; verify compile/generate/recompile semantic assertions and diagnostic/output-safety cases against installed packages outside the checkout.
- [x] 2.2 Add focused IR codec/version/migration and SDK examples; verify library-only execution without the native compiler dependency and label draft/source-only behavior according to tested package versions.
- [x] 2.3 Add source-region snippet synchronization and check-only mode; evolve `tests/tools/test_python_docs.py` and add `docs:test` for named examples. Verify stale snippets fail, API examples pass mypy/pyright and fresh-interpreter tests, and CLI recipes run in temporary directories with checked artifacts/status/diagnostics.
- [x] 2.4 Expand the compiler guide and add installation, library/API, command reference and language-limit pages; verify exported symbol/signature and CLI-help consistency plus every runnable block's canonical-source mapping.
- [x] 2.5 Add release/development prerequisite labels and exact package pairing, wheel-platform and troubleshooting guidance; verify released quickstarts in a clean wheel-only installation without Rust and development examples against the compatible candidate wheels.
- [x] 2.6 Update repository and package READMEs to link site journeys while retaining useful installation summaries; verify relative links in GitHub sources and rendered site checks.

## 3. Document qualified Morphir CLI integrations (morphir-ukvn.9.3)

- [x] 3.1 Add a versioned compatibility matrix and explicit executable/provider checks for morphir-python, finos/morphir and the MoonBit CLI; verify transport, MEP, IR, encoding, envelope and supported-operation claims against pinned source/release evidence.
- [x] 3.2 Replace placeholder-only extension setup with a concrete qualified finos/morphir host/bundle recipe covering checksum verification, repository selection/publication, installation, discovery and compile/generate; reuse existing bundle qualification and verify the displayed recipe in a fresh workspace with semantic output assertions.
- [x] 3.3 Add a MoonBit guide explaining the unsupported Extism route, separate install/invoke selection and IR/envelope constraints; verify it links the separately dispatched Extism proposal/bead when available and presents no direct-invocation success claim without independent qualification.
- [x] 3.4 Add bounded producer/consumer probes for file interchange using supplied fixtures and pinned CLI identities; publish only verified directions, with checked refusals for incompatible IR/envelope/provenance cases. Verify the guide never equates file exchange with extension invocation or relies on invented runtime conversions.
- [x] 3.5 Record reusable host-recipe qualification evidence, input/command hashes, artifact digests, platform and checker identity; verify changed pins/recipes require fresh results, missing prerequisites cannot pass and reuse requires matching relevant inputs. Document rerun and support-status update commands alongside each guide.

## 4. Validate and publish documentation through scoped CI (morphir-ukvn.9.4)

- [x] 4.1 Extend `scripts/ci_changes.py` and its focused tests for docs/static, examples/referenced APIs and host-recipe checks; verify prose changes avoid unrelated compiler builds, candidate examples reuse compatible wheel producers, unknown/full changes remain conservative, and failures/cancellation/missing/unexpected skips fail the aggregate.
- [x] 4.2 Add a reusable site build/check workflow and wire selected checks into main CI; verify PRs build and test without production privileges, both deployment bases pass and the complete candidate's required example/host evidence is available or explicitly blocks publication.
- [x] 4.3 Add trusted-main Pages publication using the exact checked site artifact and source/tool/package/evidence manifest; verify deploy depends on all required checks, missing or mismatched evidence refuses promotion, and deploy-only permissions and the github-pages environment are correctly scoped.
- [x] 4.4 Document deployment settings, authorized manual runs, pin updates, evidence retention and rollback; verify the instructions identify any required maintainer setting and can restore a retained verified artifact without rebuilding it.
- [x] 4.5 Run the complete candidate's site/browser/example/host checks and required code quality gates; record actual run identities, tool versions and representative timings, reassess the provisional CI design, and verify no supported recipe or published snippet lacks qualification.

## Workflow follow-up

- Obtain review and maintainer approval before merging or deploying. If Pages settings are unavailable, present the verified artifact and exact required setting as the final approval step.
- After authorized main publication, verify public links, base paths, search and example downloads; retain the deployed source/artifact identity.
- Archive after implementation and review requirements are satisfied, repair the archived design asset paths, relink the epic spec id and close beads with commit/test evidence. Sync the shared tracker.
