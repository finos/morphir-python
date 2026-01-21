import pytest
from morphir.ir.path import from_string as path
from morphir.ir.distribution import (
    PackageInfo,
    LibraryDistribution,
    SpecsDistribution,
    ApplicationDistribution
)
from morphir.ir.package import (
    Specification as PackageSpec,
    Definition as PackageDef
)

class TestDistribution:
    def test_package_info(self):
        pi = PackageInfo(path("my/pkg"), "1.0.0")
        assert pi.name == path("my/pkg")
        assert pi.version == "1.0.0"

    def test_library_distribution(self):
        pi = PackageInfo(path("lib/pkg"), "1.0.0")
        lib = LibraryDistribution(
            package=pi,
            definition=PackageDef(),
            dependencies={}
        )
        assert isinstance(lib, LibraryDistribution)
        assert lib.package == pi

    def test_app_distribution(self):
        pi = PackageInfo(path("app/pkg"), "1.0.0")
        app = ApplicationDistribution(
            package=pi,
            definition=PackageDef(),
            dependencies={},
            entry_points={}
        )
        assert isinstance(app, ApplicationDistribution)
