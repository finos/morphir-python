import pytest
from morphir.ir.ref import DefRef, PointerRef, FileWithDefs

def test_def_ref():
    ref = DefRef(name="my-def")
    assert ref.name == "my-def"

def test_pointer_ref():
    ref = PointerRef(pointer=["defs", "my-def"])
    assert ref.pointer == ["defs", "my-def"]

def test_pointer_ref_from_string():
    ref = PointerRef.from_string("#/defs/my-def")
    assert ref.pointer == ["defs", "my-def"]

    with pytest.raises(ValueError):
        PointerRef.from_string("invalid-pointer")

def test_file_with_defs():
    file = FileWithDefs(
        content={"foo": 1},
        defs={"my-def": 42}
    )
    assert file.content == {"foo": 1}
    assert file.defs["my-def"] == 42
