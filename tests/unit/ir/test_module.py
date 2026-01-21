import pytest
from typing import cast
from morphir.ir.name import from_string as name
from morphir.ir.module import Specification, Definition
from morphir.ir.documented import Documented
from morphir.ir.access_controlled import Public, Private

def test_module_specification():
    spec = Specification(doc="My Module")
    assert spec.doc == "My Module"
    assert spec.types == {}
    assert spec.values == {}

def test_module_definition():
    defn = Definition(doc="My Module Def")
    assert defn.doc == "My Module Def"
    assert defn.types == {}
    assert defn.values == {}
    
    # Test adding a private value
    # value spec/def are placeholders for now
    from morphir.ir.value import Definition as ValueDef, Unit, ValueAttributes
    from morphir.ir.type import Unit as UnitType, TypeAttributes
    
    val_def = ValueDef(
        input_types=[],
        output_type=UnitType(TypeAttributes()),
        body=Unit(ValueAttributes())
    )
    doc_val = Documented(doc="A Value", value=val_def)
    access_val = Private(doc_val)
    
    defn.values[name("myVal")] = access_val
    assert defn.values[name("myVal")] == access_val
