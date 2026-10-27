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

## Morphir IR versions

`morphir.ir` holds two first-class IR versions side by side:

| Package | IR | Source of truth | JSON codec |
|---------|----|-----------------|------------|
| `morphir.ir.v3` | format 3.0.0, what morphir-elm writes today | [morphir-elm](https://github.com/finos/morphir-elm) at `bc99af69` | `morphir.ir.v3.codec`, matches morphir-elm byte for byte |
| `morphir.ir.v4` | IR v4, **draft upstream** | [finos/morphir](https://github.com/finos/morphir) at `efa36060` | `morphir.ir.v4.codec`, **draft** |

`morphir.ir` and its old submodule paths (`morphir.ir.name`, `morphir.ir.value`,
and so on) still re-export the v4 classes; `morphir.ir.Name` is
`morphir.ir.v4.Name`. The v3 classes are distinct, so a type checker reports a v4
node where a v3 node is expected.

```python
from pathlib import Path

from morphir.ir import v3, v4
from morphir.ir.format_version import read_format_version
from morphir.ir.migrate import Ok, v3_to_v4, v4_to_v3
from morphir.ir.v3 import codec as v3_codec
from morphir.ir.v4 import codec as v4_codec

text = Path("tests/fixtures/ir/v3/elm-simpleValueTree.json").read_text()
library = v3_codec.decode_versioned_distribution(text)
assert isinstance(library, v3.Library)

upgraded = v3_to_v4(library, package_version="1.2.0")
assert isinstance(upgraded.value, v4.LibraryDistribution)
document = v4_codec.encode_versioned_distribution(upgraded.value)
assert document["formatVersion"] == 4

downgraded = v4_to_v3(upgraded.value)
assert isinstance(downgraded, Ok) and downgraded.value == library
assert read_format_version("3.0.0") == read_format_version(3)
```

### Reading `formatVersion`

`morphir.ir.format_version` reads the version of every IR document before any
decoder runs. It accepts the integer `3`, the string `"3"`, and the release
string `"3.0.0"`, and normalizes all three to release 3.0.0. Writers are
canonical: integer `N` for `N.0.0`, otherwise the exact release string.

Accepting strings is a deliberate divergence, so that migration tools can read
files written by other tools:

- morphir-elm decodes `formatVersion` as an integer only, so it rejects
  `"3"` and `"3.0.0"`;
- the [finos/morphir format-version contract](https://github.com/finos/morphir/blob/main/docs/spec/ir/format-version.md)
  accepts `3` and `"3.0.0"` but rejects `"3"`.

The support table is `[3.0.0,3.1.0),[4.0.0,4.1.0)`. Formats 1 and 2 fail with
`unsupported_format_version_major`; IR 3.1.0 fails with
`unsupported_format_version_minor` until
[finos/morphir-python#28](https://github.com/finos/morphir-python/issues/28) lands.
Failures raise `morphir.ir.diagnostics.DiagnosticError`, whose diagnostics carry
the stable codes of the finos contract.

### Draft IR v4

IR v4 is not frozen upstream. `morphir.ir.v4.codec` follows the finos/morphir v4
JSON profile at commit `efa36060` (`FINOS_MORPHIR_PIN`), and its spellings may
change in a later minor release of this package. It writes `formatVersion` 4 and
the distribution wrapped by its kind, never a format-3 shape. The module
docstring lists the gaps between the Python v4 model and upstream v4, each of
which fails with a diagnostic instead of guessing or dropping data.

`PackageInfo.version` is optional (`str | None`). Neither format 3 nor v4 JSON has
a package release version, so the draft codec does not write it and decodes it as
absent. `v3_to_v4` sets it only from `package_version`, and `v4_to_v3` drops it
with the warning `package_version_dropped`.

### Migrations

`morphir.ir.migrate.v3_to_v4` always succeeds for a v3 Library.
`v4_to_v3` returns `Ok(value, warnings)` or `Err(diagnostics)` and reports every
construct format 3.0.0 cannot hold in one pass: Specs and Application
distributions, `Hole`, `Native`, `External`, `DocumentLiteral`, a missing
`inferred_type`, semantic attributes, and missing member documentation. Value
source locations fail unless you pass `drop_source_locations=True`.

v4 JSON spells a value-definition input as a bare type, so it has no place for
the per-input attributes of a typed v3 model. morphir-elm writes the resolved
type there, which can differ from the declared type (an alias expanded, a type
variable instantiated), and the draft codec then fails with `no_v4_spelling`.
Opt in to dropping them with `v3_to_v4(..., drop_input_attributes=True)`,
`drop_input_attributes(dist)` for any v4 distribution, or
`morphir-tools ir convert --to v4 --drop-input-attributes`. Each input that loses
information reports `input_attributes_dropped`; without the opt-in the in-memory
migration stays lossless.

```python
from pathlib import Path

from morphir.ir.migrate import v3_to_v4
from morphir.ir.v3 import codec as v3_codec
from morphir.ir.v4 import codec as v4_codec

text = Path("tests/fixtures/ir/v3/elm-reference-model.json").read_text()
upgraded = v3_to_v4(
    v3_codec.decode_versioned_distribution(text), drop_input_attributes=True
)
assert {w.code for w in upgraded.warnings} == {"input_attributes_dropped"}
assert v4_codec.encode_versioned_distribution(upgraded.value)["formatVersion"] == 4
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
| `morphir.sdk.local_date` | `Morphir.SDK.LocalDate` | `datetime.date`, no time zone |
| `morphir.sdk.local_time` | `Morphir.SDK.LocalTime` | `LocalTime`, milliseconds from the epoch |
| `morphir.sdk.instant` | `Morphir.SDK.Instant` | `Instant`, milliseconds from the epoch |
| `morphir.sdk.uuid` | `Morphir.SDK.UUID` | `uuid.UUID` |
| `morphir.sdk.regex` | `Morphir.SDK.Regex` | `Regex` over the `re` module |
| `morphir.sdk.aggregate` | `Morphir.SDK.Aggregate` | `Aggregation`, `Operator` |
| `morphir.sdk.rule` | `Morphir.SDK.Rule` | `Callable[[A], Maybe[B]]` |
| `morphir.sdk.key` | `Morphir.SDK.Key` | `int` and flat tuples |
| `morphir.sdk.stateful_app` | `Morphir.SDK.StatefulApp` | `StatefulApp` |
| `morphir.sdk.result_list` | `Morphir.SDK.ResultList` | `tuple[Result[E, A], ...]` |

This is every module of the `Morphir.SDK` package specification. The `Json`
modules of morphir-elm are not part of that specification and are not included.

Notes on the modules beyond elm/core:

- `instant.Instant` is its own class over a number of milliseconds, not an alias
  of `datetime.datetime`, so a naive `datetime` cannot pass as an instant. Use
  `instant.from_datetime` and `instant.to_datetime` to convert.
- `local_time.LocalTime` is a point in time, not a time of day. In Elm it is an
  alias of `Time.Posix`, so it does not go around midnight.
- `regex` patterns use Python `re` syntax, which differs from JavaScript in
  places (named groups are `(?P<name>...)`, `\d` and `\w` follow Unicode). The
  module docstring lists the differences.
- `aggregate` leaves out the part of the Elm module that inspects Morphir IR
  values (`constructAggregationCall`); the specification does not list it.
  `aggregate.aggregate` yields its rows in ascending key order.
- `key.Key4` and larger are flat tuples. Elm nests them only because an Elm tuple
  holds three elements at most; the order of two keys is the same.

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
  A list inside a key or member is stored as a tuple, so a later change to the
  list cannot break the sorted order, and the value stays hashable. Build a
  `Dict` or `Set` with `from_list`, `singleton` or `insert`; the class constructor
  accepts only entries that are already sorted, and raises `ValueError` otherwise.
- **Failures.** Where Elm's runtime fails, the Python function raises:
  `basics.mod_by(0, x)` raises `ZeroDivisionError`, and `basics.equal` raises
  `TypeError` on a function, also one held inside a tuple, a list, a `Maybe`, a
  `Result`, a `Dict` or a `Set`.
- **Powers stay real.** `basics.power` follows JavaScript `Math.pow`, as the Elm
  runtime does: `power(-1.0, 0.5)` is `NaN` and `power(0.0, -1.0)` is infinity,
  where Python `**` gives a complex number and raises. Two integers with an
  exponent of zero or more give an exact integer.

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
