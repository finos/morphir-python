# Spec Delta

## MODIFIED Requirements

### Requirement: Convert between v3 and v4
The `ir convert` command SHALL convert format 3.0.0 to v4 and v4 to format 3.0.0 through the library migrations. It SHALL accept an optional package version and an opt-in flag to drop per-input attributes for upgrades, and an opt-in flag to drop source locations on downgrade. Success writes the target file; failure exits non-zero, prints each diagnostic, and leaves no output file. (bead: morphir-ukvn.8)

#### Scenario: Upgrade v3 file to v4
- **WHEN** the user converts a valid format-3 Library file to v4
- **THEN** the tool writes a `formatVersion` 4 file and exits 0

#### Scenario: Downgrade failure is visible
- **WHEN** the user converts a v4 file that cannot be represented in format 3.0.0
- **THEN** the tool exits non-zero, prints each diagnostic code and location, and does not create the output file

#### Scenario: Downgrade warnings are printed
- **WHEN** a downgrade succeeds with dropped information
- **THEN** the tool prints each warning code and still exits 0

#### Scenario: Upgrade with input attributes needs opt-in
- **WHEN** the user converts the morphir-elm reference model to v4 without `--drop-input-attributes`
- **THEN** the tool exits non-zero with `no_v4_spelling`, names the flag, and does not create the output file

#### Scenario: Upgrade drops input attributes on request
- **WHEN** the user converts the same file with `--drop-input-attributes`
- **THEN** the tool writes a `formatVersion` 4 file, prints each `input_attributes_dropped` warning, and exits 0
