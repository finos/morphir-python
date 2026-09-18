"""Step definitions for the Morphir SDK feature."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from behave import given, then, when

from morphir.sdk import basics, maybe
from morphir.sdk import decimal as sdk_decimal
from morphir.sdk import dict as sdk_dict

if TYPE_CHECKING:
    from behave.runner import Context


def _parse_pairs(text: str) -> tuple[tuple[str, int], ...]:
    pairs = (item.strip().split("=") for item in text.split(","))
    return tuple((key, int(value)) for key, value in pairs)


@when('I import the SDK module "{name}"')
def step_import_sdk_module(context: Context, name: str) -> None:
    """Import one module of the morphir.sdk package."""
    context.sdk_module = importlib.import_module(f"morphir.sdk.{name}")


@then("the SDK module should be available")
def step_sdk_module_available(context: Context) -> None:
    """Verify the SDK module was imported and exports names."""
    assert context.sdk_module is not None
    assert context.sdk_module.__all__, "The SDK module exports no names"


@given('an SDK dictionary built from the pairs "{pairs}"')
def step_build_dictionary(context: Context, pairs: str) -> None:
    """Build a dictionary from text such as "b=2, a=1"."""
    context.dictionary = sdk_dict.from_list(_parse_pairs(pairs))


@given('another SDK dictionary built from the pairs "{pairs}"')
def step_build_other_dictionary(context: Context, pairs: str) -> None:
    """Build a second dictionary from text such as "a=1, b=2"."""
    context.other_dictionary = sdk_dict.from_list(_parse_pairs(pairs))


@when("I list the keys of the dictionary")
def step_list_keys(context: Context) -> None:
    """List the keys of the dictionary."""
    context.keys = sdk_dict.keys(context.dictionary)


@then('the keys should be "{expected}"')
def step_keys_should_be(context: Context, expected: str) -> None:
    """Verify the keys and their order."""
    assert ", ".join(context.keys) == expected, f"Got {context.keys}"


@then("the two dictionaries should be equal")
def step_dictionaries_equal(context: Context) -> None:
    """Verify structural equality of the two dictionaries."""
    assert basics.equal(context.dictionary, context.other_dictionary)
    assert context.dictionary == context.other_dictionary


@when("I round the float {value:f} with the SDK")
def step_round_float(context: Context, value: float) -> None:
    """Round a float with Basics.round."""
    context.rounded = basics.round(value)


@then("the rounded value should be {expected:d}")
def step_rounded_value(context: Context, expected: int) -> None:
    """Verify the rounded value."""
    assert context.rounded == expected, f"Got {context.rounded}"


@when('I add the decimals "{left}" and "{right}" with the SDK')
def step_add_decimals(context: Context, left: str, right: str) -> None:
    """Parse and add two decimals."""
    a = maybe.with_default(sdk_decimal.zero, sdk_decimal.from_string(left))
    b = maybe.with_default(sdk_decimal.zero, sdk_decimal.from_string(right))
    context.decimal_result = sdk_decimal.add(a, b)


@then('the decimal result should print as "{expected}"')
def step_decimal_prints_as(context: Context, expected: str) -> None:
    """Verify the positional string form of the result."""
    actual = sdk_decimal.to_string(context.decimal_result)
    assert actual == expected, f"Got {actual}"
