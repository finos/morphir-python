from morphir.ir.access_controlled import Public
from morphir.ir.name import from_string as name
from morphir.ir.type import EMPTY_TYPE_ATTRIBUTES, Unit, Variable
from morphir.ir.type_def import CustomTypeDefinition
from morphir.ir.type_spec import TypeAliasSpecification


def test_type_alias_spec():
    unit_type = Unit(EMPTY_TYPE_ATTRIBUTES)
    spec = TypeAliasSpecification(type_params=[], tpe=unit_type)
    assert spec.tpe == unit_type
    assert spec.type_params == []


def test_custom_type_def():
    # type Option a = Some a | None
    # Constructors: Dict[Name, List[Tuple[Name, Type]]]
    # Actually Constructors is Dict[Name, ConstructorArgs]
    # ConstructorArgs is List[Tuple[Name, Type]]
    # This implies labeled arguments for constructors?
    # Usually sum types are like `Some(a)`.
    # Getting constructor args as (Name, Type) suggests record-like args or positional with names?
    # In Morphir, constructor args are named.

    var_a = Variable(EMPTY_TYPE_ATTRIBUTES, name("a"))

    constructors = {name("Some"): [(name("value"), var_a)], name("None"): []}

    defn = CustomTypeDefinition(
        type_params=[name("a")], constructors=Public(constructors)
    )

    assert defn.type_params == [name("a")]
    assert isinstance(defn.constructors, Public)
    assert defn.constructors.value[name("Some")][0][1] == var_a
