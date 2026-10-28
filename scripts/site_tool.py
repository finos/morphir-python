"""Install the pinned Telescope release and run its stock consumer commands."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINS = ROOT / "site/toolchain.json"


class SiteError(Exception):
    """A site tool prerequisite or release verification failed."""


def digest(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def install_archive(
    archive: Path, destination: Path, expected: str, version: str
) -> Path:
    """Install a verified native release without trusting its archive paths."""
    if digest(archive) != expected:
        raise SiteError(f"SHA-256 mismatch for {archive.name}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as scratch:
        staged = Path(scratch) / "install"
        staged.mkdir()
        with tarfile.open(archive) as release:
            binaries = [
                m for m in release.getmembers() if Path(m.name).name == "telescope"
            ]
            if len(binaries) != 1 or not binaries[0].isfile():
                raise SiteError("Release must contain one regular telescope executable")
            stream = release.extractfile(binaries[0])
            if stream is None:
                raise SiteError("Cannot read release executable")
            binary = staged / "telescope"
            binary.write_bytes(stream.read())
            binary.chmod(0o755)
        actual = subprocess.check_output([str(binary), "--version"], text=True).strip()
        if actual != version:
            raise SiteError(
                f"Telescope version mismatch: expected {version}, got {actual}"
            )
        (staged / "install.json").write_text(
            json.dumps(
                {
                    "version": version,
                    "archive_sha256": expected,
                    "binary_sha256": digest(binary),
                },
                indent=2,
            )
            + "\n"
        )
        backup = destination.with_name(destination.name + ".previous")
        if backup.exists():
            shutil.rmtree(backup)
        if destination.exists():
            destination.rename(backup)
        try:
            staged.rename(destination)
        except OSError:
            if backup.exists():
                backup.rename(destination)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    return destination / "telescope"


def setup() -> Path:
    """Download and verify the release for this qualified host platform."""
    config = json.loads(PINS.read_text())
    machine = {"aarch64": "arm64", "x86_64": "x64"}.get(
        platform.machine(), platform.machine()
    )
    target = f"{platform.system().lower()}-{machine}"
    release = config["platforms"].get(target)
    if release is None:
        raise SiteError(f"Unqualified Telescope platform: {target}; see docs/site.md")
    destination = ROOT / ".dev/tools" / f"telescope-{config['version']}-{target}"
    binary = destination / "telescope"
    receipt = destination / "install.json"
    if binary.is_file() and receipt.is_file():
        installed = json.loads(receipt.read_text())
        if installed.get("archive_sha256") == release["sha256"] and installed.get(
            "binary_sha256"
        ) == digest(binary):
            return binary
    with tempfile.TemporaryDirectory(prefix="telescope-download-") as scratch:
        archive = Path(scratch) / "release.tar.gz"
        with urllib.request.urlopen(release["url"], timeout=120) as response:
            archive.write_bytes(response.read())
        return install_archive(
            archive, destination, release["sha256"], config["version"]
        )


def main(argv: list[str] | None = None) -> None:
    """Run a reproducible site command without installing the Rust toolchain."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["setup", "build", "check", "serve"])
    parser.add_argument("--base", default="/morphir-python/")
    parser.add_argument("--out", default="_site")
    parser.add_argument("--port", type=int, default=4173)
    args = parser.parse_args(argv)
    try:
        binary = setup()
        if args.command == "setup":
            print(binary)
            return
        if args.command == "build":
            subprocess.run(
                [sys.executable, str(ROOT / "scripts/docs_examples.py"), "archive"],
                check=True,
            )
        command = [
            str(binary),
            args.command,
            "--config",
            "site/site.json",
            "--out",
            args.out,
            "--base",
            args.base,
        ]
        if args.command == "check":
            command.extend(["--format", "json"])
        if args.command == "serve":
            command.extend(["--port", str(args.port)])
            os.chdir(ROOT)
            os.execv(binary, command)
        subprocess.run(command, cwd=ROOT, check=True)
    except (SiteError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"site: {exc}\n")


if __name__ == "__main__":
    main()
