# Release Python packages and extensions

The package versions are independent. A maintainer approves tags and publication.
The [Release workflow](https://github.com/finos/morphir-python/actions/workflows/release.yml)
qualifies the tagged commit before publishing. Its manual run qualifies a
candidate, including the platform matrix, without publishing a release.

| Tag | Published output | Installation |
| --- | --- | --- |
| `morphir-v<version>` | Core wheel and source archive on PyPI and GitHub Releases | Python package installer |
| `native-v<version>` | Five native compiler wheels and a source archive on PyPI | Exact dependency of the CLI |
| `python-v<version>` | CLI wheel and source archive on PyPI and GitHub Releases | mise `pypi:`/`pipx:`, uv or pip |
| `extension/python/v<version>` | WASM and five process executables, separate runtime descriptors, process bundle archive, qualification evidence and `SHA256SUMS` on GitHub Releases | Morphir extension host |

The CLI release is a Python distribution. mise installs it from PyPI into an
isolated environment; GitHub release assets are distribution mirrors, not
standalone executables. The [installation guide](installation.md) gives the
tested configurations. The WASM guest is a separate artifact and does not
install through the CLI's Python package backend.

## Prepare a release

1. Set the package version and its corresponding constants and dependency pins.
   Keep the native crate, native package metadata and the CLI's exact native
   requirement consistent. Run `mise run check`.
2. Run the Release workflow manually on the candidate branch. Inspect every
   required job, the platform install checks and qualification receipts. Missing,
   failed, cancelled or skipped required evidence blocks publication.
3. Release the core library and native package before a CLI release that needs
   their new versions. The CLI gate requires published matching dependencies and
   refuses native source changes after its pinned `native-v` tag.
4. After maintainer approval, push the corresponding version tag at the reviewed
   commit. A manual run does not authorize or perform publication. Check the
   tagged run and the resulting PyPI files or GitHub release assets.

## What qualification proves

Normal CI checks a fresh candidate installation with both mise/uv and actual
mise/pipx on Linux. It reuses the existing core, CLI and native wheels. The
candidate install is restricted to an offline wheel directory, with dependencies
resolved under the workspace release constraints, so PyPI cannot substitute a
published package with the same version for the candidate.

Native releases and manual release qualification cover Linux x86_64/aarch64,
macOS arm64/x86_64 and Windows x86_64. A CLI release also runs these platforms,
using its pinned published native wheels instead of rebuilding Rust. Every
selected platform must pass before the CLI publishes. The reused Linux wheel
already passes the same installer checks in the qualification workflow.

Each installer has separate temporary mise configuration, state, cache and
package environments outside the checkout. Tests check installed versions,
compile and generate both IR v3 and draft v4, recompile generated source and run
the generated model with Rust absent from `PATH`. Receipts retain candidate and
dependency hashes. This complements the existing API, source archive, license,
vulnerability and host checks.

The WASM gate checks the tag's compiler version, source commit, descriptor digest
and checksum contents. Publication rechecks `SHA256SUMS` for the final release
asset names, including the renamed release descriptor.

## Qualify both extension runtimes

The manual and extension-tag workflows run the shared executable MCK on each
process producer and once for the portable WASM guest. `rust/extension.toml`
pins the merged upstream source, tree, lockfile, Python JSON corpus and complete
91-case identity set. `scripts.mep_tool` verifies that source and builds its CLI;
it never replaces upstream expectations. Cargo may reuse compatible cached
objects. Each report names an immutable copy of the built checker.

`scripts.qualify_mep` runs `morphir mck mep guest-run`, then `report-check` with
the original checker and all identity files still available. A failed run or
recheck prevents the producer from uploading a qualified candidate. The WASM
adapter forwards raw request/response bytes to the guest. Its notification and
exit checks cover the adapter/guest route, as documented in the
[extension guide](python-extension.md).

The collector consumes only successful producers in the same workflow run. It
verifies source, artifact, checker definitions, lockfiles, corpus, all required
case identities, discovery claims, raw report hashes and the successful saved
recheck receipt. Windows and macOS paths remain unchanged. This is a trusted
producer handoff, not a second filesystem recheck on Linux. A standalone report
with `qualified: true` is insufficient.

Missing, stale, failed or mismatched evidence blocks process assembly and the
dependent extension promotion job. The candidate also checks installed-byte
integrity, full diagnostic parity with the matching Python API, Windows runtime
imports, extracted-archive runtime switching, and real Rust host behavior. The
final release retains raw MCK reports and recheck receipts, assembly and runtime
receipts, and the host timing evidence. Publication verifies final checksums.
Historical WASM releases remain available with their original bytes.

## Reproduce the installer checks

Check the published configurations without changing your global mise setup:

```bash
uv run python -m scripts.qualify_mise --report .dev/qualification/mise-released.json
```

For candidates, first build the distributions using the existing tasks, then
run `mise run cli:qualify-mise`. CI passes the existing Linux native producer's
wheel; a `python-v` release uses the published-native directory qualified by
`native:qualify`. The script also accepts three explicit wheel paths for another
platform, as shown in the workflow.

Keep successful run IDs and the artifact receipts with the release record.
For a failed publication, inspect which files were accepted before retrying.
Do not replace a published version's bytes or move a released tag. Correct the
source, qualify a new version and publish a new tag.
