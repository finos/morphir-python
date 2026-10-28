# Proposal

## Why

Python users need a discoverable guide to the library, compiler API, CLI and extension. The current repository guides do not provide a public site or explain the different support and IR conventions of the two Morphir CLIs in one place.

## What Changes

- Publish a repository-owned documentation site using a pinned release of moonrockz/telescope, with navigation, search, readable code examples and local preview instructions. Use morphir-moonbit's blue/orange palette and responsive hero, code window, pipeline and feature-card landing design.
- Add tested examples for Python API compilation/generation, IR codecs and migration, SDK usage, and CLI compile/generate/inspect/convert workflows. Explain package installation, supported platforms, diagnostics and language limits.
- Document the Python extension's qualified installation and invocation through finos/morphir. Publish a compatibility matrix and verified file-based IR interchange recipes for the MoonBit-based CLI, with explicit unsupported cases.
- Keep MoonBit Extism adapter implementation in a separate upstream proposal. This change documents current support and links the follow-up; it does not claim that the existing Python WASM bundle works with the MoonBit core-WASM adapter.
- Add scoped example/site checks and GitHub Pages delivery. Report concrete reusable site limitations to Telescope, linking existing upstream work where it already covers the need.

## Capabilities

### New Capabilities

- `docs/site`: Discoverable, accessible repository documentation, reproducible preview and checked publication.
- `docs/examples`: Executable Python API and CLI learning workflows with explicit package/version prerequisites.
- `docs/cli-integration`: Qualified extension and IR interchange guidance for each Morphir CLI, including compatibility limits.

### Modified Capabilities

None. Compiler, extension protocol and IR behavior remain governed by their existing specs.

## Beads

- **Tracked by**: `morphir-ukvn.9`.
- **Related**: `morphir-ukvn.1.6` supplies the migrated compiler, native package and extension. The separate MoonBit Extism proposal was dispatched to the Codex workspace `propose-extism-python` in finos/morphir-moonbit; its eventual artifact/bead will be linked without blocking this site's accurate compatibility guidance.

## Impact

Documentation under `docs/`, package READMEs, canonical examples and their tests; new `site/` configuration/assets; mise tasks; CI selection and Pages workflows. Telescope is a build-time tool only. Python package runtime dependencies and public APIs do not change. GitHub Pages repository settings require a maintainer action if Actions deployment is not enabled. This proposal authorizes no deployment, runtime adapter changes or upstream Telescope implementation.
