# Format-3 golden fixtures

These files are Morphir IR format 3 (`"formatVersion": 3`) as written by
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

The rentals example is format 2 and is deliberately not included.
