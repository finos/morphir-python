"""Stage process extensions with the pinned Morphir CLI's canonical bundler.

Receipts live outside the canonical three-file bundle. They bind its source,
platform, launch convention, executable mode and exact bytes. Publication and
installed-host qualification are separate steps.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from scripts import extension_bundle as bundle

PLATFORMS = (
    "x86_64-unknown-linux-gnu",
    "aarch64-unknown-linux-gnu",
    "aarch64-apple-darwin",
    "x86_64-apple-darwin",
    "x86_64-pc-windows-msvc",
)


def artifact_name(version: str, platform: str) -> str:
    """Return the raw executable name for an explicitly supported platform."""
    if platform not in PLATFORMS:
        raise bundle.BundleError(f"unsupported process platform {platform}")
    suffix = ".exe" if platform.endswith("windows-msvc") else ""
    return f"morphir-python-extension-{version}-{platform}{suffix}"


def receipt(directory: Path, commit: str, platform: str) -> dict[str, Any]:
    """Refuse a candidate whose descriptor, bytes, identity or mode disagree."""
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise bundle.BundleError("source commit must be a full lowercase Git SHA")
    version = bundle.crate_version()
    name = artifact_name(version, platform)
    expected = {name, f"{name}.sha256", "release.json"}
    if {p.name for p in directory.iterdir()} != expected:
        raise bundle.BundleError("process bundle has missing or extra files")
    if any(p.is_symlink() or not p.is_file() for p in directory.iterdir()):
        raise bundle.BundleError("process bundle files must be regular files")
    try:
        descriptor = json.loads((directory / "release.json").read_text())
        (artifact,) = descriptor["artifacts"]
        claims = artifact["claims"]
        digest = bundle.sha256((directory / name).read_bytes())
        if not (
            descriptor["schemaVersion"] == "2.0.0-draft.2"
            and descriptor["extensionId"] == "morphir-python"
            and descriptor["shortId"] == "python"
            and descriptor["version"] == version
            and descriptor["gitCommit"] == commit
            and artifact["runtime"] == "process"
            and artifact["platform"] == platform
            and artifact["filename"] == name
            and artifact["sha256"] == digest
            and claims["extension"]["id"] == descriptor["extensionId"]
            and claims["extension"]["version"] == version
            and claims["protocolVersions"]
            == bundle.declaration()["extension"]["mep_versions"]
        ):
            raise bundle.BundleError("process descriptor disagrees with candidate")
        if (directory / f"{name}.sha256").read_text() != f"{digest}  {name}\n":
            raise bundle.BundleError("process checksum disagrees with executable")
    except (KeyError, ValueError, TypeError) as error:
        raise bundle.BundleError(f"invalid process descriptor: {error}") from error
    mode = stat.S_IMODE((directory / name).stat().st_mode)
    if os.name != "nt" and mode & stat.S_IXUSR == 0:
        raise bundle.BundleError("process artifact lacks owner executable mode")
    return {
        "schemaVersion": 1,
        "sourceCommit": commit,
        "runtime": "process",
        "platform": platform,
        "version": version,
        "arguments": [],
        "explicitArguments": ["--stdio"],
        "executable": True,
        "mode": oct(mode),
        "files": {
            name: bundle.sha256((directory / name).read_bytes())
            for name in sorted(expected)
        },
        "claims": claims,
    }


def package(executable: Path, output: Path, commit: str) -> dict[str, Any]:
    """Run the pinned native bundler on a uniquely named copy of exact bytes."""
    platform = bundle._target()
    name = artifact_name(bundle.crate_version(), platform)
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise bundle.BundleError("source commit must be a full lowercase Git SHA")
    if output.exists() or output.is_symlink():
        raise bundle.BundleError(f"bundle directory {output} already exists")
    if executable.is_symlink() or not executable.is_file():
        raise bundle.BundleError("process executable must be a regular file")
    cli, archive_digest = bundle.morphir_cli()
    with tempfile.TemporaryDirectory(prefix="python-process-bundle-") as temporary:
        copied = Path(temporary) / name
        shutil.copyfile(executable, copied)
        copied.chmod(0o700)
        subprocess.run(
            [
                str(cli.resolve()),
                "--no-banner",
                "extension",
                "bundle",
                "--executable",
                str(copied),
                "--extension-id",
                "morphir-python",
                "--short-id",
                "python",
                "--version",
                bundle.crate_version(),
                "--platform",
                platform,
                "--output",
                str(output.resolve()),
            ],
            check=True,
        )
    # gitCommit is a canonical optional descriptor member. All runtime fields
    # and claims come from the upstream writer and its live describe probe.
    descriptor_path = output / "release.json"
    descriptor = json.loads(descriptor_path.read_text())
    descriptor["gitCommit"] = commit
    descriptor_path.write_text(json.dumps(descriptor, indent=2) + "\n")
    result = receipt(output, commit, platform)
    result["bundler"] = {
        "version": bundle.declaration()["host"]["version"],
        "archiveSha256": archive_digest,
        "binarySha256": bundle.sha256(cli.read_bytes()),
    }
    result["cargoLockSha256"] = bundle.sha256(
        (bundle.ROOT / "rust/Cargo.lock").read_bytes()
    )
    return result


def main(argv: list[str] | None = None) -> int:
    """Write a source-bound process receipt outside the canonical bundle."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--host-check",
        action="store_true",
        help="install offline and compare v3/v4 with the matching Python API",
    )
    args = parser.parse_args(argv)
    if args.report.resolve().is_relative_to(args.output.resolve()):
        parser.error("the report must be outside the canonical bundle")
    try:
        result = package(args.executable, args.output, args.commit)
        if args.host_check:
            result["installedHost"] = bundle.host_round_trips(args.output, result)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2) + "\n")
    except (bundle.BundleError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"process bundle refused: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
