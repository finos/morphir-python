"""Tests for ``morphir-python compile`` and ``generate`` (capability tools/python-codegen)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from morphir.ir import diagnostics as d
from morphir.ir.v3 import codec as v3_codec
from morphir.ir.v3 import distribution as v3_dist
from morphir.ir.v4 import codec as v4_codec
from morphir_tools import cli
from morphir_tools.cli import app
from morphir_tools.python import diagnostics as codes

runner = CliRunner()
V3_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ir" / "v3"

MODELS = """\
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Pending:
    pass

@dataclass(frozen=True)
class Approved:
    amount: float

type Decision = Pending | Approved

type Point = tuple[float, float]
"""

RULES = """\
from __future__ import annotations
from collections.abc import Callable
from .models import Decision, Point

def choose(flag: bool, first: int, second: int) -> int:
    if flag:
        return first
    else:
        return second

def pick(flag: bool, first: Decision, second: Decision) -> Decision:
    return first if flag else second

def pair(left: float, right: float) -> Point:
    return (left, right)

def apply_twice(step: Callable[[int], int], value: int) -> int:
    return step(step(value))

def twice_identity(value: int) -> int:
    return apply_twice(lambda item: item, value)
"""


def library_at(path: Path) -> v3_dist.Library:
    library = v3_codec.decode_versioned_distribution(path.read_text())
    assert isinstance(library, v3_dist.Library)
    return library


def run(*args: str | Path) -> Result:
    return runner.invoke(app, [str(a) for a in args])


@pytest.fixture
def source(tmp_path: Path) -> Path:
    root = tmp_path / "src"
    (root / "acme").mkdir(parents=True)
    (root / "acme" / "models.py").write_text(MODELS)
    (root / "acme" / "rules.py").write_text(RULES)
    return root


def compile_to(source: Path, output: Path, *extra: str) -> Path:
    result = run(
        "compile", source, "--package", "acme/example", "--output", output, *extra
    )
    assert result.exit_code == 0, result.output
    return output


def tree(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): path.read_text()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class TestCompile:
    def test_directory_defaults_to_v3_and_inspects(
        self, source: Path, tmp_path: Path
    ) -> None:
        output = compile_to(source, tmp_path / "model.json")
        library = library_at(output)
        modules = {
            "/".join("-".join(n) for n in path): module.access.value
            for path, module in library.definition.modules.items()
        }
        assert modules == {"acme/models": "Public", "acme/rules": "Public"}
        inspected = run("ir", "inspect", output)
        assert inspected.exit_code == 0
        assert "format: 3.0.0" in inspected.output
        assert "package: acme/example" in inspected.output

    def test_v4_reports_draft_status(self, source: Path, tmp_path: Path) -> None:
        result = run(
            "compile",
            source,
            "--package",
            "acme/example",
            "--ir-version",
            "v4",
            "--output",
            tmp_path / "model.json",
        )
        assert result.exit_code == 0, result.output
        assert v4_codec.DRAFT_NOTICE in result.output
        inspected = run("ir", "inspect", tmp_path / "model.json")
        assert "format: 4.0.0" in inspected.output

    def test_repeated_expose_selects_modules(
        self, source: Path, tmp_path: Path
    ) -> None:
        output = compile_to(source, tmp_path / "model.json", "--expose", "acme/models")
        library = library_at(output)
        access = sorted(
            module.access.value for module in library.definition.modules.values()
        )
        assert access == ["Private", "Public"]

    def test_single_file_uses_its_parent_as_root(self, tmp_path: Path) -> None:
        file = tmp_path / "rules.py"
        file.write_text("def keep(value: int) -> int:\n    return value\n")
        output = compile_to(file, tmp_path / "model.json")
        library = library_at(output)
        assert [
            "/".join("-".join(n) for n in path) for path in library.definition.modules
        ] == ["rules"]

    def test_failure_keeps_existing_output_and_reports_location(
        self, tmp_path: Path
    ) -> None:
        file = tmp_path / "broken.py"
        file.write_text("def broken(:\n")
        output = tmp_path / "model.json"
        output.write_text("previous")
        result = run("compile", file, "--package", "acme/x", "--output", output)
        assert result.exit_code == 1
        assert f"error: {codes.PY_SYNTAX} at broken.py:1:" in result.output
        assert output.read_text() == "previous"

    def test_unsupported_construct_fails(self, tmp_path: Path) -> None:
        file = tmp_path / "side_effect.py"
        file.write_text("open('owned.txt', 'w').write('x')\n")
        result = run(
            "compile", file, "--package", "acme/x", "--output", tmp_path / "m.json"
        )
        assert result.exit_code == 1
        assert codes.PY_UNSUPPORTED in result.output
        assert not (tmp_path / "m.json").exists()
        assert not (tmp_path / "owned.txt").exists()

    def test_empty_directory_is_an_error(self, tmp_path: Path) -> None:
        (tmp_path / "empty").mkdir()
        result = run(
            "compile", tmp_path / "empty", "--package", "acme/x", "--output", "x.json"
        )
        assert result.exit_code == 1
        assert "no Python source files" in result.output

    def test_symlinked_directories_are_not_followed(
        self, source: Path, tmp_path: Path
    ) -> None:
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "extra.py").write_text("def other(v: int) -> int:\n    return v\n")
        (source / "linked").symlink_to(outside, target_is_directory=True)
        output = compile_to(source, tmp_path / "model.json")
        library = library_at(output)
        assert len(library.definition.modules) == 2

    def test_unreadable_source_is_reported(self, tmp_path: Path) -> None:
        result = run(
            "compile", tmp_path / "absent.py", "--package", "a/b", "--output", "x.json"
        )
        assert result.exit_code == 1
        assert "cannot read" in result.output


class TestGenerate:
    @pytest.mark.parametrize("version", ["v3", "v4"])
    def test_generates_nested_importable_modules(
        self, source: Path, tmp_path: Path, version: str
    ) -> None:
        model = compile_to(source, tmp_path / "m.json", "--ir-version", version)
        out = tmp_path / "generated"
        result = run("generate", model, "--output-dir", out)
        assert result.exit_code == 0, result.output
        assert sorted(tree(out)) == ["acme/models.py", "acme/rules.py"]
        check = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                "import sys; sys.path.insert(0, sys.argv[1]);"
                "from acme import rules, models;"
                "print(rules.choose(True, 1, 2), rules.choose(False, 1, 2),"
                " rules.pair(1.0, 2.0), rules.twice_identity(7),"
                " rules.pick(False, models.Pending(), models.Approved(2.5)))",
                str(out),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        assert check.stdout.strip() == ("1 2 (1.0, 2.0) 7 Approved(amount=2.5)")

    @pytest.mark.parametrize("version", ["v3", "v4"])
    def test_round_trip_recompiles_to_equal_ir(
        self, source: Path, tmp_path: Path, version: str
    ) -> None:
        first = compile_to(
            source,
            tmp_path / "first.json",
            "--ir-version",
            version,
            "--expose",
            "acme/models",
        )
        out = tmp_path / "generated"
        assert run("generate", first, "--output-dir", out).exit_code == 0
        second = compile_to(
            out,
            tmp_path / "second.json",
            "--ir-version",
            version,
            "--expose",
            "acme/models",
        )
        codec = v3_codec if version == "v3" else v4_codec
        assert codec.decode_versioned_distribution(
            first.read_text()
        ) == codec.decode_versioned_distribution(second.read_text())

    def test_refuses_a_nonempty_directory(self, source: Path, tmp_path: Path) -> None:
        model = compile_to(source, tmp_path / "m.json")
        out = tmp_path / "generated"
        out.mkdir()
        (out / "keep.txt").write_text("mine")
        result = run("generate", model, "--output-dir", out)
        assert result.exit_code == 1
        assert "not empty" in result.output
        assert tree(out) == {"keep.txt": "mine"}

    def test_accepts_an_empty_directory(self, source: Path, tmp_path: Path) -> None:
        model = compile_to(source, tmp_path / "m.json")
        out = tmp_path / "generated"
        out.mkdir()
        assert run("generate", model, "--output-dir", out).exit_code == 0
        assert sorted(tree(out)) == ["acme/models.py", "acme/rules.py"]

    def test_refuses_a_symlinked_output_directory(
        self, source: Path, tmp_path: Path
    ) -> None:
        model = compile_to(source, tmp_path / "m.json")
        real = tmp_path / "real"
        real.mkdir()
        (tmp_path / "link").symlink_to(real, target_is_directory=True)
        result = run("generate", model, "--output-dir", tmp_path / "link")
        assert result.exit_code == 1
        assert "symbolic link" in result.output

    def test_injected_write_failure_publishes_nothing(
        self, source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        model = compile_to(source, tmp_path / "m.json")
        out = tmp_path / "generated"
        calls: list[Path] = []
        original = Path.write_text

        def failing(self: Path, data: str, *args: object, **kwargs: object) -> int:
            calls.append(self)
            if len(calls) == 2:
                raise OSError(28, "No space left on device")
            return original(self, data, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "write_text", failing)
        result = run("generate", model, "--output-dir", out)
        monkeypatch.undo()
        assert result.exit_code == 1
        assert "No space left on device" in result.output
        assert "Traceback" not in result.output
        assert not out.exists()
        assert [p.name for p in tmp_path.iterdir() if p.name.startswith(".")] == []

    def test_late_module_rejection_writes_nothing(
        self, source: Path, tmp_path: Path
    ) -> None:
        model = json.loads(compile_to(source, tmp_path / "m.json").read_text())
        elm = json.loads((V3_FIXTURES / "elm-simpleValueTree.json").read_text())
        ((_, late),) = elm["distribution"][3]["modules"]
        # "zzz" sorts after every supported module, so it is generated last.
        model["distribution"][3]["modules"].append([[["zzz"]], late])
        mixed = tmp_path / "mixed.json"
        mixed.write_text(json.dumps(model))
        out = tmp_path / "generated"
        result = run("generate", mixed, "--output-dir", out)
        assert result.exit_code == 1
        assert "error: PY" in result.output
        assert not out.exists()

    @pytest.mark.parametrize(
        ("document", "code"),
        [
            ({"distribution": []}, d.MISSING_FORMAT_VERSION),
            (
                {"formatVersion": "three", "distribution": []},
                d.INVALID_FORMAT_VERSION_SYNTAX,
            ),
            (
                {"formatVersion": 9, "distribution": []},
                d.UNSUPPORTED_FORMAT_VERSION_MAJOR,
            ),
        ],
    )
    def test_version_errors_use_the_library_codes(
        self, tmp_path: Path, document: object, code: str
    ) -> None:
        model = tmp_path / "bad.json"
        model.write_text(json.dumps(document))
        result = run("generate", model, "--output-dir", tmp_path / "out")
        assert result.exit_code == 1
        assert f"error: {code}" in result.output
        assert not (tmp_path / "out").exists()

    def test_specs_distribution_is_rejected(self, tmp_path: Path) -> None:
        specs = (
            Path(__file__).resolve().parents[1]
            / "fixtures"
            / "ir"
            / "v3"
            / "mck-distributions-0011-specs.json"
        )
        result = run("generate", specs, "--output-dir", tmp_path / "out")
        assert result.exit_code == 1
        assert codes.UNSUPPORTED_DISTRIBUTION in result.output


class TestArtifactPaths:
    @pytest.mark.parametrize(
        "paths",
        [
            ("/etc/passwd.py",),
            ("../escape.py",),
            ("acme/../../escape.py",),
            ("C:/windows.py",),
            ("back\\slash.py",),
            ("",),
            ("acme//double.py",),
            ("a.py", "a.py"),
            ("Rules.py", "rules.py"),
            ("acme.py", "acme.py/inner.py"),
        ],
    )
    def test_invalid_artifact_sets_are_rejected(self, paths: tuple[str, ...]) -> None:
        with pytest.raises(cli.OutputError):
            cli.validate_artifact_paths(paths)

    def test_valid_artifact_set_is_accepted(self) -> None:
        cli.validate_artifact_paths(("acme/models.py", "acme/rules.py", "top.py"))


class TestIndependence:
    def test_ir_commands_do_not_load_the_compiler(self, tmp_path: Path) -> None:
        fixture = (
            Path(__file__).resolve().parents[1]
            / "fixtures"
            / "ir"
            / "v3"
            / "elm-simpleValueTree.json"
        )
        script = textwrap.dedent(
            """
            import sys
            from typer.testing import CliRunner
            from morphir_tools.cli import app
            runner = CliRunner()
            assert runner.invoke(app, ["ir", "inspect", sys.argv[1]]).exit_code == 0
            out = sys.argv[2]
            assert runner.invoke(
                app, ["ir", "convert", sys.argv[1], "--to", "v4", "-o", out]
            ).exit_code == 0
            loaded = [m for m in sys.modules if m.startswith("morphir_python_native")]
            assert loaded == [], loaded
            assert "morphir_tools.python._api" not in sys.modules
            """
        )
        subprocess.run(
            [sys.executable, "-c", script, str(fixture), str(tmp_path / "v4.json")],
            check=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
