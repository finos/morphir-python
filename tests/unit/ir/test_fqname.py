from morphir.ir.fqname import FQName
from morphir.ir.name import from_string as name_from_string
from morphir.ir.path import from_string as path_from_string


class TestFQName:
    def test_creation(self):
        # Canonical input
        fqn = FQName.from_string("Morphir.SDK:Start#Do-Something")
        assert fqn.package_path == path_from_string("Morphir.SDK")
        assert fqn.module_path == path_from_string("Start")
        assert fqn.local_name == name_from_string("Do-Something")

    def test_to_string(self):
        # Canonical: Package:Module#Name
        fqn = FQName.from_string("Morphir/SDK:Basics#Int")
        assert fqn.to_string() == "morphir/sdk:basics#int"

        # Test camelCase input becoming kebab in canonical string
        fqn2 = FQName.from_string("Morphir:SDK#makeTuple")
        assert fqn2.to_string() == "morphir:sdk#make-tuple"

    def test_fqn_constructor(self):
        fqn = FQName.fqn("Morphir.SDK", "Basics", "Int")
        assert fqn.package_path == path_from_string("Morphir.SDK")
        # Canonical string output check
        assert fqn.to_string() == "morphir/sdk:basics#int"
