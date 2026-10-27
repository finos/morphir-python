"""Release selection and package ownership checks."""

import hashlib
import zipfile
from email.message import Message
from pathlib import Path

import pytest

from scripts.check_distributions import (
    ReleasePackage,
    match_published_wheel,
    select_package,
    validate_archive,
    validate_metadata,
)

CORE = ReleasePackage("morphir", "0.0.1", "morphir", Path("core"), "morphir-v")
CLI = ReleasePackage(
    "morphir-python", "0.0.2", "morphir_tools", Path("cli"), "python-v"
)


@pytest.mark.parametrize(
    ("tag", "expected"),
    [("", None), ("morphir-v0.0.1", CORE), ("python-v0.0.2", CLI)],
)
def test_independent_release_versions(
    tag: str, expected: ReleasePackage | None
) -> None:
    assert select_package(tag, (CORE, CLI)) == expected


@pytest.mark.parametrize("tag", ["v0.0.1", "morphir-v0.0.2", "python-v0.0.1"])
def test_wrong_or_ambiguous_release_tag_is_rejected(tag: str) -> None:
    with pytest.raises(ValueError, match="release tag"):
        select_package(tag, (CORE, CLI))


def metadata(package: ReleasePackage) -> Message:
    result = Message()
    result["Name"] = package.name
    result["Version"] = package.version
    result["License-Expression"] = "Apache-2.0"
    return result


def test_library_rejects_cli_dependencies() -> None:
    value = metadata(CORE)
    validate_metadata(CORE, value)
    value["Requires-Dist"] = "typer>=0.15"
    with pytest.raises(ValueError, match="no runtime dependencies"):
        validate_metadata(CORE, value)


def test_cli_requires_a_versioned_library_dependency() -> None:
    value = metadata(CLI)
    with pytest.raises(ValueError, match="library dependency"):
        validate_metadata(CLI, value)
    value["Requires-Dist"] = "morphir>=0.0.1"
    validate_metadata(CLI, value)


def test_wrong_distribution_identity_is_rejected() -> None:
    value = metadata(CORE)
    value.replace_header("Name", "morphir-python")
    with pytest.raises(ValueError, match="identity"):
        validate_metadata(CORE, value)


def test_cli_promotion_rejects_a_different_published_library(tmp_path: Path) -> None:
    wheel = tmp_path / "morphir-0.0.1-py3-none-any.whl"
    wheel.write_bytes(b"tested core candidate")
    with pytest.raises(ValueError, match="published library"):
        match_published_wheel(wheel, {wheel.name: "different-digest"})
    with pytest.raises(ValueError, match="published library"):
        match_published_wheel(wheel, {})
    match_published_wheel(
        wheel, {wheel.name: hashlib.sha256(b"tested core candidate").hexdigest()}
    )


@pytest.mark.parametrize("name", ["morphir", "morphir-python"])
def test_archives_reject_the_other_packages_namespace(
    tmp_path: Path, name: str
) -> None:
    namespace = "morphir" if name == "morphir" else "morphir_tools"
    other = "morphir_tools" if name == "morphir" else "morphir"
    package = ReleasePackage(name, "0.0.1", namespace, tmp_path, "unused-v")
    value = metadata(package)
    if name == "morphir-python":
        value["Requires-Dist"] = "morphir>=0.0.1"
    path = tmp_path / f"{package.stem}-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{package.stem}.dist-info/METADATA", value.as_bytes())
        archive.writestr(f"{package.stem}.dist-info/licenses/LICENSE", "Apache-2.0")
        archive.writestr(f"{other}/__init__.py", "")
        if name == "morphir-python":
            archive.writestr(
                f"{package.stem}.dist-info/entry_points.txt",
                "[console_scripts]\nmorphir-python = morphir_tools.cli:main\n",
            )
    with pytest.raises(ValueError, match="Unexpected bundled namespace"):
        validate_archive(package, path)


def test_cli_release_requires_the_complete_published_native_release() -> None:
    from scripts.check_distributions import (
        native_candidates_for,
        require_published_native,
    )

    complete = set(native_candidates_for("0.1.0"))
    require_published_native("0.1.0", complete | {"extra.whl"})
    with pytest.raises(ValueError, match="win_amd64"):
        require_published_native(
            "0.1.0", {name for name in complete if "win_amd64" not in name}
        )
    with pytest.raises(ValueError, match="before this CLI"):
        require_published_native("0.1.0", set())
