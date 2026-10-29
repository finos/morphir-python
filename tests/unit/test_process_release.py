"""A release must contain the same qualified candidate on every platform."""

from __future__ import annotations

import copy
import json
import tarfile
from typing import TYPE_CHECKING, Any

import pytest

from scripts import extension_bundle as bundle
from scripts import process_diagnostics
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
        receipt["processDiagnostics"] = {
            "scope": "legacy-process-diagnostic-parity",
            "artifactSha256": digest,
            "checkerSha256": bundle.sha256(
                (bundle.ROOT / "scripts/process_diagnostics.py").read_bytes()
            ),
            "inputSha256": bundle.sha256(process_diagnostics.SOURCE.encode()),
            "compilerVersion": version,
            "nativeVersion": tools_pin(),
            "protocolVersion": "0.1",
            "cleanEnvironment": True,
            "exitCode": 0,
            "stderr": "",
            "cases": {
                version: {
                    "diagnostics": [{"code": "PY004", "severity": "error"}],
                    "pythonApi": [{"code": "PY004", "severity": "error"}],
                }
                for version in ("3", "4")
            },
        }
        receipt["installedHost"] = {
            **copy.deepcopy(receipt),
            "host": {
                "morphir": bundle.declaration()["host"]["version"],
                "sha256": archive_digest,
                "binary_sha256": "b" * 64,
            },
            "python_api": {"native_version": tools_pin(), "compiler_version": version},
            "offline_round_trips": results,
            "installed_integrity": {
                "expected_sha256": digest,
                "tampered_sha256": "e" * 64,
                "exit_code": 1,
                "stdout": "",
                "stderr": f"digest mismatch: expected {digest}, got {'e' * 64}",
                "fresh_project": True,
            },
            "qualification_script_sha256": bundle.sha256(
                (bundle.ROOT / "scripts/extension_bundle.py").read_bytes()
            ),
        }
        path = platform_root / f".dev/qualification/process-{target}.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(receipt))
        if target.endswith("windows-msvc"):
            (path.parent / "windows-process-imports.json").write_text(
                json.dumps(
                    {
                        "sourceCommit": COMMIT,
                        "crt": "static",
                        "artifact": {"sha256": digest},
                        "checkerSha256": bundle.sha256(
                            (
                                bundle.ROOT
                                / ".github/scripts/check_process_windows.ps1"
                            ).read_bytes()
                        ),
                        "tool": {
                            "name": "dumpbin.exe",
                            "sha256": "d" * 64,
                            "version": "test",
                        },
                        "dependencies": ["kernel32.dll", "ntdll.dll"],
                    }
                )
            )
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


def archive_candidate(tmp_path: Path) -> tuple[Path, Path, Path]:
    inputs, directory = tmp_path / "inputs", tmp_path / "canonical"
    claims, results = candidates(inputs)
    report = release.assemble(inputs, directory, COMMIT, claims, results)
    wasm = tmp_path / "wasm"
    wasm.mkdir()
    version = bundle.crate_version()
    name = f"morphir-python-binding-{version}.wasm"
    digest = bundle.sha256(b"WASM fixture")
    (wasm / name).write_bytes(b"WASM fixture")
    (wasm / f"{name}.sha256").write_text(f"{digest}  {name}\n")
    (wasm / "release.json").write_text(
        json.dumps(
            {
                "extensionId": "morphir-python",
                "version": version,
                "gitCommit": COMMIT,
                "artifacts": [
                    {
                        "runtime": "wasm",
                        "filename": name,
                        "sha256": digest,
                        "claims": claims,
                    }
                ],
            }
        )
    )
    assembled = tmp_path / "assembly.json"
    assembled.write_text(json.dumps(report))
    return directory, assembled, wasm


def test_download_archive_keeps_exact_bytes_modes_and_canonical_descriptor(
    tmp_path: Path,
) -> None:
    directory, assembled, wasm = archive_candidate(tmp_path)
    version = bundle.crate_version()
    report = json.loads(assembled.read_text())
    first = release.archive_bundle(
        directory, assembled, wasm, tmp_path / "assets", COMMIT
    )
    second = release.archive_bundle(
        directory, assembled, wasm, tmp_path / "again", COMMIT
    )
    assert first == second
    assert first["sourceCommit"] == COMMIT
    assert len(list((tmp_path / "assets").iterdir())) == 14
    with tarfile.open(
        tmp_path / "assets" / f"morphir-python-extension-{version}.tar.gz"
    ) as archive:
        assert set(archive.getnames()) == set(report["files"])
        for member in archive.getmembers():
            stream = archive.extractfile(member)
            assert stream is not None
            assert bundle.sha256(stream.read()) == report["files"][member.name]
            assert member.isfile()
            assert member.uid == member.gid == member.mtime == 0
            assert member.mode == (
                0o644 if member.name.endswith((".json", ".sha256")) else 0o700
            )
    lines = (tmp_path / "assets/SHA256SUMS").read_text().splitlines()
    assert len(lines) == 13
    for line in lines:
        checksum, filename = line.split("  ")
        assert checksum == bundle.sha256((tmp_path / "assets" / filename).read_bytes())


@pytest.mark.parametrize(
    "change",
    ["bytes", "receipt", "source", "claims", "platform", "extra", "symlink", "copy"],
)
def test_archive_refuses_changed_inputs_or_transfers_without_partial_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    directory, assembled, wasm = archive_candidate(tmp_path)
    executable = directory / process.artifact_name(
        bundle.crate_version(), process.PLATFORMS[0]
    )
    report = json.loads(assembled.read_text())
    descriptor = json.loads((directory / "release.json").read_text())
    if change == "bytes":
        executable.write_bytes(b"changed bytes")
    elif change == "receipt":
        report["files"][executable.name] = "c" * 64
    elif change == "source":
        report["sourceCommit"] = "c" * 40
    elif change in ("claims", "platform"):
        if change == "claims":
            descriptor["artifacts"][0]["claims"]["capabilities"]["streaming"] = True
        else:
            descriptor["artifacts"][0]["platform"] = descriptor["artifacts"][1][
                "platform"
            ]
        (directory / "release.json").write_text(json.dumps(descriptor))
        report["files"]["release.json"] = bundle.sha256(
            (directory / "release.json").read_bytes()
        )
    elif change == "extra":
        (directory / "unqualified").write_bytes(b"extra")
    elif change == "symlink":
        target = tmp_path / "outside"
        executable.rename(target)
        executable.symlink_to(target)
    elif change == "copy":
        original = release.shutil.copyfile

        def changed_copy(source: Path, destination: Path) -> None:
            original(source, destination)
            destination.write_bytes(b"changed transfer")

        monkeypatch.setattr(release.shutil, "copyfile", changed_copy)
    assembled.write_text(json.dumps(report))
    with pytest.raises((bundle.BundleError, OSError)):
        release.archive_bundle(directory, assembled, wasm, tmp_path / "assets", COMMIT)
    assert not (tmp_path / "assets").exists()


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
        "windows-runtime",
        "windows-bytes",
        "windows-checker",
        "windows-missing",
        "integrity-digest",
        "integrity-not-run",
        "integrity-cache",
        "integrity-reason",
        "diagnostics-missing",
        "diagnostics-code",
        "diagnostics-api",
        "diagnostics-checker",
        "diagnostics-artifact",
        "diagnostics-version",
        "diagnostics-environment",
        "diagnostics-v4",
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
    if change == "diagnostics-missing":
        receipt.pop("processDiagnostics", None)
    elif change.startswith("diagnostics-"):
        proof = receipt["processDiagnostics"]
        if change == "diagnostics-code":
            proof["cases"]["3"]["diagnostics"][0]["code"] = "PY001"
            proof["cases"]["3"]["pythonApi"][0]["code"] = "PY001"
        elif change == "diagnostics-api":
            proof["cases"]["3"]["pythonApi"][0]["code"] = "PY001"
        elif change == "diagnostics-checker":
            proof["checkerSha256"] = "c" * 64
        elif change == "diagnostics-artifact":
            proof["artifactSha256"] = "c" * 64
        elif change == "diagnostics-version":
            proof["compilerVersion"] = "0.0.0"
        elif change == "diagnostics-environment":
            proof["cleanEnvironment"] = False
        elif change == "diagnostics-v4":
            del proof["cases"]["4"]
    elif change.startswith("integrity-"):
        proof = receipt["installedHost"]["installed_integrity"]
        if change == "integrity-digest":
            proof["expected_sha256"] = "c" * 64
        elif change == "integrity-not-run":
            proof["exit_code"] = 0
        elif change == "integrity-cache":
            proof["fresh_project"] = False
        elif change == "integrity-reason":
            proof["stderr"] = "unrelated permission error"
    elif change.startswith("windows-"):
        windows = (
            inputs
            / "morphir-python-process-x86_64-pc-windows-msvc/.dev/qualification/windows-process-imports.json"
        )
        proof = json.loads(windows.read_text())
        if change == "windows-missing":
            windows.unlink()
        else:
            if change == "windows-runtime":
                proof["dependencies"].append("VCRUNTIME140.dll")
            elif change == "windows-bytes":
                proof["artifact"]["sha256"] = "c" * 64
            elif change == "windows-checker":
                proof["checkerSha256"] = "c" * 64
            windows.write_text(json.dumps(proof))
    elif change == "missing":
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
