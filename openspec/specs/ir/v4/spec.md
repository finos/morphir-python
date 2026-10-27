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
- **WHEN** a caller encodes a v4 value that has no spelling in the pinned v4 JSON profile, such as the deprecated Python `Native` or `External` value nodes, structured type constraints, or a value-definition input whose attributes differ from its declared type
- **THEN** encoding fails with `no_v4_spelling` naming the construct rather than dropping it

### Requirement: Draft status is explicit
Documentation for the v4 model and codec SHALL state that IR v4 is a draft upstream, name the pinned finos/morphir commit, and state that spellings may change in later minor releases of this package. (bead: morphir-ukvn.8)

#### Scenario: Draft notice is present
- **WHEN** a user reads the v4 codec documentation
- **THEN** it identifies v4 as draft and names the pinned upstream commit

### Requirement: Value definitions have upstream bodies
A v4 value definition, at module level or in a let binding, SHALL be one of four bodies: an expression body, a native body with a native hint, an external body with one or more platform bindings and an optional fallback expression, or an incomplete body with an incompleteness and an optional partial expression. Native, external and incomplete bodies MUST hold bare input types. (bead: morphir-ukvn.8.14)

#### Scenario: Native body round trips
- **WHEN** a module value with a native body and an `Arithmetic` hint is encoded and decoded
- **THEN** the JSON is `{"NativeBody": {"inputTypes": ..., "outputType": ..., "nativeInfo": {"hint": {"Arithmetic": {}}}}}` and the decoded value equals the original

#### Scenario: External platforms are unique
- **WHEN** an external body names the same target platform twice
- **THEN** encoding and decoding fail with `duplicate_member`

#### Scenario: External body needs a binding
- **WHEN** an external body has no platform binding
- **THEN** encoding and decoding fail with a structured error

#### Scenario: Platform-specific hint names its platform
- **WHEN** a native body's `PlatformSpecific` hint has no `platform` member
- **THEN** decoding fails with `missing_member`

### Requirement: Incomplete definitions and typed hole reasons
The v4 model SHALL represent an incompleteness as a hole with a typed reason (`UnresolvedReference`, `DeletedDuringRefactor` or `TypeMismatch`) and an optional partial type, or as a draft. A type definition MAY be incomplete, with type parameters, an incompleteness and an optional partial type expression. A `Hole` value SHALL carry a typed reason. (bead: morphir-ukvn.8.14)

#### Scenario: Incomplete type definition round trips
- **WHEN** an incomplete type definition whose hole reason is a type mismatch is encoded and decoded
- **THEN** the JSON is `{"IncompleteTypeDefinition": {"typeParams": [...], "incompleteness": {"Hole": {"reason": {"TypeMismatch": {"expected": ..., "found": ...}}}}}}` and the decoded definition equals the original

#### Scenario: Draft is not a hole reason
- **WHEN** a hole reason is spelled `{"Draft": {}}`
- **THEN** decoding fails with `unknown_node`

### Requirement: Specifications carry annotations
Module, type and value specifications SHALL carry an ordered list of annotations. An annotation SHALL be either compact (a name and optional free text) or structured (a name and positional or named value arguments). The codec SHALL write `annotations` only when the list is non-empty and SHALL omit an empty `arguments` member. Definitions MUST NOT carry annotations. (bead: morphir-ukvn.8.14)

#### Scenario: Compact and structured annotations round trip
- **WHEN** a type alias specification with a compact annotation with text, a structured annotation with one positional and one named argument, and a structured annotation without arguments is encoded and decoded
- **THEN** the compact annotation is written as `"pkg:mod#name:text"`, the argument-less structured annotation as `{"name": ...}`, and the decoded specification equals the original

#### Scenario: Definitions refuse annotations
- **WHEN** a type definition carries an `annotations` member
- **THEN** decoding fails with `unknown_member`

### Requirement: Union type expression
The v4 model SHALL represent an untagged union as a type expression with attributes and an ordered list of two or more alternatives. The codec SHALL preserve alternative order, duplicates and nesting, and MUST refuse a union with fewer than two alternatives. (bead: morphir-ukvn.8.14)

#### Scenario: Union round trips
- **WHEN** a union of `String` and `Int` is encoded and decoded
- **THEN** the JSON is `{"Union": {"alternatives": [..., ...]}}` and the decoded type equals the original

#### Scenario: Singleton union is refused
- **WHEN** a union has one alternative
- **THEN** encoding and decoding fail with a structured error

### Requirement: Python-only v4 constructs are deprecated
The Python `Native` and `External` value nodes and the structured type constraints SHALL stay constructible for compatibility, SHALL be documented as deprecated because upstream v4 has no spelling for them, and MUST keep failing encoding with `no_v4_spelling`. (bead: morphir-ukvn.8.14)

#### Scenario: Deprecated value node still refuses to encode
- **WHEN** a caller encodes a value that contains a Python `Native` value node
- **THEN** encoding fails with `no_v4_spelling`, and the documentation directs the caller to a native definition body
