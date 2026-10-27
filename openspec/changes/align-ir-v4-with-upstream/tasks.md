# Tasks

## 1. Per-input attribute drop (morphir-ukvn.8.15)

- [x] 1.1 Add `INPUT_ATTRIBUTES_DROPPED = "input_attributes_dropped"` to `morphir.ir.diagnostics` and `drop_input_attributes(lib)` to `morphir.ir.migrate`, which resets every module and let-bound expression-body input to its declared type and reports one warning per input that lost information; verify unit tests for a changed input, an unchanged input, a let-bound input, and the warning location
- [x] 1.2 Add `drop_input_attributes: bool = False` to `v3_to_v4` and verify that the morphir-elm reference model migrates with 10 warnings (8 module-level and 2 let-bound inputs) and encodes as v4 JSON with the flag, and that without it the v3 to v4 to v3 round trip is still semantically equal
- [x] 1.3 Add `ir convert --drop-input-attributes`, mention the flag in the `no_v4_spelling` input error, and verify CLI tests: without the flag the reference model fails with no output file; with it the tool writes v4 JSON, prints the warnings, and exits 0
- [x] 1.4 Document the drop in the `packages/morphir` README and the codec docstring's gap list, and verify the documented example runs

## 2. Typed hole reasons, incompleteness and incomplete type definitions (morphir-ukvn.8.14.2)

- [x] 2.1 Add `morphir.ir.v4.incompleteness` with `UnresolvedReference`, `DeletedDuringRefactor`, `TypeMismatch`, `HoleReason`, `HoleIncompleteness`, `DraftIncompleteness` and `Incompleteness`, re-exported from `morphir.ir.v4`; verify construction and import-identity tests
- [x] 2.2 Type `Hole.reason` as `HoleReason`, encode and decode reasons with their kit members, and verify that `{"Draft": {}}` as a reason fails with `unknown_node` and a non-object reason fails with a structured error
- [x] 2.3 Add `type_def.IncompleteTypeDefinition(type_params, incompleteness, partial_type_exp)` and its codec spelling, and verify round trips for kit `definitions-0014`, `-0015` and `-0024` in expanded form
- [x] 2.4 Make reverse migration fail with `unsupported_v4_downgrade` for an incomplete type definition and verify the construct name and location

## 3. Value-definition bodies (morphir-ukvn.8.14.1)

- [ ] 3.1 Add `NativeHint` kinds, `NativeInfo`, `ExternalBinding`, `NativeBody`, `ExternalBody`, `IncompleteBody` and `ValueDefinitionBody` to `morphir.ir.v4.value`, widen module values and let bindings to `ValueDefinitionBody`, and verify the type checkers pass
- [ ] 3.2 Encode and decode the three bodies with the kit members, and verify round trips for kit `definitions-0007` to `-0009`, `-0016` and `-0025` in expanded form
- [ ] 3.3 Refuse duplicate target platforms (`duplicate_member`), an empty `externals` list, and a `PlatformSpecific` hint without `platform` (`missing_member`), and verify one test each
- [ ] 3.4 Make reverse migration fail with `unsupported_v4_downgrade` for each new body at module level and in a let binding, and verify the locations
- [ ] 3.5 Make `drop_input_attributes` and the expression-body checks skip the new bodies, which hold bare input types, and verify a Library that mixes bodies encodes

## 4. Annotations on specifications (morphir-ukvn.8.14.3)

- [ ] 4.1 Add `morphir.ir.v4.annotation` with `CompactAnnotation`, `StructuredAnnotation`, `PositionalArgument`, `NamedArgument` and `Annotation`, and an `annotations` field (empty default, last) on module, type and value specifications; verify existing positional constructors still work
- [ ] 4.2 Encode and decode annotations (written first, only when non-empty; `arguments` omitted when empty; compact text after the first colon after `#`), and verify kit `definitions-0020` to `-0022` round trip and that `"arguments": []` reads as an argument-less structured annotation
- [ ] 4.3 Verify that a type definition with `annotations` fails decoding with `unknown_member` (kit `definitions-0023`)
- [ ] 4.4 Make reverse migration fail with `unsupported_v4_downgrade` for annotations on a specification in a v4 dependency, and verify the location

## 5. Union type expression (morphir-ukvn.8.14.4)

- [ ] 5.1 Add `type.Union(attributes, alternatives)` to the `Type` union and `map_attributes`, and verify a substitution-style attribute map keeps order and duplicates
- [ ] 5.2 Encode and decode `{"Union": {"attributes"?, "alternatives": [...]}}`, refuse fewer than two alternatives both ways, and verify round trips including a nested union
- [ ] 5.3 Make reverse migration fail with `unsupported_v4_downgrade` for a union and verify the location

## 6. Deprecations, docs and integration checks (morphir-ukvn.8.14.5)

- [ ] 6.1 Mark the `Native` and `External` value nodes and `TypeConstraints` as deprecated in docstrings, naming the replacement, and verify a test that they still fail encoding with `no_v4_spelling`
- [ ] 6.2 Update the codec module docstring's gap list and the README "Morphir IR versions" section for the new constructs and the typed hole reason, and verify the README examples run
- [ ] 6.3 File a follow-up bead to remove the deprecated constructs and verify it is a child of `morphir-ukvn.8` with label `repo:morphir-python`
- [ ] 6.4 Run `mise run check` and `mise run test-bdd` and verify lint, both type checkers, tests and coverage of at least 80% pass

## Workflow follow-up

- Archive the change in the same PR once all tasks are done, fix the design asset prefix, and relink `morphir-ukvn.8.14` to the archived path
- `morphir-ukvn.8.16` re-syncs the codec with upstream compact spellings when upstream v4 settles
