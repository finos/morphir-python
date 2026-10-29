"""Published snippets must agree with the examples users actually execute."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from scripts.docs_examples import synchronize


def test_snippet_drift_fails_check_without_overwriting_the_edit(tmp_path: Path) -> None:
    (tmp_path / "examples").mkdir()
    (tmp_path / "examples/demo.py").write_text('print("checked")\n')
    (tmp_path / "docs").mkdir()
    guide = tmp_path / "docs/guide.md"
    original = (
        "<!-- example: examples/demo.py -->\n```python\nwrong\n```\n<!-- /example -->\n"
    )
    guide.write_text(original)
    assert synchronize(tmp_path, write=False) == ["docs/guide.md"]
    assert guide.read_text() == original
    assert synchronize(tmp_path, write=True) == ["docs/guide.md"]
    assert 'print("checked")' in guide.read_text()
    assert synchronize(tmp_path, write=False) == []
