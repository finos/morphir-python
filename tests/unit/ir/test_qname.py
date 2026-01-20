import pytest
from morphir.ir.name import from_string as name_from_string
from morphir.ir.path import from_string as path_from_string
from morphir.ir.qname import QName

class TestQName:
    def test_creation(self):
        qn = QName.from_string("Morphir.SDK:Int")
        assert qn.module_path == path_from_string("Morphir.SDK")
        assert qn.local_name == name_from_string("Int")

    def test_to_string(self):
        qn = QName.from_string("Morphir.SDK:Int")
        assert qn.to_string() == "Morphir.SDK:int" # camelCase for local name

    def test_from_name(self):
        n = name_from_string("foo")
        qn = QName.from_name(n)
        assert len(qn.module_path) == 0
        assert qn.local_name == n
