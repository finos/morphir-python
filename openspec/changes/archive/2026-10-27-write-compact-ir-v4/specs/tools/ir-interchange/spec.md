# Spec Delta

## ADDED Requirements

### Requirement: Choose the v4 spelling on conversion
`ir convert --to v4` SHALL write the compact canonical spelling by default and SHALL accept `--v4-spelling expanded` to write the expanded spelling. The option SHALL be rejected as a usage error with any other value, and SHALL have no effect on v3 output. (bead: morphir-ukvn.8.16)

#### Scenario: Default conversion is compact
- **WHEN** the user converts a format 3 file with `ir convert --to v4`
- **THEN** the written document uses compact spellings, such as type references as FQName strings, and `ir inspect` reads it

#### Scenario: Expanded conversion on request
- **WHEN** the user adds `--v4-spelling expanded`
- **THEN** the written document uses the expanded spellings and decodes to the same model as the compact output
