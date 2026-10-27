# Spec Delta

## MODIFIED Requirements

### Requirement: Support table is checked before decoding
The reader SHALL declare the support table `[3.0.0,3.1.0),[4.0.0,4.1.0)` and MUST finish recognition and the support check before invoking any distribution decoder or migration. A release outside the table SHALL fail with `unsupported_format_version_major` or `unsupported_format_version_minor`. (bead: morphir-ukvn.8)

#### Scenario: IR 3.1.0 is refused for now
- **WHEN** a document declares `formatVersion` `"3.1.0"`
- **THEN** reading fails with `unsupported_format_version_minor` before the distribution is decoded

#### Scenario: Historical versions are refused
- **WHEN** a document declares `formatVersion` `1` or `2` and is read against a support table
- **THEN** reading fails with `unsupported_format_version_major` and a message that names the legacy readers for formats 1 and 2

### Requirement: Canonical format version output
Writers SHALL emit `formatVersion` first, as the integer `N` for a baseline release `N.0.0` and as the exact release string otherwise, regardless of the spelling that was read. Writers MUST NOT emit the legacy formats 1 and 2. (bead: morphir-ukvn.8)

#### Scenario: Read string, write integer
- **WHEN** a document read with `formatVersion` `"3.0.0"` is written again
- **THEN** the output declares `formatVersion` as the integer `3`

#### Scenario: Legacy versions are never written
- **WHEN** a caller asks for the spelling of format 1 or 2
- **THEN** the writer refuses instead of returning `1` or `2`

## ADDED Requirements

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
