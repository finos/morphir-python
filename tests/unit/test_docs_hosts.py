"""Compatibility receipts cannot silently survive changed recipes."""

import json
from typing import TYPE_CHECKING

import pytest

from scripts.docs_hosts import INPUTS, input_hashes, verify_evidence

if TYPE_CHECKING:
    from pathlib import Path


def test_edited_recipe_invalidates_previously_successful_evidence(
    tmp_path: Path,
) -> None:
    for name in INPUTS:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("original")
    report = {
        "state": "succeeded",
        "inputs": input_hashes(tmp_path),
        "rust_recipe": {"recipe": "examples/extension.sh", "exit_code": 0},
        "moonbit_refusals": {
            v: {"error": "extension.unsupported_model_envelope"} for v in ("3", "4")
        },
    }
    verify_evidence(json.loads(json.dumps(report)), tmp_path)
    (tmp_path / "examples/extension.sh").write_text("changed command")
    with pytest.raises(ValueError, match="stale"):
        verify_evidence(report, tmp_path)


def test_missing_successful_host_result_is_not_reusable(tmp_path: Path) -> None:
    for name in INPUTS:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("original")
    with pytest.raises(ValueError, match="lacks"):
        verify_evidence(
            {"state": "succeeded", "inputs": input_hashes(tmp_path)}, tmp_path
        )


def test_released_receipt_can_qualify_a_version_other_than_the_current_crate(
    tmp_path: Path,
) -> None:
    from scripts import extension_bundle

    version = "1.2.3"
    artifact = f"morphir-python-binding-{version}.wasm"
    digest = extension_bundle.sha256(b"fixture")
    (tmp_path / artifact).write_bytes(b"fixture")
    (tmp_path / f"{artifact}.sha256").write_text(f"{digest}  {artifact}\n")
    descriptor = {
        "extensionId": "morphir-python",
        "version": version,
        "artifacts": [
            {
                "sha256": digest,
                "claims": {
                    "extension": {"id": "morphir-python", "version": version},
                    "capabilities": {
                        "frontend": {
                            "compile": True,
                            "multiDocument": True,
                            "irVersions": ["3", "4"],
                        },
                        "backend": {"generate": True, "targets": ["python"]},
                    },
                },
            }
        ],
    }
    (tmp_path / "release.json").write_text(json.dumps(descriptor))
    assert extension_bundle.receipt(tmp_path, version=version)["version"] == version
