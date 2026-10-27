# Proposal

## Why

Morphir IR format version 3 is what morphir-elm writes today (`currentFormatVersion = 3`), but morphir-python only models IR v4 and has no JSON decoder at all. Without a first-class v3 library, a format-version reader, and migrations, this repo cannot load or produce the IR existing tooling emits, and later v4 work has no stable baseline to migrate from.

## What Changes

- Add a shared format-version reader (`morphir.ir.format_version`) that accepts integer and string spellings (`3`, `"3"`, `"3.0.0"`), normalizes them to an exact release, checks a declared support table, and reports the stable diagnostic codes from the finos/morphir format-version contract. Accepting the string forms is a deliberate divergence from morphir-elm's integer-only decoder.
- Add a first-class Python IR for format 3.0.0 (`morphir.ir.v3`). morphir-elm's types and `*.Codec` modules are normative for v3 content; where finos/morphir's v3 schema or docs disagree, elm wins.
- Make today's IR explicitly first-class v4 (`morphir.ir.v4`). `morphir.ir` and its existing submodule paths keep re-exporting the same class objects.
- Add a **draft** v4 JSON codec (`formatVersion` 4 envelope, finos/morphir v4 JSON profile spellings) so v4 can be read and written at all. IR v4 is not frozen upstream; the codec pins a finos/morphir commit and is labelled draft.
- Make `PackageInfo.version` optional (`str | None`), because v4 JSON has no package-version slot (finos/morphir decision 0017) and v3 has none either.
- Add migrations: v3→v4 forward; v4→v3 lossy with structured failures that reuse upstream diagnostic codes where they exist.
- Add a Typer CLI in `morphir-tools` with `ir inspect` and `ir convert`.
- IR format versions 1 and 2, and IR 3.1.0 (v3 `Specs` and v3 document trees), remain follow-up work.

## Capabilities

### New Capabilities

- `ir/format-version`: Recognition, normalization, support-table checks, and diagnostics for the `formatVersion` field shared by every IR codec (**author call:** keep separate, do not fold into `ir/v3`)
- `ir/v3`: First-class Morphir IR format 3.0.0 model and JSON codecs, with morphir-elm as the normative source
- `ir/v4`: First-class Morphir IR v4 model surface and a draft v4 JSON codec, with draft status stated explicitly (**author call:** draft codec is its own task group / bead `morphir-ukvn.8.11`)
- `ir/migrate`: Migrations between IR v3 and IR v4, including attribute mapping and lossy-downgrade failure reporting
- `tools/ir-interchange`: CLI inspect and convert for versioned `morphir-ir.json`

### Modified Capabilities

- (none — no existing openspec capabilities yet)

## Beads

- **Tracked by**: `morphir-ukvn.8`
- **Related**: `morphir-1dc1` (closed; Rust/Python extension IR v3/v4, related ecosystem work with a different deliverable), `morphir-ukvn` (roadmap parent). Upstream: finos/morphir bead `morphir-diwy` owns the ecosystem v4→v3 downgrade rules; [finos/morphir-python#28](https://github.com/finos/morphir-python/issues/28) tracks adopting IR 3.1.0.

## Impact

- `packages/morphir`: new `ir.format_version`, `ir.v3`, `ir.v4` (relocated modules plus shims at old paths), draft v4 JSON codec, `ir.migrate`; `PackageInfo.version` becomes optional. Core stays dependency-free.
- `packages/morphir-tools`: Typer dependency (tools package only) and a `morphir-tools` console script.
- Tests: golden format-3 fixtures copied from morphir-elm and finos/morphir with provenance recorded.
- Documentation and agent guidance for dual-version IR; no change to morphir-elm or finos/morphir.
