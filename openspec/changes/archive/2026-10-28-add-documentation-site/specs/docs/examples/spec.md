# Verified learning examples

## Purpose

Help Python users learn the library and tools through reproducible examples whose displayed source and documented results stay consistent with the qualified packages.

## ADDED Requirements

### Requirement: Installation guidance identifies package responsibilities
The guides SHALL distinguish the library, CLI distribution and automatically installed native compiler package. Each workflow MUST identify required interpreter/platform support and qualified package versions, separating released capabilities from source-only or draft capabilities. (bead: morphir-ukvn.9.2)

#### Scenario: Start with an installed package
- **WHEN** a user follows the compiler quickstart on a qualified wheel platform
- **THEN** the guide installs the CLI distribution and its compatible compiler without requiring the user to install Rust

#### Scenario: Use only the library
- **WHEN** a user follows an IR or SDK example
- **THEN** the guide identifies the library-only installation and does not require the compiler package for that example

### Requirement: API examples cover both compiler directions
The guides SHALL provide complete examples for in-memory Python compilation, generation from typed IR, and structured diagnostics. Examples MUST explain supported syntax, package/module identity, exposure and IR version selection. (bead: morphir-ukvn.9.2)

#### Scenario: Compile and generate through Python
- **WHEN** a user runs the API example with the documented prerequisites
- **THEN** the example compiles a multi-module model, inspects its typed result and generates source artifacts with the documented relative paths

#### Scenario: Understand unsupported source
- **WHEN** a user runs the diagnostic example
- **THEN** the example returns the documented error code and available source location and explains the relevant language limit

### Requirement: Library examples explain IR and SDK usage
The guides SHALL provide executable examples for reading and writing versioned IR, explicit supported migration and representative SDK operations. They MUST explain format support and refusal or loss diagnostics without implying that every distribution or construct can be compiled or generated. (bead: morphir-ukvn.9.2)

#### Scenario: Inspect and migrate a model
- **WHEN** a user follows the library example using the supplied fixture
- **THEN** the example reads its version, decodes and writes it, and demonstrates an explicit supported conversion with its documented diagnostics

### Requirement: CLI examples cover a complete workflow
The guides SHALL include runnable compile, generate, inspect and convert examples, with input fixtures, expected files and exit behavior. They MUST explain output-directory constraints and distinguish semantic round trips from source-text preservation. (bead: morphir-ukvn.9.2)

#### Scenario: Follow the CLI quickstart
- **WHEN** a user runs the documented compile, inspect, generate and recompile sequence in a fresh directory
- **THEN** the commands produce the documented artifacts and preserve the supported model's normalized semantics

#### Scenario: Diagnose a command failure
- **WHEN** a documented failing command uses unsupported source or a nonempty generation directory
- **THEN** the observed exit status and diagnostic match the guide and existing user files remain intact

### Requirement: Displayed examples match checked sources
Every example presented as runnable SHALL have a canonical source and automated verification of its claimed result. Displayed code MUST match that source. API examples SHALL pass the project's type checks; CLI examples SHALL verify commands and outputs in isolated temporary directories. Unsupported platform or external-host cases MUST be labeled with their qualification limits. (bead: morphir-ukvn.9.2)

#### Scenario: A snippet drifts
- **WHEN** an edit changes a displayed runnable snippet without updating its checked source
- **THEN** documentation verification fails before publication

#### Scenario: An API or CLI option changes
- **WHEN** a public signature or command option used in an example changes incompatibly
- **THEN** verification detects the obsolete example or reference rather than publishing a successful quickstart claim
