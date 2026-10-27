# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
