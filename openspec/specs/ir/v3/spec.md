# ir/v3 Specification

## Purpose
Provides a first-class Morphir IR format 3 model and JSON codecs in Python (3.0.0, with morphir-elm as the normative source, and the 3.1.0 Specs distribution, with finos/morphir as the normative source), so tooling can load and produce the IR that morphir-elm and other v3 tools emit.

## Requirements

### Requirement: morphir-elm is normative for v3 content
The v3 model and JSON shapes SHALL follow morphir-elm `Morphir.IR.*` types and `*.Codec` modules for format 3.0.0. Where finos/morphir v3 schemas or docs disagree with morphir-elm on 3.0.0 content, morphir-elm MUST win. What format 3.1.0 adds, which morphir-elm does not implement, SHALL follow the finos/morphir v3 specification and decision record 0018. (bead: morphir-ukvn.8.13)

#### Scenario: Elm output decodes
- **WHEN** a `morphir-ir.json` written by morphir-elm `morphir make` is decoded
- **THEN** decoding succeeds without a Python-specific JSON variant

#### Scenario: The finos 3.1.0 example decodes
- **WHEN** the v3 `Specs` document of the finos/morphir kit case distributions-0011 is decoded and encoded again
- **THEN** decoding succeeds and the output is equal to the kit's canonical JSON

### Requirement: V3 model mirrors morphir-elm concepts
The library SHALL expose a v3 model whose concepts match morphir-elm: names as word lists, paths, qualified and fully qualified names, access control, documented values, literals, types, values, patterns, modules, packages, and the `Library` distribution, plus the `Specs` distribution of format 3.1.0. A v3 `Library` SHALL carry type attributes of unit and value attributes of a v3 type, as in elm. (bead: morphir-ukvn.8.13)

#### Scenario: Library distribution is representable
- **WHEN** a caller constructs a v3 Library with a package name, dependency specifications, and a package definition whose values carry types
- **THEN** the model keeps those parts without any v4-only construct

#### Scenario: Library has no package version
- **WHEN** a caller constructs a v3 Library
- **THEN** the model has no package release version, because format 3.0.0 has none

#### Scenario: Specs distribution is representable
- **WHEN** a caller constructs a v3 Specs with a package name, dependency specifications, and a package specification
- **THEN** the model keeps those parts, holds no definitions, and has no package release version

### Requirement: V3 JSON matches morphir-elm format 3.0.0
The library SHALL encode and decode versioned distribution JSON with the shapes of morphir-elm `Morphir.IR.FormatVersion.Codec` and the codecs it uses. Node codecs SHALL take attribute codecs as parameters, as elm does. Version recognition SHALL use the shared format-version reader. (bead: morphir-ukvn.8.13)

#### Scenario: Round trip versioned morphir-ir.json
- **WHEN** a valid morphir-elm `morphir-ir.json` with `formatVersion` 3 is decoded and encoded again
- **THEN** the output declares `formatVersion` 3 and its distribution is semantically equal to the input

#### Scenario: String version is accepted on read
- **WHEN** an otherwise valid format-3 document declares `formatVersion` `"3.0.0"`
- **THEN** it decodes, and encoding writes the integer `3`

#### Scenario: Wrong family at the v3 entry point
- **WHEN** a document with `formatVersion` 4 is passed to the v3 decoder
- **THEN** decoding fails with `unsupported_format_version_major` naming the found version and that only 3.0.x and 3.1.x are accepted

#### Scenario: Unknown distribution kind
- **WHEN** a format-3 document has a distribution tag other than `Library` or `Specs`
- **THEN** decoding fails with `unknown_node` naming the tag and both known kinds

### Requirement: V3 is independently usable
Callers SHALL be able to construct, inspect, encode, and decode v3 IR without converting to v4, and v3 classes SHALL be distinct from v4 classes. (bead: morphir-ukvn.8)

#### Scenario: Inspect without migration
- **WHEN** a caller loads a format-3 distribution
- **THEN** they can read package, module, type, and value structure through the v3 API alone

#### Scenario: Versions do not mix
- **WHEN** a caller passes a v4 node where the v3 model expects a v3 node
- **THEN** static type checking reports an error

### Requirement: V3 Specs distribution JSON
The library SHALL encode and decode a v3 `Specs` distribution as `["Specs", package, dependencies, specification]`, where `specification` is a package specification whose modules are spelled as a dependency's modules are. (bead: morphir-ukvn.8.13)

#### Scenario: Specs round trips
- **WHEN** a document with `formatVersion` `"3.1.0"` and a `Specs` distribution is decoded and encoded again
- **THEN** the output declares `formatVersion` `"3.1.0"` and its distribution is semantically equal to the input

#### Scenario: A Specs distribution with dependencies
- **WHEN** a `Specs` distribution lists dependency package specifications
- **THEN** they decode as the dependencies of a `Library` do

### Requirement: A Specs distribution needs 3.1.0 or later
The v3 reader SHALL refuse a `Specs` distribution whose document declares a release below `3.1.0`, such as `3`, `"3"` or `"3.0.1"`, with `specs_before_3_1` at the `formatVersion` member. A `Library` SHALL stay readable at every supported 3.x release. (bead: morphir-ukvn.8.13)

#### Scenario: Specs declared as 3 is refused
- **WHEN** a document declares `formatVersion` `3`, `"3"`, `"3.0.0"` or `"3.0.1"` and holds a `Specs` distribution
- **THEN** decoding fails with `specs_before_3_1`

#### Scenario: Library declared as 3.1.0 is read
- **WHEN** a document declares `formatVersion` `"3.1.0"` and holds a `Library` distribution
- **THEN** it decodes as a v3 Library

### Requirement: A Specs distribution holds specifications only
The v3 reader SHALL refuse a member other than `types`, `values` and `doc` in a module of a `Specs` distribution's own package specification with `unknown_member`, so a module definition is not read as a specification. Dependency modules keep the morphir-elm reading. (bead: morphir-ukvn.8.13)

#### Scenario: A module definition in a Specs is refused
- **WHEN** a `Specs` distribution's own module is spelled `{"access": "Public", "value": {...}}`
- **THEN** decoding fails with `unknown_member` at that module

### Requirement: Writers emit the lowest version that fits
The v3 writer SHALL emit `formatVersion` `3` for a `Library` and `"3.1.0"` for a `Specs`, whatever version the input declared, so every reader of 3.0.0 still reads every `Library` this library writes. (bead: morphir-ukvn.8.13)

#### Scenario: Library read as 3.1.0 is written as 3
- **WHEN** a `Library` read from a document that declares `"3.1.0"` is encoded
- **THEN** the output declares the integer `formatVersion` `3`

#### Scenario: Specs is written as 3.1.0
- **WHEN** a v3 `Specs` is encoded
- **THEN** the output declares `formatVersion` `"3.1.0"`

### Requirement: Format 1 is read into the format 3.0.0 model
The library SHALL decode `"formatVersion": 1` documents with the spellings of the morphir-elm `*/CodecV1.elm` decoders at `bc99af69` into a v3 `Library`, never a `Specs`: snake_case tags, `["public", x]` access control, `[doc, x]` or bare documentation, `[name, type]` record fields, `{"name", "spec"}` and `{"name", "def"}` package modules, and no module documentation. (bead: morphir-ukvn.8.12)

#### Scenario: morphir-elm format-1 output decodes
- **WHEN** the morphir-elm rentals example written as format 1 is decoded
- **THEN** decoding succeeds and gives a v3 Library with the package name `morphir/example/app`

#### Scenario: Format-3 tags are refused in format 1
- **WHEN** a format-1 type, value, literal, or distribution uses a TitleCase tag such as `"Variable"` or `"Library"`
- **THEN** decoding fails with `unknown_node`

#### Scenario: Documentation pair or bare value
- **WHEN** a format-1 documented entry is `["a doc", x]` or the bare `x`
- **THEN** it decodes with doc `"a doc"` or `""`, and when both readings fail the error carries the diagnostics of both

#### Scenario: Derived types use the elm decoder spelling
- **WHEN** a format-1 type specification is tagged `"derived_type_specification"`
- **THEN** it decodes, while `"DerivedTypeSpecification"`, which only the elm encoder wrote, fails with `unknown_node`

### Requirement: Format 2 is read into the format 3.0.0 model
The library SHALL decode `"formatVersion": 2` documents whose shapes are those of format 3.0.0 except that value and pattern tags are snake_case, as in morphir-elm `Value/CodecV2.elm` at `02aa36af`. Literals and types SHALL use their format-3 TitleCase tags, as morphir-elm wrote them. Reading format 2 is a deliberate divergence from morphir-elm, which now refuses it. (bead: morphir-ukvn.8.12)

#### Scenario: morphir-elm format-2 output decodes
- **WHEN** the morphir-elm rentals example written as format 2 is decoded
- **THEN** decoding succeeds and gives a v3 Library

#### Scenario: Mixed spellings are refused
- **WHEN** a format-2 value uses the tag `"Literal"`, or a literal inside it uses `"bool_literal"`
- **THEN** decoding fails with `unknown_node`

### Requirement: Legacy formats upgrade to format 3.0.0
Formats 1 and 2 SHALL decode into the same v3 model as format 3.0.0, so encoding the result with the format 3.0.0 codec is the upgrade, and the v3-to-v4 migration applies unchanged. The library MUST NOT provide encoders for formats 1 and 2, and the format 3.0.0 decoder SHALL keep refusing them. (bead: morphir-ukvn.8.12)

#### Scenario: Both legacy formats give one model
- **WHEN** the rentals example is decoded from its format-1 file and from its format-2 file
- **THEN** both give the same v3 Library

#### Scenario: Upgrade writes format 3
- **WHEN** a decoded legacy document is encoded with the format 3.0.0 codec
- **THEN** the output declares `formatVersion` 3 and decodes back to the same Library

#### Scenario: The format 3.0.0 entry point stays strict
- **WHEN** a format-1 or format-2 document is passed to the format 3.0.0 decoder
- **THEN** decoding fails with `unsupported_format_version_major`
