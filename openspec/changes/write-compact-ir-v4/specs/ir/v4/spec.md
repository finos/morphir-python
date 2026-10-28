# Spec Delta

## ADDED Requirements

### Requirement: Write the compact canonical v4 spelling
By default, the v4 encoders SHALL write the compact canonical spelling of the pinned finos/morphir v4 JSON profile, as morphir-core writes it at the same profile. A node without attributes SHALL use its shortest schema-valid form, and a node that carries attributes SHALL keep the expanded spelling with `attributes` first. (bead: morphir-ukvn.8.16)

#### Scenario: Compiler output re-encodes byte for byte
- **WHEN** a v4 document written by morphir-core 0.2.0 for a compiled Python model is decoded and encoded with the default spelling
- **THEN** the encoded JSON equals the original document, including member order

#### Scenario: Compact node forms
- **WHEN** a model with type variables, argument-free and applied type references, tuples, literals, variables, references, constructors, field functions, lists, tuple patterns and literal patterns is encoded
- **THEN** they are written as name or FQName strings, `{"Reference": [fqname, args...]}`, `{"Tuple": [...]}`, `{"Kind": payload}` literals, and wrappers holding their payload directly

#### Scenario: Attributes keep the expanded spelling
- **WHEN** a type or value carrying a source location or an inferred type is encoded
- **THEN** that node is written in the expanded spelling with `attributes` first, while nodes without attributes stay compact

### Requirement: Write documentation flattened
The v4 encoders SHALL write documentation flattened, with `doc` first beside the documented node's own members (decision 0010), and SHALL NOT write the nested `{"doc", "value"}` wrapper. (bead: morphir-ukvn.8.16)

#### Scenario: Documented type definition
- **WHEN** a documented type definition is encoded
- **THEN** `doc` is its first member, followed by the definition's members, and decoding returns the same documentation and definition

### Requirement: Select the expanded spelling
Callers SHALL be able to select the expanded spelling, which writes every node in its expanded form. Both spellings SHALL decode to the model that was encoded. (bead: morphir-ukvn.8.16)

#### Scenario: Expanded spelling on request
- **WHEN** a caller selects the expanded spelling for a model
- **THEN** every node is written expanded, and decoding returns the same model as decoding the default output
