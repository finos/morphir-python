# ir/v3 Specification

## Purpose
Provides a first-class Morphir IR format 3.0.0 model and JSON codecs in Python, with morphir-elm as the normative source, so tooling can load and produce the IR that morphir-elm emits today.

## Requirements

### Requirement: morphir-elm is normative for v3 content
The v3 model and JSON shapes SHALL follow morphir-elm `Morphir.IR.*` types and `*.Codec` modules for format 3.0.0. Where finos/morphir v3 schemas or docs disagree with morphir-elm on 3.0.0 content, morphir-elm MUST win. (bead: morphir-ukvn.8)

#### Scenario: Elm output decodes
- **WHEN** a `morphir-ir.json` written by morphir-elm `morphir make` is decoded
- **THEN** decoding succeeds without a Python-specific JSON variant

### Requirement: V3 model mirrors morphir-elm concepts
The library SHALL expose a v3 model whose concepts match morphir-elm: names as word lists, paths, qualified and fully qualified names, access control, documented values, literals, types, values, patterns, modules, packages, and the `Library` distribution. A v3 `Library` SHALL carry type attributes of unit and value attributes of a v3 type, as in elm. (bead: morphir-ukvn.8)

#### Scenario: Library distribution is representable
- **WHEN** a caller constructs a v3 Library with a package name, dependency specifications, and a package definition whose values carry types
- **THEN** the model keeps those parts without any v4-only construct

#### Scenario: Library has no package version
- **WHEN** a caller constructs a v3 Library
- **THEN** the model has no package release version, because format 3.0.0 has none

### Requirement: V3 JSON matches morphir-elm format 3.0.0
The library SHALL encode and decode versioned distribution JSON with the shapes of morphir-elm `Morphir.IR.FormatVersion.Codec` and the codecs it uses. Node codecs SHALL take attribute codecs as parameters, as elm does. Version recognition SHALL use the shared format-version reader. (bead: morphir-ukvn.8)

#### Scenario: Round trip versioned morphir-ir.json
- **WHEN** a valid morphir-elm `morphir-ir.json` with `formatVersion` 3 is decoded and encoded again
- **THEN** the output declares `formatVersion` 3 and its distribution is semantically equal to the input

#### Scenario: String version is accepted on read
- **WHEN** an otherwise valid format-3 document declares `formatVersion` `"3.0.0"`
- **THEN** it decodes, and encoding writes the integer `3`

#### Scenario: Wrong family at the v3 entry point
- **WHEN** a document with `formatVersion` 4 is passed to the v3 decoder
- **THEN** decoding fails with `unsupported_format_version_major` naming the found version and that only 3.0.x is accepted

#### Scenario: Unknown distribution kind
- **WHEN** a format-3 document has a distribution tag other than `Library`
- **THEN** decoding fails with a structured error naming the tag

### Requirement: V3 is independently usable
Callers SHALL be able to construct, inspect, encode, and decode v3 IR without converting to v4, and v3 classes SHALL be distinct from v4 classes. (bead: morphir-ukvn.8)

#### Scenario: Inspect without migration
- **WHEN** a caller loads a format-3 distribution
- **THEN** they can read package, module, type, and value structure through the v3 API alone

#### Scenario: Versions do not mix
- **WHEN** a caller passes a v4 node where the v3 model expects a v3 node
- **THEN** static type checking reports an error
