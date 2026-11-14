"""Install a Python package and run compile/generate using the released .NET CLI."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from scripts.check_process_windows import sha256
from scripts.process_command import run

HOST_URL = (
    "https://github.com/finos/morphir-dotnet/releases/download/v0.5.0-alpha.1/"
    "morphir-dotnet-0.5.0-alpha.1-self-contained-win-arm64.zip"
)
HOST_SHA256 = "07887a38d4a74e7ccd50e8849ff99b37c7f5e2798419b1f2b4c6d4267afccfcd"


def environment(work: Path) -> dict[str, str]:
    """Use a dedicated absolute Home without inheriting a generation overlay."""
    env = os.environ.copy()
    env["MORPHIR_HOME"] = str(work.resolve() / "home")
    env.pop("MORPHIR_EXTENSION_OVERLAY", None)
    return env


def validate_operation(report: dict[str, Any], version: str) -> None:
    """Require success through the exact installed provider and supported draft."""
    provider = report.get("provider", {})
    if (
        report.get("success") is not True
        or provider.get("extensionId") != "morphir-python"
        or provider.get("version") != version
        or provider.get("mepVersion") != "0.2.0-draft.1"
    ):
        raise RuntimeError("Operation did not use the installed package and protocol")


def download_host(work: Path) -> Path:
    """Download and verify the pinned Windows ARM64 self-contained host."""
    archive = work / "morphir-host.zip"
    with (
        urllib.request.urlopen(HOST_URL, timeout=60) as response,
        archive.open("xb") as out,
    ):
        shutil.copyfileobj(response, out)
    if sha256(archive) != HOST_SHA256:
        raise RuntimeError("Host archive digest differs")
    host_dir = work / "host"
    with zipfile.ZipFile(archive) as zipped:
        zipped.extractall(host_dir)
    return (host_dir / "morphir.exe").resolve(strict=True)


def check(packages: Path, work: Path, host: Path | None = None) -> None:
    """Exercise the actual installed process in a fresh, isolated working directory."""
    packages = packages.resolve(strict=True)
    work = work.resolve()
    work.mkdir(parents=True)
    host = host.resolve(strict=True) if host is not None else download_host(work)
    releases = list(packages.glob("*.release.json"))
    if len(releases) != 1:
        raise RuntimeError("Expected exactly one package declaration")
    descriptor = json.loads(releases[0].read_text(encoding="utf-8"))
    (artifact,) = descriptor["artifacts"]
    env = environment(work)
    home = env["MORPHIR_HOME"]
    for arguments in (
        [
            "extension",
            "repository",
            "add",
            "python-local",
            "--directory",
            str(packages),
            "--home",
            home,
            "--local-developer",
        ],
        [
            "extension",
            "install",
            "morphir-python",
            "--repository",
            "python-local",
            "--local-release",
            str(releases[0]),
            "--local-archive",
            str(packages / artifact["filename"]),
            "--home",
            home,
            "--local-developer",
            "--no-probe",
        ],
    ):
        print(run([str(host), *arguments], cwd=work, env=env), end="")
    (work / "identity.py").write_text(
        "def identity(value: int) -> int: return value\n",
        encoding="utf-8",
        newline="\n",
    )
    for operation, arguments in (
        (
            "compile",
            [
                "compile",
                "--language",
                "python",
                "--input",
                "identity.py",
                "--package-name",
                "acme/demo",
                "--ir-version",
                "4",
                "--output",
                "compiled",
            ],
        ),
        (
            "generate",
            [
                "generate",
                "--input",
                "compiled/morphir-ir.json",
                "--target",
                "python",
                "--output",
                "generated",
            ],
        ),
    ):
        output = run(
            [str(host), *arguments, "--extension-id", "morphir-python", "--json"],
            cwd=work,
            env=env,
        )
        validate_operation(json.loads(output), descriptor["version"])
        (work / f"{operation}.json").write_text(output, encoding="utf-8", newline="\n")
    run(
        [
            sys.executable,
            "-c",
            "import runpy; "
            "assert runpy.run_path('generated/identity.py')['identity'](42) == 42",
        ],
        cwd=work,
        env=env,
    )
    print(
        f"Installed Python {descriptor['version']}: "
        "compile, generate and generated code passed."
    )


def main(argv: list[str] | None = None) -> int:
    """Run the installed journey, acquiring the pinned host unless one is supplied."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-executable", type=Path)
    parser.add_argument("--package-directory", type=Path, required=True)
    parser.add_argument("--work-directory", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        check(args.package_directory, args.work_directory, args.host_executable)
    except subprocess.CalledProcessError as error:
        parser.exit(
            1,
            f"Installed process check failed: {error}\n"
            f"{error.stdout or ''}{error.stderr or ''}",
        )
    except (
        OSError,
        RuntimeError,
        ValueError,
        KeyError,
        subprocess.SubprocessError,
    ) as error:
        parser.exit(1, f"Installed process check failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
