[![FINOS - Incubating](https://cdn.jsdelivr.net/gh/finos/contrib-toolbox@master/images/badge-incubating.svg)](https://community.finos.org/docs/governance/Software-Projects/stages/incubating)
[![CI](https://github.com/finos/morphir-python/actions/workflows/ci.yml/badge.svg)](https://github.com/finos/morphir-python/actions/workflows/ci.yml)

# Morphir Python

Python port of [Morphir](https://morphir.finos.org) - a library of tools for building and working with functional domain models.

Morphir enables you to write business logic once and use it across multiple platforms, languages, and runtimes. It provides a strongly-typed intermediate representation (IR) that captures the semantics of your domain model.

## Packages

This monorepo contains two packages:

| Package | Description | PyPI |
|---------|-------------|------|
| `morphir` | Core library - IR models, types, and functional domain modeling primitives | [![PyPI](https://img.shields.io/pypi/v/morphir)](https://pypi.org/project/morphir/) |
| `morphir-tools` | CLI tools and extensions for working with Morphir | [![PyPI](https://img.shields.io/pypi/v/morphir-tools)](https://pypi.org/project/morphir-tools/) |

## Installation

### Library Only

If you just need the Morphir library for your Python project:

```bash
pip install morphir
```

Or with uv:

```bash
uv add morphir
```

### With CLI Tools

For the full toolset including CLI commands:

```bash
pip install morphir-tools
```

Or with uv:

```bash
uv add morphir-tools
```

## Quick Start

```python
from morphir.ir import Type, Value

# Example usage will be added as the library develops
```

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
| `mise run clean` | Clean build artifacts |

## Project Principles

This project follows functional programming principles:

- **Immutability**: Data structures are immutable by default
- **Type Safety**: Strict type annotations with mypy and pyright
- **Algebraic Data Types**: Using `@dataclass(frozen=True)`, Unions, and Protocols
- **Making Illegal States Unrepresentable**: Domain modeling that prevents invalid states at compile time

## Roadmap

1. Core IR model implementation
2. JSON serialization/deserialization
3. Type checking and validation
4. Code generation backends
5. CLI tooling

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
