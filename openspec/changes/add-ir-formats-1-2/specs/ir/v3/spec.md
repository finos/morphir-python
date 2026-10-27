# Spec Delta

## ADDED Requirements

### Requirement: Format 1 is read into the format 3.0.0 model
The library SHALL decode `"formatVersion": 1` documents with the spellings of the morphir-elm `*/CodecV1.elm` decoders at `bc99af69` into the v3 model: snake_case tags, `["public", x]` access control, `[doc, x]` or bare documentation, `[name, type]` record fields, `{"name", "spec"}` and `{"name", "def"}` package modules, and no module documentation. (bead: morphir-ukvn.8.12)

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
