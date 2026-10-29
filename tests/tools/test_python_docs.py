"""Published learning examples run against installed APIs and stay type checked."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from scripts.docs_examples import MARKER, ROOT, run_examples, synchronize


def test_published_snippets_and_references_match_their_sources() -> None:
    assert synchronize() == []
    for page in (ROOT / "docs").glob("*.md"):
        outside_markers = MARKER.sub("", page.read_text())
        assert not re.search(r"```python\n", outside_markers), page


def test_named_examples_and_cli_recipe_run_outside_the_checkout() -> None:
    result = run_examples(Path(sys.executable))
    assert result["state"] == "succeeded"
    assert "examples/cli.sh" in result["examples"]


def test_api_examples_pass_both_type_checkers(tmp_path: Path) -> None:
    manifest = json.loads((ROOT / "examples/manifest.json").read_text())
    for index, item in enumerate(manifest["examples"]):
        example = tmp_path / f"example_{index}.py"
        example.write_text((ROOT / item["source"]).read_text())
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
                command, capture_output=True, text=True, cwd=ROOT
            )
            assert completed.returncode == 0, completed.stdout + completed.stderr
