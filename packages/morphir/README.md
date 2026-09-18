# Morphir

Python port of [Morphir](https://morphir.finos.org) - functional domain modeling for the enterprise.

This is the core library package containing:

- Morphir IR (Intermediate Representation) models
- Type definitions and type algebra
- Pure functional primitives
- The Morphir SDK runtime (`morphir.sdk`)

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

## Morphir SDK

`morphir.sdk` is the standard library that Morphir models compile against. The
set of functions is the `Morphir.IR.SDK.*` package specification of
[morphir-elm](https://github.com/finos/morphir-elm). The reference behaviour is
elm/core 1.0.5 plus the `Morphir.SDK.*` Elm runtime. The package has no
dependencies and does no IO.

| Module | Elm module | Python data |
|--------|------------|-------------|
| `morphir.sdk.basics` | `Morphir.SDK.Basics` | `int`, `float`, `bool`, `Order` (`LT`, `EQ`, `GT`) |
| `morphir.sdk.char` | `Morphir.SDK.Char` | `str` with one code point |
| `morphir.sdk.string` | `Morphir.SDK.String` | `str` |
| `morphir.sdk.list` | `Morphir.SDK.List` | `tuple[A, ...]` |
| `morphir.sdk.dict` | `Morphir.SDK.Dict` | `Dict[K, V]`, entries sorted by key |
| `morphir.sdk.set` | `Morphir.SDK.Set` | `Set[A]`, members sorted |
| `morphir.sdk.maybe` | `Morphir.SDK.Maybe` | `Just[A] \| Nothing` |
| `morphir.sdk.result` | `Morphir.SDK.Result` | `Ok[A] \| Err[E]`, as `Result[E, A]` |
| `morphir.sdk.tuple` | `Morphir.SDK.Tuple` | `tuple[A, B]` |
| `morphir.sdk.decimal` | `Morphir.SDK.Decimal` | `decimal.Decimal` |
| `morphir.sdk.int` | `Morphir.SDK.Int` | `Int8`, `Int16`, `Int32`, `Int64` (`NewType` over `int`) |
| `morphir.sdk.number` | `Morphir.SDK.Number` | `Number`, an exact rational |

Not included yet: `LocalDate`, `LocalTime`, `Instant`, `UUID`, `Regex`,
`Aggregate`, `Rule`, `Key`, `StatefulApp`, `ResultList` and `Json`.

### Conventions

- **Names** are the Elm names in snake_case: `withDefault` is `with_default`,
  `integerDivide` is `integer_divide`, `toInt8` is `to_int8`. A name that is a
  Python keyword gets a trailing underscore: `not_`, `and_`, `or_`. The one
  exception is `isNaN`, which is `is_nan`. The test
  `tests/unit/sdk/test_spec_coverage.py` lists every Elm name with its Python name.
- **Arguments** are in Elm order, with the data last, and are not curried:
  `list.map(f, xs)`, `dict.get(key, d)`, `maybe.with_default(0, m)`.
- **Data is immutable.** An Elm list is a tuple; functions accept any `Sequence`
  and yield a tuple. `Maybe`, `Result`, `Dict`, `Set` and `Number` are frozen
  dataclasses, so they compare by value and work with `match`.
- **Module names** are the Elm names in lower case, so `list`, `dict`, `set`,
  `int`, `tuple`, `string` and `decimal` have the name of a built-in or of a
  standard library module. This is safe because Python 3 imports are absolute:
  `import decimal` always gives the standard library. (Do not run a file of the
  `sdk` directory as a script, or put that directory on `sys.path`; that would hide
  the standard library modules.) Many functions also have the
  name of a built-in (`map`, `filter`, `round`, ...). Import the modules with an
  alias and call the functions through the module:

  ```python
  from morphir.sdk import dict as Dict
  from morphir.sdk import list as List
  ```

- **Comparable keys.** `Dict` keys, `Set` members and the arguments of
  `basics.compare`, `list.sort` and so on must be numbers, strings, or tuples or
  lists of these. Other values (also `bool`, and a mix of `int` and `str`) raise
  `TypeError`, because Python has no compile-time check for Elm's `comparable`.
- **Failures.** Where Elm's runtime fails, the Python function raises:
  `basics.mod_by(0, x)` raises `ZeroDivisionError`, and `basics.equal` on
  functions raises `TypeError`.

### Departures from Elm

- Python integers have no size limit. `Int` arithmetic never overflows, `Int64`
  covers the full 64-bit range, and `Number` is exact at any size.
- A `str` is a sequence of code points, not of UTF-16 code units. `string.length`,
  `string.slice` and the other index functions count a character above U+FFFF as
  1, where Elm counts 2. Strings compare by code point.
- `basics.remainder_by(0, x)` raises `ZeroDivisionError`; Elm yields `NaN`.
  `basics.round`, `floor`, `ceiling` and `truncate` raise on `NaN` and the
  infinities, because the result is an `int`.
- `char.to_locale_upper` and `char.to_locale_lower` do the same as `to_upper` and
  `to_lower`; Python has no locale rules for case.
- `decimal.from_float` raises `ValueError` on `NaN` and the infinities.
  `decimal.shift_decimal_left` moves the exponent; the Elm runtime multiplies by a
  float. Arithmetic results keep 50 significant digits with half-up rounding, from
  a context that is local to the module. The global `decimal` context is never
  read or changed.
- `number` comparisons give the correct answer for a negative denominator (the
  Elm runtime compares `3/-4` and `1/2` wrongly), and `number.simplify` yields a
  positive denominator (`3/-6` becomes `-1/2`). As in Elm, arithmetic results are
  not reduced, so `==` on two `Number` values is structural; use `number.equal`
  to compare by value.

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
