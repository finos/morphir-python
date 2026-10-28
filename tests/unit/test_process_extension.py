"""Process release receipts bind canonical descriptors and exact executable bytes."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

import pytest

from scripts import extension_bundle as wasm
from scripts import process_extension as process

if TYPE_CHECKING:
    from pathlib import Path


def candidate(directory: Path) -> str:
    version = wasm.crate_version()
    name = process.artifact_name(version, "aarch64-apple-darwin")
    binary = directory / name
    binary.write_bytes(b"executable fixture")
    binary.chmod(0o700)
    digest = wasm.sha256(binary.read_bytes())
    (directory / f"{name}.sha256").write_text(f"{digest}  {name}\n")
    (directory / "release.json").write_text(
        json.dumps(
            {
                "schemaVersion": "2.0.0-draft.2",
                "extensionId": "morphir-python",
                "shortId": "python",
                "version": version,
                "gitCommit": "a" * 40,
                "platformDifferences": "none",
                "artifacts": [
                    {
                        "runtime": "process",
                        "platform": "aarch64-apple-darwin",
                        "filename": name,
                        "sha256": digest,
                        "claimCheck": "unchecked",
                        "claims": {
                            "protocolVersions": ["0.1"],
                            "extension": {"id": "morphir-python", "version": version},
                            "capabilities": {},
                        },
                    }
                ],
            }
        )
    )
    return name


def test_process_receipt_binds_source_bytes_launch_and_mode(tmp_path: Path) -> None:
    name = candidate(tmp_path)
    receipt = process.receipt(tmp_path, "a" * 40, "aarch64-apple-darwin")
    assert receipt["sourceCommit"] == "a" * 40
    assert receipt["arguments"] == []
    assert receipt["explicitArguments"] == ["--stdio"]
    assert receipt["runtime"] == "process"
    assert receipt["files"][name] == wasm.sha256((tmp_path / name).read_bytes())
    assert receipt["executable"] is True


@pytest.mark.parametrize(
    "change",
    [
        "bytes",
        "digest",
        "source",
        "platform",
        "runtime",
        "claims",
        "missing",
        "extra",
        "mode",
    ],
)
def test_process_receipt_refuses_mismatched_candidates(
    tmp_path: Path, change: str
) -> None:
    name = candidate(tmp_path)
    descriptor = json.loads((tmp_path / "release.json").read_text())
    if change == "bytes":
        (tmp_path / name).write_bytes(b"changed")
    elif change == "digest":
        (tmp_path / f"{name}.sha256").write_text("wrong")
    elif change == "source":
        descriptor["gitCommit"] = "b" * 40
    elif change == "platform":
        descriptor["artifacts"][0]["platform"] = "x86_64-pc-windows-msvc"
    elif change == "runtime":
        descriptor["artifacts"][0]["runtime"] = "wasm"
    elif change == "claims":
        descriptor["artifacts"][0]["claims"]["extension"]["version"] = "0.0.0"
    elif change == "missing":
        (tmp_path / name).unlink()
    elif change == "extra":
        (tmp_path / "unqualified").touch()
    elif change == "mode":
        if os.name == "nt":
            pytest.skip("POSIX executable mode")
        (tmp_path / name).chmod(0o600)
    (tmp_path / "release.json").write_text(json.dumps(descriptor))
    with pytest.raises(wasm.BundleError):
        process.receipt(tmp_path, "a" * 40, "aarch64-apple-darwin")


def test_process_platforms_are_explicit_and_windows_uses_exe() -> None:
    assert len(process.PLATFORMS) == 5
    assert process.artifact_name("0.4.2", "x86_64-pc-windows-msvc").endswith(".exe")
    with pytest.raises(wasm.BundleError, match="unsupported process platform"):
        process.artifact_name("0.4.2", "riscv64-unknown-linux-gnu")
