# Spec Delta

## Purpose

Provide a documented, isolated CLI installation through mise and require verified installer behavior for the distributions that a release promotes.

## ADDED Requirements

### Requirement: Isolated wheel-only CLI installation
The CLI SHALL be installable through documented mise configurations using uv or actual pipx with managed CPython 3.14. Each configuration MUST install the compatible native compiler from a wheel, expose `morphir-python`, and keep its dependencies separate from application environments. (bead: morphir-bj9r)

#### Scenario: Clean managed installation
- **WHEN** a user applies either documented configuration on a qualified platform
- **THEN** mise installs the interpreter and CLI environment and `mise exec -- morphir-python --help` succeeds without a Rust toolchain

#### Scenario: No compatible native wheel
- **WHEN** the selected interpreter or platform has no compatible compiler wheel
- **THEN** installation fails rather than compiling Rust from a source distribution

### Requirement: Installer qualification uses identified candidate artifacts
Release qualification SHALL install the exact identified core, native and CLI candidate wheels in fresh environments outside the checkout. Candidate installation MUST use a constrained offline wheel set, reject missing or mismatched candidate identities, and retain input and dependency digests with installed versions. (bead: morphir-bj9r)

#### Scenario: A same-version package exists on PyPI
- **WHEN** the candidate and a published package have the same version but different bytes
- **THEN** qualification installs the supplied candidate bytes without substituting the PyPI package

#### Scenario: Native candidate is missing
- **WHEN** supplied candidate inputs do not contain the required native wheel
- **THEN** qualification refuses the set before resolving a replacement from an index

### Requirement: Installed commands preserve compiler behavior
Both supported installers SHALL qualify installed CLI compilation, inspection, generation and recompilation for supported IR v3/v4 models, including generated-model execution, with Rust absent from the execution PATH. (bead: morphir-bj9r)

#### Scenario: Installed compiler round trip
- **WHEN** each installer processes the supported multi-module fixture in v3 and v4
- **THEN** generated Python recompiles to equivalent IR and the generated model returns the expected values

### Requirement: CLI publication requires platform installer evidence
CLI publication SHALL require successful installer qualification for every advertised release platform using that release's core/CLI wheels and exact published native dependency. Missing, failed, cancelled or unexpectedly skipped required qualification MUST block publication. Normal CI SHALL qualify the Linux candidate path. (bead: morphir-bj9r)

#### Scenario: One platform fails qualification
- **WHEN** any advertised platform fails, is cancelled, or lacks required installer evidence
- **THEN** the CLI is not promoted to PyPI or its GitHub release

#### Scenario: Compatible producer artifacts exist
- **WHEN** the same qualified candidate wheel is available to a compatible consumer
- **THEN** the consumer can reuse it with its identity retained rather than rebuilding the compiler

### Requirement: Installation channels remain explicit
The CLI SHALL retain Python wheel/source distribution publication on PyPI and GitHub Releases. The documented mise package route SHALL use PyPI; it MUST NOT imply that a standalone executable or the WASM plugin is installed by that route. (bead: morphir-bj9r)

#### Scenario: User chooses the mise route
- **WHEN** a user follows the installation guide
- **THEN** the guide identifies managed Python, the isolated CLI environment, compatible wheel requirements and the distinct WASM extension channel
