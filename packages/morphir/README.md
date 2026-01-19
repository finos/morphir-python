# Morphir

Python port of [Morphir](https://morphir.finos.org) - functional domain modeling for the enterprise.

This is the core library package containing:

- Morphir IR (Intermediate Representation) models
- Type definitions and type algebra
- Pure functional primitives

## Installation

```bash
pip install morphir
```

Or with uv:

```bash
uv add morphir
```

## Usage

```python
from morphir.ir import Type, Value

# Example usage will be added as the library develops
```

## Requirements

- Python 3.14+

## Design Principles

This library follows functional programming principles:

- **Immutability**: All data structures are immutable (frozen dataclasses)
- **Type Safety**: Complete type annotations with strict mypy/pyright checking
- **Algebraic Data Types**: Using unions and frozen dataclasses
- **Making Illegal States Unrepresentable**: Domain modeling prevents invalid states

## License

Apache-2.0 - see the [LICENSE](../../LICENSE) file for details.

## Related Packages

- [morphir-tools](https://pypi.org/project/morphir-tools/) - CLI tools and extensions
