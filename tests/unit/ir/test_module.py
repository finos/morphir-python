from morphir.ir.access_controlled import Private
from morphir.ir.documented import Documented
from morphir.ir.module import Definition, Specification
from morphir.ir.name import from_string as name


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
    from morphir.ir.type import TypeAttributes
    from morphir.ir.type import Unit as UnitType
    from morphir.ir.value import Definition as ValueDef
    from morphir.ir.value import Unit, ValueAttributes

    val_def = ValueDef(
        input_types=[],
        output_type=UnitType(TypeAttributes()),
        body=Unit(ValueAttributes()),
    )
    doc_val = Documented(doc="A Value", value=val_def)
    access_val = Private(doc_val)

    defn.values[name("myVal")] = access_val
    assert defn.values[name("myVal")] == access_val
