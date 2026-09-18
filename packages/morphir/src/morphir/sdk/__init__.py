"""The Morphir SDK: the standard library that Morphir models compile against.

Each module mirrors one `Morphir.SDK` module. The set of functions is the
`Morphir.IR.SDK.*` package specification of finos/morphir-elm. The reference
behaviour is elm/core 1.0.5 plus the `Morphir.SDK.*` Elm runtime.

============  =======================  ========================================
Module        Elm module               Python data
============  =======================  ========================================
basics        Morphir.SDK.Basics       `int`, `float`, `bool`, `Order`
char          Morphir.SDK.Char         `str` with one code point
string        Morphir.SDK.String       `str`
list          Morphir.SDK.List         `tuple[A, ...]`
dict          Morphir.SDK.Dict         `Dict[K, V]`, sorted by key
set           Morphir.SDK.Set          `Set[A]`, sorted
maybe         Morphir.SDK.Maybe        `Just[A] | Nothing`
result        Morphir.SDK.Result       `Ok[A] | Err[E]`
tuple         Morphir.SDK.Tuple        `tuple[A, B]`
decimal       Morphir.SDK.Decimal      `decimal.Decimal`
int           Morphir.SDK.Int          `Int8`, `Int16`, `Int32`, `Int64`
number        Morphir.SDK.Number       `Number`, an exact rational
local_date    Morphir.SDK.LocalDate    `datetime.date`
local_time    Morphir.SDK.LocalTime    `LocalTime`, milliseconds from the epoch
instant       Morphir.SDK.Instant      `Instant`, milliseconds from the epoch
uuid          Morphir.SDK.UUID         `uuid.UUID`
regex         Morphir.SDK.Regex        `Regex` over the `re` module
aggregate     Morphir.SDK.Aggregate    `Aggregation`, `Operator`
rule          Morphir.SDK.Rule         `Callable[[A], Maybe[B]]`
key           Morphir.SDK.Key          `int` and flat tuples
stateful_app  Morphir.SDK.StatefulApp  `StatefulApp`
result_list   Morphir.SDK.ResultList   `tuple[Result[E, A], ...]`
============  =======================  ========================================

Conventions:

* Names are the Elm names in snake_case: `withDefault` is `with_default`,
  `integerDivide` is `integer_divide`, `toInt8` is `to_int8`. A name that is a
  Python keyword gets a trailing underscore: `not_`, `and_`, `or_`. The one
  exception is `isNaN`, which is `is_nan`.
* Arguments are in Elm order, with the data last, and are not curried:
  `list.map(f, xs)`, `dict.get(key, d)`, `maybe.with_default(0, m)`.
* All data is immutable. Functions are pure and never mutate their input.
* Where Elm's runtime fails (`mod_by(0, x)`, comparison of functions), the
  Python function raises an exception. Each docstring names the exception.

Several modules and functions have the name of a Python built-in (`list`,
`dict`, `map`, `filter`, ...). Import the modules with an alias, and call the
functions through the module:

    >>> from morphir.sdk import dict as Dict
    >>> from morphir.sdk import list as List
    >>> from morphir.sdk import maybe as Maybe
    >>> ages = Dict.from_list((("tom", 42), ("sue", 38)))
    >>> Maybe.with_default(0, Dict.get("sue", ages))
    38
    >>> List.map(lambda n: n * 2, Dict.values(ages))
    (76, 84)

This package has no dependencies and does no IO.
"""

from morphir.sdk import (
    aggregate,
    basics,
    char,
    decimal,
    dict,
    instant,
    int,
    key,
    list,
    local_date,
    local_time,
    maybe,
    number,
    regex,
    result,
    result_list,
    rule,
    set,
    stateful_app,
    string,
    tuple,
    uuid,
)

__all__ = [
    "aggregate",
    "basics",
    "char",
    "decimal",
    "dict",
    "instant",
    "int",
    "key",
    "list",
    "local_date",
    "local_time",
    "maybe",
    "number",
    "regex",
    "result",
    "result_list",
    "rule",
    "set",
    "stateful_app",
    "string",
    "tuple",
    "uuid",
]
