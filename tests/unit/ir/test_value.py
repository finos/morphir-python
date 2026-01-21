from morphir.ir.fqname import FQName
from morphir.ir.literal import IntegerLiteral
from morphir.ir.name import from_string as name
from morphir.ir.value import (
    Apply,
    Constructor,
    Lambda,
    List,
    LiteralValue,
    Tuple,
    ValueAttributes,
    Variable,
    WildcardPattern,
)


class TestValue:
    def test_literal_value(self):
        v = LiteralValue(ValueAttributes(), IntegerLiteral(10))
        assert isinstance(v.literal, IntegerLiteral)
        assert v.literal.value == 10

    def test_variable(self):
        v = Variable(ValueAttributes(), name("x"))
        assert v.name == name("x")

    def test_apply(self):
        func = Variable(ValueAttributes(), name("f"))
        arg = Variable(ValueAttributes(), name("x"))
        app = Apply(ValueAttributes(), func, arg)
        assert app.function == func
        assert app.argument == arg

    def test_lambda_pattern(self):
        pattern = WildcardPattern(ValueAttributes())
        body = Variable(ValueAttributes(), name("x"))
        lam = Lambda(ValueAttributes(), pattern, body)
        assert lam.pattern == pattern
        assert lam.body == body

    def test_constructor(self):
        fqn = FQName.from_string("Morphir.SDK:Maybe#Just")
        c = Constructor(ValueAttributes(), fqn)
        assert c.fqname == fqn

    def test_recursive_structures(self):
        # List of Tuples
        tup = Tuple(
            ValueAttributes(),
            [
                LiteralValue(ValueAttributes(), IntegerLiteral(1)),
                Variable(ValueAttributes(), name("a")),
            ],
        )
        lst = List(ValueAttributes(), [tup])
        assert len(lst.elements) == 1
        assert isinstance(lst.elements[0], Tuple)
