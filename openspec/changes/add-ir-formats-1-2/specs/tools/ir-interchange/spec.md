# Spec Delta

## MODIFIED Requirements

### Requirement: Inspect versioned morphir-ir.json
The `ir inspect` command SHALL read a file with the shared format-version reader, decode it with the matching v3 or v4 codec, and report the normalized format version, the distribution kind, and the package name. A legacy format 1 or 2 file SHALL be decoded with its legacy decoder and reported as legacy. (bead: morphir-ukvn.8.13)

#### Scenario: Report format version 3
- **WHEN** the user inspects a morphir-elm `morphir-ir.json` with `formatVersion` 3
- **THEN** the tool reports format 3.0.0, kind Library, and the package name, and exits 0

#### Scenario: Report a v3 Specs
- **WHEN** the user inspects a file with `formatVersion` `"3.1.0"` and a `Specs` distribution
- **THEN** the tool reports format 3.1.0, kind Specs, and the package name, and exits 0

#### Scenario: Unversioned IR is rejected clearly
- **WHEN** the input JSON has no `formatVersion` member
- **THEN** the tool exits non-zero, reports `missing_format_version`, and says the IR should be regenerated

#### Scenario: Draft v4 is labelled
- **WHEN** the user inspects a v4 file
- **THEN** the report states that v4 support is draft

#### Scenario: Legacy format is labelled
- **WHEN** the user inspects a morphir-elm file with `formatVersion` 1 or 2
- **THEN** the tool reports the legacy format, kind Library, and the package name, says that `ir convert` upgrades it to format 3.0.0, and exits 0

## ADDED Requirements

### Requirement: Legacy files are upgraded, never written
The `ir convert` command SHALL read format 1 and format 2 files with the library legacy decoders and write them as a format 3.0.0 `Library` (`--to v3`) or draft v4 (`--to v4`, through the v3-to-v4 migration). A legacy file SHALL never become a `Specs` distribution, and no target SHALL write format 1 or 2. (bead: morphir-ukvn.8.12)

#### Scenario: Upgrade a legacy file to format 3
- **WHEN** the user converts the morphir-elm rentals example in format 1 or format 2 with `--to v3`
- **THEN** the tool writes a `formatVersion` 3 Library file, the same file for both inputs, and exits 0

#### Scenario: Upgrade a legacy file to v4
- **WHEN** the user converts a format-1 file with `--to v4`
- **THEN** the tool writes a `formatVersion` 4 file and exits 0

#### Scenario: A broken legacy file leaves no output
- **WHEN** the user converts a format-1 file whose distribution uses a format-3 tag
- **THEN** the tool exits non-zero with `unknown_node` and does not create the output file

### Requirement: Scope excludes later 3.x minors
The tools MUST reject any 3.x release from 3.2.0 on, and any major outside the support table other than the legacy formats 1 and 2, rather than load or convert them. (bead: morphir-ukvn.8.12)

#### Scenario: Unsupported format version is named
- **WHEN** the user supplies a file whose `formatVersion` is `"3.2.0"` or 5
- **THEN** the tool exits non-zero with the format-version diagnostic code and says only 3.0.x, 3.1.x and draft 4.0.x are supported

## REMOVED Requirements

### Requirement: Scope excludes formats 1 and 2 and later 3.x minors
**Reason**: Formats 1 and 2 are now read and upgraded. The refusal of later 3.x minors moves to the requirement "Scope excludes later 3.x minors".
**Migration**: Convert format 1 and 2 files with `ir convert --to v3`.
