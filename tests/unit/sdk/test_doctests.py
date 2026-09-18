"""Runs the examples in the morphir.sdk docstrings."""

import doctest
import importlib

import pytest

import morphir.sdk

_MODULES = ["morphir.sdk", *(f"morphir.sdk.{name}" for name in morphir.sdk.__all__)]


@pytest.mark.parametrize("module_name", _MODULES)
def test_docstring_examples(module_name: str) -> None:
    module = importlib.import_module(module_name)
    results = doctest.testmod(module)
    assert results.failed == 0
