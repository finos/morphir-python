"""Tests for the morphir-python IR interchange CLI (capability tools/ir-interchange)."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from morphir.ir import diagnostics as d
from morphir_tools.cli import app

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ir" / "v3"
VALUE_TREE = FIXTURES / "elm-simpleValueTree.json"
REFERENCE = FIXTURES / "elm-reference-model.json"
KIT_SPECS = FIXTURES / "mck-distributions-0011-specs.json"
RUST_SPECS = FIXTURES / "rust-classic-specs-transport.json"
LEGACY = FIXTURES.parent / "legacy"
RENTALS_1 = LEGACY / "elm-rentals-format-1.json"
RENTALS_2 = LEGACY / "elm-rentals-format-2.json"

runner = CliRunner()


def run(*args: str | Path):  # type: ignore[no-untyped-def]
    return runner.invoke(app, [str(a) for a in args])


def write(tmp_path: Path, name: str, content: object) -> Path:
    path = tmp_path / name
    path.write_text(content if isinstance(content, str) else json.dumps(content))
    return path


@pytest.fixture
def v4_file(tmp_path: Path) -> Path:
    out = tmp_path / "v4.json"
    assert run("ir", "convert", VALUE_TREE, "--to", "v4", "-o", out).exit_code == 0
    return out


class TestHelp:
    def test_command_name(self) -> None:
        result = run("--help")
        assert result.exit_code == 0
        assert "morphir-python" in result.output

    def test_ir_help(self) -> None:
        result = run("ir", "--help")
        assert result.exit_code == 0
        assert "inspect" in result.output
        assert "convert" in result.output

    def test_main_entry_point(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import sys

        from morphir_tools import cli

        monkeypatch.setattr(sys, "argv", ["morphir-python", "ir", "--help"])
        with pytest.raises(SystemExit) as info:
            cli.main()
        assert info.value.code == 0


class TestInspect:
    def test_format_3(self) -> None:
        result = run("ir", "inspect", VALUE_TREE)
        assert result.exit_code == 0
        assert "format: 3.0.0" in result.stdout
        assert "kind: Library" in result.stdout
        assert "package: morphir/example/app" in result.stdout
        assert "draft" not in result.stdout

    def test_v3_specs(self) -> None:
        result = run("ir", "inspect", KIT_SPECS)
        assert result.exit_code == 0
        assert "format: 3.1.0" in result.stdout
        assert "kind: Specs" in result.stdout
        assert "package: my/pkg" in result.stdout

    def test_library_at_3_1_0(self, tmp_path: Path) -> None:
        doc = json.loads(VALUE_TREE.read_text())
        doc["formatVersion"] = "3.1.0"
        result = run("ir", "inspect", write(tmp_path, "x.json", doc))
        assert result.exit_code == 0
        assert "format: 3.1.0" in result.stdout
        assert "kind: Library" in result.stdout

    def test_specs_before_3_1(self, tmp_path: Path) -> None:
        doc = {"formatVersion": 3, "distribution": ["Specs", [["a"]], [], {}]}
        result = run("ir", "inspect", write(tmp_path, "x.json", doc))
        assert result.exit_code == 1
        assert f"{d.SPECS_BEFORE_3_1} at formatVersion" in result.stderr

    def test_v4_is_labelled_draft(self, v4_file: Path) -> None:
        result = run("ir", "inspect", v4_file)
        assert result.exit_code == 0
        assert "format: 4.0.0" in result.stdout
        assert "draft" in result.stdout

    def test_missing_version(self, tmp_path: Path) -> None:
        result = run("ir", "inspect", write(tmp_path, "x.json", {"distribution": []}))
        assert result.exit_code == 1
        assert d.MISSING_FORMAT_VERSION in result.stderr
        assert "regenerate" in result.stderr

    @pytest.mark.parametrize(
        ("version", "code"),
        [
            ("3.2.0", d.UNSUPPORTED_FORMAT_VERSION_MINOR),
            (5, d.UNSUPPORTED_FORMAT_VERSION_MAJOR),
        ],
    )
    def test_unsupported_versions(
        self, tmp_path: Path, version: object, code: str
    ) -> None:
        doc = {"formatVersion": version, "distribution": []}
        result = run("ir", "inspect", write(tmp_path, "x.json", doc))
        assert result.exit_code == 1
        assert code in result.stderr
        assert "only 3.0.x, 3.1.x and draft 4.0.x" in result.stderr

    def test_unreadable_file(self, tmp_path: Path) -> None:
        result = run("ir", "inspect", tmp_path / "missing.json")
        assert result.exit_code == 1
        assert "cannot read" in result.stderr

    def test_same_codes_as_library(self, tmp_path: Path) -> None:
        doc = {"formatVersion": 3, "distribution": ["Application", [], [], {}]}
        result = run("ir", "inspect", write(tmp_path, "x.json", doc))
        assert result.exit_code == 1
        assert d.UNKNOWN_NODE in result.stderr

    def test_specs_kind(self, tmp_path: Path) -> None:
        doc = {"formatVersion": 4, "distribution": {"Specs": {"packageName": "a/b"}}}
        result = run("ir", "inspect", write(tmp_path, "x.json", doc))
        assert result.exit_code == 0
        assert "kind: Specs" in result.stdout

    def test_application_kind(self, tmp_path: Path) -> None:
        doc = {
            "formatVersion": 4,
            "distribution": {"Application": {"packageName": "a", "entryPoints": {}}},
        }
        result = run("ir", "inspect", write(tmp_path, "x.json", doc))
        assert "kind: Application" in result.stdout


class TestConvert:
    def test_upgrade_v3_to_v4(self, tmp_path: Path) -> None:
        out = tmp_path / "out.json"
        result = run(
            "ir",
            "convert",
            VALUE_TREE,
            "--to",
            "v4",
            "-o",
            out,
            "--package-version",
            "1.2.0",
        )
        assert result.exit_code == 0
        written = json.loads(out.read_text())
        assert written["formatVersion"] == 4
        assert "Library" in written["distribution"]

    def test_downgrade_round_trip(self, tmp_path: Path, v4_file: Path) -> None:
        out = tmp_path / "back.json"
        result = run("ir", "convert", v4_file, "--to", "v3", "-o", out)
        assert result.exit_code == 0
        assert json.loads(out.read_text()) == json.loads(VALUE_TREE.read_text())

    def test_same_version_rewrites_canonically(
        self, tmp_path: Path, v4_file: Path
    ) -> None:
        out = tmp_path / "same.json"
        assert run("ir", "convert", VALUE_TREE, "--to", "v3", "-o", out).exit_code == 0
        assert run("ir", "convert", v4_file, "--to", "v4", "-o", out).exit_code == 0

    def test_specs_upgrade_and_downgrade(self, tmp_path: Path) -> None:
        up = tmp_path / "up.json"
        result = run("ir", "convert", RUST_SPECS, "--to", "v4", "-o", up)
        assert result.exit_code == 0
        written = json.loads(up.read_text())
        assert written["formatVersion"] == 4
        assert "Specs" in written["distribution"]
        back = tmp_path / "back.json"
        result = run("ir", "convert", up, "--to", "v3", "-o", back)
        assert result.exit_code == 0
        assert result.stderr == ""
        assert json.loads(back.read_text()) == json.loads(RUST_SPECS.read_text())

    def test_v3_rewrite_emits_the_lowest_version(self, tmp_path: Path) -> None:
        doc = json.loads(VALUE_TREE.read_text())
        doc["formatVersion"] = "3.1.0"
        out = tmp_path / "out.json"
        source = write(tmp_path, "x.json", doc)
        assert run("ir", "convert", source, "--to", "v3", "-o", out).exit_code == 0
        assert json.loads(out.read_text())["formatVersion"] == 3
        assert run("ir", "convert", KIT_SPECS, "--to", "v3", "-o", out).exit_code == 0
        assert json.loads(out.read_text()) == json.loads(KIT_SPECS.read_text())

    def test_downgrade_failure_leaves_no_output(self, tmp_path: Path) -> None:
        doc = {
            "formatVersion": 4,
            "distribution": {"Application": {"packageName": "a", "entryPoints": {}}},
        }
        out = tmp_path / "out.json"
        result = run(
            "ir", "convert", write(tmp_path, "x.json", doc), "--to", "v3", "-o", out
        )
        assert result.exit_code == 1
        assert f"{d.UNSUPPORTED_V4_DOWNGRADE} at distribution" in result.stderr
        assert not out.exists()
        assert list(tmp_path.iterdir()) == [tmp_path / "x.json"]

    def test_encode_failure_leaves_no_output(self, tmp_path: Path) -> None:
        out = tmp_path / "out.json"
        result = run("ir", "convert", REFERENCE, "--to", "v4", "-o", out)
        assert result.exit_code == 1
        assert d.NO_V4_SPELLING in result.stderr
        assert "--drop-input-attributes" in result.stderr
        assert not out.exists()

    def test_drop_input_attributes_on_upgrade(self, tmp_path: Path) -> None:
        out = tmp_path / "out.json"
        result = run(
            "ir",
            "convert",
            REFERENCE,
            "--to",
            "v4",
            "-o",
            out,
            "--drop-input-attributes",
        )
        assert result.exit_code == 0, result.output
        assert result.stderr.count(d.INPUT_ATTRIBUTES_DROPPED) == 10
        assert json.loads(out.read_text())["formatVersion"] == 4

    def test_downgrade_warnings_exit_zero(self, tmp_path: Path) -> None:
        unit = {"Unit": {}}
        attrs = {
            "inferredType": unit,
            "source": {"startLine": 1, "startColumn": 1, "endLine": 1, "endColumn": 2},
        }
        value = {
            "Public": {
                "doc": "d",
                "value": {
                    "ExpressionBody": {
                        "inputTypes": {},
                        "outputType": unit,
                        "body": {"Unit": {"attributes": attrs}},
                    }
                },
            }
        }
        doc = {
            "formatVersion": 4,
            "distribution": {
                "Library": {
                    "packageName": "a",
                    "def": {
                        "modules": {
                            "m": {"Public": {"types": {}, "values": {"v": value}}}
                        }
                    },
                }
            },
        }
        src = write(tmp_path, "x.json", doc)
        out = tmp_path / "out.json"
        failed = run("ir", "convert", src, "--to", "v3", "-o", out)
        assert failed.exit_code == 1
        assert d.UNSUPPORTED_ATTRIBUTES_DOWNGRADE in failed.stderr
        result = run(
            "ir", "convert", src, "--to", "v3", "-o", out, "--drop-source-locations"
        )
        assert result.exit_code == 0
        assert f"warning: {d.SOURCE_LOCATION_DROPPED}" in result.stderr
        assert out.exists()

    def test_usage_error(self) -> None:
        assert run("ir", "convert", VALUE_TREE, "--to", "v9", "-o", "x").exit_code == 2


class TestLegacy:
    @pytest.mark.parametrize(("fixture", "label"), [(RENTALS_1, "1"), (RENTALS_2, "2")])
    def test_inspect(self, fixture: Path, label: str) -> None:
        result = run("ir", "inspect", fixture)
        assert result.exit_code == 0
        assert f"format: {label} (legacy)" in result.stdout
        assert "kind: Library" in result.stdout
        assert "package: morphir/example/app" in result.stdout
        assert "ir convert" in result.stdout

    def test_both_formats_upgrade_to_one_format_3_file(self, tmp_path: Path) -> None:
        out1, out2 = tmp_path / "from1.json", tmp_path / "from2.json"
        assert run("ir", "convert", RENTALS_1, "--to", "v3", "-o", out1).exit_code == 0
        assert run("ir", "convert", RENTALS_2, "--to", "v3", "-o", out2).exit_code == 0
        assert out1.read_text() == out2.read_text()
        assert json.loads(out1.read_text())["formatVersion"] == 3
        inspected = run("ir", "inspect", out1)
        assert "format: 3.0.0" in inspected.stdout

    @pytest.mark.parametrize("fixture", [RENTALS_1, RENTALS_2])
    def test_upgrade_to_v4(self, tmp_path: Path, fixture: Path) -> None:
        out = tmp_path / "v4.json"
        result = run("ir", "convert", fixture, "--to", "v4", "-o", out)
        assert result.exit_code == 0
        assert json.loads(out.read_text())["formatVersion"] == 4

    def test_broken_legacy_file_leaves_no_output(self, tmp_path: Path) -> None:
        doc = {"formatVersion": 1, "distribution": ["Library", [], [], {}]}
        out = tmp_path / "out.json"
        src = write(tmp_path, "x.json", doc)
        result = run("ir", "convert", src, "--to", "v3", "-o", out)
        assert result.exit_code == 1
        assert d.UNKNOWN_NODE in result.stderr
        assert not out.exists()
        assert run("ir", "inspect", src).exit_code == 1

    def test_string_legacy_version_is_invalid(self, tmp_path: Path) -> None:
        doc = {"formatVersion": "1", "distribution": []}
        result = run("ir", "inspect", write(tmp_path, "x.json", doc))
        assert result.exit_code == 1
        assert d.INVALID_FORMAT_VERSION_SYNTAX in result.stderr
