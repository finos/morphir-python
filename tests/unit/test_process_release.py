"""A release must contain the same qualified candidate on every platform."""

from __future__ import annotations

import copy
import json
from typing import TYPE_CHECKING, Any

import pytest

from scripts import extension_bundle as bundle
from scripts import process_extension as process
from scripts import process_release as release
from scripts.qualify_native import tools_pin

if TYPE_CHECKING:
    from pathlib import Path

COMMIT = "a" * 40


def candidates(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    version = bundle.crate_version()
    claims = {
        "protocolVersions": bundle.declaration()["extension"]["mep_versions"],
        "extension": {"id": "morphir-python", "version": version},
        "capabilities": {},
    }
    results = {
        v: {
            "modules": ["acme/models.py", "acme/rules.py"],
            "agrees_with_python_api": True,
        }
        for v in ["v3", "v4"]
    }
    for target in process.PLATFORMS:
        platform_root = root / f"morphir-python-process-{target}"
        directory = platform_root / ".morphir/build/extensions/python-process"
        directory.mkdir(parents=True)
        name = process.artifact_name(version, target)
        executable = directory / name
        executable.write_bytes(target.encode())
        executable.chmod(0o700)
        digest = bundle.sha256(executable.read_bytes())
        (directory / f"{name}.sha256").write_text(f"{digest}  {name}\n")
        descriptor = {
            "schemaVersion": "2.0.0-draft.2",
            "shortId": "python",
            "extensionId": "morphir-python",
            "version": version,
            "gitCommit": COMMIT,
            "platformDifferences": "none",
            "artifacts": [
                {
                    "runtime": "process",
                    "platform": target,
                    "filename": name,
                    "sha256": digest,
                    "claims": claims,
                    "claimCheck": "unchecked",
                }
            ],
        }
        (directory / "release.json").write_text(json.dumps(descriptor))
        receipt = process.receipt(directory, COMMIT, target)
        archive_digest = bundle.declaration()["host"]["sha256"][target]
        receipt["bundler"] = {
            "version": bundle.declaration()["host"]["version"],
            "archiveSha256": archive_digest,
            "binarySha256": "b" * 64,
        }
        receipt["cargoLockSha256"] = bundle.sha256(
            (bundle.ROOT / "rust/Cargo.lock").read_bytes()
        )
        receipt["installedHost"] = {
            **copy.deepcopy(receipt),
            "host": {
                "morphir": bundle.declaration()["host"]["version"],
                "sha256": archive_digest,
                "binary_sha256": "b" * 64,
            },
            "python_api": {"native_version": tools_pin(), "compiler_version": version},
            "offline_round_trips": results,
            "qualification_script_sha256": bundle.sha256(
                (bundle.ROOT / "scripts/extension_bundle.py").read_bytes()
            ),
        }
        path = platform_root / f".dev/qualification/process-{target}.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(receipt))
        # Artifact transfer preserves bytes, but not POSIX execute bits.
        executable.chmod(0o600)
    return claims, results


def test_complete_process_set_keeps_canonical_per_platform_artifacts(
    tmp_path: Path,
) -> None:
    inputs, output = tmp_path / "inputs", tmp_path / "release"
    claims, results = candidates(inputs)
    report = release.assemble(inputs, output, COMMIT, claims, results)
    assert report["sourceCommit"] == COMMIT
    assert report["platforms"] == list(process.PLATFORMS)
    assert len(report["files"]) == 11
    descriptor = json.loads((output / "release.json").read_text())
    assert len(descriptor["artifacts"]) == 5
    assert {artifact["runtime"] for artifact in descriptor["artifacts"]} == {"process"}
    assert all(artifact["claims"] == claims for artifact in descriptor["artifacts"])


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "extra",
        "source",
        "lock",
        "files",
        "claims",
        "host",
        "api",
        "v4",
        "results",
        "bytes",
        "checker",
        "binary",
    ],
)
def test_mixed_missing_or_unqualified_process_sets_are_refused(
    tmp_path: Path, change: str
) -> None:
    inputs, output = tmp_path / "inputs", tmp_path / "release"
    claims, results = candidates(inputs)
    target = process.PLATFORMS[0]
    platform_root = inputs / f"morphir-python-process-{target}"
    receipt_path = platform_root / f".dev/qualification/process-{target}.json"
    receipt = json.loads(receipt_path.read_text())
    if change == "missing":
        receipt_path.unlink()
    elif change == "extra":
        (inputs / "morphir-python-process-unknown").mkdir()
    elif change == "source":
        receipt["sourceCommit"] = "c" * 40
    elif change == "lock":
        receipt["cargoLockSha256"] = "c" * 64
    elif change == "files":
        receipt["files"]["release.json"] = "c" * 64
    elif change == "claims":
        receipt["claims"]["capabilities"]["progress"] = True
    elif change == "host":
        receipt["bundler"]["archiveSha256"] = "c" * 64
    elif change == "checker":
        receipt["installedHost"]["qualification_script_sha256"] = "c" * 64
    elif change == "binary":
        receipt["installedHost"]["host"]["binary_sha256"] = "c" * 64
    elif change == "api":
        receipt["installedHost"]["python_api"]["native_version"] = "0.0.0"
    elif change == "v4":
        del receipt["installedHost"]["offline_round_trips"]["v4"]
    elif change == "results":
        receipt["installedHost"]["offline_round_trips"]["v4"]["modules"] = []
    elif change == "bytes":
        name = process.artifact_name(bundle.crate_version(), target)
        (platform_root / ".morphir/build/extensions/python-process" / name).write_bytes(
            b"changed executable"
        )
    if change != "missing":
        receipt_path.write_text(json.dumps(receipt))
    with pytest.raises((bundle.BundleError, OSError)):
        release.assemble(inputs, output, COMMIT, claims, results)
    assert not output.exists()


def test_process_assembly_does_not_overwrite_an_existing_directory(
    tmp_path: Path,
) -> None:
    inputs, output = tmp_path / "inputs", tmp_path / "release"
    claims, results = candidates(inputs)
    output.mkdir()
    (output / "keep").write_text("user data")
    with pytest.raises(FileExistsError):
        release.assemble(inputs, output, COMMIT, claims, results)
    assert (output / "keep").read_text() == "user data"
