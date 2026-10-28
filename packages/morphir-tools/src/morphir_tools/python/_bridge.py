"""Lazy loading and compatibility checks for the private native compiler."""

from __future__ import annotations

import functools
from importlib import import_module, metadata
from typing import Protocol, cast

from ._types import NativeCompilerInfo, NativeCompilerUnavailable

EXPECTED_NATIVE_VERSION = "0.1.1"
"""The exact ``morphir-python-native`` version this release was qualified with.

It must equal the pin in this distribution's ``pyproject.toml``.
"""

EXPECTED_BRIDGE_API = 1
"""The bridge contract revision this release speaks."""

_DISTRIBUTION = "morphir-python-native"


class NativeModule(Protocol):
    """The private ``morphir_python_native._native`` module."""

    BRIDGE_API: int
    COMPILER_VERSION: str
    __version__: str

    def compile(self, request: str) -> str:
        """Compile a JSON request."""
        ...

    def generate(self, ir: str) -> str:
        """Generate Python from IR JSON text."""
        ...


def _unavailable(detail: str) -> NativeCompilerUnavailable:
    return NativeCompilerUnavailable(
        f"the Morphir Python compiler is unavailable: {detail}. Reinstall "
        f"morphir-python, which requires {_DISTRIBUTION}=={EXPECTED_NATIVE_VERSION}."
    )


@functools.cache
def load() -> NativeCompilerInfo:
    """Import the native module once and check that this release can use it.

    Raises:
        NativeCompilerUnavailable: When the module is missing, or its
            distribution version, module version or bridge revision differ from
            what this release expects.
    """
    try:
        installed = metadata.version(_DISTRIBUTION)
    except metadata.PackageNotFoundError:
        raise _unavailable(f"{_DISTRIBUTION} is not installed") from None
    try:
        native = cast("NativeModule", import_module("morphir_python_native._native"))
    except ImportError as error:
        raise _unavailable(f"its native module cannot be imported ({error})") from None
    if installed != EXPECTED_NATIVE_VERSION:
        raise _unavailable(
            f"{_DISTRIBUTION} {installed} is installed but this release needs "
            f"{EXPECTED_NATIVE_VERSION}"
        )
    if native.__version__ != installed:
        raise _unavailable(
            f"the native module reports {native.__version__} but its distribution "
            f"is {installed}"
        )
    if native.BRIDGE_API != EXPECTED_BRIDGE_API:
        raise _unavailable(
            f"bridge revision {native.BRIDGE_API} differs from the expected "
            f"{EXPECTED_BRIDGE_API}"
        )
    return NativeCompilerInfo(installed, native.BRIDGE_API, native.COMPILER_VERSION)


def module() -> NativeModule:
    """Return the checked native module, loading it on first use."""
    load()
    return cast("NativeModule", import_module("morphir_python_native._native"))
