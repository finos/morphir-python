# python/extension Specification

## Purpose

Distribute the Python language compiler from morphir-python for native Rust consumers, ordinary Python installations and Morphir extension hosts, with one maintained implementation.

## Requirements

### Requirement: Rust consumers use an independently buildable crate
The migrated crate SHALL retain the `morphir-python-binding` package name and native `PythonExtension` frontend/backend API. A Rust consumer MUST be able to build and invoke it without a morphir-rust sibling checkout, CPython or Python extension linking. (bead: morphir-ukvn.1.6)

#### Scenario: External Cargo consumer
- **WHEN** a standalone Cargo project depends on the binding at an exact committed revision in morphir-python
- **THEN** it builds and invokes compile and generate using declared core/SDK dependencies without local source overrides or Python development libraries

### Requirement: MEP behavior remains compatible
The extension SHALL retain identity `morphir-python`, Python language/target identifiers, initialization and capability negotiation, compile/generate methods and advertised IR v3/v4 support. Native Rust, Python and packaged WASM invocations SHALL agree on supported model semantics and language diagnostic codes. (bead: morphir-ukvn.1.6)

#### Scenario: Existing host installs the replacement bundle
- **WHEN** a compatible Morphir host installs the bundle built from morphir-python
- **THEN** initialization, capability discovery, Python compilation and Python generation succeed through the existing protocol

### Requirement: Python installation hides Rust implementation details
Installing `morphir-python` on qualified CPython platforms SHALL install its compatible native compiler dependency automatically from wheels. Compilation and generation MUST require neither a Rust toolchain nor a separately installed Morphir CLI at runtime. The `morphir` distribution SHALL keep zero third-party runtime dependencies. (bead: morphir-ukvn.1.6)

#### Scenario: Clean wheel-only installation
- **WHEN** a user installs the qualified distributions into a clean CPython 3.14 environment on a supported wheel platform with Rust absent
- **THEN** Python API compilation and generation and both new CLI commands succeed

#### Scenario: Library-only user
- **WHEN** a user installs only `morphir`
- **THEN** IR and SDK imports work without the compiler dependency or native shared libraries

### Requirement: Qualified artifacts are self-contained
Native wheels and source distributions SHALL include required runtime files, typing information and build inputs. Published artifact metadata SHALL declare supported interpreter/platform combinations and compatible package versions. Qualification MUST install built artifacts outside the source checkout. (bead: morphir-ukvn.1.6)

#### Scenario: Build from the source archive
- **WHEN** a contributor builds the native wheel from its source archive with the documented build toolchain
- **THEN** the build succeeds without missing workspace files or sibling repositories and the wheel passes an installed API smoke test

### Requirement: Python extension releases belong to morphir-python
Replacement Python extension bundles SHALL be built, qualified and released from finos/morphir-python with checksums, capability claims and source provenance. Ecosystem installation references SHALL resolve the replacement provider there; historical release assets MUST remain available. (bead: morphir-ukvn.1.6)

#### Scenario: Ecosystem installation follows the new owner
- **WHEN** a qualified replacement is published and selected in the ecosystem extension repository
- **THEN** `morphir extension install morphir-python` obtains its bundle from morphir-python, verifies it and supports offline compile/generate/recompile

### Requirement: Old implementation is removed after replacement qualification
The cutover SHALL remove the Python binding implementation, workspace membership and Python-specific publishing ownership from morphir-rust. Tests and integrations MUST use the new provider or independent host fixtures without depending on the deleted directory. (bead: morphir-ukvn.1.6)

#### Scenario: Rust workspace after removal
- **WHEN** the replacement provider has passed migration qualification and the coordinated removal lands
- **THEN** the morphir-rust workspace and its CI remain valid with no Python compiler implementation or references requiring the former crate directory
