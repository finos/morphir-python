# Legacy format 1 and 2 golden fixtures

These files are Morphir IR format 1 (`"formatVersion": 1`) and format 2
(`"formatVersion": 2`) as written by morphir-elm. They are the same rentals
example, written once in each format, so both must decode to the same model. They
are copied byte-for-byte and are not edited. Tests read them directly; morphir-elm
is not a test-time dependency.

The source repository is licensed under the Apache License, Version 2.0.
Copyright 2020 Morgan Stanley and the FINOS Morphir contributors.

| Fixture | Format | Repository | Commit | Path |
| --- | --- | --- | --- | --- |
| `elm-rentals-format-1.json` | 1 | [finos/morphir-elm](https://github.com/finos/morphir-elm) | `bc99af69a8b24d391311fae3822a87eafef3c334` | `tests-integration/cli/test-data/rentals/expected-morphir-ir-v1.json` |
| `elm-rentals-format-2.json` | 2 | finos/morphir-elm | `bc99af69` | `tests-integration/cli/test-data/rentals/expected-morphir-ir.json` |

Both files were added to morphir-elm in commit `9497ed82` and have not changed
since.
