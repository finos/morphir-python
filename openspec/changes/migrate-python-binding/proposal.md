# Proposal

## Why

Python compilation and generation currently live in morphir-rust, separate from the Python IR library and CLI. Moving their implementation here lets Python contributors maintain the binding and gives Python callers and CLI users the same compiler without requiring knowledge of Rust or a separate Morphir executable.

## What Changes

- Move `morphir-python-binding`, its fixtures, examples, acceptance tests and supported-subset documentation into this repository's Rust half, preserving its native Rust API and MEP extension identity.
- Add an in-process CPython extension, a typed Python compilation/generation API, and prebuilt wheels. Keep `morphir` dependency-free; put compiler integration in the tools distribution and its native dependency.
- Add `morphir-python compile` and `morphir-python generate` for Python source to versioned IR and IR to Python, including multi-module inputs, diagnostics and safe output handling.
- Preserve the existing supported Python subset and IR v3/v4 behavior. Reject unsupported constructs explicitly. Validate the Python/Rust IR boundary against this repository's codecs instead of assuming matching model names imply compatibility.
- Build and qualify the extension bundle here, then cut over ecosystem distribution references. **BREAKING**: remove the old crate, Python bundle ownership and workspace-local fixture references from morphir-rust after replacement qualification.
- Measure compiler and Python integration costs with reproducible benchmarks. Treat a Rust performance advantage as unproven.

## Capabilities

### New Capabilities

- `python/compiler`: Supported Python language mapping, deterministic compilation/generation, typed Python access and diagnostics across IR versions.
- `python/extension`: Independent Rust consumption, MEP compatibility, installable Python wheels and ecosystem extension distribution owned here.
- `tools/python-codegen`: CLI compilation and Python generation through the public Python API.

### Modified Capabilities

None. Existing `tools/ir-interchange` requirements continue to govern `ir inspect` and `ir convert`.

## Beads

- **Tracked by**: `morphir-ukvn.1.6`, reused as an epic for the existing A4 migration and the Python API/CLI requested here.
- **Related**: `morphir-ukvn.1.3` and `morphir-ukvn.1.3.3`, existing common-layout and release qualification dependencies; `morphir-rust-72s`, existing compiler foundations and broader language backlog; `morphir-nhbd`, prior Python bundle publication; `morphir-ukvn.8`, Python IR compatibility; `morphir-opua.1.4.4`, separate future Python component-host wrapper, not a dependency of the in-process compiler API.

## Impact

This repository gains a Rust workspace, a separate native wheel distribution, compiler API and CLI commands, scoped CI and extension release qualification. `morphir` and the current pure-Python tools wheel retain their own namespaces and release tags; installing tools also resolves a compatible native wheel. Native extension and bundle versions are explicit and independent of the Python CLI version.

Coordinated changes are required in finos/morphir-rust for removal and in finos/morphir for bundle discovery, tests and pinned integration references. Published core/SDK dependencies, or exact committed git revisions where necessary, replace sibling-checkout paths. Real releases, merges and registry promotion remain maintainer-approved; qualification builds and draft changes do not imply publication.
