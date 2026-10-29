"""Release tags and exact candidate sets for native and extension releases."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import textwrap
from typing import TYPE_CHECKING

import pytest

from scripts import release_candidates as r

if TYPE_CHECKING:
    from pathlib import Path

VERSIONS = {
    "morphir": "0.0.1",
    "python": "0.0.2",
    "native": "0.1.0",
    "extension": "0.4.0",
}


@pytest.mark.parametrize(
    ("tag", "kind"),
    [
        ("morphir-v0.0.1", "morphir"),
        ("python-v0.0.2", "python"),
        ("native-v0.1.0", "native"),
        ("extension/python/v0.4.0", "extension"),
    ],
)
def test_tags_name_their_release(tag: str, kind: str) -> None:
    assert r.classify(tag, VERSIONS).kind == kind


@pytest.mark.parametrize(
    "tag",
    ["native-v0.2.0", "extension/python/v0.3.0", "v0.1.0", "extension/rust/v1.0.0"],
)
def test_mismatched_or_unknown_tags_are_refused(tag: str) -> None:
    with pytest.raises(r.CandidateError):
        r.classify(tag, VERSIONS)


def test_the_source_versions_are_readable() -> None:
    assert set(r.source_versions()) == set(VERSIONS)


def native_set(directory: Path, version: str = "0.1.0") -> None:
    stem = f"morphir_python_native-{version}"
    for tag in r.NATIVE_PLATFORMS:
        (directory / f"{stem}-cp314-abi3-{tag}.whl").write_bytes(tag.encode())
    (directory / f"{stem}.tar.gz").write_bytes(b"sdist")


def test_complete_native_candidates_are_accepted(tmp_path: Path) -> None:
    native_set(tmp_path)
    assert len(r.native_candidates(tmp_path, "0.1.0")) == 6


@pytest.mark.parametrize("change", ["missing", "extra", "version"])
def test_incomplete_native_candidates_are_refused(tmp_path: Path, change: str) -> None:
    native_set(tmp_path)
    if change == "missing":
        next(tmp_path.glob("*win_amd64.whl")).unlink()
    elif change == "extra":
        (tmp_path / "morphir_python_native-0.1.0-cp314-cp314-linux_x86_64.whl").touch()
    else:
        next(tmp_path.glob("*.tar.gz")).rename(
            tmp_path / "morphir_python_native-0.0.9.tar.gz"
        )
    with pytest.raises(r.CandidateError):
        r.native_candidates(tmp_path, "0.1.0")


def bundle(directory: Path, *, commit: str = "a" * 40, version: str = "0.4.0") -> None:
    artifact = f"morphir-python-binding-{version}.wasm"
    wasm = b"\0asm"
    digest = hashlib.sha256(wasm).hexdigest()
    (directory / artifact).write_bytes(wasm)
    (directory / f"{artifact}.sha256").write_text(f"{digest}  {artifact}\n")
    (directory / "release.json").write_text(
        json.dumps(
            {"version": version, "gitCommit": commit, "artifacts": [{"sha256": digest}]}
        )
    )


def test_a_bundle_from_the_tagged_commit_is_accepted(tmp_path: Path) -> None:
    bundle(tmp_path)
    assert len(r.bundle_candidates(tmp_path, "0.4.0", "a" * 40)) == 3


@pytest.mark.parametrize("options", [{"commit": "b" * 40}, {"version": "0.3.0"}])
def test_mismatched_bundles_are_refused(
    tmp_path: Path, options: dict[str, str]
) -> None:
    bundle(tmp_path, **options)
    with pytest.raises((r.CandidateError, KeyError, OSError)):
        r.bundle_candidates(tmp_path, "0.4.0", "a" * 40)


def test_a_bundle_without_provenance_is_refused(tmp_path: Path) -> None:
    bundle(tmp_path)
    descriptor = json.loads((tmp_path / "release.json").read_text())
    del descriptor["gitCommit"]
    (tmp_path / "release.json").write_text(json.dumps(descriptor))
    with pytest.raises(r.CandidateError, match="built from None"):
        r.bundle_candidates(tmp_path, "0.4.0", "a" * 40)


def test_a_bundle_with_a_wrong_checksum_is_refused(tmp_path: Path) -> None:
    bundle(tmp_path)
    artifact = "morphir-python-binding-0.4.0.wasm"
    (tmp_path / f"{artifact}.sha256").write_text(f"{'0' * 64}  {artifact}\n")
    with pytest.raises(r.CandidateError, match="checksum"):
        r.bundle_candidates(tmp_path, "0.4.0", "a" * 40)


def test_the_command_writes_a_receipt(tmp_path: Path) -> None:
    native_set(tmp_path)
    version = r.source_versions()["native"]
    if version != "0.1.0":
        pytest.skip("fixture names the current native version")
    r.main(["native", str(tmp_path), "--tag", f"native-v{version}"])
    assert len((tmp_path / "SHA256SUMS").read_text().splitlines()) == 6


@pytest.mark.skipif(
    os.name == "nt" or shutil.which("bash") is None,
    reason="The native-candidates workflow shell runs on Ubuntu",
)
@pytest.mark.parametrize(
    ("tag", "accepted"),
    [
        (None, True),
        ("native-v{native}", True),
        ("extension/python/v{extension}", True),
        ("native-v9.9.9", False),
    ],
)
def test_workflow_verifies_native_candidates_for_each_tag_route(
    tmp_path: Path, tag: str | None, accepted: bool
) -> None:
    """Execute the production shell and its strict validator with real ref inputs."""
    versions = r.source_versions()
    native_set(tmp_path, versions["native"])
    workflow = (r.ROOT / ".github/workflows/release.yml").read_text()
    step = workflow.split(
        "      - name: Refuse missing, extra or mismatched candidates\n", 1
    )[1]
    script = textwrap.dedent(
        step.split("        run: |\n", 1)[1].split("\n      - name:", 1)[0]
    )
    ref_name = tag.format(**versions) if tag else "main"
    # GitHub expands this expression before handing a step to Bash.
    script = script.replace(
        "${{ github.ref_type == 'tag' && github.ref_name || '' }}",
        ref_name if tag else "",
    ).replace("dist/candidates", shlex.quote(str(tmp_path)))
    result = subprocess.run(
        ["bash", "-e", "-c", script],
        cwd=r.ROOT,
        env=os.environ
        | {
            "GITHUB_REF": f"refs/tags/{ref_name}" if tag else "refs/heads/main",
            "GITHUB_REF_NAME": ref_name,
            "GITHUB_REF_TYPE": "tag" if tag else "branch",
        },
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert (result.returncode == 0) == accepted, result.stderr
    receipt = tmp_path / "SHA256SUMS"
    if accepted:
        assert len(receipt.read_text().splitlines()) == 6
    else:
        assert not receipt.exists()
