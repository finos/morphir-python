[![FINOS - Incubating](https://cdn.jsdelivr.net/gh/finos/contrib-toolbox@master/images/badge-incubating.svg)](https://community.finos.org/docs/governance/Software-Projects/stages/incubating)
[![CI](https://github.com/finos/morphir-python/actions/workflows/ci.yml/badge.svg)](https://github.com/finos/morphir-python/actions/workflows/ci.yml)

# Morphir Python

Python port of [Morphir](https://morphir.finos.org) - a library of tools for building and working with functional domain models.

Morphir enables you to write business logic once and use it across multiple platforms, languages, and runtimes. It provides a strongly-typed intermediate representation (IR) that captures the semantics of your domain model.

## Installation

Install the library, Morphir SDK runtime, and CLI together:

```bash
pip install morphir-python
```

Or with uv:

```bash
uv add morphir-python
```

| PyPI distribution | Python imports | Command |
|-------------------|----------------|---------|
| [`morphir-python`](https://pypi.org/project/morphir-python/) | `morphir`, `morphir_tools` | `morphir-python` |

The distribution includes the core library and tools. It does not require a
separate `morphir` package from PyPI.

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
| `mise run clean` | Clean build artifacts |

## Releases

The initial PyPI release is `morphir-python==0.0.1`, containing both the `morphir`
library and the `morphir-python` CLI. Python 3.14 or later is required. The root
`pyproject.toml` defines the public distribution. The library workspace under
`packages/morphir/` remains independent of CLI dependencies for development; it
is included in the bundle rather than published separately by this workflow.

Publishing uses [PyPI trusted publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
without a stored PyPI token. Configure the `morphir-python` project on PyPI with:

| Publisher field | Value |
|-----------------|-------|
| Owner | `finos` |
| Repository | `morphir-python` |
| Workflow filename | `release.yml` |
| Environment | `pypi` |

The GitHub `pypi` environment permits release tags matching `v*` or `python-v*`.
After maintainer approval, push a tag such as `python-v0.0.1` whose version matches
root package metadata and the runtime `__version__` values. Refresh `uv.lock`
when changing versions. A new tag records the corrected source without moving
the earlier failed `v0.0.1` tag.

The release workflow runs the same lint, format, type, coverage and BDD checks as
PR CI. It builds the bundle once, validates wheel and source metadata and license
files, verifies that every library and CLI source file is in the wheel, installs
only that wheel in an isolated environment, checks imports and the CLI, then
scans the locked runtime dependency versions with `pip-audit` and `pip-licenses`.
Known vulnerabilities, audit failures, unknown licenses and licenses outside the
Apache-2.0, MIT, BSD-2-Clause, BSD-3-Clause and ISC allowlist block publication.
The allowlist also accepts corresponding legacy license classifiers. The CVE
scan queries third-party dependencies, excluding the first-party bundle being
released. These checks use package metadata and known vulnerability advisories;
they do not replace a source-code license or security review. Scan reports are
retained as workflow artifacts.

Only the publishing job receives `id-token: write`. It publishes the checked
artifacts, then a separate job creates the GitHub release. The workflow's manual
**Run workflow** action runs qualification without publishing. To qualify locally:

```bash
mise run install
mise run check
mise run coverage
mise run build
RELEASE_TAG=python-v0.0.1 mise run release-check
```

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
