"""Checks that every value in the Morphir.IR.SDK specification has a Python name.

The Elm names below come from the `vSpec` entries of the matching
`Morphir.IR.SDK.<Module>` file in finos/morphir-elm. Each one maps to the Python
name that `morphir.sdk` must expose. The rule is snake_case, with a trailing
underscore where the result is a Python keyword (`not_`, `and_`, `or_`). The one
exception is `isNaN`, which maps to `is_nan`.
"""

import importlib
import keyword
import re

import pytest

import morphir.sdk

# Module name -> {Elm value name: Python attribute name}.
SPEC: dict[str, dict[str, str]] = {
    "basics": {
        "add": "add",
        "subtract": "subtract",
        "multiply": "multiply",
        "divide": "divide",
        "integerDivide": "integer_divide",
        "power": "power",
        "toFloat": "to_float",
        "round": "round",
        "floor": "floor",
        "ceiling": "ceiling",
        "truncate": "truncate",
        "modBy": "mod_by",
        "remainderBy": "remainder_by",
        "negate": "negate",
        "abs": "abs",
        "clamp": "clamp",
        "isNaN": "is_nan",
        "isInfinite": "is_infinite",
        "sqrt": "sqrt",
        "logBase": "log_base",
        "e": "e",
        "pi": "pi",
        "cos": "cos",
        "sin": "sin",
        "tan": "tan",
        "acos": "acos",
        "asin": "asin",
        "atan": "atan",
        "atan2": "atan2",
        "degrees": "degrees",
        "radians": "radians",
        "turns": "turns",
        "toPolar": "to_polar",
        "fromPolar": "from_polar",
        "equal": "equal",
        "notEqual": "not_equal",
        "lessThan": "less_than",
        "greaterThan": "greater_than",
        "lessThanOrEqual": "less_than_or_equal",
        "greaterThanOrEqual": "greater_than_or_equal",
        "max": "max",
        "min": "min",
        "compare": "compare",
        "not": "not_",
        "and": "and_",
        "or": "or_",
        "xor": "xor",
        "append": "append",
        "identity": "identity",
        "always": "always",
        "composeLeft": "compose_left",
        "composeRight": "compose_right",
        "never": "never",
    },
    "char": {
        "isUpper": "is_upper",
        "isLower": "is_lower",
        "isAlpha": "is_alpha",
        "isAlphaNum": "is_alpha_num",
        "isDigit": "is_digit",
        "isOctDigit": "is_oct_digit",
        "isHexDigit": "is_hex_digit",
        "toUpper": "to_upper",
        "toLower": "to_lower",
        "toLocaleUpper": "to_locale_upper",
        "toLocaleLower": "to_locale_lower",
        "toCode": "to_code",
        "fromCode": "from_code",
    },
    "string": {
        "isEmpty": "is_empty",
        "length": "length",
        "reverse": "reverse",
        "repeat": "repeat",
        "replace": "replace",
        "append": "append",
        "concat": "concat",
        "split": "split",
        "join": "join",
        "words": "words",
        "lines": "lines",
        "slice": "slice",
        "left": "left",
        "right": "right",
        "dropLeft": "drop_left",
        "dropRight": "drop_right",
        "contains": "contains",
        "startsWith": "starts_with",
        "endsWith": "ends_with",
        "indexes": "indexes",
        "indices": "indices",
        "toInt": "to_int",
        "fromInt": "from_int",
        "toFloat": "to_float",
        "fromFloat": "from_float",
        "fromChar": "from_char",
        "cons": "cons",
        "uncons": "uncons",
        "toList": "to_list",
        "fromList": "from_list",
        "toUpper": "to_upper",
        "toLower": "to_lower",
        "pad": "pad",
        "padLeft": "pad_left",
        "padRight": "pad_right",
        "trim": "trim",
        "trimLeft": "trim_left",
        "trimRight": "trim_right",
        "map": "map",
        "filter": "filter",
        "foldl": "foldl",
        "foldr": "foldr",
        "any": "any",
        "all": "all",
    },
    "list": {
        "singleton": "singleton",
        "repeat": "repeat",
        "range": "range",
        "cons": "cons",
        "map": "map",
        "indexedMap": "indexed_map",
        "foldl": "foldl",
        "foldr": "foldr",
        "filter": "filter",
        "filterMap": "filter_map",
        "length": "length",
        "reverse": "reverse",
        "member": "member",
        "all": "all",
        "any": "any",
        "maximum": "maximum",
        "minimum": "minimum",
        "sum": "sum",
        "product": "product",
        "append": "append",
        "concat": "concat",
        "concatMap": "concat_map",
        "intersperse": "intersperse",
        "map2": "map2",
        "map3": "map3",
        "map4": "map4",
        "map5": "map5",
        "sort": "sort",
        "sortBy": "sort_by",
        "sortWith": "sort_with",
        "isEmpty": "is_empty",
        "head": "head",
        "tail": "tail",
        "take": "take",
        "drop": "drop",
        "partition": "partition",
        "unzip": "unzip",
        "innerJoin": "inner_join",
        "leftJoin": "left_join",
    },
    "dict": {
        "empty": "empty",
        "singleton": "singleton",
        "insert": "insert",
        "update": "update",
        "remove": "remove",
        "isEmpty": "is_empty",
        "member": "member",
        "get": "get",
        "size": "size",
        "keys": "keys",
        "values": "values",
        "toList": "to_list",
        "fromList": "from_list",
        "map": "map",
        "foldl": "foldl",
        "foldr": "foldr",
        "filter": "filter",
        "partition": "partition",
        "union": "union",
        "intersect": "intersect",
        "diff": "diff",
        "merge": "merge",
    },
    "set": {
        "empty": "empty",
        "singleton": "singleton",
        "insert": "insert",
        "remove": "remove",
        "isEmpty": "is_empty",
        "member": "member",
        "size": "size",
        "toList": "to_list",
        "fromList": "from_list",
        "map": "map",
        "foldl": "foldl",
        "foldr": "foldr",
        "filter": "filter",
        "partition": "partition",
        "union": "union",
        "intersect": "intersect",
        "diff": "diff",
    },
    "maybe": {
        "andThen": "and_then",
        "map": "map",
        "map2": "map2",
        "map3": "map3",
        "map4": "map4",
        "map5": "map5",
        "withDefault": "with_default",
        "hasValue": "has_value",
    },
    "result": {
        "andThen": "and_then",
        "map": "map",
        "map2": "map2",
        "map3": "map3",
        "map4": "map4",
        "map5": "map5",
        "withDefault": "with_default",
        "toMaybe": "to_maybe",
        "fromMaybe": "from_maybe",
        "mapError": "map_error",
    },
    "tuple": {
        "pair": "pair",
        "first": "first",
        "second": "second",
        "mapFirst": "map_first",
        "mapSecond": "map_second",
        "mapBoth": "map_both",
    },
    "decimal": {
        "fromInt": "from_int",
        "fromFloat": "from_float",
        "fromString": "from_string",
        "hundred": "hundred",
        "thousand": "thousand",
        "million": "million",
        "tenth": "tenth",
        "hundredth": "hundredth",
        "thousandth": "thousandth",
        "millionth": "millionth",
        "bps": "bps",
        "toString": "to_string",
        "toFloat": "to_float",
        "add": "add",
        "sub": "sub",
        "negate": "negate",
        "mul": "mul",
        "div": "div",
        "divWithDefault": "div_with_default",
        "truncate": "truncate",
        "round": "round",
        "gt": "gt",
        "gte": "gte",
        "eq": "eq",
        "neq": "neq",
        "lt": "lt",
        "lte": "lte",
        "compare": "compare",
        "abs": "abs",
        "shiftDecimalLeft": "shift_decimal_left",
        "shiftDecimalRight": "shift_decimal_right",
        "zero": "zero",
        "one": "one",
        "minusOne": "minus_one",
    },
    "int": {
        "fromInt8": "from_int8",
        "toInt8": "to_int8",
        "fromInt16": "from_int16",
        "toInt16": "to_int16",
        "fromInt32": "from_int32",
        "toInt32": "to_int32",
        "fromInt64": "from_int64",
        "toInt64": "to_int64",
    },
    "number": {
        "fromInt": "from_int",
        "equal": "equal",
        "notEqual": "not_equal",
        "lessThan": "less_than",
        "lessThanOrEqual": "less_than_or_equal",
        "greaterThan": "greater_than",
        "greaterThanOrEqual": "greater_than_or_equal",
        "add": "add",
        "subtract": "subtract",
        "multiply": "multiply",
        "divide": "divide",
        "abs": "abs",
        "negate": "negate",
        "reciprocal": "reciprocal",
        "coerceToDecimal": "coerce_to_decimal",
        "toDecimal": "to_decimal",
        "toFractionalString": "to_fractional_string",
        "simplify": "simplify",
        "isSimplified": "is_simplified",
        "zero": "zero",
        "one": "one",
    },
}

# Values that Elm defines as constants, not functions.
CONSTANTS: dict[str, frozenset[str]] = {
    "basics": frozenset({"e", "pi"}),
    "decimal": frozenset({"zero", "one", "minus_one"}),
    "number": frozenset({"zero", "one"}),
}

# Elm names that do not follow the snake_case rule.
EXCEPTIONS: dict[str, str] = {"isNaN": "is_nan"}

_CASES = [
    (module, elm_name, python_name)
    for module, names in SPEC.items()
    for elm_name, python_name in names.items()
]


def _to_snake_case(elm_name: str) -> str:
    if elm_name in EXCEPTIONS:
        return EXCEPTIONS[elm_name]
    snake = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", elm_name).lower()
    return f"{snake}_" if keyword.iskeyword(snake) else snake


class TestSpecCoverage:
    def test_all_core_modules_are_listed(self) -> None:
        assert sorted(SPEC) == sorted(morphir.sdk.__all__)

    def test_spec_size(self) -> None:
        assert {module: len(names) for module, names in SPEC.items()} == {
            "basics": 53,
            "char": 13,
            "string": 44,
            "list": 39,
            "dict": 22,
            "set": 17,
            "maybe": 8,
            "result": 10,
            "tuple": 6,
            "decimal": 34,
            "int": 8,
            "number": 21,
        }

    @pytest.mark.parametrize(("module", "elm_name", "python_name"), _CASES)
    def test_value_exists(self, module: str, elm_name: str, python_name: str) -> None:
        sdk_module = importlib.import_module(f"morphir.sdk.{module}")
        assert hasattr(sdk_module, python_name), f"{module}.{python_name} is missing"
        value = getattr(sdk_module, python_name)
        if python_name in CONSTANTS.get(module, frozenset()):
            assert not callable(value)
        else:
            assert callable(value), f"{module}.{python_name} is not callable"

    @pytest.mark.parametrize(("module", "elm_name", "python_name"), _CASES)
    def test_name_follows_the_mapping_rule(
        self, module: str, elm_name: str, python_name: str
    ) -> None:
        assert python_name == _to_snake_case(elm_name)

    @pytest.mark.parametrize("module", sorted(SPEC))
    def test_values_are_in_dunder_all(self, module: str) -> None:
        sdk_module = importlib.import_module(f"morphir.sdk.{module}")
        missing = set(SPEC[module].values()) - set(sdk_module.__all__)
        assert not missing
