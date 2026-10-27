## REMOVED Requirements

### Requirement: Support table is checked before decoding
**Reason**: The table now includes IR 3.1, so the scenario that refused `"3.1.0"` no longer holds.
**Migration**: See the requirement "Support table with IR 3.1 is checked before decoding".

## ADDED Requirements

### Requirement: Support table with IR 3.1 is checked before decoding
The reader SHALL declare the support table `[3.0.0,3.2.0),[4.0.0,4.1.0)` and MUST finish recognition and the support check before invoking any distribution decoder or migration. A release outside the table SHALL fail with `unsupported_format_version_major` or `unsupported_format_version_minor`. (bead: morphir-ukvn.8.13)

#### Scenario: IR 3.1.0 is supported
- **WHEN** a document declares `formatVersion` `"3.1.0"` or `"3.1.4"`
- **THEN** the support check passes and the distribution is decoded

#### Scenario: A later 3.x minor is refused
- **WHEN** a document declares `formatVersion` `"3.2.0"`
- **THEN** reading fails with `unsupported_format_version_minor` before the distribution is decoded, and the message names the accepted table `[3.0.0,3.2.0),[4.0.0,4.1.0)`

#### Scenario: Historical versions are refused
- **WHEN** a document declares `formatVersion` `1` or `2`
- **THEN** reading fails with `unsupported_format_version_major` and a message that formats 1 and 2 are follow-up work
