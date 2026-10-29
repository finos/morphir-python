# python/compiler Specification

## Purpose

Compile supported Python domain models to Morphir IR and generate executable Python through an ordinary typed Python API, sharing behavior with native Rust and MEP callers.

## Requirements

### Requirement: Compile the established Python subset
Compilation SHALL preserve the migrated binding's frozen dataclasses, named unions, fixed tuples, annotated pure functions, scalar literals and comparisons, conditionals, typed calls, unary contextual lambdas, local imports and module exposure behavior. It MUST reject unsupported syntax with structured diagnostics. (bead: morphir-ukvn.1.6)

#### Scenario: Compile a multi-module model
- **WHEN** a caller submits models and rules modules with imported ADTs, tuple aliases and annotated conditional functions
- **THEN** compilation preserves their module identities, references, declaration order and configured public/private module access

#### Scenario: Reject an unsupported construct
- **WHEN** a model uses an assignment or an unsupported external import
- **THEN** compilation reports the binding's diagnostic code and available source location without returning a successful partial model

### Requirement: Source processing is static
Compilation and generation MUST NOT import or execute submitted source or generated Python. (bead: morphir-ukvn.1.6)

#### Scenario: Input attempts a side effect
- **WHEN** source includes top-level file-writing code
- **THEN** compilation rejects the unsupported construct and no file is written by that source

### Requirement: Versioned IR interoperates with the Python library
Compilation SHALL produce v3.0 Library IR by default and draft v4 Library IR on request. Generated models MUST decode with this repository's matching codec. Generation SHALL accept supported v3.0 and draft v4 Library models, reject unsupported versions and constructs, and preserve arbitrary-precision integers wherever the selected format permits them. (bead: morphir-ukvn.1.6)

#### Scenario: Python codec reads compiler output
- **WHEN** a supported model is compiled to each advertised target version
- **THEN** the shared format reader and matching Python codec decode it without losing module, type or value semantics

#### Scenario: Independently authored IR generates Python
- **WHEN** a Library model using supported constructs comes from the Python codec or an independent ecosystem fixture
- **THEN** generation produces valid Python without requiring that model to originate in this compiler

#### Scenario: Unsupported distribution or format
- **WHEN** generation receives a Specs distribution or an unsupported format version
- **THEN** it reports an explicit diagnostic rather than inventing value bodies or silently migrating the model

### Requirement: Typed Python API supports both directions
The Python API SHALL accept in-memory source documents, package identity, exposure and target-version options, and return immutable typed results with a version-specific Python IR model. Generation SHALL accept a supported Python IR model and return immutable relative-path source artifacts. Failures SHALL expose structured diagnostics with code, severity and available source location. (bead: morphir-ukvn.1.6)

#### Scenario: Python caller compiles and generates
- **WHEN** a caller supplies source strings through the documented Python API and passes the compiled model to generation
- **THEN** both operations work in process without MEP envelopes, Rust types, temporary files, or a separate executable in the caller's code

#### Scenario: Warning accompanies success
- **WHEN** the compiler returns valid IR with a warning
- **THEN** the result retains the warning and its severity separately from successful model data

### Requirement: Round trips preserve supported semantics
For supported models, compile/generate/recompile SHALL preserve normalized module access, references, type definitions and value behavior in each target IR version. Source formatting and equivalent expression spelling need not be preserved. (bead: morphir-ukvn.1.6)

#### Scenario: Conditional and higher-order behavior survives generation
- **WHEN** a model using conditional branches, a typed call and a unary closure is generated and recompiled
- **THEN** normalized IR remains equivalent and executing the generated code in a separate verification process produces the expected results

### Requirement: Source document order does not affect results
Compilation SHALL produce equivalent models and diagnostics for permutations of the same source set, with deterministic artifact ordering during generation. (bead: morphir-ukvn.1.6)

#### Scenario: Reordered modules
- **WHEN** callers compile the same dependent source modules in different orders
- **THEN** normalized models and diagnostic ordering agree, and subsequent generation returns the same ordered artifacts
