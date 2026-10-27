# ir/migrate Specification

## Purpose
Defines migrations between Morphir IR format 3.0.0 and IR v4, including how attributes, documentation, and package versions map, so programs move forward safely and reverse migration fails explicitly when v4 content cannot be represented in v3.

## Requirements

### Requirement: Forward migrate v3 to v4
The library SHALL migrate a valid v3 Library to a v4 Library. Unit type attributes SHALL become empty v4 type attributes; each v3 value attribute type SHALL become the v4 `inferred_type` with no source and no extensions; `WholeNumberLiteral` SHALL become `IntegerLiteral`. The caller MAY supply a package release version; otherwise it is absent. (bead: morphir-ukvn.8)

#### Scenario: Shared Library content migrates forward
- **WHEN** a v3 Library is migrated to v4
- **THEN** every v4 definition matches its source, and every value and pattern carries the source type as `inferred_type`

#### Scenario: Package version comes from the caller
- **WHEN** a v3 Library is migrated with package version `1.2.0`
- **THEN** the v4 package identity carries `1.2.0`, and without that argument the version is absent

### Requirement: Reverse migrate v4 to v3 with known failure paths
The library SHALL migrate v4 to v3. When the input uses concepts v3 cannot represent, migration SHALL fail with structured errors and MUST NOT invent or drop IR content, except as allowed by the dropped-information requirement. (bead: morphir-ukvn.8)

#### Scenario: Specs and Application do not downgrade
- **WHEN** a v4 Specs or Application distribution is migrated to v3
- **THEN** migration fails with `unsupported_v4_downgrade` naming the distribution kind

#### Scenario: V4-only nodes are reported
- **WHEN** a v4 Library contains a `Hole`, `Native`, or `External` value, or a `DocumentLiteral`
- **THEN** migration fails with `unsupported_v4_downgrade` naming the construct and its location

#### Scenario: V4-only definitions and types are reported
- **WHEN** a v4 Library contains a native, external or incomplete value-definition body, an incomplete type definition, a `Union` type, or a specification with annotations
- **THEN** migration fails with `unsupported_v4_downgrade` naming the construct and its location

#### Scenario: Missing types are reported
- **WHEN** a v4 value, pattern, or value-definition input has no `inferred_type`
- **THEN** migration fails with `missing_inferred_type` at that location

#### Scenario: Semantic attributes are reported
- **WHEN** v4 type attributes carry a source, constraints, or extensions, or value attributes carry extensions
- **THEN** migration fails with `unsupported_attributes_downgrade`

#### Scenario: Absent member documentation is reported
- **WHEN** a v4 type or value member has no documentation
- **THEN** migration fails with `unsupported_documentation_downgrade`, because v3 member documentation is a required string

#### Scenario: Compatible Library downgrades
- **WHEN** a v4 Library uses only concepts v3 can represent
- **THEN** migration succeeds with a v3 Library

### Requirement: Dropped information is limited and reported
Reverse migration SHALL drop the package release version, which v3 cannot hold, and report `package_version_dropped`. Value source locations SHALL fail with `unsupported_attributes_downgrade` unless the caller opts in to dropping them, which reports `source_location_dropped`. Nothing else MAY be dropped. (bead: morphir-ukvn.8)

#### Scenario: Package version is dropped with a warning
- **WHEN** a compatible v4 Library with package version `1.2.0` is migrated to v3
- **THEN** migration succeeds and reports `package_version_dropped`

#### Scenario: Source locations need opt-in
- **WHEN** a v4 value carries a source location and the caller did not opt in to dropping it
- **THEN** migration fails with `unsupported_attributes_downgrade`

### Requirement: Shared subset round trips
For any valid v3 Library, migrating to v4 and back to v3 SHALL succeed and SHALL yield a Library semantically equal to the original. (bead: morphir-ukvn.8)

#### Scenario: Elm fixture survives v3 to v4 to v3
- **WHEN** a golden morphir-elm format-3 fixture is migrated to v4 and back
- **THEN** the result is semantically equal to the decoded fixture and reports only `package_version_dropped` if a version was supplied

### Requirement: Migration results are explicit
Migration APIs SHALL return a success value with any warnings, or a failure holding one or more diagnostics. Each diagnostic SHALL expose a stable code, the construct name, and a location path. Codes SHALL reuse upstream codes where they exist. (bead: morphir-ukvn.8)

#### Scenario: Failure is machine-readable
- **WHEN** reverse migration fails
- **THEN** callers can read each diagnostic's code, construct, and location without parsing message text

### Requirement: Per-input attributes drop on request
The library SHALL let a caller drop the value attributes of value-definition inputs, because v4 JSON spells an input as a bare type. On request, each input SHALL keep only its declared type as `inferred_type`, and each input that lost information SHALL report `input_attributes_dropped` at its location. Without the request, forward migration MUST keep input attributes unchanged. (bead: morphir-ukvn.8.15)

#### Scenario: Reference model upgrades to encodable v4
- **WHEN** the morphir-elm reference model, whose inputs carry resolved types that differ from their declared types, is migrated to v4 with the input-attribute drop requested
- **THEN** migration succeeds, reports one `input_attributes_dropped` warning per affected input, and the v4 Library encodes as v4 JSON

#### Scenario: Default upgrade stays lossless
- **WHEN** the same model is migrated to v4 without the request
- **THEN** no input attribute changes and the v3 to v4 to v3 round trip is semantically equal

#### Scenario: Inputs that lose nothing report nothing
- **WHEN** every input's attributes are empty or hold only its declared type
- **THEN** the drop reports no warning
