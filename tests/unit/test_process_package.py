"""Process packages use the existing Morphir extension installation contract."""

from __future__ import annotations

import copy
import hashlib
import json
import zipfile
from typing import TYPE_CHECKING, Any

import pytest

from scripts import extension_bundle as bundle
from scripts import process_package as packages

if TYPE_CHECKING:
    from pathlib import Path


def claims() -> dict[str, Any]:
    return {
        "claimsVersion": "0.1.0-draft.2",
        "extension": {"id": "morphir-python", "version": bundle.crate_version()},
        "protocolVersions": ["0.2.0-draft.1"],
        "capabilities": {"frontend": {"compile": True}},
    }


@pytest.mark.parametrize(
    "platform,entry",
    [
        ("aarch64-pc-windows-msvc", "morphir-python-extension.exe"),
        ("x86_64-pc-windows-msvc", "morphir-python-extension.exe"),
        ("aarch64-apple-darwin", "morphir-python-extension"),
        ("x86_64-unknown-linux-gnu", "morphir-python-extension"),
    ],
)
def test_package_binds_archive_and_canonical_executable_tree(
    tmp_path: Path, platform: str, entry: str
) -> None:
    executable = tmp_path / "guest"
    executable.write_bytes(b"guest")
    original = claims()
    output = tmp_path / "package"
    packages.package(executable, output, platform, "a" * 40, original)
    descriptor_file = next(output.glob("*.release.json"))
    descriptor = json.loads(descriptor_file.read_text())
    assert descriptor["$schema"] == (
        "https://morphir.finos.org/schemas/extensions/"
        "0.1.0-preview.1/release.schema.json"
    )
    assert descriptor["critical"] == ["artifacts.package"]
    assert descriptor["gitCommit"] == "a" * 40
    (artifact,) = descriptor["artifacts"]
    assert artifact["platform"] == platform
    assert artifact["runtime"] == "process"
    assert artifact["claims"] == {
        key: value for key, value in original.items() if key != "claimsVersion"
    }
    assert original == claims()
    digest = hashlib.sha256(b"guest").hexdigest()
    expected_manifest = (
        f"morphir-package-tree 0.1.0-preview.1\nx 5 {digest} {entry}\n"
    ).encode("ascii")
    manifest = next(output.glob("*.manifest")).read_bytes()
    assert manifest == expected_manifest
    assert artifact["package"] == {
        "format": "zip",
        "entryPoint": entry,
        "executables": [entry],
        "treeSha256": hashlib.sha256(manifest).hexdigest(),
    }
    archive = output / artifact["filename"]
    assert artifact["sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.namelist() == [entry]
        assert zipped.read(entry) == b"guest"
    for line in (output / "SHA256SUMS").read_text().splitlines():
        expected, name = line.split("  ")
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == expected


@pytest.mark.parametrize(
    "change", ["id", "version", "commit", "platform", "legacy_protocol"]
)
def test_invalid_package_inputs_do_not_create_output(
    tmp_path: Path, change: str
) -> None:
    executable = tmp_path / "guest"
    executable.write_bytes(b"guest")
    observed = copy.deepcopy(claims())
    commit, platform = "a" * 40, "aarch64-pc-windows-msvc"
    if change in ("id", "version"):
        observed["extension"][change] = "wrong"
    elif change == "commit":
        commit = "main"
    elif change == "platform":
        platform = "unknown"
    else:
        observed["protocolVersions"].append("0.1")
    output = tmp_path / "package"
    with pytest.raises(bundle.BundleError):
        packages.package(executable, output, platform, commit, observed)
    assert not output.exists()


def test_historical_bundle_offers_do_not_define_the_current_process_protocol(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    historical = bundle.declaration()
    historical["extension"]["mep_versions"] = ["0.2.0-draft.1", "0.1"]
    monkeypatch.setattr(bundle, "declaration", lambda: historical)
    executable = tmp_path / "guest"
    executable.write_bytes(b"guest")
    packages.package(
        executable, tmp_path / "package", "aarch64-pc-windows-msvc", "a" * 40, claims()
    )
