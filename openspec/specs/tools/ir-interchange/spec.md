# tools/ir-interchange Specification

## Purpose
Gives morphir-python users commands to inspect versioned `morphir-ir.json` files and convert them between format 3 (3.0.x and 3.1.x) and draft IR v4, using the same library readers, codecs, and migrations that Python callers use.

## Requirements

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

### Requirement: Choose the v4 spelling on conversion
`ir convert --to v4` SHALL write the compact canonical spelling by default and SHALL accept `--v4-spelling expanded` to write the expanded spelling. The option SHALL be rejected as a usage error with any other value, and SHALL have no effect on v3 output. (bead: morphir-ukvn.8.16)

#### Scenario: Default conversion is compact
- **WHEN** the user converts a format 3 file with `ir convert --to v4`
- **THEN** the written document uses compact spellings, such as type references as FQName strings, and `ir inspect` reads it

#### Scenario: Expanded conversion on request
- **WHEN** the user adds `--v4-spelling expanded`
- **THEN** the written document uses the expanded spellings and decodes to the same model as the compact output
