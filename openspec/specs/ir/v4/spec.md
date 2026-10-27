# ir/v4 Specification

## Purpose
Keeps Morphir IR v4 as a first-class Python model alongside v3, and adds a draft v4 JSON codec, while stating plainly that upstream IR v4 is not yet stable and that this surface will follow upstream changes.

## Requirements

### Requirement: V4 remains a first-class IR surface
The library SHALL continue to expose the current IR v4 model (names, paths, types, values, modules, packages, and the Library, Specs, and Application distributions) as a first-class API usable without converting to v3. (bead: morphir-ukvn.8)

#### Scenario: V4 types stay available
- **WHEN** a caller imports the v4 IR surface
- **THEN** they can construct Library, Specs, and Application distributions and the existing v4 type and value structures

### Requirement: V4 package identity is explicit
The library SHALL make IR v4 reachable at `morphir.ir.v4`. `morphir.ir` and its existing submodule paths SHALL keep working and SHALL re-export the same class objects, so identity and `isinstance` checks agree across paths. (bead: morphir-ukvn.8)

#### Scenario: Versioned and compatibility imports agree
- **WHEN** a caller imports a v4 class from `morphir.ir.v4` and the same class from `morphir.ir` or an existing submodule such as `morphir.ir.name`
- **THEN** both names refer to the same class object

### Requirement: Package release version is optional
The v4 package identity SHALL hold a package name and an optional release version. A missing version SHALL be valid, because v4 JSON has no package-version member and release versions belong to distribution bindings. (bead: morphir-ukvn.8)

#### Scenario: Unversioned package
- **WHEN** a caller constructs a v4 Library without a package release version
- **THEN** construction succeeds and the version reads as absent

### Requirement: Draft v4 JSON codec
The library SHALL encode and decode v4 versioned distributions as `formatVersion` first and a distribution wrapped by its kind (`Library`, `Specs`, `Application`) using finos/morphir v4 JSON profile spellings at a pinned commit. The codec MUST be documented as draft and MUST NOT write morphir-elm format-3 shapes. (bead: morphir-ukvn.8)

#### Scenario: V4 round trip
- **WHEN** a v4 Library built only from constructs the codec supports is encoded and decoded
- **THEN** the result equals the original, except that the package release version is absent

#### Scenario: V4 encode is not format 3
- **WHEN** a v4 distribution is encoded
- **THEN** the output declares `formatVersion` 4 and uses no format-3 tagged-array distribution shape

#### Scenario: Unsupported spelling is refused
- **WHEN** v4 input contains a node kind or member the codec does not recognize
- **THEN** decoding fails with a structured error that names the node and its location, and does not guess

#### Scenario: Construct with no draft spelling
- **WHEN** a caller encodes a v4 value that has no spelling in the pinned v4 JSON profile, such as the Python `Native` or `External` value nodes
- **THEN** encoding fails with a structured error naming the construct rather than dropping it

### Requirement: Draft status is explicit
Documentation for the v4 model and codec SHALL state that IR v4 is a draft upstream, name the pinned finos/morphir commit, and state that spellings may change in later minor releases of this package. (bead: morphir-ukvn.8)

#### Scenario: Draft notice is present
- **WHEN** a user reads the v4 codec documentation
- **THEN** it identifies v4 as draft and names the pinned upstream commit
