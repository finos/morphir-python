import pytest
from morphir.ir.path import from_string as path
from morphir.ir.module import Definition as ModuleDef
from morphir.ir.package import Specification, Definition
from morphir.ir.access_controlled import Public, Private

def test_package_specification():
    spec = Specification()
    assert spec.modules == {}

def test_package_definition():
    defn = Definition()
    assert defn.modules == {}
    
    # Add a module
    mod_path = path("My.Module")
    mod_def = ModuleDef(doc="Test Module")
    defn.modules[mod_path] = Public(mod_def)
    
    assert defn.modules[mod_path].value.doc == "Test Module"
