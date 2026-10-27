"""The Python compiler guide's examples run against the public API."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

GUIDE = Path(__file__).resolve().parents[2] / "docs" / "python-compiler.md"


def python_blocks() -> list[str]:
    return re.findall(r"```python\n(.*?)```", GUIDE.read_text(), flags=re.DOTALL)


def test_the_guide_has_an_api_example() -> None:
    assert any("compile_sources" in block for block in python_blocks())


def test_api_examples_run_in_a_fresh_interpreter(tmp_path: Path) -> None:
    for block in python_blocks():
        completed = subprocess.run(
            [sys.executable, "-I", "-c", block],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        assert completed.stdout.split() == ["acme/models.py", "acme/rules.py"]
        assert list(tmp_path.iterdir()) == []


def test_api_examples_pass_both_type_checkers(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    for index, block in enumerate(python_blocks()):
        example = tmp_path / f"example_{index}.py"
        example.write_text(block)
        for command in (
            [
                sys.executable,
                "-m",
                "mypy",
                "--strict",
                "--no-incremental",
                str(example),
            ],
            [
                sys.executable,
                "-m",
                "pyright",
                "--pythonpath",
                sys.executable,
                str(example),
            ],
        ):
            completed = subprocess.run(
                command, capture_output=True, text=True, cwd=root, check=False
            )
            assert completed.returncode == 0, completed.stdout + completed.stderr
