# Proposal

## Why

The finos/morphir v4 JSON profile at the codec's pin (`efa36060`) says writers SHOULD emit the compact canonical vocabulary unless expanded output is explicitly selected. The Python v4 writer emits only the expanded spelling and the pre-decision nested `{"doc", "value"}` wrapper. Its output is therefore larger than other Morphir tools' output and spelled differently: it is 30–35% larger than morphir-core's output for the same compiled models (benchmark run 20261027T194412Z). The reader half landed with the Python binding migration; this change does the writer half of `morphir-ukvn.8.16`.

## What Changes

- The v4 encoders write the compact canonical spelling by default. A node without attributes uses its shortest schema-valid form: a type variable as its name string; a type reference without arguments as its FQName string, or `{"Reference": [fqname, args...]}` with arguments; a tuple type as `{"Tuple": [...]}`; a literal as `{"Kind": payload}`; `Literal`, `Constructor`, `Reference`, `Variable`, `FieldFunction`, `Tuple` and `List` values, and `TuplePattern` and `LiteralPattern` patterns, with the payload directly under the tag. A node that carries attributes keeps the expanded spelling.
- Documentation is written flattened, with `doc` first beside the documented node's members (decision 0010), instead of the nested `{"doc", "value"}` wrapper.
- Callers can still select the expanded spelling: `Spelling.EXPANDED` in the library, `--v4-spelling expanded` in `morphir-python ir convert`. **BREAKING** for consumers that parse v4 JSON written by this library and accept only the expanded spelling; every schema-valid reader, including this library and morphir-core, reads both.
- Out of scope, still waiting for upstream v4 to settle: legacy-spelling warnings, kit diagnostic renames, `Union` and 4.1.0 linked annotations, and the morphir-diwy downgrade code names.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ir/v4`: the writer's default spelling, flattened documentation, and spelling selection.
- `tools/ir-interchange`: `ir convert --to v4` writes the compact spelling by default and offers `--v4-spelling`.

## Beads

- **Tracked by**: `morphir-ukvn.8.16` (writer half; its other scope stays deferred on upstream).

## Impact

`packages/morphir/src/morphir/ir/v4/codec.py`, its tests, the `ir convert` command and documentation. Encoded v4 output changes shape, but the decoded model does not. Generation in `morphir_tools.python` sends compact v4 to the native compiler, which reads both spellings.
