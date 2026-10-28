"""Qualify the native compiler distribution and a clean installation of all three.

Subcommands:

- ``wheel WHEEL``: check one ``morphir-python-native`` wheel's contents, tags and
  metadata against the Rust crate and the tools pin.
- ``sdist SDIST --out DIR``: check that the source archive holds every Rust
  input, then build a wheel from it in a temporary directory outside the
  checkout, with no sibling repository reachable.
- ``install WHEEL...``: install the exact core, native and tools wheels into a
  new virtual environment with Rust absent from ``PATH``, then exercise the
  installed API and CLI, a library-only installation and a deliberately
  mismatched native installation.

Every subcommand prints one JSON receipt naming the artifacts and their SHA-256
digests, and exits non-zero on the first failed check.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

ROOT = Path(__file__).resolve().parents[1]
NATIVE = "morphir-python-native"
NATIVE_CRATE = ROOT / "rust" / "crates" / "morphir-python-native" / "Cargo.toml"
TOOLS_PROJECT = ROOT / "packages" / "morphir-tools" / "pyproject.toml"
SAMPLE = ROOT / "tests" / "fixtures" / "python" / "loans"

REQUIRED_SDIST_FILES = (
    "pyproject.toml",
    "rust/Cargo.toml",
    "rust/Cargo.lock",
    "rust/crates/morphir-python-native/Cargo.toml",
    "rust/crates/morphir-python-native/src/lib.rs",
    "rust/crates/morphir-python-binding/Cargo.toml",
    "rust/crates/morphir-python-binding/src/lib.rs",
    "python/morphir_python_native/__init__.py",
    "python/morphir_python_native/_native.pyi",
    "python/morphir_python_native/py.typed",
)

# Wheel tags the release builds; abi3 for CPython 3.14 and later.
WHEEL_NAME = re.compile(
    r"^morphir_python_native-(?P<version>[^-]+)-cp314-abi3-(?P<platform>[a-z0-9_.]+)\.whl$"
)


class QualificationError(Exception):
    """A qualification check failed."""


def sha256(path: Path) -> str:
    """Return the hexadecimal SHA-256 digest of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def crate_version(manifest: Path = NATIVE_CRATE) -> str:
    """Return the native crate version, which is also the distribution version."""
    return str(tomllib.loads(manifest.read_text())["package"]["version"])


def tools_pin(project: Path = TOOLS_PROJECT) -> str:
    """Return the exact native version the tools distribution requires."""
    for requirement in tomllib.loads(project.read_text())["project"]["dependencies"]:
        match = re.fullmatch(rf"{NATIVE}==([^\s;]+)", requirement.replace(" ", ""))
        if match:
            return match.group(1)
    raise QualificationError(f"{project} has no exact {NATIVE} requirement")


def check_versions(version: str, expected_module: str | None = None) -> None:
    """Require the crate version, the tools pin and the tools constant to agree."""
    pin = tools_pin()
    if version != crate_version() or version != pin:
        raise QualificationError(
            f"native version {version} differs from crate {crate_version()} "
            f"or tools pin {pin}"
        )
    bridge = (
        ROOT
        / "packages"
        / "morphir-tools"
        / "src"
        / "morphir_tools"
        / "python"
        / "_bridge.py"
    ).read_text()
    if f'EXPECTED_NATIVE_VERSION = "{version}"' not in bridge:
        raise QualificationError("EXPECTED_NATIVE_VERSION differs from the native pin")
    if expected_module is not None and expected_module != version:
        raise QualificationError(
            f"compiled module reports {expected_module}, distribution is {version}"
        )


def validate_wheel(path: Path) -> dict[str, object]:
    """Check a native wheel's name, files, tags and metadata.

    Raises:
        QualificationError: For the first problem found.
    """
    match = WHEEL_NAME.match(path.name)
    if match is None:
        raise QualificationError(f"{path.name} is not a cp314-abi3 native wheel")
    version = match["version"]
    check_versions(version)
    stem = f"morphir_python_native-{version}"
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        metadata = BytesParser().parsebytes(archive.read(f"{stem}.dist-info/METADATA"))
        wheel = archive.read(f"{stem}.dist-info/WHEEL").decode()
    modules = [
        name
        for name in names
        if re.fullmatch(r"morphir_python_native/_native\.(abi3\.so|pyd)", name)
    ]
    required = {
        "morphir_python_native/__init__.py",
        "morphir_python_native/_native.pyi",
        "morphir_python_native/py.typed",
        f"{stem}.dist-info/licenses/LICENSE",
    }
    if len(modules) != 1 or not required <= names:
        raise QualificationError(
            f"{path.name} lacks {sorted(required - names)} or one native module"
        )
    if metadata["Name"] != NATIVE or metadata["Version"] != version:
        raise QualificationError(f"{path.name} has the wrong distribution identity")
    if metadata["License-Expression"] != "Apache-2.0":
        raise QualificationError(f"{path.name} lacks the Apache-2.0 license")
    if metadata.get_all("Requires-Dist"):
        raise QualificationError(f"{path.name} must have no runtime dependencies")
    if metadata["Requires-Python"] != ">=3.14":
        raise QualificationError(f"{path.name} must require Python 3.14 or later")
    if "Root-Is-Purelib: false" not in wheel:
        raise QualificationError(f"{path.name} must be a platform wheel")
    return {"wheel": path.name, "sha256": sha256(path), "version": version}


def validate_sdist_names(names: Sequence[str], version: str) -> None:
    """Require every Rust and Python build input under the archive root."""
    prefix = f"morphir_python_native-{version}/"
    present = {name.removeprefix(prefix) for name in names if name.startswith(prefix)}
    missing = [name for name in REQUIRED_SDIST_FILES if name not in present]
    if missing:
        raise QualificationError(f"the source archive lacks {missing}")
    if any(".." in name.split("/") or name.startswith("/") for name in names):
        raise QualificationError("the source archive has an unsafe member path")


def build_from_sdist(path: Path, out: Path) -> dict[str, object]:
    """Build a wheel from the source archive alone, outside the checkout."""
    version = crate_version()
    if path.name != f"morphir_python_native-{version}.tar.gz":
        raise QualificationError(f"unexpected source archive name {path.name}")
    with tarfile.open(path) as archive:
        validate_sdist_names(archive.getnames(), version)
    with tempfile.TemporaryDirectory(prefix="native-sdist-") as scratch:
        isolated = Path(scratch)
        if ROOT in isolated.parents:
            raise QualificationError("the scratch directory is inside the checkout")
        copy = isolated / path.name
        shutil.copy2(path, copy)
        out.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["uv", "build", "--wheel", str(copy), "--out-dir", str(isolated / "dist")],
            cwd=isolated,
            check=True,
        )
        (wheel,) = (isolated / "dist").glob("*.whl")
        validate_wheel(wheel)
        target = out / wheel.name
        shutil.copy2(wheel, target)
    return {
        "sdist": path.name,
        "sdist_sha256": sha256(path),
        "wheel": target.name,
        "wheel_sha256": sha256(target),
    }


def rust_free_path(venv: Path) -> str:
    """Return a PATH holding the virtual environment and system tools only."""
    entries = [str(venv / ("Scripts" if os.name == "nt" else "bin"))]
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        tools = (
            shutil.which(tool, path=entry) for tool in ("cargo", "rustc", "rustup")
        )
        managed = any(word in entry for word in ("cargo", "rustup", "mise"))
        if entry and not managed and all(found is None for found in tools):
            entries.append(entry)
    path = os.pathsep.join(entries)
    for tool in ("cargo", "rustc", "rustup"):
        if shutil.which(tool, path=path) is not None:
            raise QualificationError(f"{tool} is still on the qualification PATH")
    return path


INSTALLED_CHECK = r"""
import json, shutil, subprocess, sys, tempfile
from importlib.metadata import distribution, version
from pathlib import Path

import morphir_python_native._native as native
from morphir_tools.python import (
    CompiledV3, CompiledV4, Generated, IrVersion, SourceDocument,
    compile_sources, generate_python, native_compiler,
)

sample = Path(sys.argv[1])
info = native_compiler()
assert info.version == version("morphir-python-native") == native.__version__
assert not distribution("morphir").requires
docs = [SourceDocument(p.relative_to(sample).as_posix(), p.read_text())
        for p in sorted(sample.rglob("*.py"))]
for ir_version, kind in ((IrVersion.V3, CompiledV3), (IrVersion.V4, CompiledV4)):
    compiled = compile_sources(docs, package="acme/example", ir_version=ir_version)
    assert isinstance(compiled, kind), compiled
    generated = generate_python(compiled.distribution)
    assert isinstance(generated, Generated), generated
    again = compile_sources(
        [SourceDocument(a.path, a.text) for a in generated.artifacts],
        package="acme/example", ir_version=ir_version,
    )
    assert again == compiled
work = Path(tempfile.mkdtemp())
cli = [shutil.which("morphir-python", path=str(Path(sys.executable).parent))]
for flag in ("v3", "v4"):
    model, out = work / f"{flag}.json", work / f"gen-{flag}"
    subprocess.run(cli + ["compile", str(sample), "--package", "acme/example",
                          "--ir-version", flag, "-o", str(model)], check=True)
    subprocess.run(cli + ["ir", "inspect", str(model)], check=True)
    subprocess.run(cli + ["generate", str(model), "--output-dir", str(out)], check=True)
    result = subprocess.run(
        [sys.executable, "-I", "-c",
         "import sys; sys.path.insert(0, sys.argv[1]); from acme import rules;"
         "print(rules.choose(True, 1, 2), rules.twice_identity(7))", str(out)],
        check=True, capture_output=True, text=True)
    assert result.stdout.split() == ["1", "7"], result.stdout
print(json.dumps({"native": info.version, "compiler": info.compiler_version,
                  "bridge_api": info.bridge_api}))
"""

LIBRARY_CHECK = r"""
from importlib.util import find_spec
from morphir.ir import format_version
from morphir.sdk import basics
assert basics.round(2.5) == 3 and format_version.V3.major == 3
assert find_spec("morphir_python_native") is None
assert find_spec("morphir_tools") is None
"""


def venv_python(directory: Path, system: str = os.name) -> Path:
    """Return the interpreter path inside a virtual environment."""
    if system == "nt":
        return directory / "Scripts" / "python.exe"
    return directory / "bin" / "python"


def _venv(directory: Path) -> Path:
    subprocess.run(
        ["uv", "venv", "--quiet", "--python", "3.14", str(directory)], check=True
    )
    return venv_python(directory)


def _script(python: Path, name: str) -> str:
    found = shutil.which(name, path=str(python.parent))
    if found is None:
        raise QualificationError(f"{name} is not installed next to {python}")
    return found


def _mismatch(python: Path, path: str) -> None:
    """Fake an incompatible native install and require a clear refusal."""
    metadata = subprocess.run(
        [
            str(python),
            "-I",
            "-c",
            "from importlib.metadata import distribution as d;"
            "print(d('morphir-python-native')._path)",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    file = Path(metadata) / "METADATA"
    # uv may hard-link installed metadata to its wheel cache. Replace this
    # installation's directory entry so the negative fixture cannot corrupt
    # the cache or another environment's copy of the qualified distribution.
    replacement = file.with_name("METADATA.mismatch")
    replacement.write_text(
        re.sub(r"(?m)^Version: .*$", "Version: 0.0.0", file.read_text())
    )
    replacement.replace(file)
    result = subprocess.run(
        [
            _script(python, "morphir-python"),
            "compile",
            str(SAMPLE),
            "--package",
            "acme/example",
            "-o",
            str(Path(metadata).parent / "x.json"),
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": path},
        check=False,
    )
    if result.returncode != 1 or "morphir-python-native 0.0.0" not in result.stderr:
        raise QualificationError(
            f"a mismatched native install was not refused clearly: {result.stderr}"
        )


def install(wheels: Sequence[Path]) -> dict[str, object]:
    """Install the exact wheels without Rust and exercise them."""
    by_name = {wheel.name.split("-")[0]: wheel for wheel in wheels}
    expected = {"morphir", "morphir_python", "morphir_python_native"}
    if set(by_name) != expected:
        raise QualificationError(f"expected one wheel each for {sorted(expected)}")
    validate_wheel(by_name["morphir_python_native"])
    with tempfile.TemporaryDirectory(prefix="native-install-") as scratch:
        work = Path(scratch)
        python = _venv(work / "full")
        path = rust_free_path(work / "full")
        env = {**os.environ, "PATH": path, "CARGO_HOME": str(work / "no-cargo")}
        env.pop("VIRTUAL_ENV", None)
        subprocess.run(
            ["uv", "pip", "install", "--quiet", "--no-build", "--python", str(python)]
            + [str(w) for w in wheels],
            check=True,
        )
        installed = subprocess.run(
            [str(python), "-I", "-c", INSTALLED_CHECK, str(SAMPLE)],
            env=env,
            check=True,
            capture_output=True,
            text=True,
            cwd=work,
        )
        library = _venv(work / "library")
        subprocess.run(
            [
                *("uv", "pip", "install", "--quiet", "--no-build"),
                *("--python", str(library), str(by_name["morphir"])),
            ],
            check=True,
        )
        subprocess.run([str(library), "-I", "-c", LIBRARY_CHECK], env=env, check=True)
        _mismatch(python, path)
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "rust_on_path": False,
        "artifacts": {wheel.name: sha256(wheel) for wheel in wheels},
        "installed": json.loads(installed.stdout.strip().splitlines()[-1]),
        "library_only": "passed",
        "mismatch_refused": True,
    }


def main(argv: Sequence[str] | None = None) -> None:
    """Run one qualification subcommand and print its receipt."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    wheel = commands.add_parser("wheel")
    wheel.add_argument("wheel", type=Path)
    sdist = commands.add_parser("sdist")
    sdist.add_argument("sdist", type=Path)
    sdist.add_argument("--out", type=Path, required=True)
    installs = commands.add_parser("install")
    installs.add_argument("wheels", type=Path, nargs=3)
    args = parser.parse_args(argv)
    try:
        if args.command == "wheel":
            receipt = validate_wheel(args.wheel)
        elif args.command == "sdist":
            receipt = build_from_sdist(args.sdist, args.out)
        else:
            receipt = install(args.wheels)
    except (QualificationError, subprocess.CalledProcessError) as error:
        print(f"qualification failed: {error}", file=sys.stderr)
        raise SystemExit(1) from None
    print(json.dumps({"check": args.command, **receipt}, indent=2))


if __name__ == "__main__":
    main()
