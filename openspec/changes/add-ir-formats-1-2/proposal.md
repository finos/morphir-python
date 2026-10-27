# Proposal

## Why

morphir-elm wrote `"formatVersion": 1` until October 2021 and `"formatVersion": 2` until May 2023, and old `morphir-ir.json` files in those formats still exist. morphir-python refuses both with `unsupported_format_version_major`, so a user with an old file must find an old morphir-elm to regenerate it. morphir-elm still reads format 1 through its `CodecV1` modules; this change gives morphir-python the same ability, extends it to format 2, and upgrades both to format 3.0.0.

## What Changes

- Add read-only decoders for format 1 (port of morphir-elm `*/CodecV1.elm` at `bc99af69`) and format 2 (format 3.0.0 shapes with the snake_case value and pattern tags of morphir-elm `Value/CodecV2.elm` at `02aa36af`). Both decode into the existing format 3.0.0 model, as elm does, so encoding the result with the 3.0.0 codec is the upgrade.
- Reading format 2 is a deliberate divergence from morphir-elm today, which refuses it ("Please regenerate it!").
- Teach the shared format-version reader to recognize the legacy integers `1` and `2` through a separate legacy path. The support table, its spelling, and the existing diagnostic codes stay as they are: the finos release grammar starts at major 3, so formats 1 and 2 never enter a support table, and `read_format_version` still refuses them. No writer emits format 1 or 2.
- `morphir-tools ir inspect` reports legacy files, and `ir convert` upgrades them to format 3.0.0 or draft v4. Today both commands refuse formats 1 and 2.
- Add the morphir-elm rentals example in format 1 and format 2 as golden fixtures, with provenance.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `ir/format-version`: formats 1 and 2 are recognized as legacy, read-only formats outside the support table, instead of being refused as follow-up work; legacy formats are never written.
- `ir/v3`: legacy decoders read formats 1 and 2 into the format 3.0.0 model.
- `tools/ir-interchange`: inspect and convert accept formats 1 and 2 and upgrade them; only IR 3.1.0 stays refused by this change.

## Beads

- **Tracked by**: `morphir-ukvn.8.12`
- **Related**: `morphir-ukvn.8` (parent epic, first-class IR v3), `morphir-ukvn.8.13` (IR 3.1.0, in progress in parallel; it changes the support table and the 3.1 refusal, which this change leaves alone)

## Impact

- `packages/morphir`: `ir.format_version` gains `LegacyFormat`, `recognize_legacy_format`, `read_document_with_legacy` and `read_legacy_document`; `write_format_version` refuses majors 1 and 2. New modules `ir.v3.codec_v1`, `ir.v3.codec_v2` and the private `ir.v3._legacy_value`. The 3.0.0 codec and the v4 package do not change. No new dependency.
- `packages/morphir-tools`: `ir inspect` and `ir convert` dispatch on legacy formats.
- Tests and fixtures: `tests/fixtures/ir/legacy/` with two morphir-elm files; unit, CLI and BDD tests. The CLI tests that expected formats 1 and 2 to be refused change.
- Documentation: the `morphir` and `morphir-tools` READMEs.
