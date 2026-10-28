# CLI integration guidance

## Purpose

Give users accurate, reproducible instructions for using the Python extension and exchanging IR across the independently implemented Morphir CLIs.

## ADDED Requirements

### Requirement: Compatibility guidance identifies the host
The documentation SHALL distinguish morphir-python, finos/morphir and the MoonBit-based Morphir CLI by provider and version. Its compatibility matrix MUST identify extension transport, protocol, IR formats, artifact shape, supported operations and qualification evidence for each host. (bead: morphir-ukvn.9.3)

#### Scenario: Two CLIs use the same executable name
- **WHEN** a user selects an extension setup recipe
- **THEN** the guide identifies which Morphir implementation must be installed and how to verify it before invoking commands

### Requirement: Qualified extension setup is reproducible
The finos/morphir guide SHALL document a qualified Python bundle/host pair, checksum verification, repository publication or selection, installation, discovery and compile/generate invocation. It MUST distinguish installing a bundle from selecting it for execution. (bead: morphir-ukvn.9.3)

#### Scenario: Use a clean extension repository
- **WHEN** a user follows the guide with the pinned bundle and host in a fresh workspace
- **THEN** the host verifies and installs the expected extension, compiles the supplied Python model and generates Python with the documented artifacts

### Requirement: Unsupported adapters are explicit
The documentation MUST state that the current Python Extism guest is not interchangeable with the MoonBit core-WASM process adapter. Until an Extism adapter is independently qualified, the MoonBit guide SHALL label direct invocation unsupported and link its separate upstream proposal. (bead: morphir-ukvn.9.3)

#### Scenario: Attempt direct MoonBit invocation
- **WHEN** a user reads how to connect the current Python WASM bundle to the MoonBit CLI
- **THEN** the guide explains the adapter and protocol gap and does not present an unqualified direct-invocation command as working

### Requirement: IR interchange claims are qualified
Each documented interchange direction SHALL identify the exact producer/consumer pair, model subset, version, encoding and artifact shape. Successful recipes MUST verify the consumer's result; refusal cases MUST identify the incompatibility. The guide MUST distinguish file exchange from invoking the Python extension through that host. (bead: morphir-ukvn.9.3)

#### Scenario: Exchange a model using a supported route
- **WHEN** a user follows a recipe classified as supported for the qualified versions
- **THEN** the supplied fixture reaches the documented consumer operation through the stated conversion steps with checked semantic results

#### Scenario: Formats or envelopes differ
- **WHEN** the current host pair cannot exchange the supplied model without unsupported conversion or provenance loss
- **THEN** the guide records a tested refusal and the missing capability rather than suggesting that renaming a plain IR file supplies the required envelope

### Requirement: Qualification failures cannot silently become support claims
Host integration checks SHALL record pinned host and bundle identities, commands, expected artifacts and diagnostics. Changes to a supported recipe MUST rerun its required qualification before publication. External-host availability problems MUST remain visible and cannot count as a passing compatibility check. (bead: morphir-ukvn.9.3)

#### Scenario: A supported recipe changes
- **WHEN** an edit changes a host pin, bundle pin or executable setup command
- **THEN** publication requires evidence for that exact combination and changed recipe

#### Scenario: The host cannot be obtained
- **WHEN** qualification cannot obtain a required host or bundle
- **THEN** the result reports the unavailable prerequisite and blocks a new or revised supported claim
