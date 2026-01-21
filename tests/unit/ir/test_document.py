from morphir.ir.document import (
    DocArray,
    DocBool,
    DocFloat,
    DocInt,
    DocNull,
    DocObject,
    DocString,
    array,
    bool_,
    float_,
    int_,
    null,
    object_,
    string,
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
    val = obj.fields["key"]
    assert isinstance(val, DocString)
    assert val.value == "val"


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
