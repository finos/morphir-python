"""Tests for the morphir core library package."""

from importlib.metadata import distribution

import morphir


class TestMorphirPackage:
    """Tests for the morphir package initialization."""

    def test_version_is_defined(self) -> None:
        """The package should have a version attribute."""
        assert hasattr(morphir, "__version__")

    def test_core_has_no_runtime_dependencies_or_commands(self) -> None:
        """Library-only installs must not pull in CLI dependencies or scripts."""
        package = distribution("morphir")
        assert not package.requires
        assert not package.entry_points

    def test_version_matches_expected(self, sample_version: str) -> None:
        """The version should match the expected value."""
        assert morphir.__version__ == sample_version

    def test_version_is_string(self) -> None:
        """The version should be a string."""
        assert isinstance(morphir.__version__, str)

    def test_version_follows_semver(self) -> None:
        """The version should follow semantic versioning format."""
        parts = morphir.__version__.split(".")
        assert len(parts) >= 2, "Version should have at least major.minor"
        for part in parts:
            assert part.isdigit() or "-" in part or "+" in part


class TestMorphirIR:
    """Tests for the morphir.ir submodule."""

    def test_ir_module_is_importable(self) -> None:
        """The ir submodule should be importable."""
        from morphir import ir

        assert ir is not None

    def test_ir_module_has_all(self) -> None:
        """The ir submodule should have an __all__ attribute."""
        from morphir import ir

        assert hasattr(ir, "__all__")
        assert isinstance(ir.__all__, list)
