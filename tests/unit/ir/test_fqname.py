import pytest
from morphir.ir.name import from_string as name_from_string
from morphir.ir.path import from_string as path_from_string
from morphir.ir.fqname import FQName

class TestFQName:
    def test_creation(self):
        fqn = FQName.from_string("Morphir.SDK:Basics:Int")
        assert fqn.package_path == path_from_string("Morphir.SDK")
        assert fqn.module_path == path_from_string("Basics")
        assert fqn.local_name == name_from_string("Int")

    def test_to_string(self):
        fqn = FQName.from_string("Morphir.SDK:Basics:Int")
        assert fqn.to_string() == "Morphir.SDK:Basics:int"

    def test_fqn_constructor(self):
        fqn = FQName.fqn("Morphir.SDK", "Basics", "Int")
        assert fqn.package_path == path_from_string("Morphir.SDK")
