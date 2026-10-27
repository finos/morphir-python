[![FINOS - Incubating](https://cdn.jsdelivr.net/gh/finos/contrib-toolbox@master/images/badge-incubating.svg)](https://community.finos.org/docs/governance/Software-Projects/stages/incubating)
[![CI](https://github.com/finos/morphir-python/actions/workflows/ci.yml/badge.svg)](https://github.com/finos/morphir-python/actions/workflows/ci.yml)

# Morphir Python

Python port of [Morphir](https://morphir.finos.org) - a library of tools for building and working with functional domain models.

Morphir enables you to write business logic once and use it across multiple platforms, languages, and runtimes. It provides a strongly-typed intermediate representation (IR) that captures the semantics of your domain model.

## Installation

The library and CLI are separate distributions:

| PyPI distribution | Contents | Python import / command |
|-------------------|----------|-------------------------|
| [`morphir`](https://pypi.org/project/morphir/) | Core library, IR models, and SDK runtime; no third-party runtime dependencies | `import morphir` |
| [`morphir-python`](https://pypi.org/project/morphir-python/) | CLI, Python compiler API and tool integrations; depends on `morphir` and one exact `morphir-python-native` | `import morphir_tools`; `morphir-python` |
| [`morphir-python-native`](https://pypi.org/project/morphir-python-native/) | Private native compiler wheels, installed automatically by `morphir-python` | none (private) |

Install just the library and SDK:

```bash
pip install morphir==0.0.1
# or: uv add morphir==0.0.1
```

Install the CLI, which also installs the library:

```bash
pip install morphir-python==0.0.2
# or: uv add morphir-python==0.0.2
```

Python 3.14 or later is required. The CLI inspects and converts IR, compiles a
supported subset of Python to Morphir IR, and generates Python from Morphir IR.
The compiler runs in process from prebuilt wheels; you do not need Rust. See the
[Python compiler guide](docs/python-compiler.md) for the API, the CLI commands and
the supported subset.

The same compiler is the Rust crate
[`morphir-python-binding`](rust/crates/morphir-python-binding/README.md) and the
`morphir-python` Morphir extension. This repository builds and releases both; see
the [extension guide](docs/python-extension.md).

### Migrating from the bundled 0.0.1 release

`morphir-python==0.0.1` bundled both namespaces. Starting with `0.0.2`, library
files belong to the separate `morphir` distribution. Use a fresh virtual
environment, or remove both old package owners before reinstalling in your
existing virtual environment:

```bash
python -m pip uninstall -y morphir-python morphir
python -m pip install morphir-python==0.0.2
```

Library-only consumers can install `morphir==0.0.1` instead. Imports remain
`morphir` and `morphir_tools`; the command remains `morphir-python`. The release
checks exercise the uninstall/reinstall migration from the published old bundle.

## Quick Start

Morphir IR comes in two first-class versions: format 3.0.0 (`morphir.ir.v3`), which
morphir-elm writes today, and draft IR v4 (`morphir.ir.v4`, also re-exported as
`morphir.ir`). Read a morphir-elm file and migrate it to v4:

```python
from pathlib import Path

from morphir.ir.migrate import v3_to_v4
from morphir.ir.v3 import codec

library = codec.decode_versioned_distribution(Path("morphir-ir.json").read_text())
v4_library = v3_to_v4(library).value
```

Or from the command line:

```bash
morphir-python ir inspect morphir-ir.json
morphir-python ir convert morphir-ir.json --to v4 -o morphir-ir.v4.json
```

See the [morphir package README](packages/morphir/README.md#morphir-ir-versions)
for format-version handling, the draft v4 status, and migrations, the
[IR specs](openspec/specs/) for the requirements, and the archived
[`add-ir-v3-support` change](openspec/changes/archive/2026-10-27-add-ir-v3-support/proposal.md)
for the design.

## Morphir SDK

`morphir.sdk` is the Python runtime for the Morphir SDK, the standard library that
Morphir models compile against. It covers the core modules of the
`Morphir.IR.SDK` specification: `basics`, `char`, `string`, `list`, `dict`, `set`,
`maybe`, `result`, `tuple`, `decimal`, `int` and `number`. The behaviour follows
elm/core 1.0.5 and the `Morphir.SDK` Elm runtime.

```python
from morphir.sdk import basics
from morphir.sdk import decimal as Decimal
from morphir.sdk import dict as Dict
from morphir.sdk import list as List
from morphir.sdk import maybe as Maybe
from morphir.sdk.maybe import Just, Nothing

# Elm argument order, data last, not curried
List.map(lambda n: n * 2, (1, 2, 3))            # (2, 4, 6)
Maybe.with_default(0, List.head(()))            # 0

# Immutable Dict, sorted by structural comparable keys
prices = Dict.from_list(((("EUR", 2), 1.5), (("EUR", 1), 1.2)))
Dict.keys(prices)                               # (("EUR", 1), ("EUR", 2))
Dict.get(("EUR", 1), prices)                    # Just(value=1.2)

# Elm number rules
basics.round(2.5)                               # 3, not Python's 2
basics.integer_divide(-7, 2)                    # -3
Decimal.to_string(Decimal.add(Decimal.tenth(1), Decimal.tenth(2)))  # "0.3"
```

Names are the Elm names in snake_case (`withDefault` is `with_default`). See the
[`morphir` package README](packages/morphir/README.md#morphir-sdk) for the
conventions and the list of departures from Elm.

## Requirements

- Python 3.14+

## Development Setup

This project uses [mise](https://mise.jdx.dev/) for tool management and [uv](https://docs.astral.sh/uv/) for Python package management.

### Prerequisites

Install mise (if not already installed):

```bash
curl https://mise.run | sh
```

### Setup

1. Clone the repository:

```bash
git clone https://github.com/finos/morphir-python.git
cd morphir-python
```

2. Install tools and dependencies:

```bash
mise install
uv sync --all-groups
```

3. Run the checks:

```bash
mise run check
```

### Available Tasks

| Task | Description |
|------|-------------|
| `mise run lint` | Run ruff linter |
| `mise run format` | Run ruff formatter |
| `mise run typecheck` | Run mypy and pyright |
| `mise run test` | Run pytest unit tests |
| `mise run test-bdd` | Run behave BDD tests |
| `mise run test-all` | Run all tests |
| `mise run coverage` | Run tests with coverage |
| `mise run check` | Run all checks |
| `mise run build` | Build packages |
| `mise run release-check` | Validate built packages and scan runtime dependencies for vulnerabilities and licenses |
| `mise run rust:check` | Format, lint and test the Rust workspace and build the WASM guest |
| `mise run rust:consumer` | Build an independent Cargo consumer of the current commit |
| `mise run native:build` | Build the native wheel and source archive into `dist/native` |
| `mise run native:qualify` | Qualify the native archive and a clean install without Rust |
| `mise run extension:bundle` | Build the MEP extension bundle and check it offline in a Morphir host |
| `mise run bench` | Measure native, bridge, API and CLI compile and generate times |
| `mise run clean` | Clean build artifacts |

## Releases

The repository root is a development workspace. Public package metadata is in
`packages/morphir/pyproject.toml` and `packages/morphir-tools/pyproject.toml`.
Versions are independent: the first library release is `morphir==0.0.1`, and the
first CLI-only release is `morphir-python==0.0.2`. The already published bundled
CLI `0.0.1` and its `python-v0.0.1` tag remain unchanged.

### Trusted publisher configuration

Configure a [trusted publisher](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
for **each** PyPI project. Use a pending publisher if a project has no release yet.
Both publishers use this repository and the same workflow/environment identity:

| Field | Library / SDK | CLI |
|-------|---------------|-----|
| PyPI project | `morphir` | `morphir-python` |
| Repository owner | `finos` | `finos` |
| Repository name | `morphir-python` | `morphir-python` |
| Workflow filename | `release.yml` | `release.yml` |
| Environment | `pypi` | `pypi` |
| Tag example | `morphir-v0.0.1` | `python-v0.0.2` |

On GitHub, the `pypi` environment permits both `morphir-v*` and `python-v*` tag
patterns. No stored PyPI token is needed. Only the selected publishing job
receives `id-token: write`; a manual workflow run qualifies artifacts without
publishing. Bare `v*` tags are not used for new releases.

### Qualification and publication

1. Update the selected package's metadata and runtime `__version__`. Update the
   CLI's minimum library dependency when its API requirements change, and run
   `uv lock`.
2. Run `mise run install`, `mise run check`, `mise run coverage`, `mise run build`
   and `mise run release-check`. Without a tag, this qualifies both distributions.
3. After maintainer approval, tag the candidate with the selected package prefix
   and exact version, then push that tag. To release the initial library:

   ```bash
   git tag -a morphir-v0.0.1 -m 'Release morphir library and SDK 0.0.1'
   git push origin morphir-v0.0.1
   ```

4. Publish the library before any CLI that needs it. A later `python-v0.0.2` tag
   publishes only the CLI. Its qualification requires the published library wheel
   to have the same SHA256 digest as the core artifact used in testing. If core
   sources or metadata change, bump and publish the core version first.
5. Verify the selected PyPI files and a clean installation. The workflow creates
   a GitHub release containing only the selected package's artifacts. Never move
   an existing release tag or overwrite an existing PyPI version.

Release and PR CI run lint, formatting, type, coverage and BDD checks before
building both candidates. Artifact checks enforce exact names/versions, complete source inclusion,
separate namespace ownership, Apache license files, no core runtime dependencies
or console scripts, and the CLI's versioned core dependency. Isolated installs
exercise the library/SDK without CLI dependencies, CLI behavior, and migration
from the old bundle. PR qualification checks both runtime environments; a tagged
release scans only its selected package, and the migration check runs for CLI
qualification. CVE and license checks cover locked installed runtime versions;
the core has no third-party dependencies. Scan reports are retained as
workflow artifacts. Scans use metadata/advisories and do not replace source-code
security or license review.

### Native compiler and extension bundle releases

Two more tag families release the compiler. Their versions come from the Rust
crates and are independent of the Python package versions:

| Tag | Releases | Version source | Publishes to |
|-----|----------|----------------|--------------|
| `native-v<version>` | `morphir-python-native` wheels and source archive | `rust/crates/morphir-python-native/Cargo.toml` | PyPI, `pypi` environment |
| `extension/python/v<version>` | `morphir-python` MEP extension bundle | `rust/crates/morphir-python-binding/Cargo.toml` | GitHub release, `extension-release` environment |

Add a trusted publisher for the PyPI project `morphir-python-native` with the
same repository, workflow and `pypi` environment, and allow `native-v*` tags in
that environment. Create an `extension-release` environment that allows
`extension/python/v*` tags and requires a maintainer review.

A `native-v` tag builds one wheel for each qualified platform (Linux glibc
x86_64 and aarch64, macOS arm64 and x86_64, Windows x86_64) and installs each
exact wheel with the core and CLI wheels into a clean environment without Rust.
The Linux x86_64 wheel and the source archive are the ones CI already tested.
Publication downloads the set that `scripts/release_candidates.py` accepted and
checks it against its `SHA256SUMS` receipt. A missing, failed, skipped, extra or
mismatched candidate stops the release. A manual run of `release.yml` qualifies
every platform without publishing.

An `extension/python/v` tag publishes the bundle that CI built from that tag's
commit and checked in the pinned Morphir CLI. Its `release.json` must name that
commit and its WASM digest.

Publish in this order, each step after maintainer approval:

1. `native-v<version>`, when the native compiler changed.
2. `python-v<version>` for a CLI that pins it. Its qualification refuses to
   continue until every platform file of the pinned native version is on PyPI.
3. `extension/python/v<version>`, when the compiler changed. Then update the
   ecosystem pin in finos/morphir (`.config/published-extension-bundles.toml`).

Never delete or overwrite a published version or an older bundle; select an
earlier version through the pins to roll back.

For targeted qualification, `RELEASE_TAG=morphir-v0.0.1 mise run release-check`
validates the library tag. `RELEASE_TAG=python-v0.0.2 mise run release-check` also
checks the published core dependency. The latter must wait until the library is
published. Unknown tags or a tag/version mismatch block publication.

## Project Principles

This project follows functional programming principles:

- **Immutability**: Data structures are immutable by default
- **Type Safety**: Strict type annotations with mypy and pyright
- **Algebraic Data Types**: Using `@dataclass(frozen=True)`, Unions, and Protocols
- **Making Illegal States Unrepresentable**: Domain modeling that prevents invalid states at compile time

## Roadmap

1. Core IR model implementation
2. Morphir SDK runtime (`morphir.sdk`) - core modules done
3. JSON serialization/deserialization
4. Type checking and validation
5. Code generation backends
6. CLI tooling

## Contributing

For any questions, bugs or feature requests please open an [issue](https://github.com/finos/morphir-python/issues).
For anything else please send an email to morphir@finos.org.

To submit a contribution:

1. Fork it (<https://github.com/finos/morphir-python/fork>)
2. Create your feature branch (`git checkout -b feature/fooBar`)
3. Read our [contribution guidelines](.github/CONTRIBUTING.md) and [Community Code of Conduct](https://www.finos.org/code-of-conduct)
4. Commit your changes (`git commit -am 'Add some fooBar'`)
5. Push to the branch (`git push origin feature/fooBar`)
6. Create a new Pull Request

_NOTE:_ Commits and pull requests to FINOS repositories will only be accepted from those contributors with an active, executed Individual Contributor License Agreement (ICLA) with FINOS OR who are covered under an existing and active Corporate Contribution License Agreement (CCLA) executed with FINOS. Commits from individuals not covered under an ICLA or CCLA will be flagged and blocked by the FINOS Clabot tool (or [EasyCLA](https://community.finos.org/docs/governance/Software-Projects/easycla)). Please note that some CCLAs require individuals/employees to be explicitly named on the CCLA.

*Need an ICLA? Unsure if you are covered under an existing CCLA? Email [help@finos.org](mailto:help@finos.org)*

## Related Projects

- [Morphir](https://github.com/finos/morphir) - The main Morphir project
- [Morphir Elm](https://github.com/finos/morphir-elm) - Elm implementation
- [Morphir Scala](https://github.com/finos/morphir-scala) - Scala implementation

## License

Copyright 2026 FINOS

Distributed under the [Apache License, Version 2.0](http://www.apache.org/licenses/LICENSE-2.0).

SPDX-License-Identifier: [Apache-2.0](https://spdx.org/licenses/Apache-2.0)
