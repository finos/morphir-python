# Format-3 golden fixtures

The files in the first table are Morphir IR format 3 (`"formatVersion": 3`) as written by
morphir-elm or published by finos/morphir as v3 examples. They are copied
byte-for-byte and are not edited. Tests read them directly; morphir-elm is not a
test-time dependency.

Both source repositories are licensed under the Apache License, Version 2.0.
Copyright 2020 Morgan Stanley and the FINOS Morphir contributors.

| Fixture | Repository | Commit | Path |
| --- | --- | --- | --- |
| `elm-base.json` | [finos/morphir-elm](https://github.com/finos/morphir-elm) | `bc99af69a8b24d391311fae3822a87eafef3c334` | `tests-integration/cli/test-ir-files/base-ir.json` |
| `elm-listType.json` | finos/morphir-elm | `bc99af69` | `tests-integration/cli/test-ir-files/listType-ir.json` |
| `elm-multilevelModules.json` | finos/morphir-elm | `bc99af69` | `tests-integration/cli/test-ir-files/multilevelModules-ir.json` |
| `elm-simpleTypeTree.json` | finos/morphir-elm | `bc99af69` | `tests-integration/cli/test-ir-files/simpleTypeTree-ir.json` |
| `elm-simpleValueTree.json` | finos/morphir-elm | `bc99af69` | `tests-integration/cli/test-ir-files/simpleValueTree-ir.json` |
| `elm-tupleType.json` | finos/morphir-elm | `bc99af69` | `tests-integration/cli/test-ir-files/tupleType-ir.json` |
| `elm-reference-model.json` | finos/morphir-elm | `bc99af69` | `tests-integration/reference-model/morphir-ir.json` |
| `finos-greeting-example.json` | [finos/morphir](https://github.com/finos/morphir) | `efa36060` | `website/static/ir/examples/v3/greeting-example.json` |
| `finos-rule-set-example.json` | finos/morphir | `efa36060` | `website/static/ir/examples/v3/rule-set-example.json` |

The rentals example is format 2, so it is in [`../legacy/`](../legacy/PROVENANCE.md)
with its format-1 twin, not here.

## Format 3.1.0 fixtures

These files are IR format 3.1.0 (`"formatVersion": "3.1.0"`), each holding a v3
`Specs` distribution (finos/morphir decision record 0018). Upstream they are
inline strings, not files: each fixture is the exact text of that string, with a
trailing newline added, and is not otherwise edited.

Both source repositories are licensed under the Apache License, Version 2.0.

| Fixture | Repository | Commit | Source |
| --- | --- | --- | --- |
| `mck-distributions-0011-specs.json` | [finos/morphir](https://github.com/finos/morphir) | `efa36060` | `spec/ir/mck/distributions.feature`, scenario distributions-0011, its "canonical JSON spelling" |
| `rust-classic-specs-transport.json` | [finos/morphir-rust](https://github.com/finos/morphir-rust) | `cd9f7fb` | `crates/morphir-common/tests/classic_specs_transport.rs`, the `SPECS` constant |
