# Spec Delta

## MODIFIED Requirements

### Requirement: Inspect versioned morphir-ir.json
The `ir inspect` command SHALL read a file with the shared format-version reader, decode it with the matching v3 or v4 codec, and report the normalized format version, the distribution kind, and the package name. A legacy format 1 or 2 file SHALL be decoded with its legacy decoder and reported as legacy. (bead: morphir-ukvn.8)

#### Scenario: Report format version 3
- **WHEN** the user inspects a morphir-elm `morphir-ir.json` with `formatVersion` 3
- **THEN** the tool reports format 3.0.0, kind Library, and the package name, and exits 0

#### Scenario: Unversioned IR is rejected clearly
- **WHEN** the input JSON has no `formatVersion` member
- **THEN** the tool exits non-zero, reports `missing_format_version`, and says the IR should be regenerated

#### Scenario: Draft v4 is labelled
- **WHEN** the user inspects a v4 file
- **THEN** the report states that v4 support is draft

#### Scenario: Legacy format is labelled
- **WHEN** the user inspects a morphir-elm file with `formatVersion` 1 or 2
- **THEN** the tool reports the legacy format, kind Library, and the package name, says that `ir convert` upgrades it to format 3.0.0, and exits 0

### Requirement: Convert between v3 and v4
The `ir convert` command SHALL convert format 3.0.0 to v4 and v4 to format 3.0.0 through the library migrations. It SHALL accept an optional package version for upgrades and an opt-in flag to drop source locations on downgrade. Success writes the target file; failure exits non-zero, prints each diagnostic, and leaves no output file. (bead: morphir-ukvn.8)

#### Scenario: Upgrade v3 file to v4
- **WHEN** the user converts a valid format-3 Library file to v4
- **THEN** the tool writes a `formatVersion` 4 file and exits 0

#### Scenario: Downgrade failure is visible
- **WHEN** the user converts a v4 file that cannot be represented in format 3.0.0
- **THEN** the tool exits non-zero, prints each diagnostic code and location, and does not create the output file

#### Scenario: Downgrade warnings are printed
- **WHEN** a downgrade succeeds with dropped information
- **THEN** the tool prints each warning code and still exits 0

## ADDED Requirements

### Requirement: Legacy files are upgraded, never written
The `ir convert` command SHALL read format 1 and format 2 files with the library legacy decoders and write them as format 3.0.0 (`--to v3`) or draft v4 (`--to v4`, through the v3-to-v4 migration). No target SHALL write format 1 or 2. (bead: morphir-ukvn.8.12)

#### Scenario: Upgrade a legacy file to format 3
- **WHEN** the user converts the morphir-elm rentals example in format 1 or format 2 with `--to v3`
- **THEN** the tool writes a `formatVersion` 3 file, the same file for both inputs, and exits 0

#### Scenario: Upgrade a legacy file to v4
- **WHEN** the user converts a format-1 file with `--to v4`
- **THEN** the tool writes a `formatVersion` 4 file and exits 0

#### Scenario: A broken legacy file leaves no output
- **WHEN** the user converts a format-1 file whose distribution uses a format-3 tag
- **THEN** the tool exits non-zero with `unknown_node` and does not create the output file

## REMOVED Requirements

### Requirement: Scope excludes formats 1, 2, and 3.1
**Reason**: Formats 1 and 2 are now read and upgraded. The refusal of IR 3.1.0 stays, as the shared reader's support-table requirement (`ir/format-version`) states it, and the tools report the reader's diagnostic.
**Migration**: Convert format 1 and 2 files with `ir convert --to v3`; IR 3.1.0 files are still refused until IR 3.1.0 support lands.
