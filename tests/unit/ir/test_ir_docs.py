"""Runs the IR documentation examples: README code and module doctests."""

import doctest
import importlib
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
README = ROOT / "packages" / "morphir" / "README.md"

DOCTEST_MODULES = [
    "morphir.ir.format_version",
    "morphir.ir.migrate",
    "morphir.ir.v3.fqname",
    "morphir.ir.v3.name",
    "morphir.ir.v4.codec",
]


def test_readme_ir_example_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Python blocks of the IR section of the package README run."""
    section = README.read_text().split("## Morphir IR versions", 1)[1]
    section = section.split("\n## ", 1)[0]
    blocks = re.findall(r"```python\n(.*?)```", section, re.S)
    assert blocks
    monkeypatch.chdir(ROOT)
    for block in blocks:
        exec(compile(block, str(README), "exec"), {})


@pytest.mark.parametrize("module_name", DOCTEST_MODULES)
def test_docstring_examples(module_name: str) -> None:
    results = doctest.testmod(importlib.import_module(module_name))
    assert results.failed == 0


def test_readme_links_resolve() -> None:
    """The IR documentation links between READMEs and the change exist."""
    for readme in (
        README,
        ROOT / "README.md",
        ROOT / "packages/morphir-tools/README.md",
    ):
        for target in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", readme.read_text()):
            if not target.endswith(("README.md", "proposal.md")):
                continue
            assert (readme.parent / target).exists(), f"{readme.name}: {target}"
