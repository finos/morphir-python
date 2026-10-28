"""Require explicit multi-document claims in Python release bundles."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from scripts import extension_bundle as bundle

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("multi_document", [None, False, True])
def test_bundle_requires_multi_document_claim(
    tmp_path: Path, multi_document: bool | None
) -> None:
    version = bundle.crate_version()
    artifact = f"morphir-python-binding-{version}.wasm"
    wasm = b"qualification fixture"
    digest = bundle.sha256(wasm)
    (tmp_path / artifact).write_bytes(wasm)
    (tmp_path / f"{artifact}.sha256").write_text(f"{digest}  {artifact}\n")
    frontend: dict[str, object] = {"compile": True, "irVersions": ["3", "4"]}
    if multi_document is not None:
        frontend["multiDocument"] = multi_document
    (tmp_path / "release.json").write_text(
        json.dumps(
            {
                "extensionId": "morphir-python",
                "version": version,
                "artifacts": [
                    {
                        "sha256": digest,
                        "claims": {
                            "extension": {"id": "morphir-python", "version": version},
                            "capabilities": {
                                "frontend": frontend,
                                "backend": {"generate": True, "targets": ["python"]},
                            },
                        },
                    }
                ],
            }
        )
    )
    if multi_document is True:
        assert bundle.receipt(tmp_path)["multiDocument"] is True
    else:
        with pytest.raises(bundle.BundleError, match="claims lack"):
            bundle.receipt(tmp_path)
