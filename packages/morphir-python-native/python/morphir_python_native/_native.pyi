"""Type information for the private CPython bridge to the Morphir Python compiler."""

from typing import Final

BRIDGE_API: Final[int]
"""Revision of the JSON contract with ``morphir_tools.python``."""

COMPILER_VERSION: Final[str]
"""Version of the linked ``morphir-python-binding`` compiler."""

__version__: Final[str]
"""Version of this native module, equal to the distribution version."""

def compile(request: str) -> str:
    """Compile a JSON request and return a JSON result."""

def generate(ir: str) -> str:
    """Generate Python from versioned IR JSON text and return a JSON result."""
