# Proposal

## Why

The Python v4 model predates the upstream v4 profile. It cannot hold the native, external and incomplete definition bodies, incomplete type definitions, annotations, typed hole reasons or `Union` types that upstream v4 spells, so the draft codec refuses valid upstream documents with `unknown_node` or `unknown_member`. In the other direction, the morphir-elm reference model cannot be written as v4 JSON: its typed inputs carry a resolved type that differs from the declared type, and upstream v4 has no slot for per-input attributes, so encoding fails with `no_v4_spelling`.

## What Changes

- Add the upstream v4 value-definition bodies `NativeBody`, `ExternalBody` and `IncompleteBody` beside today's expression body (`Definition`). Module values and let bindings hold any of the four bodies.
- Add typed hole reasons (`UnresolvedReference`, `DeletedDuringRefactor`, `TypeMismatch`), the `Incompleteness` kinds `Hole` and `Draft`, and `IncompleteTypeDefinition`. **BREAKING** (draft API): `Hole.reason` is a typed `HoleReason`, not raw JSON.
- Add annotations (compact and structured, with positional and named arguments) to module, type and value specifications.
- Add the draft `Union` type expression (two or more alternatives).
- Extend the draft codec to read and write all of the above in the expanded spelling at the pinned commit, with the kit's refusals (duplicate external platforms, a platform-specific hint without its platform, a `Draft` hole reason, a union with fewer than two alternatives).
- Extend reverse migration so every new construct fails with `unsupported_v4_downgrade` at its location. Format 3.0.0 has no home for any of them.
- Add an explicit, reported drop of per-input value attributes: `drop_input_attributes` on `v3_to_v4`, a standalone function for any v4 Library, and `ir convert --drop-input-attributes`. Each input that loses information reports `input_attributes_dropped`. Without the opt-in, behaviour is unchanged: the in-memory migration stays lossless and encoding fails with `no_v4_spelling`.
- Keep the Python-only `Native` and `External` value nodes and the structured `TypeConstraints`, which upstream v4 cannot spell, and mark them deprecated. Their removal is follow-up work.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `ir/v4`: the model and draft codec cover the upstream definition bodies, incompleteness, annotations and `Union`; the Python-only constructs are deprecated.
- `ir/migrate`: the new v4 constructs fail reverse migration; per-input attributes can be dropped on request, with a warning.
- `tools/ir-interchange`: `ir convert` accepts `--drop-input-attributes` for upgrades.

## Beads

- **Tracked by**: `morphir-ukvn.8.14` (realign the Python v4 model with upstream finos/morphir v4)
- **Related**: `morphir-ukvn.8.15` (per-input attribute spelling; task group 1 of this change), `morphir-ukvn.8` (parent epic, IR v3 and v4 in morphir-python), `morphir-ukvn.8.16` (later re-sync of the draft codec when upstream v4 settles, including compact spellings), `morphir-diwy` (finos/morphir: v4 to v3 downgrade rules; codes may be renamed when it settles), `morphir-ukvn.7.9.1` (closed: the `Union` reference implementation in finos/morphir-moonbit)

## Impact

- `packages/morphir`: `morphir.ir.v4` modules `value`, `type`, `type_def`, `type_spec`, `module` and new `annotation` and `incompleteness` modules; `morphir.ir.v4.codec`; `morphir.ir.migrate`; `morphir.ir.diagnostics` (new warning code `input_attributes_dropped`). The core stays dependency-free.
- `packages/morphir-tools`: one new `ir convert` option.
- Callers that build `Hole` values with raw JSON reasons must pass a `HoleReason`. Callers that match on `module.Definition.values` entries must handle the three new bodies.
- No change to v3 or to format-3 encoding.
