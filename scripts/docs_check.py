"""Qualify released and candidate documentation examples in isolated wheel installs."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    """Execute a required qualification step and preserve its exit status."""
    subprocess.run(command, cwd=ROOT, check=True)


def examples(python: Path, group: str = "all") -> dict[str, Any]:
    """Capture an installed example result from its own interpreter."""
    output = subprocess.check_output(
        [str(python), str(ROOT / "scripts/docs_examples.py"), "test", "--group", group],
        cwd=ROOT,
        text=True,
    )
    return dict(json.loads(output))


def main() -> None:
    """Build pure wheels once and qualify both released and development examples."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-wheel-dir", type=Path)
    parser.add_argument("--report", type=Path, default=ROOT / ".dev/docs-examples.json")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "examples/manifest.json").read_text())
    released = manifest["released"]
    output = ROOT / ".dev/docs-wheels"
    output.mkdir(parents=True, exist_ok=True)
    # The only compiled wheel can be supplied by the existing CI producer.
    for package in ("morphir", "morphir-tools"):
        run(
            [
                "uv",
                "build",
                str(ROOT / "packages" / package),
                "--wheel",
                "--out-dir",
                str(output),
            ]
        )
    with tempfile.TemporaryDirectory(prefix="morphir-docs-wheels-") as scratch:
        base = Path(scratch)

        def environment(name: str, requirements: list[str]) -> Path:
            directory = base / name
            run(["uv", "venv", "--python", sys.executable, str(directory)])
            python = directory / (
                "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
            )
            run(
                [
                    "uv",
                    "pip",
                    "install",
                    "--python",
                    str(python),
                    "--only-binary=:all:",
                    *requirements,
                ]
            )
            return python

        released_python = environment(
            "released", [f"{p}=={v}" for p, v in released.items()]
        )
        released_report = examples(released_python)
        library_python = environment("library", [f"morphir=={released['morphir']}"])
        library_report = examples(library_python, "library")
        run(
            [
                str(library_python),
                "-I",
                "-c",
                "import importlib.util; "
                "assert importlib.util.find_spec('morphir_python_native') is None",
            ]
        )
        candidate_wheels = []
        for package in ("morphir", "morphir-tools"):
            import tomllib

            project = tomllib.loads(
                (ROOT / "packages" / package / "pyproject.toml").read_text()
            )["project"]
            wheel_name = (
                project["name"].replace("-", "_")
                + "-"
                + project["version"]
                + "-py3-none-any.whl"
            )
            candidate_wheels.append(str(output / wheel_name))
        native = []
        if args.native_wheel_dir:
            native = [str(p.absolute()) for p in args.native_wheel_dir.glob("*.whl")]
            if len(native) != 1:
                parser.error("Expected exactly one qualified native wheel")
        candidate_python = environment("candidate", candidate_wheels + native)
        candidate_report = examples(candidate_python)
        run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(candidate_python),
                "pytest==9.0.2",
                "mypy==1.19.1",
                "pyright==1.1.408",
            ]
        )
        run([str(candidate_python), str(ROOT / "scripts/docs_examples.py"), "check"])
        run(
            [
                str(candidate_python),
                "-m",
                "pytest",
                "tests/tools/test_python_docs.py",
                "tests/unit/test_docs_examples.py",
                "tests/unit/test_docs_hosts.py",
            ]
        )
        report = {
            "state": "succeeded",
            "source": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "released": released_report,
            "candidate": candidate_report,
            "library": library_report,
            "wheels": {
                Path(p).name: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                for p in candidate_wheels + native
            },
        }
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
        print(args.report)


if __name__ == "__main__":
    main()
