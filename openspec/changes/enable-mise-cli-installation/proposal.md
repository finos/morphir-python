# Proposal

## Why

The CLI already ships Python distributions on PyPI and GitHub Releases, but users lack a documented, qualified mise installation path. Release qualification must prove that both supported Python package installers consume the intended wheels and that the final WASM assets retain their verified checksums.

## What Changes

- Document pinned mise/uv and actual mise/pipx configurations with managed CPython 3.14 and wheel-only dependencies.
- Qualify isolated installs of the exact candidate core/native/CLI wheels, including v3/v4 compilation, generation, recompilation and generated-model execution without Rust.
- Gate CLI publication on the existing five-platform qualification matrix, consuming published native wheels for CLI tags and reusing compatible producer artifacts.
- Retain CLI wheel/source mirrors and independent WASM GitHub Releases; verify the WASM checksum contents and final named asset receipt before publication.
- Record the implementation already delivered in PR #52; completed tasks refer to actual evidence. No standalone CLI executable or process MEP guest is introduced here.

## Capabilities

### New Capabilities

- `tools/cli-installation`: Isolated, wheel-only CLI installation through mise and qualification of installer behavior before publication.

### Modified Capabilities

- `python/extension`: Final release asset checksum validation before publishing the WASM extension.

## Beads

- **Tracked by**: `morphir-bj9r`
- **Related**: `morphir-ukvn.9` (documentation site), `morphir-5hxy` (separate process/current-MEP proposal).

## Impact

Installation and release documentation, canonical examples, installed-artifact qualification, the existing CI Build category and release platform matrix, and WASM publication validation. Runtime APIs, package namespaces and release tag families remain compatible. PyPI remains the mise installation source; GitHub Releases retain the CLI distribution mirrors. Merges, tags and public publication require maintainer approval.
