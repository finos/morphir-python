# Format-4 example fixtures

These files are the v4 example distributions that finos/morphir publishes. They
use the compact v4 spelling. They are copied byte-for-byte and are not edited.

The source repository is licensed under the Apache License, Version 2.0.
Copyright 2020 Morgan Stanley and the FINOS Morphir contributors.

| Fixture | Repository | Commit | Path |
| --- | --- | --- | --- |
| `finos-books-and-records-example.json` | [finos/morphir](https://github.com/finos/morphir) | `efa360608cf977d807695be33d60571e4f9c3e05` | `website/static/ir/examples/v4/books-and-records-example.json` |
| `finos-complete-example.json` | finos/morphir | `efa36060` | `website/static/ir/examples/v4/complete-example.json` |

Kit case distributions-0004 says that a reader accepts `complete-example.json`.
Its module path `u-s/f-r-2052-a` has adjacent single-letter words, which the
Python word-list name model cannot represent, so the tests expect `invalid_name`
at that module and decode the rest after a substitution.
