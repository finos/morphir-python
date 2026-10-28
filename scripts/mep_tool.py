"""Build the exact shared MCK source without changing its frozen expectations."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from scripts import extension_bundle as bundle


def sha(path: Path) -> str:
    """Hash available file bytes without loading a checker binary into memory."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def object_file(path: Path) -> dict[str, Any]:
    """Read a required JSON object at the tool boundary."""
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise bundle.BundleError(f"expected an object: {path}")
    return value


def freeze_binary(executable: Path, cache: Path) -> Path:
    """Keep report identities independent of mutable Cargo output filenames."""
    if executable.is_symlink() or not executable.is_file():
        raise bundle.BundleError("MCK build output must be a regular file")
    digest = sha(executable)
    frozen = cache / digest / executable.name
    frozen.parent.mkdir(parents=True, exist_ok=True)
    if frozen.exists() or frozen.is_symlink():
        if frozen.is_symlink() or not frozen.is_file() or sha(frozen) != digest:
            raise bundle.BundleError("stored MCK checker integrity differs")
        return frozen
    created = False
    try:
        with frozen.open("xb") as destination, executable.open("rb") as source:
            created = True
            shutil.copyfileobj(source, destination)
        if sha(frozen) != digest:
            raise bundle.BundleError("MCK checker copy integrity differs")
        if os.name != "nt":
            frozen.chmod(0o700)
    except BaseException:
        if created:
            frozen.unlink(missing_ok=True)
        raise
    return frozen


def command(arguments: list[str], *, cwd: Path | None = None) -> str:
    """Run a bounded setup command, retaining diagnostics on failure."""
    result = subprocess.run(
        arguments,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=180,
    )
    if result.returncode:
        raise bundle.BundleError(f"{arguments[0]} failed: {result.stderr}")
    return result.stdout.strip()


def build_checker(source: Path, target: Path, log: Path) -> None:
    """Build with bounded CI diagnostics and preserve the complete raw log."""
    with log.open("wb") as stream:
        result = subprocess.run(
            [
                "cargo",
                "build",
                "--locked",
                "--manifest-path",
                str(source / "Cargo.toml"),
                "--target-dir",
                str(target),
                "-p",
                "morphir",
            ],
            cwd=bundle.ROOT,
            env=os.environ | {"CARGO_PROFILE_DEV_DEBUG": "0", "CARGO_INCREMENTAL": "0"},
            stdout=stream,
            stderr=subprocess.STDOUT,
            timeout=1800,
        )
    if result.returncode:
        tail = "\n".join(
            log.read_bytes().decode("utf-8", errors="replace").splitlines()[-80:]
        )
        raise bundle.BundleError(f"MCK build failed; full log {log}\n{tail[-16000:]}")


def prepare(output: Path, target: Path | None = None) -> dict[str, Any]:
    """Fetch source by Git identity and run Cargo even when a build cache exists.

    Cargo owns compatible object reuse. A cached receipt alone never authorizes
    execution. Only the needed Rust submodule is initialized.
    """
    pin = bundle.declaration()["mep"]
    cache = bundle.ROOT / ".dev/mep-tool" / pin["rev"]
    source = cache / "source"
    source.mkdir(parents=True, exist_ok=True)
    if not (source / ".git").is_dir():
        command(["git", "init", str(source)])
        command(["git", "remote", "add", "origin", pin["repository"]], cwd=source)
        command(["git", "config", "core.autocrlf", "false"], cwd=source)
        command(["git", "config", "core.longpaths", "true"], cwd=source)
    if command(["git", "remote", "get-url", "origin"], cwd=source) != pin["repository"]:
        raise bundle.BundleError("MCK source cache has another repository")
    command(["git", "fetch", "--depth", "1", "origin", pin["rev"]], cwd=source)
    # Refuse tracked/untracked modifications rather than resetting somebody's work.
    if command(["git", "status", "--porcelain"], cwd=source):
        raise bundle.BundleError("MCK source cache is dirty")
    command(["git", "checkout", "--detach", pin["rev"]], cwd=source)
    if command(["git", "rev-parse", "HEAD^{tree}"], cwd=source) != pin["tree"]:
        raise bundle.BundleError("MCK source tree differs from the audited pin")
    command(
        [
            "git",
            "-c",
            "core.autocrlf=false",
            "-c",
            "core.longpaths=true",
            "submodule",
            "update",
            "--init",
            "--depth",
            "1",
            "ecosystem/morphir-rust",
        ],
        cwd=source,
    )
    kit = source / pin["kit"]
    if (
        sha(source / "Cargo.lock") != pin["cargo_lock_sha256"]
        or sha(kit) != pin["corpus_sha256"]
    ):
        raise bundle.BundleError("MCK lockfile or frozen corpus differs")
    command(["mise", "trust", str(source / ".config/mise/config.toml")])
    target = (target or cache / "target").resolve()
    log = cache / "build.log"
    # This is a correctness checker, not the implementation being benchmarked.
    # A dev-profile build reduces setup cost and is identified in the receipt.
    build_checker(source, target, log)
    if command(["git", "status", "--porcelain"], cwd=source):
        raise bundle.BundleError("MCK build changed its pinned source")
    executable = target / "debug" / ("morphir.exe" if os.name == "nt" else "morphir")
    executable = freeze_binary(executable, cache / "bin")
    receipt = {
        "kind": "source-built-shared-mck",
        "revision": pin["rev"],
        "tree": pin["tree"],
        "executable": str(executable),
        "binarySha256": sha(executable),
        "kit": str(kit),
        "corpusSha256": sha(kit),
        "cargoLockSha256": sha(source / "Cargo.lock"),
        "profile": "dev",
        "debugInfo": False,
        "incremental": False,
        "rustc": command(["rustc", "-vV"]),
        "preparerSha256": sha(Path(__file__)),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main() -> None:
    """Prepare one compatible checker for explicit conformance consumers."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-dir", type=Path)
    args = parser.parse_args()
    prepare(args.output, args.target_dir)


if __name__ == "__main__":
    main()
