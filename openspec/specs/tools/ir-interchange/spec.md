# tools/ir-interchange Specification

## Purpose
Gives morphir-tools users commands to inspect versioned `morphir-ir.json` files and convert them between format 3 (3.0.x and 3.1.x) and draft IR v4, using the same library readers, codecs, and migrations that Python callers use.

## Requirements

### Requirement: Inspect versioned morphir-ir.json
The `ir inspect` command SHALL read a file with the shared format-version reader, decode it with the matching v3 or v4 codec, and report the normalized format version, the distribution kind, and the package name. (bead: morphir-ukvn.8.13)

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

### Requirement: CLI uses library code paths
The tools MUST NOT parse IR JSON with ad-hoc CLI code; reading, decoding, encoding, and migration SHALL go through the library APIs. (bead: morphir-ukvn.8)

#### Scenario: Same result as the library
- **WHEN** the user inspects or converts a file that the library rejects
- **THEN** the tool reports the same diagnostic codes the library returns

### Requirement: Convert between v3 and v4
The `ir convert` command SHALL convert format 3 (3.0.x and 3.1.x) to v4 and v4 to format 3 through the library migrations, for `Library` and `Specs` distributions. It SHALL accept an optional package version and an opt-in flag to drop per-input attributes for upgrades, and an opt-in flag to drop source locations on downgrade. Success writes the target file; failure exits non-zero, prints each diagnostic, and leaves no output file. (bead: morphir-ukvn.8.13)

#### Scenario: Upgrade v3 file to v4
- **WHEN** the user converts a valid format-3 Library file to v4
- **THEN** the tool writes a `formatVersion` 4 file and exits 0

#### Scenario: Specs converts both ways
- **WHEN** the user converts a v3 Specs file to v4, or a compatible v4 Specs file to v3
- **THEN** the tool writes a v4 Specs with `formatVersion` 4, or a v3 Specs with `formatVersion` `"3.1.0"`, and exits 0

#### Scenario: Downgrade failure is visible
- **WHEN** the user converts a v4 file that cannot be represented in format 3
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

### Requirement: Scope excludes formats 1 and 2 and later 3.x minors
The tools MUST reject formats 1 and 2 and any 3.x release from 3.2.0 on, rather than load or convert them. This differs from morphir-elm, which still reads format 1. (bead: morphir-ukvn.8.13)

#### Scenario: Unsupported format version is named
- **WHEN** the user supplies a file whose `formatVersion` is 1, 2, or `"3.2.0"`
- **THEN** the tool exits non-zero with the format-version diagnostic code and says only 3.0.x, 3.1.x and draft 4.0.x are supported
