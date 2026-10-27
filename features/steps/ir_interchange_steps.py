"""Step definitions for the IR interchange CLI."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from behave import given, then, when
from typer.testing import CliRunner

from morphir_tools.cli import app

if TYPE_CHECKING:
    from behave.runner import Context

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "ir" / "v3"


def _workdir(context: Context) -> Path:
    if not hasattr(context, "workdir"):
        context.workdir = Path(tempfile.mkdtemp(prefix="morphir-bdd-"))
    return context.workdir


def _run(context: Context, *args: str) -> None:
    context.result = CliRunner().invoke(app, list(args))


@given('the golden fixture "{name}"')
def step_fixture(context: Context, name: str) -> None:
    """Select a golden format-3 fixture as input."""
    context.input = FIXTURES / name
    context.fixture = context.input


@given("a file with the JSON '{text}'")
def step_json_file(context: Context, text: str) -> None:
    """Write JSON text to an input file."""
    path = _workdir(context) / "input.json"
    path.write_text(text)
    context.input = path


@when('I run "ir inspect" on it')
def step_inspect(context: Context) -> None:
    """Inspect the input file."""
    _run(context, "ir", "inspect", str(context.input))


@when('I convert it to "{target}"')
def step_convert(context: Context, target: str) -> None:
    """Convert the input file to the target version."""
    context.output = _workdir(context) / f"converted-{target}.json"
    _run(
        context,
        "ir",
        "convert",
        str(context.input),
        "--to",
        target,
        "-o",
        str(context.output),
    )


@when("I inspect the converted file")
def step_inspect_converted(context: Context) -> None:
    """Inspect the converted file."""
    _run(context, "ir", "inspect", str(context.output))


@when('I convert the converted file to "{target}"')
def step_convert_converted(context: Context, target: str) -> None:
    """Convert the converted file again."""
    context.input = context.output
    step_convert(context, target)


@then("the command exits with code {code:d}")
def step_exit_code(context: Context, code: int) -> None:
    """Check the exit code."""
    assert context.result.exit_code == code, context.result.output


@then('the output contains "{text}"')
def step_output_contains(context: Context, text: str) -> None:
    """Check standard output."""
    assert text in context.result.stdout, context.result.stdout


@then('the errors contain "{text}"')
def step_errors_contain(context: Context, text: str) -> None:
    """Check standard error."""
    assert text in context.result.stderr, context.result.stderr


@then("the converted file declares formatVersion {version:d}")
def step_declares_version(context: Context, version: int) -> None:
    """Check the converted file's formatVersion."""
    assert json.loads(context.output.read_text())["formatVersion"] == version


@then("the converted file has the same JSON as the fixture")
def step_same_json(context: Context) -> None:
    """Check the converted file matches the fixture JSON."""
    assert json.loads(context.output.read_text()) == json.loads(
        context.fixture.read_text()
    )


@then("no converted file exists")
def step_no_output(context: Context) -> None:
    """Check no output file was written."""
    assert not context.output.exists()
