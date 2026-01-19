"""Tests for the morphir-tools package."""

import morphir_tools


class TestMorphirToolsPackage:
    """Tests for the morphir-tools package initialization."""

    def test_version_is_defined(self) -> None:
        """The package should have a version attribute."""
        assert hasattr(morphir_tools, "__version__")

    def test_version_matches_expected(self, sample_version: str) -> None:
        """The version should match the expected value."""
        assert morphir_tools.__version__ == sample_version

    def test_version_is_string(self) -> None:
        """The version should be a string."""
        assert isinstance(morphir_tools.__version__, str)

    def test_version_follows_semver(self) -> None:
        """The version should follow semantic versioning format."""
        parts = morphir_tools.__version__.split(".")
        assert len(parts) >= 2, "Version should have at least major.minor"
        for part in parts:
            assert part.isdigit() or "-" in part or "+" in part
