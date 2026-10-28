# Spec Delta

## Purpose

Let morphir-python CLI users compile supported Python models into versioned Morphir IR and generate Python packages from supported IR using the same Python API as application callers.

## ADDED Requirements

### Requirement: Compile Python sources from the CLI
`morphir-python compile SOURCE --package PACKAGE --output FILE` SHALL compile one Python file or a directory source tree through the public Python API. It SHALL default to IR v3 and support `--ir-version v4` and repeated `--expose MODULE` selections. Omitting exposure SHALL expose every module. Output SHALL be a versioned IR document readable by `ir inspect`. (bead: morphir-ukvn.1.6)

#### Scenario: Compile a source directory
- **WHEN** the user compiles a directory containing supported models and locally importing rules modules
- **THEN** the tool writes one versioned Library document with correct module identities and requested exposure, and exits zero

#### Scenario: Choose draft v4
- **WHEN** the user requests `--ir-version v4`
- **THEN** the tool writes draft v4 and reports its draft status

### Requirement: Generate Python from versioned IR
`morphir-python generate FILE --output-dir DIRECTORY` SHALL read IR with the shared format reader and matching Python codec, then call the public generation API. It SHALL write all generated relative-path Python modules while preserving their directory structure. (bead: morphir-ukvn.1.6)

#### Scenario: Generate modules with imports
- **WHEN** a supported Library contains models and rules in nested modules
- **THEN** generation produces importable modules with the expected paths and supported behavior

#### Scenario: Version parsing uses the shared contract
- **WHEN** an input has a malformed, missing or unsupported format version
- **THEN** generation reports the same version diagnostic code as the Python library and exits non-zero

### Requirement: Report failures and warnings consistently
Both commands SHALL preserve Python API diagnostic codes, severities and available locations. Failures SHALL exit non-zero, with diagnostics on stderr. Success warnings SHALL remain distinguishable from errors and SHALL NOT cause a non-zero exit. (bead: morphir-ukvn.1.6)

#### Scenario: Invalid source
- **WHEN** compilation encounters a supported parser error or unsupported construct
- **THEN** stderr identifies its code and available source location, and no successful IR output is written

#### Scenario: Unsupported IR construct
- **WHEN** generation receives an unsupported value form
- **THEN** it reports the API diagnostic and writes no generated modules

### Requirement: Output publication preserves existing user data
Commands MUST finish validation before publishing output. Compile failures MUST preserve an existing output file. Generation SHALL require a nonexistent or empty output directory, reject escaping or colliding artifact paths, and stage all files before publishing them. Failures MUST leave no partial generated output or overwritten user files. (bead: morphir-ukvn.1.6)

#### Scenario: Existing generation directory contains files
- **WHEN** the user selects a nonempty output directory
- **THEN** the command fails clearly and preserves every existing file

#### Scenario: Generation fails on a later module
- **WHEN** generation cannot handle one module after processing another
- **THEN** no final output module is published

#### Scenario: Artifact path escapes the selected directory
- **WHEN** an artifact path is absolute, traverses a parent directory, or would traverse a symlink
- **THEN** the command rejects the artifact set before writing any output

### Requirement: Existing IR commands remain independent
`ir inspect` and `ir convert` SHALL retain their existing options, shared library behavior and results without initializing the Python compiler. (bead: morphir-ukvn.1.6)

#### Scenario: Inspect and convert an existing fixture
- **WHEN** the user runs either existing command after installing the updated tools
- **THEN** its existing compatibility and diagnostic tests continue to pass

### Requirement: CLI supports a complete round trip
Generated Python in the supported subset SHALL be accepted by `compile` when supplied the original package and exposure options, yielding equivalent normalized IR in the chosen target version. (bead: morphir-ukvn.1.6)

#### Scenario: Compile generate recompile
- **WHEN** the user compiles a supported multi-module model, generates Python, then recompiles that output with the same package, exposure and IR version
- **THEN** both IR documents describe equivalent supported definitions and generated Python returns the expected results
