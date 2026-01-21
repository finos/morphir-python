import pytest
from morphir.ir.document import (
    DocNull, DocBool, DocInt, DocFloat, DocString, DocArray, DocObject,
    null, bool_, int_, float_, string, array, object_
)

def test_document_variants():
    assert DocNull() == DocNull()
    assert DocBool(True).value is True
    assert DocInt(42).value == 42
    assert DocFloat(3.14).value == 3.14
    assert DocString("test").value == "test"
    
    arr = DocArray([DocInt(1), DocInt(2)])
    assert arr.elements == [DocInt(1), DocInt(2)]

    obj = DocObject({"key": DocString("val")})
    assert obj.fields["key"].value == "val"

def test_document_helpers():
    assert null() == DocNull()
    assert bool_(False) == DocBool(False)
    assert int_(10) == DocInt(10)
    assert float_(1.5) == DocFloat(1.5)
    assert string("s") == DocString("s")
    
    arr = array([int_(1)])
    assert isinstance(arr, DocArray)
    assert arr.elements[0] == DocInt(1)
    
    obj = object_({"k": string("v")})
    assert isinstance(obj, DocObject)
    assert obj.fields["k"] == DocString("v")
