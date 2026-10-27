"""Step definitions for Python compilation and generation."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from behave import given, then, when
from typer.testing import CliRunner

from morphir.ir import format_version as fv
from morphir.ir.v3 import access_controlled as v3_ac
from morphir.ir.v3 import codec as v3_codec
from morphir.ir.v3 import distribution as v3_dist
from morphir.ir.v4 import codec as v4_codec
from morphir.ir.v4 import distribution as v4_dist
from morphir_tools.cli import app

if TYPE_CHECKING:
    from behave.runner import Context

SAMPLES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "python"

CHECK = (
    "import sys; sys.path.insert(0, sys.argv[1]);"
    "from acme import models, rules;"
    "print(rules.choose(True, 1, 2), rules.choose(False, 1, 2),"
    " rules.pair(1.0, 2.0), rules.twice_identity(7),"
    " rules.pick(False, models.Pending(), models.Approved(2.5)))"
)


def _workdir(context: Context) -> Path:
    if not hasattr(context, "workdir"):
        context.workdir = Path(tempfile.mkdtemp(prefix="morphir-bdd-"))
    return context.workdir


def _run(context: Context, *args: str) -> None:
    context.result = CliRunner().invoke(app, list(args))


def _compile(context: Context, source: Path, output: Path) -> None:
    args = ["compile", str(source), "--package", context.package]
    args += ["--ir-version", context.version, "--output", str(output)]
    for module in context.exposed:
        args += ["--expose", module]
    _run(context, *args)


def _decode(context: Context, path: Path) -> object:
    codec = v3_codec if context.version == "v3" else v4_codec
    return codec.decode_versioned_distribution(path.read_text())


@given('the Python sample project "{name}"')
def step_sample(context: Context, name: str) -> None:
    """Select a checked-in Python source tree."""
    context.source = SAMPLES / name


@given('a Python source file with the text "{text}"')
def step_source_file(context: Context, text: str) -> None:
    """Write a one-line Python source file."""
    context.source = _workdir(context) / "bad.py"
    context.source.write_text(text + "\n")


@when('I compile it with package "{package}" to IR "{version}" exposing "{module}"')
def step_compile_exposing(
    context: Context, package: str, version: str, module: str
) -> None:
    """Compile the source with one exposed module."""
    context.package, context.version, context.exposed = package, version, [module]
    context.model = _workdir(context) / "model.json"
    _compile(context, context.source, context.model)


@when('I compile it with package "{package}" to IR "{version}"')
def step_compile(context: Context, package: str, version: str) -> None:
    """Compile the source exposing every module."""
    context.package, context.version, context.exposed = package, version, []
    context.model = _workdir(context) / "model.json"
    _compile(context, context.source, context.model)


@when("I generate Python from the compiled model")
def step_generate(context: Context) -> None:
    """Generate Python into a new directory."""
    context.generated = _workdir(context) / "generated"
    _run(
        context, "generate", str(context.model), "--output-dir", str(context.generated)
    )


@when('I generate Python into a directory that already contains "{name}"')
def step_generate_nonempty(context: Context, name: str) -> None:
    """Generate Python into a directory holding a user file."""
    context.generated = _workdir(context) / "generated"
    context.generated.mkdir()
    (context.generated / name).write_text("keep")
    _run(
        context, "generate", str(context.model), "--output-dir", str(context.generated)
    )


@when("I recompile the generated Python with the same options")
def step_recompile(context: Context) -> None:
    """Compile the generated tree again."""
    context.recompiled = _workdir(context) / "recompiled.json"
    _compile(context, context.generated, context.recompiled)
    assert context.result.exit_code == 0, context.result.output


@when("a program compiles the project with the Python API")
def step_api(context: Context) -> None:
    """Compile through morphir_tools.python in this process."""
    from morphir_tools.python import SourceDocument, compile_sources

    root = context.source
    context.compiled = compile_sources(
        [
            SourceDocument(path.relative_to(root).as_posix(), path.read_text())
            for path in sorted(root.rglob("*.py"))
        ],
        package="acme/example",
    )


@then("the compiled model declares formatVersion {major:d}")
def step_format(context: Context, major: int) -> None:
    """Check the written format version."""
    version, _ = fv.read_document(context.model.read_text())
    assert version.major == major, version


@then('module "{public}" is public and module "{private}" is private')
def step_access(context: Context, public: str, private: str) -> None:
    """Check module access in the decoded model."""
    model = _decode(context, context.model)
    assert isinstance(model, v3_dist.Library | v4_dist.LibraryDistribution)
    access: dict[str, str] = {}
    for path, module in model.definition.modules.items():
        name = "/".join("-".join(words) for words in path)
        if isinstance(module, v3_ac.AccessControlled):
            access[name] = module.access.value
        else:
            access[name] = type(module).__name__
    assert access == {public: "Public", private: "Private"}, access


@then('the generated files are "{names}"')
def step_generated_files(context: Context, names: str) -> None:
    """Check the generated relative paths."""
    found = sorted(
        path.relative_to(context.generated).as_posix()
        for path in context.generated.rglob("*")
        if path.is_file()
    )
    assert found == [name.strip() for name in names.split(",")], found


@then("the generated code gives the expected results in a separate process")
def step_execute(context: Context) -> None:
    """Run the generated modules in a new interpreter."""
    completed = subprocess.run(
        [sys.executable, "-I", "-c", CHECK, str(context.generated)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert completed.stdout.strip() == "1 2 (1.0, 2.0) 7 Approved(amount=2.5)", (
        completed.stdout + completed.stderr
    )


@then("the recompiled model equals the compiled model")
def step_equal(context: Context) -> None:
    """Compare the decoded models."""
    assert _decode(context, context.model) == _decode(context, context.recompiled)


@then("no compiled model is written")
def step_no_model(context: Context) -> None:
    """Check that compilation wrote nothing."""
    assert not context.model.exists()


@then('the directory still contains only "{name}"')
def step_only(context: Context, name: str) -> None:
    """Check that generation left the user's directory alone."""
    assert [p.name for p in context.generated.iterdir()] == [name]


@then("the program receives a v3 Library model")
def step_api_model(context: Context) -> None:
    """Check the API result type."""
    from morphir_tools.python import CompiledV3

    assert isinstance(context.compiled, CompiledV3), context.compiled
    assert isinstance(context.compiled.distribution, v3_dist.Library)


@then("generating Python from that model returns {count:d} artifacts")
def step_api_generate(context: Context, count: int) -> None:
    """Generate in process from the API model."""
    from morphir_tools.python import Generated, generate_python

    generated = generate_python(context.compiled.distribution)
    assert isinstance(generated, Generated), generated
    assert len(generated.artifacts) == count
