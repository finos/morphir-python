# Tasks

Implement against `design.html` and the two delta specs. Follow TDD; claim the group bead before work and close it with test and commit evidence.

## 1. Write compact canonical v4 and flattened documentation (morphir-ukvn.8.16.1)

- [x] 1.1 Add `Spelling` and its per-call selection to the v4 encoders, write the compact forms of types, literals, values and patterns without attributes, and keep the expanded form for nodes with attributes; verify that decoding and re-encoding the checked-in morphir-core compiler fixtures gives byte-identical JSON, that a unit test covers each compact node form, and that a test over every node kind finds no compact form in expanded output.
- [x] 1.2 Write documentation flattened with `doc` first in both spellings; verify round trips of documented type and value definitions and specifications, and refusal with `no_v4_spelling` of a documented node that is not an object.
- [x] 1.3 Add `--v4-spelling compact|expanded` to `ir convert`, update the codec docstring, README and CLI docs; verify CLI tests for both values and a rejected value, `ir inspect` of compact output, the existing v3/v4 conversion and BDD tests, and `mise run check`.
