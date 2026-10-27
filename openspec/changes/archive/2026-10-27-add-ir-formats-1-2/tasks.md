# Tasks

## 1. Legacy format-version reading (morphir-ukvn.8.12.1)

- [x] 1.1 Add `LegacyFormat`, `recognize_legacy_format`, `read_document_with_legacy` and `read_legacy_document` to `morphir.ir.format_version` without changing the support table; verify with `tests/unit/ir/test_format_version.py::TestLegacy`
- [x] 1.2 Name the legacy readers in the `unsupported_format_version_major` message for 1 and 2, and make `write_format_version` refuse majors 1 and 2; verify with the updated `TestSupport` and `TestWriting` tests
- [x] 1.3 Document the legacy path in the `format_version` module docstring; verify that the doctests in `tests/unit/ir/test_ir_docs.py` pass

## 2. Format 1 and format 2 decoders (morphir-ukvn.8.12.2)

- [x] 2.1 Copy the morphir-elm rentals example in format 1 and format 2 to `tests/fixtures/ir/legacy/` with a `PROVENANCE.md`, and point the v3 provenance note at it; verify that the files match the morphir-elm `bc99af69` files byte for byte
- [x] 2.2 Add the shared snake_case value and pattern decoders in `morphir.ir.v3._legacy_value`; verify through the value and pattern tests of 2.3 and 2.4
- [x] 2.3 Port the CodecV1 decoders to `morphir.ir.v3.codec_v1`; verify every tag and wrapper with `tests/unit/ir/test_v3_legacy_codec.py` (format-1 classes)
- [x] 2.4 Add the format-2 decoders in `morphir.ir.v3.codec_v2`; verify with the `TestFormat2` tests
- [x] 2.5 Check both rentals fixtures decode to the same Library, upgrade to format 3 and v4, and stay refused by the 3.0.0 decoder; verify with `TestElmFixtures`

## 3. CLI upgrade of legacy files (morphir-ukvn.8.12.3)

- [x] 3.1 Make `ir inspect` report legacy files and `ir convert` upgrade them to v3 and v4; verify with the legacy tests in `tests/tools/test_cli.py`, which replace the tests that expected 1 and 2 to be refused
- [x] 3.2 Add BDD scenarios for inspecting and upgrading a legacy file to `features/ir_interchange.feature`; verify with `mise run test-bdd`

## 4. Docs and integration checks (morphir-ukvn.8.12.4)

- [x] 4.1 Describe legacy formats 1 and 2 in `packages/morphir/README.md` and `packages/morphir-tools/README.md`, and list the new modules in the `morphir.ir.v3` docstring; verify with `tests/unit/ir/test_ir_docs.py`
- [x] 4.2 Run `mise run check` and `mise run test-bdd`; verify lint, format, mypy, pyright, tests and coverage of at least 80% pass

## Workflow follow-up

- Archive the change in the same branch with the `openspec-archive-change` skill; fix the design.html asset prefix and set the epic spec id to the archived path.
- Open the pull request, watch CI and review, and close the group beads.
