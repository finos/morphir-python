"""Require explicit multi-document claims in Python release bundles."""

from __future__ import annotations

import io
import json
import zipfile
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


def test_windows_cli_archive_is_verified_and_only_the_binary_is_extracted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bundle.platform, "system", lambda: "Windows")
    monkeypatch.setattr(bundle.platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(bundle, "CACHE", tmp_path)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("release/morphir.exe", b"verified CLI")
        archive.writestr("../../unwanted", b"do not extract")
    archive_bytes = stream.getvalue()
    digest = bundle.sha256(archive_bytes)
    monkeypatch.setattr(
        bundle,
        "declaration",
        lambda: {
            "host": {
                "version": "test",
                "release": "https://example.invalid/releases",
                "sha256": {"x86_64-pc-windows-msvc": digest},
            }
        },
    )
    urls: list[str] = []

    def download(url: str, *, timeout: int) -> io.BytesIO:
        assert timeout > 0
        urls.append(url)
        return io.BytesIO(archive_bytes)

    monkeypatch.setattr(bundle.urllib.request, "urlopen", download)
    executable, actual_digest = bundle.morphir_cli()
    assert actual_digest == digest
    assert executable.name == "morphir.exe"
    assert executable.read_bytes() == b"verified CLI"
    assert urls == [
        "https://example.invalid/releases/morphir-test-x86_64-pc-windows-msvc.zip"
    ]
    assert sorted(
        p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file()
    ) == [
        "morphir-test-x86_64-pc-windows-msvc/morphir-test-x86_64-pc-windows-msvc.zip",
        "morphir-test-x86_64-pc-windows-msvc/morphir.exe",
    ]

    executable.write_bytes(b"changed cached CLI")
    with pytest.raises(bundle.BundleError, match="cached Morphir CLI"):
        bundle.morphir_cli()
    assert len(urls) == 1

    executable.write_bytes(b"verified CLI")
    (executable.parent / "morphir-test-x86_64-pc-windows-msvc.zip").write_bytes(
        b"changed archive"
    )
    with pytest.raises(bundle.BundleError, match="digest differs"):
        bundle.morphir_cli()
    assert len(urls) == 1


def test_integrity_refusal_requires_the_mismatch_and_both_actual_hashes() -> None:
    expected, observed = "a" * 64, "b" * 64
    assert bundle.is_digest_mismatch(
        f"digest mismatch: expected {expected[:32]}\n│ {expected[32:]}, got {observed}",
        expected,
        observed,
    )
    assert not bundle.is_digest_mismatch(
        "cannot read morphir-integrity/sha256/log", expected, observed
    )
    assert not bundle.is_digest_mismatch(
        f"digest mismatch: expected {expected}", expected, observed
    )
    assert not bundle.is_digest_mismatch(
        f"invalid module at sha256/{expected}", expected, observed
    )
