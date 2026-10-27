# Proposal

## Why

IR format `3.1.0` is a minor revision of the classic IR (finos/morphir decision record 0018, issue finos/morphir#970). It adds a v3 `Specs` distribution, which publishes the public face of a package without its definitions. The reference support table is now `[3.0.0,3.2.0),[4.0.0,4.1.0)`, and morphir-rust reads and writes `3.1.0` (finos/morphir-rust `cd9f7fb`). morphir-python still declares `[3.0.0,3.1.0)` for v3, so it refuses every `3.1.0` file with `unsupported_format_version_minor`, and it cannot write a v4 `Specs` distribution as v3. Issue [finos/morphir-python#28](https://github.com/finos/morphir-python/issues/28) asks to close that gap.

## What Changes

- Raise the support table to `[3.0.0,3.2.0),[4.0.0,4.1.0)`. `"3.1.0"` (and every `3.1.x`) is supported; `"3.2.0"` still fails with `unsupported_format_version_minor`. **BREAKING** for a caller that relies on `3.1.0` being refused.
- Add a v3 `Specs` distribution to `morphir.ir.v3`: `["Specs", package, dependencies, { modules }]`, where the fourth element is a package specification. A v3 distribution is now `Library | Specs`. **BREAKING** for a caller that types the v3 decoder result as `Library` only.
- Refuse a `Specs` distribution that declares a release below `3.1.0` (`3`, `"3"`, `"3.0.x"`) with the new diagnostic `specs_before_3_1`. Refuse a module definition among a `Specs` distribution's own modules.
- Writers emit the lowest version that fits: a v3 `Library` keeps `formatVersion: 3`, even when it was read as `"3.1.0"`; a v3 `Specs` writes `"3.1.0"`.
- Migrations: a v3 `Specs` migrates to a v4 `Specs` (`formatVersion` 4), and a v4 `Specs` downgrades to a v3 `Specs` with the same rules and diagnostics as the dependency specifications of a `Library`. An `Application` still has no v3 form.
- `morphir-tools ir inspect` reports a v3 `Specs`; `ir convert` converts `Specs` in both directions.
- Document the change in `packages/morphir/README.md` ("Morphir IR versions") and the `morphir-tools` README.
- v3 document trees, the other half of decision 0018, stay out of scope: morphir-python has no document tree for v4 either. Follow-up bead `morphir-ukvn.8.17` tracks them.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `ir/format-version`: the support table becomes `[3.0.0,3.2.0),[4.0.0,4.1.0)`.
- `ir/v3`: the v3 model and codec gain the `Specs` distribution, the `specs_before_3_1` refusal, the strict reading of a `Specs` distribution's own modules, and the lowest-version writer rule; finos/morphir is normative for what `3.1.0` adds.
- `ir/migrate`: `Specs` migrates in both directions; only `Application` is refused on downgrade.
- `tools/ir-interchange`: inspect and convert handle a v3 `Specs` and `3.1.0` input; the scope limit moves from `3.1.x` to later 3.x minors.

## Beads

- **Tracked by**: `morphir-ukvn.8.13`
- **Related**: `morphir-ukvn.8` (parent epic, first-class IR v3 alongside v4), `morphir-f22s` (closed finos/morphir work that specified v3 document trees, finos/morphir#970), `morphir-ukvn.8.14` (realigns the v4 model in parallel; this change does not touch the v4 model or codec), `morphir-ukvn.8.17` (follow-up: v3 and v4 document trees)

## Impact

- `packages/morphir`: `ir.format_version` (support table, messages), `ir.diagnostics` (`specs_before_3_1`), `ir.v3.distribution` and `ir.v3.codec` (`Specs`), `ir.migrate` (`Specs` path only). The v4 model and codec do not change. The core package stays dependency-free.
- `packages/morphir-tools`: `ir inspect` and `ir convert`.
- Tests and fixtures: new `3.1.0` fixtures in `tests/fixtures/ir/v3/` with provenance (MCK case distributions-0011 and the morphir-rust test documents); BDD scenarios in `features/ir_interchange.feature`.
- Users: files with `formatVersion` `"3.1.0"` now load; a reader that still declares `[3.0.0,3.1.0)` (morphir-elm today) refuses the `Specs` files this package writes, as decision 0018 intends.
