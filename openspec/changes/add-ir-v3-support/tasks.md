# Tasks

## 1. Format-version reader and V3 IR model and codecs (morphir-ukvn.8.1)

- [x] 1.1 Add `morphir.ir.format_version` with the permissive reader, normalization, the support table `[3.0.0,3.1.0),[4.0.0,4.1.0)`, canonical writing, and the finos diagnostic codes (design FV-1), and verify unit tests cover `3`, `"3"`, `"3.0.0"`, `true`, `"3.0.0-alpha"`, out-of-range components, `1`, `2`, `"3.1.0"`, missing, and duplicate members
- [x] 1.2 Add the `morphir.ir.v3` model modules `name`, `path`, `qname`, `fqname`, `access_controlled`, `documented`, `literal`, `type`, `value`, `module`, `package`, and `distribution` (Library only, unit type attributes, typed value attributes, no package version) and verify imports and construction tests pass
- [x] 1.3 Add `morphir.ir.v3.codec`, porting each elm module on the design ELM-1 checklist with attribute-parameterized node codecs, and verify per-node round-trip tests, including the kit's untyped `["Literal", {}, ["WholeNumberLiteral", 42]]` fragment
- [x] 1.4 Add versioned-distribution encode and decode for format 3 that use the shared reader, and verify tests for the string-version read with integer write, the wrong-family refusal of `4`, and the unknown distribution tag error

## 2. V4 package layout and re-exports (morphir-ukvn.8.2)

- [x] 2.1 Move the current IR modules to `morphir.ir.v4` (the full module list is in design PKG-1), leave a re-export shim at each old submodule path, keep `morphir.ir.__all__`, and verify existing unit and BDD tests pass unchanged
- [x] 2.2 Add identity tests asserting that classes from `morphir.ir`, `morphir.ir.<module>`, and `morphir.ir.v4` are the same objects, and that v3 and v4 classes are distinct
- [x] 2.3 Make `PackageInfo.version` `str | None = None` (design VER-1) and verify existing constructors and tests still pass
- [x] 2.4 Document the versioned import paths and the optional package version in the `packages/morphir` README and verify the documented imports run

## 3. Draft v4 JSON codec (morphir-ukvn.8.11)

- [x] 3.1 Add `morphir.ir.v4.codec` with versioned-distribution encode and decode for Library, Specs, and Application using the finos v4 JSON profile envelope and the canonical spellings at the pinned finos/morphir commit, kept in one spelling table (design V4-1), and verify round-trip tests for each distribution kind
- [x] 3.2 Make decoding fail with located diagnostics (`unknown_node`, `unknown_member`, `missing_member`, `duplicate_member`) and make encoding fail on `Native` and `External` value nodes and duplicate record fields, and verify one test per failure
- [x] 3.3 Mark the codec as draft in docstrings and the README, naming the pinned commit, and keep the existing `morphir.ir.json.encode` placeholder working; verify the docs build or lint passes

## 4. V3↔V4 migrations (morphir-ukvn.8.3)

- [x] 4.1 Add `morphir.ir.migrate` result and diagnostic types (`code`, `construct`, `location`, `message`) with code constants in one module (design Diagnostic codes), and verify the types are frozen and fully typed
- [x] 4.2 Implement `v3_to_v4` with the attribute, literal, documentation, and `package_version` mapping from the design mapping table, and verify forward tests against the golden fixtures
- [x] 4.3 Implement `v4_to_v3` that collects every failure in one pass, covering Specs, Application, `Hole`, `Native`, `External`, `DocumentLiteral`, missing `inferred_type`, semantic attributes, and missing member documentation, and verify one unit test per failure code and construct
- [x] 4.4 Implement the allowed drops (`package_version_dropped` always, `source_location_dropped` only with `drop_source_locations=True`) and verify that without the flag a source location fails with `unsupported_attributes_downgrade`
- [x] 4.5 Verify the v3→v4→v3 round trip is semantically equal for every golden fixture, and that a compatible hand-built v4 Library downgrades successfully

## 5. IR interchange CLI (morphir-ukvn.8.4)

- [x] 5.1 Add Typer with a pinned minimum version to `morphir-tools` only, add the `morphir-tools` console script with an `ir` command group, and verify `morphir-tools ir --help` runs
- [x] 5.2 Add `ir inspect` (normalized version, distribution kind, package name, draft notice for v4) and verify CLI tests for format 3, v4, missing version, and formats 1, 2, and `"3.1.0"`
- [x] 5.3 Add `ir convert --to {v3,v4}` with `-o`, `--package-version`, and `--drop-source-locations`, writing through a temporary file and renaming only on success, and verify that success writes output, warnings exit 0, and failures exit 1 with no output file

## 6. Fixtures docs and integration checks (morphir-ukvn.8.5)

- [x] 6.1 Copy the format-3 fixtures listed in design TST-1 to `tests/fixtures/ir/v3/` with a `PROVENANCE.md` (source repository, commit, path, license), and verify tests use them with no morphir-elm dependency
- [x] 6.2 Add a BDD feature for inspect and convert on a golden fixture and verify `mise run test-bdd` passes
- [x] 6.3 Document the format-version divergence (accepted spellings that morphir-elm and the finos contract reject) and the draft v4 status in user docs, and verify the links resolve
- [x] 6.4 Run `mise run check` and verify lint, typecheck (mypy and pyright strict), tests, and coverage of at least 80% pass
- [x] 6.5 Update root and agent docs briefly on dual IR versions and verify links to this change and the package README

## Workflow follow-up

- Archive the change after review requirements are satisfied (`openspec archive add-ir-v3-support`)
- File follow-up changes for IR formats 1 and 2 (morphir-elm `CodecV1`), for IR 3.1.0 (finos/morphir-python#28), and for realigning the v4 model with upstream (`Native` and `External` as definition bodies, `Union`, annotations, incomplete definitions)
- Re-sync the draft v4 codec and the migration codes when finos bead `morphir-diwy` and the kit's v4 cases settle
- Relink epic bead `morphir-ukvn.8` to the archived path and `bd dolt push`
