"""Validate release tags and the exact candidate artifacts a release may promote.

Tags and the versions they must match:

- ``morphir-v<version>`` and ``python-v<version>``: the pure Python packages,
  checked by ``scripts/check_distributions.py``;
- ``native-v<version>``: ``morphir-python-native``, the native crate version;
- ``extension/python/v<version>``: the MEP bundle, the compiler crate version.

``tag TAG`` prints the release kind and version, or fails for a malformed tag or
a version that differs from the source. ``native DIR --tag TAG`` and
``bundle DIR --tag TAG --commit SHA`` refuse a candidate set with a missing,
extra or mismatched artifact and write a ``SHA256SUMS`` receipt for publication
to verify again.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

NATIVE_PLATFORMS = (
    "manylinux_2_28_x86_64",
    "manylinux_2_28_aarch64",
    "macosx_11_0_arm64",
    "macosx_10_12_x86_64",
    "win_amd64",
)
"""The qualified native wheel platforms, documented in docs/python-compiler.md."""


class CandidateError(Exception):
    """The candidate artifacts or tag cannot be promoted."""


@dataclass(frozen=True)
class Release:
    """A release kind and the version its tag names."""

    kind: str
    version: str


def _version(manifest: Path) -> str:
    data = tomllib.loads(manifest.read_text())
    return str((data.get("package") or data["project"])["version"])


def source_versions(root: Path = ROOT) -> dict[str, str]:
    """Return the version each release kind has in the source tree."""
    return {
        "morphir": _version(root / "packages" / "morphir" / "pyproject.toml"),
        "python": _version(root / "packages" / "morphir-tools" / "pyproject.toml"),
        "native": _version(
            root / "rust" / "crates" / "morphir-python-native" / "Cargo.toml"
        ),
        "extension": _version(
            root / "rust" / "crates" / "morphir-python-binding" / "Cargo.toml"
        ),
    }


PREFIXES = (
    ("extension/python/v", "extension"),
    ("morphir-v", "morphir"),
    ("python-v", "python"),
    ("native-v", "native"),
)


def classify(tag: str, versions: dict[str, str] | None = None) -> Release:
    """Return the release a tag names, checking its version against the source.

    Raises:
        CandidateError: For an unknown prefix or a version mismatch.
    """
    versions = versions or source_versions()
    for prefix, kind in PREFIXES:
        if tag.startswith(prefix):
            version = tag.removeprefix(prefix)
            if version != versions[kind]:
                raise CandidateError(
                    f"tag {tag} names {version} but the source has {versions[kind]}"
                )
            return Release(kind, version)
    raise CandidateError(f"tag {tag!r} has no known release prefix")


def _sums(directory: Path, names: list[str]) -> str:
    lines = [
        f"{hashlib.sha256((directory / name).read_bytes()).hexdigest()}  {name}"
        for name in sorted(names)
    ]
    return "\n".join(lines) + "\n"


def native_candidates(directory: Path, version: str) -> list[str]:
    """Require exactly one wheel per qualified platform and one source archive."""
    stem = f"morphir_python_native-{version}"
    expected = {f"{stem}-cp314-abi3-{tag}.whl" for tag in NATIVE_PLATFORMS}
    expected.add(f"{stem}.tar.gz")
    found = {p.name for p in directory.iterdir() if p.suffix in {".whl", ".gz"}}
    if found != expected:
        raise CandidateError(
            f"native candidates differ: missing {sorted(expected - found)}, "
            f"unexpected {sorted(found - expected)}"
        )
    return sorted(expected)


def bundle_candidates(directory: Path, version: str, commit: str) -> list[str]:
    """Require the bundle for this version, built from exactly this commit."""
    artifact = f"morphir-python-binding-{version}.wasm"
    expected = {artifact, f"{artifact}.sha256", "release.json"}
    found = {p.name for p in directory.iterdir() if p.is_file()}
    if found != expected:
        raise CandidateError(f"bundle files differ: {sorted(found ^ expected)}")
    descriptor = json.loads((directory / "release.json").read_text())
    wasm = (directory / artifact).read_bytes()
    digest = hashlib.sha256(wasm).hexdigest()
    (entry,) = descriptor["artifacts"]
    if descriptor.get("version") != version or entry.get("sha256") != digest:
        raise CandidateError("release.json disagrees with the tag or the WASM")
    if descriptor.get("gitCommit") != commit:
        raise CandidateError(
            f"the bundle was built from {descriptor.get('gitCommit')}, not {commit}"
        )
    if not re.fullmatch(
        r"[0-9a-f]{64}  " + re.escape(artifact) + "\n",
        (directory / f"{artifact}.sha256").read_text(),
    ):
        raise CandidateError("the .sha256 file is malformed")
    return sorted(expected)


def main(argv: list[str] | None = None) -> None:
    """Run one check and print or write its receipt."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    tag = commands.add_parser("tag")
    tag.add_argument("tag")
    native = commands.add_parser("native")
    native.add_argument("directory", type=Path)
    native.add_argument("--tag", required=True)
    bundle = commands.add_parser("bundle")
    bundle.add_argument("directory", type=Path)
    bundle.add_argument("--tag", required=True)
    bundle.add_argument("--commit", required=True)
    args = parser.parse_args(argv)
    try:
        release = classify(args.tag)
        if args.command == "tag":
            print(f"kind={release.kind}\nversion={release.version}")
            return
        if args.command == "native":
            if release.kind != "native":
                raise CandidateError(f"{args.tag} is not a native release tag")
            names = native_candidates(args.directory, release.version)
        else:
            if release.kind != "extension":
                raise CandidateError(f"{args.tag} is not an extension release tag")
            names = bundle_candidates(args.directory, release.version, args.commit)
    except (CandidateError, OSError, KeyError, ValueError) as error:
        print(f"candidate refused: {error}", file=sys.stderr)
        raise SystemExit(1) from None
    sums = _sums(args.directory, names)
    (args.directory / "SHA256SUMS").write_text(sums)
    print(sums, end="")


if __name__ == "__main__":
    main()
