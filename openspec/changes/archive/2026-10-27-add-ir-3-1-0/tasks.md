# Tasks

## 1. Format-version support table for IR 3.1 (morphir-ukvn.8.13.1)

- [x] 1.1 Write failing tests in `tests/unit/ir/test_format_version.py`: `"3.1.0"` and `"3.1.4"` are supported, `"3.2.0"` fails with `unsupported_format_version_minor` and names `[3.0.0,3.2.0),[4.0.0,4.1.0)`, and the description lists `3.0.x, 3.1.x and draft 4.0.x`; verify they fail
- [x] 1.2 Raise `V3_INTERVAL` to `[3.0.0,3.2.0)`, add `V3_1`, describe each minor family, and drop the issue #28 pointer (design FV-1); verify the format-version tests pass
- [x] 1.3 Update existing tests and docstrings that assumed `[3.0.0,3.1.0)` (`test_format_version.py`, `test_v3_codec.py`, `tests/tools/test_cli.py`); verify `uv run pytest tests/` passes

## 2. V3 Specs distribution model and codec (morphir-ukvn.8.13.2)

- [x] 2.1 Copy the kit case distributions-0011 and the morphir-rust `SPECS` document into `tests/fixtures/ir/v3/` and record both in `PROVENANCE.md` (design TST-1); verify the files parse as JSON
- [x] 2.2 Write failing codec tests: the fixtures round trip and the kit fixture re-encodes to its canonical JSON; `Specs` at `3`, `"3"`, `"3.0.0"`, `"3.0.1"` fails with `specs_before_3_1`; a `Library` at `"3.1.0"` reads and writes `3`; a module definition in a `Specs` fails with `unknown_member`; an unknown tag names both kinds; verify they fail
- [x] 2.3 Add `SPECS_BEFORE_3_1` to `morphir.ir.diagnostics`, the `Specs` dataclass and `Distribution = Library | Specs` to `morphir.ir.v3.distribution`, and export `Specs` from `morphir.ir.v3` (design V3-1)
- [x] 2.4 Decode and encode `Specs` in `morphir.ir.v3.codec`: strict own modules, the version check before the body, and the lowest-version writer (design V3-2 to V3-5); verify the codec tests pass with mypy and pyright strict

## 3. V3 and v4 Specs migrations (morphir-ukvn.8.13.3)

- [x] 3.1 Write failing migration tests: a v3 `Specs` migrates to a v4 `Specs`; a compatible v4 `Specs` downgrades with `package_version_dropped`; a v4 `Specs` without member documentation fails with `unsupported_documentation_downgrade`; an `Application` still fails with `unsupported_v4_downgrade`; the fixtures survive v3 to v4 to v3; verify they fail
- [x] 3.2 Add `Specs` branches and typed overloads to `v3_to_v4` and `v4_to_v3` without touching the `Library` path or any v4 file (design MIG-1); verify the migration tests and doctests pass

## 4. IR interchange CLI and docs for IR 3.1 (morphir-ukvn.8.13.4)

- [x] 4.1 Write failing CLI tests in `tests/tools/test_cli.py` and BDD scenarios in `features/ir_interchange.feature`: inspect a v3 `Specs` reports `format: 3.1.0` and `kind: Specs`; convert a v3 `Specs` to v4 and back; `"3.2.0"` is refused naming `3.0.x, 3.1.x and draft 4.0.x`; verify they fail
- [x] 4.2 Dispatch on the decoded v3 kind in `ir inspect` and `ir convert` and update the help text (design CLI-1); verify the CLI tests and `mise run test-bdd` pass
- [x] 4.3 Update `packages/morphir/README.md` ("Morphir IR versions") and `packages/morphir-tools/README.md` for 3.1.0, `Specs`, `specs_before_3_1`, the lowest-version writer and the document-tree scope; verify `tests/unit/ir/test_ir_docs.py` passes

## 5. Integration checks for IR 3.1 (morphir-ukvn.8.13.5)

- [x] 5.1 Run `mise run check` (lint, format check, mypy and pyright strict, tests, coverage at least 80%) and `mise run test-bdd`; verify both pass
- [x] 5.2 Run `openspec validate add-ir-3-1-0 --strict`; verify it reports the change as valid

## Workflow follow-up

- Archive the change in the same branch with the `openspec-archive-change` skill, fix the design asset prefix, and set the epic spec id to the archived path.
- Open the pull request; the coordinator merges it and closes `morphir-ukvn.8.13`.
