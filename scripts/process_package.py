"""Package the Python process guest for the existing .NET extension installer.

Each native producer reads describe from its executable and emits an
extension-family descriptor and one-file ZIP. No Morphir host is needed to
build a package.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import stat
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

from scripts import extension_bundle as bundle
from scripts import process_diagnostics, process_extension

PLATFORMS = (*process_extension.PLATFORMS, "aarch64-pc-windows-msvc")
SCHEMA = (
    "https://morphir.finos.org/schemas/extensions/0.1.0-preview.1/release.schema.json"
)


def describe(executable: Path) -> dict[str, Any]:
    """Read the actual guest claims over stdio, with a bounded process lifetime."""
    messages: list[dict[str, Any]] = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "morphir.extension.describe",
            "params": {"protocolVersions": ["0.2.0-draft.1"]},
        },
        {"jsonrpc": "2.0", "method": "morphir.exit"},
    ]
    with subprocess.Popen(
        [str(executable.resolve())],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        start_new_session=os.name != "nt",
    ) as guest:
        try:
            stdout, stderr = guest.communicate(
                b"".join(map(process_diagnostics._frame, messages)), timeout=30
            )
        except subprocess.TimeoutExpired:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/PID", str(guest.pid), "/T", "/F"],
                    capture_output=True,
                    check=False,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                os.killpg(guest.pid, signal.SIGKILL)
            guest.communicate()
            raise bundle.BundleError("process describe timed out") from None
    replies = process_diagnostics._responses(stdout)
    if guest.returncode or stderr or len(replies) != 1:
        raise bundle.BundleError("process describe failed")
    reply = replies[0]
    if reply.get("jsonrpc") != "2.0" or reply.get("id") != 1 or "error" in reply:
        raise bundle.BundleError("process describe returned an invalid response")
    result = reply.get("result")
    if not isinstance(result, dict):
        raise bundle.BundleError("process describe omitted its claims")
    return result


def package(
    executable: Path,
    output: Path,
    platform: str,
    commit: str,
    claims: dict[str, Any],
) -> None:
    """Emit a deterministic one-file package, manifest, descriptor and checksums."""
    if platform not in PLATFORMS or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise bundle.BundleError("unsupported platform or invalid source commit")
    version = bundle.crate_version()
    if (
        claims.get("extension", {}).get("id") != "morphir-python"
        or claims["extension"].get("version") != version
        or claims.get("protocolVersions")
        != bundle.declaration()["extension"]["mep_versions"]
    ):
        raise bundle.BundleError("process claims differ from the compiler identity")
    if executable.is_symlink() or not executable.is_file():
        raise bundle.BundleError("package executable must be a regular file")
    data = executable.read_bytes()
    entry = "morphir-python-extension"
    if platform.endswith("windows-msvc"):
        entry += ".exe"
    stem = f"morphir-python-extension-{version}-{platform}"
    manifest = (
        "morphir-package-tree 0.1.0-preview.1\n"
        f"x {len(data)} {bundle.sha256(data)} {entry}\n"
    ).encode("ascii")
    output.mkdir(parents=True)
    archive = output / f"{stem}.zip"
    info = zipfile.ZipInfo(entry, date_time=(1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o755) << 16
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as zipped:
        zipped.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)
    descriptor = {
        "$schema": SCHEMA,
        "critical": ["artifacts.package"],
        "extensionId": "morphir-python",
        "shortId": "python",
        "version": version,
        "gitCommit": commit,
        "platformDifferences": "none",
        "artifacts": [
            {
                "runtime": "process",
                "platform": platform,
                "filename": archive.name,
                "sha256": bundle.sha256(archive.read_bytes()),
                "claims": {
                    key: value
                    for key, value in claims.items()
                    if key != "claimsVersion"
                },
                "package": {
                    "format": "zip",
                    "entryPoint": entry,
                    "executables": [entry],
                    "treeSha256": bundle.sha256(manifest),
                },
            }
        ],
    }
    (output / f"{stem}.release.json").write_text(
        json.dumps(descriptor, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (output / f"{stem}.manifest").write_bytes(manifest)
    (output / "SHA256SUMS").write_text(
        "".join(
            f"{bundle.sha256(path.read_bytes())}  {path.name}\n"
            for path in sorted(output.iterdir())
        ),
        encoding="ascii",
        newline="\n",
    )


def main(argv: list[str] | None = None) -> int:
    """Package a locally built native executable using its actual describe claims."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--platform", choices=PLATFORMS, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        executable = args.executable
        claims = describe(executable)
        package(executable, args.output, args.platform, args.commit, claims)
    except (bundle.BundleError, OSError, KeyError, TypeError, ValueError) as error:
        parser.exit(1, f"process packaging refused: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
