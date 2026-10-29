# Spec Delta

## ADDED Requirements

### Requirement: Final extension release assets retain verified integrity
The extension release SHALL verify that the WASM checksum contents match its bytes and descriptor. A digest receipt covering final published asset names, including a renamed descriptor, MUST be checked immediately before GitHub publication. A checksum or source-provenance mismatch MUST block publication. (bead: morphir-bj9r)

#### Scenario: Checksum syntax is valid but its digest is wrong
- **WHEN** the checksum file contains a correctly formatted digest that differs from the WASM bytes
- **THEN** candidate qualification refuses the bundle

#### Scenario: Descriptor receives its public asset name
- **WHEN** the verified descriptor is staged under its versioned GitHub asset name
- **THEN** the final receipt names that asset and publication verifies its bytes along with the WASM, checksum and staged qualification reports

#### Scenario: Staged asset changes before publication
- **WHEN** a file named by the final release receipt is missing or has different bytes
- **THEN** publication fails before creating or updating the GitHub release
