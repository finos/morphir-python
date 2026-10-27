"""Tests for the morphir-python package."""

from importlib.metadata import distribution, version

import morphir_tools


class TestMorphirToolsPackage:
    """Tests for the morphir-python package initialization."""

    def test_version_is_defined(self) -> None:
        """The package should have a version attribute."""
        assert hasattr(morphir_tools, "__version__")

    def test_version_matches_expected(self, sample_version: str) -> None:
        """The version should match the expected value."""
        assert morphir_tools.__version__ == sample_version

    def test_installed_distribution_name(self) -> None:
        """The tools import belongs to the morphir-python distribution."""
        assert version("morphir-python") == morphir_tools.__version__

    def test_installed_console_command(self) -> None:
        """The published command is named morphir-python."""
        commands = {
            entry.name: entry.value
            for entry in distribution("morphir-python").entry_points
            if entry.group == "console_scripts"
        }
        assert commands == {"morphir-python": "morphir_tools.cli:main"}

    def test_version_is_string(self) -> None:
        """The version should be a string."""
        assert isinstance(morphir_tools.__version__, str)

    def test_version_follows_semver(self) -> None:
        """The version should follow semantic versioning format."""
        parts = morphir_tools.__version__.split(".")
        assert len(parts) >= 2, "Version should have at least major.minor"
        for part in parts:
            assert part.isdigit() or "-" in part or "+" in part
