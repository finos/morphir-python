import pytest
from typing import cast
from morphir.ir.name import from_string as name
from morphir.ir.fqname import FQName
from morphir.ir.type import (
    Variable,
    Reference,
    Tuple,
    Record,
    ExtensibleRecord,
    Function,
    Unit,
    Field,
    TypeAttributes,
    EMPTY_TYPE_ATTRIBUTES,
    map_attributes
)

def test_variable_creation():
    v = Variable(EMPTY_TYPE_ATTRIBUTES, name("a"))
    assert v.name == name("a")
    assert v.attributes == EMPTY_TYPE_ATTRIBUTES

def test_reference_creation():
    fqn = FQName.from_string("Morphir.SDK:Int")
    r = Reference(EMPTY_TYPE_ATTRIBUTES, fqn) # No args
    assert r.fqname == fqn
    assert r.args == []

def test_nested_creation():
    # List Int
    list_fqn = FQName.from_string("Morphir.SDK:List")
    int_fqn = FQName.from_string("Morphir.SDK:Int")
    int_type = Reference(EMPTY_TYPE_ATTRIBUTES, int_fqn)
    
    list_int = Reference(EMPTY_TYPE_ATTRIBUTES, list_fqn, [int_type])
    assert list_int.fqname == list_fqn
    assert len(list_int.args) == 1
    assert list_int.args[0] == int_type

def test_map_attributes():
    # Setup: Create a type with empty attributes
    # Variable "a"
    v = Variable(EMPTY_TYPE_ATTRIBUTES, name("a"))
    
    # Transformation: Add an extension "tested": True
    ext_key = FQName.from_string("Test:tested")
    
    def transform(attr: TypeAttributes) -> TypeAttributes:
        new_ext = attr.extensions.copy()
        new_ext[ext_key] = True
        return TypeAttributes(source=None, constraints=None, extensions=new_ext)
        
    v2 = map_attributes(v, transform)
    assert isinstance(v2, Variable) # type: ignore
    assert v2.name == name("a")
    assert v2.attributes.extensions[ext_key] is True
    
    # Test recursive mapping
    # List a
    list_fqn = FQName.from_string("Morphir.SDK:List")
    list_a = Reference(EMPTY_TYPE_ATTRIBUTES, list_fqn, [v])
    
    list_a2 = map_attributes(list_a, transform)
    
    # Check top level
    assert isinstance(list_a2, Reference)
    assert list_a2.attributes.extensions[ext_key] is True
    
    # Check inner type
    v2_inner = list_a2.args[0]
    assert isinstance(v2_inner, Variable)
    assert v2_inner.attributes.extensions[ext_key] is True

def test_function_type():
    int_t = Reference(EMPTY_TYPE_ATTRIBUTES, FQName.from_string("Morphir.SDK:Int"))
    f = Function(EMPTY_TYPE_ATTRIBUTES, argument_type=int_t, return_type=int_t)
    assert f.argument_type == int_t
    assert f.return_type == int_t
