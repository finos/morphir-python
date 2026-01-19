"""Step definitions for project setup verification."""

from typing import TYPE_CHECKING, Any

from behave import given, then, when

if TYPE_CHECKING:
    from behave.runner import Context


@given("the Python environment is set up")
def step_python_environment_setup(context: Context) -> None:
    """Verify Python environment is available."""
    import sys

    context.python_version = sys.version_info
    assert context.python_version >= (3, 14), "Python 3.14+ is required"


@when("I import the morphir module")
def step_import_morphir(context: Context) -> None:
    """Import the morphir module."""
    import morphir

    context.module = morphir


@when("I import the morphir_tools module")
def step_import_morphir_tools(context: Context) -> None:
    """Import the morphir_tools module."""
    import morphir_tools

    context.module = morphir_tools


@when("I import the morphir.ir module")
def step_import_morphir_ir(context: Context) -> None:
    """Import the morphir.ir module."""
    from morphir import ir

    context.module = ir


@then("the module should be available")
def step_module_available(context: Context) -> None:
    """Verify the module was imported successfully."""
    assert context.module is not None


@then("it should have a version attribute")
def step_has_version(context: Context) -> None:
    """Verify the module has a __version__ attribute."""
    assert hasattr(context.module, "__version__")
    version: Any = context.module.__version__
    assert isinstance(version, str)
    assert len(version) > 0
