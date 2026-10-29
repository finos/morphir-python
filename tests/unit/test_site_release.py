"""Publication refuses output that differs from the checked artifact."""

import json
from typing import TYPE_CHECKING

import pytest

from scripts.site_release import producer, tree_hashes, verify

if TYPE_CHECKING:
    from pathlib import Path


def test_modified_page_blocks_promotion(tmp_path: Path) -> None:
    page = tmp_path / "index.html"
    page.write_text("<title>Checked</title>")
    manifest = {
        "state": "succeeded",
        "source": "abc",
        "eligible_for_deploy": True,
        "files": tree_hashes(tmp_path),
    }
    (tmp_path / "site-evidence.json").write_text(json.dumps(manifest))
    verify(tmp_path, "abc", deploy=True)
    page.write_text("<title>Unchecked replacement</title>")
    with pytest.raises(ValueError, match="artifact"):
        verify(tmp_path, "abc", deploy=True)


def test_preview_or_wrong_candidate_cannot_be_promoted(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<title>Preview</title>")
    manifest = {
        "state": "succeeded",
        "source": "abc",
        "eligible_for_deploy": False,
        "files": tree_hashes(tmp_path),
    }
    (tmp_path / "site-evidence.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="candidate"):
        verify(tmp_path, "other", deploy=False)
    with pytest.raises(ValueError, match="evidence"):
        verify(tmp_path, "abc", deploy=True)


@pytest.mark.parametrize(
    "changed",
    [
        {"event": "pull_request"},
        {"head_branch": "feature"},
        {"head_repository": {"full_name": "someone/fork"}},
        {"conclusion": "cancelled"},
        {"path": ".github/workflows/unrelated.yml"},
    ],
)
def test_only_a_successful_main_ci_producer_is_trusted(
    changed: dict[str, object],
) -> None:
    run = {
        "id": 123,
        "head_sha": "a" * 40,
        "event": "push",
        "head_branch": "main",
        "head_repository": {"full_name": "finos/morphir-python"},
        "conclusion": "success",
        "path": ".github/workflows/ci.yml",
    }
    assert producer(run, "finos/morphir-python") == ("a" * 40, 123)
    with pytest.raises(ValueError, match="producer"):
        producer(run | changed, "finos/morphir-python")
