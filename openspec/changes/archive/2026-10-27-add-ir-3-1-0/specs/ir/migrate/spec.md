## REMOVED Requirements

### Requirement: Reverse migrate v4 to v3 with known failure paths
**Reason**: A v4 Specs now downgrades to a v3 Specs, so the scenario that refused Specs no longer holds.
**Migration**: See the requirement "Reverse migrate v4 Library and Specs to v3 with known failure paths".

## ADDED Requirements

### Requirement: Reverse migrate v4 Library and Specs to v3 with known failure paths
The library SHALL migrate v4 to v3. When the input uses concepts v3 cannot represent, migration SHALL fail with structured errors and MUST NOT invent or drop IR content, except as allowed by the dropped-information requirement. (bead: morphir-ukvn.8.13)

#### Scenario: Application does not downgrade
- **WHEN** a v4 Application distribution is migrated to v3
- **THEN** migration fails with `unsupported_v4_downgrade` naming the distribution kind, because format 3 has no Application

#### Scenario: V4-only nodes are reported
- **WHEN** a v4 Library contains a `Hole`, `Native`, or `External` value, or a `DocumentLiteral`
- **THEN** migration fails with `unsupported_v4_downgrade` naming the construct and its location

#### Scenario: V4-only definitions and types are reported
- **WHEN** a v4 Library or Specs contains a native, external or incomplete value-definition body, an incomplete type definition, a `Union` type, or a specification with annotations
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

### Requirement: Specs migrate between v3 and v4
The library SHALL migrate a v3 `Specs` to a v4 `Specs` and a v4 `Specs` to a v3 `Specs`. Each specification SHALL map as the dependency specifications of a `Library` map, with the same diagnostics, warnings and caller-supplied package version. (bead: morphir-ukvn.8.13)

#### Scenario: V3 Specs migrates forward
- **WHEN** a v3 Specs is migrated to v4
- **THEN** the result is a v4 Specs whose package name, dependencies and module specifications match the source, with no annotations

#### Scenario: Compatible v4 Specs downgrades
- **WHEN** a v4 Specs uses only concepts v3 can represent
- **THEN** migration succeeds with a v3 Specs, and a package version is dropped with `package_version_dropped`

#### Scenario: Incompatible v4 Specs is reported
- **WHEN** a v4 Specs has a module member without documentation
- **THEN** migration fails with `unsupported_documentation_downgrade` at that member

#### Scenario: V3 Specs survives v3 to v4 to v3
- **WHEN** a v3 Specs is migrated to v4 and back
- **THEN** the result is semantically equal to the original
