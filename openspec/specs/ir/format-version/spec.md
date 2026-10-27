# ir/format-version Specification

## Purpose
Defines how morphir-python reads, normalizes, checks, and writes the `formatVersion` field of a versioned Morphir IR document, so every codec and the CLI reject unsupported input the same way, with stable diagnostic codes, before any distribution decoding starts.

## Requirements

### Requirement: Permissive format version recognition
The reader SHALL accept a JSON integer `N`, a string `"N"`, and a string `"N.minor.patch"`, and normalize each to an exact release (`3`, `"3"` and `"3.0.0"` all mean 3.0.0). Components MUST be unsigned 32-bit base-10 integers with no leading zeros. Booleans, null, floats, negatives, collections, whitespace, prerelease and build suffixes MUST be rejected. (bead: morphir-ukvn.8)

#### Scenario: Integer and string spellings normalize alike
- **WHEN** documents declare `formatVersion` as `3`, `"3"`, and `"3.0.0"`
- **THEN** each normalizes to release 3.0.0

#### Scenario: Boolean is not an integer
- **WHEN** a document declares `formatVersion` as `true`
- **THEN** recognition fails with `invalid_format_version_type`

#### Scenario: Malformed release string
- **WHEN** a document declares `formatVersion` as `"3.0.0-alpha"` or `" 3.0.0"`
- **THEN** recognition fails with `invalid_format_version_syntax`

### Requirement: Divergence from morphir-elm and the finos contract is deliberate
Accepting string spellings SHALL be documented as a deliberate divergence from morphir-elm, whose decoder accepts only an integer, and accepting `"N"` as a divergence from the finos/morphir contract, which accepts only integer `N` or `"N.minor.patch"`. Both exist to read files written by other tools during migration. (bead: morphir-ukvn.8)

#### Scenario: Divergence is visible to users
- **WHEN** a user reads the package documentation for format version handling
- **THEN** it states which accepted spellings morphir-elm and the finos/morphir contract would reject

### Requirement: Stable format version diagnostics
Format-version failures SHALL use the finos/morphir contract codes: `missing_format_version`, `duplicate_format_version`, `invalid_format_version_type`, `invalid_format_version_syntax`, `format_version_out_of_range`, `unsupported_format_version_major`, and `unsupported_format_version_minor`. (bead: morphir-ukvn.8)

#### Scenario: Missing version
- **WHEN** the document root has no `formatVersion` member
- **THEN** reading fails with `missing_format_version`

#### Scenario: Duplicate version member
- **WHEN** the document root contains `formatVersion` twice
- **THEN** reading fails with `duplicate_format_version` rather than keeping the last value

### Requirement: Canonical format version output
Writers SHALL emit `formatVersion` first, as the integer `N` for a baseline release `N.0.0` and as the exact release string otherwise, regardless of the spelling that was read. Writers MUST NOT emit the legacy formats 1 and 2. (bead: morphir-ukvn.8)

#### Scenario: Read string, write integer
- **WHEN** a document read with `formatVersion` `"3.0.0"` is written again
- **THEN** the output declares `formatVersion` as the integer `3`

#### Scenario: Legacy versions are never written
- **WHEN** a caller asks for the spelling of format 1 or 2
- **THEN** the writer refuses instead of returning `1` or `2`

### Requirement: Support table with IR 3.1 is checked before decoding
The reader SHALL declare the support table `[3.0.0,3.2.0),[4.0.0,4.1.0)` and MUST finish recognition and the support check before invoking any distribution decoder or migration. A release outside the table SHALL fail with `unsupported_format_version_major` or `unsupported_format_version_minor`. (bead: morphir-ukvn.8.13)

#### Scenario: IR 3.1.0 is supported
- **WHEN** a document declares `formatVersion` `"3.1.0"` or `"3.1.4"`
- **THEN** the support check passes and the distribution is decoded

#### Scenario: A later 3.x minor is refused
- **WHEN** a document declares `formatVersion` `"3.2.0"`
- **THEN** reading fails with `unsupported_format_version_minor` before the distribution is decoded, and the message names the accepted table `[3.0.0,3.2.0),[4.0.0,4.1.0)`

#### Scenario: Historical versions are refused
- **WHEN** a document declares `formatVersion` `1` or `2` and is read against a support table
- **THEN** reading fails with `unsupported_format_version_major` and a message that names the legacy readers for formats 1 and 2

### Requirement: Legacy formats are recognized outside the support table
A legacy-aware read SHALL recognize the JSON integers `1` and `2` as legacy formats 1 and 2 and return them without a support check, because the finos release grammar starts at major 3. Every other value SHALL be read and checked as before, with the same diagnostics. The strings `"1"`, `"2"` and `"1.0.0"` MUST stay invalid, because morphir-elm wrote legacy formats only as integers. (bead: morphir-ukvn.8.12)

#### Scenario: Integer legacy version
- **WHEN** a legacy-aware read sees `formatVersion` `1` or `2`
- **THEN** it reports legacy format 1 or 2 and does not consult the support table

#### Scenario: Other versions keep their diagnostics
- **WHEN** a legacy-aware read sees `formatVersion` `"1"`, `true`, `5`, or no `formatVersion`
- **THEN** it fails with `invalid_format_version_syntax`, `invalid_format_version_type`, `unsupported_format_version_major`, or `missing_format_version`, as the table reader does

#### Scenario: Support table keeps the release grammar
- **WHEN** a caller reads the support table
- **THEN** every interval starts at major 3 or above and its spelling is unchanged

### Requirement: A legacy reader accepts exactly one legacy format
A reader for one legacy format SHALL accept a document only when its `formatVersion` is that legacy integer. Any other recognized version SHALL fail with `unsupported_format_version_major`, naming the version found and the one legacy format accepted. (bead: morphir-ukvn.8.12)

#### Scenario: Format 3 at the format-1 reader
- **WHEN** a document with `formatVersion` 3 is passed to the format-1 reader
- **THEN** reading fails with `unsupported_format_version_major` and says that only legacy format 1 is accepted
