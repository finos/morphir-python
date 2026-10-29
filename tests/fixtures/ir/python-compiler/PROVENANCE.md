# Python compiler output fixtures

These files are the IR documents that the migrated Python compiler wrote for a
small `acme/example` package. The compiler is `morphir-python-binding` 0.4.0
(`rust/crates/morphir-python-binding`), which writes IR through Rust
`morphir-core` 0.2.0. `morphir-core` writes the compact canonical v4 spelling.

Each file is the `ir` member of a probe result, written again with two-space
indentation. No value is edited.

| Fixture | Format | Probe |
| --- | --- | --- |
| `modules-v4.json` | v4 (`"formatVersion": 4`) | modules `models` and `rules` |
| `adt-v4.json` | v4 (`"formatVersion": 4`) | the same modules, with more value bodies |
| `modules-v3.json` | v3 (`"formatVersion": 3`) | the v3 output for `modules-v4.json` |

`tests/unit/ir/test_v4_compact.py` reads them.
