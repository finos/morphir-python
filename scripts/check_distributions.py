"""Validate independently versioned library and CLI release artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import tarfile
import tomllib
import zipfile
from configparser import ConfigParser
from dataclasses import dataclass
from email.parser import BytesParser
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.request import urlopen

from scripts.release_candidates import NATIVE_PLATFORMS, classify

if TYPE_CHECKING:
    from collections.abc import Mapping
    from email.message import Message


@dataclass(frozen=True)
class ReleasePackage:
    """A distribution and the source namespace it exclusively owns."""

    name: str
    version: str
    namespace: str
    directory: Path
    tag_prefix: str

    @property
    def stem(self) -> str:
        """Return the normalized archive name and version."""
        return f"{self.name.replace('-', '_')}-{self.version}"

    @property
    def wheel(self) -> Path:
        """Return the pure Python wheel path."""
        return self.directory / "dist" / f"{self.stem}-py3-none-any.whl"


def load_packages(root: Path) -> tuple[ReleasePackage, ...]:
    """Read independent versions from the two public package projects."""
    packages: list[ReleasePackage] = []
    for name, folder, namespace, prefix in (
        ("morphir", "morphir", "morphir", "morphir-v"),
        ("morphir-python", "morphir-tools", "morphir_tools", "python-v"),
    ):
        directory = root / "packages" / folder
        project = tomllib.loads((directory / "pyproject.toml").read_text())["project"]
        if project["name"] != name:
            raise ValueError(f"Unexpected project identity in {directory}")
        packages.append(
            ReleasePackage(name, project["version"], namespace, directory, prefix)
        )
    return tuple(packages)


def select_package(
    tag: str, packages: tuple[ReleasePackage, ...]
) -> ReleasePackage | None:
    """Select only the package whose prefix and exact version match the tag."""
    if not tag:
        return None
    for package in packages:
        if tag == f"{package.tag_prefix}{package.version}":
            return package
    raise ValueError(f"Invalid release tag {tag!r}: expected a package prefix/version")


def validate_metadata(package: ReleasePackage, metadata: Message) -> None:
    """Enforce identity, licensing and the library-to-CLI dependency boundary."""
    if metadata["Name"] != package.name or metadata["Version"] != package.version:
        raise ValueError(f"Incorrect distribution identity for {package.name}")
    if metadata["License-Expression"] != "Apache-2.0":
        raise ValueError(f"Missing Apache-2.0 license for {package.name}")
    requirements = metadata.get_all("Requires-Dist", [])
    if package.name == "morphir" and requirements:
        raise ValueError("morphir must have no runtime dependencies")
    if package.name == "morphir-python" and not any(
        requirement.startswith("morphir>=") for requirement in requirements
    ):
        raise ValueError("morphir-python must declare a versioned library dependency")


def validate_archive(package: ReleasePackage, path: Path) -> None:
    """Check archive metadata, namespace ownership, source completeness and CLI."""
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            raw = archive.read(f"{package.stem}.dist-info/METADATA")
            license_path = f"{package.stem}.dist-info/licenses/LICENSE"
            entry_points = f"{package.stem}.dist-info/entry_points.txt"
            if package.name == "morphir" and entry_points in names:
                raise ValueError("The library must not install console commands")
            if package.name == "morphir-python":
                config = ConfigParser()
                config.read_string(archive.read(entry_points).decode())
                if dict(config["console_scripts"]) != {
                    "morphir-python": "morphir_tools.cli:main"
                }:
                    raise ValueError("Incorrect morphir-python console command")
        source_prefix = ""
    else:
        with tarfile.open(path) as archive:
            names = set(archive.getnames())
            member = archive.extractfile(f"{package.stem}/PKG-INFO")
            if member is None:
                raise ValueError(f"Missing package metadata in {path}")
            raw = member.read()
            license_path = f"{package.stem}/LICENSE"
        source_prefix = f"{package.stem}/src/"
    validate_metadata(package, BytesParser().parsebytes(raw))
    if license_path not in names:
        raise ValueError(f"Missing license file in {path}")
    other = "morphir_tools" if package.name == "morphir" else "morphir"
    if any(name.startswith(f"{source_prefix}{other}/") for name in names):
        raise ValueError(f"Unexpected bundled namespace {other} in {path}")
    source = package.directory / "src"
    expected = {
        source_prefix + p.relative_to(source).as_posix()
        for p in (source / package.namespace).rglob("*")
        if p.is_file() and p.suffix in (".py", ".typed")
    }
    missing = expected - names
    if not expected or missing:
        raise ValueError(f"Missing package sources in {path}: {missing}")


def match_published_wheel(wheel: Path, published: Mapping[str, str]) -> None:
    """Refuse CLI promotion if its tested core differs from the published core."""
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    if published.get(wheel.name) != digest:
        raise ValueError(
            "The published library must match the qualified core wheel; "
            "publish a new library version before releasing this CLI"
        )


def require_published_native(version: str, published: set[str]) -> None:
    """Refuse a CLI release before its exact native dependency is published.

    Args:
        version: The exact ``morphir-python-native`` version the CLI pins.
        published: File names PyPI lists for that version.
    """
    expected = set(native_candidates_for(version))
    if not expected <= published:
        raise ValueError(
            f"publish morphir-python-native {version} with every qualified platform "
            f"before this CLI; missing {sorted(expected - published)}"
        )


def native_candidates_for(version: str) -> list[str]:
    """Return the file names a complete native release contains."""
    stem = f"morphir_python_native-{version}"
    return [f"{stem}-cp314-abi3-{tag}.whl" for tag in NATIVE_PLATFORMS] + [
        f"{stem}.tar.gz"
    ]


def main() -> None:
    """Validate both candidates and require the selected CLI's published inputs."""
    root = Path(__file__).resolve().parents[1]
    packages = load_packages(root)
    tag = os.environ.get("RELEASE_TAG", "")
    if tag.startswith(("native-v", "extension/python/v")):
        classify(tag)
        tag = ""
    selected = select_package(tag, packages)
    for package in packages:
        expected = {package.wheel.name, f"{package.stem}.tar.gz"}
        actual = {
            p.name
            for p in (package.directory / "dist").iterdir()
            if p.is_file() and p.name != ".gitignore"
        }
        if actual != expected:
            raise ValueError(f"Unexpected distributions for {package.name}: {actual}")
        for filename in expected:
            validate_archive(package, package.directory / "dist" / filename)
        print(f"Validated {package.name} {package.version}")
    if selected is not None and selected.name == "morphir-python":
        core = packages[0]
        url = f"https://pypi.org/pypi/morphir/{core.version}/json"
        with urlopen(url, timeout=30) as response:
            data = json.load(response)
        digests: dict[str, str] = {
            item["filename"]: item["digests"]["sha256"] for item in data["urls"]
        }
        match_published_wheel(core.wheel, digests)
        print("The CLI's qualified core matches the published library")
        pin = next(
            requirement.split("==", 1)[1]
            for requirement in tomllib.loads(
                (packages[1].directory / "pyproject.toml").read_text()
            )["project"]["dependencies"]
            if requirement.startswith("morphir-python-native==")
        )
        url = f"https://pypi.org/pypi/morphir-python-native/{pin}/json"
        with urlopen(url, timeout=30) as response:
            files = {item["filename"] for item in json.load(response)["urls"]}
        require_published_native(pin, files)
        print(f"The CLI's native dependency {pin} is published")


if __name__ == "__main__":
    main()
