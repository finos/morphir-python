import pytest
from decimal import Decimal
from morphir.ir.literal import (
    BoolLiteral,
    CharLiteral,
    StringLiteral,
    IntegerLiteral,
    FloatLiteral,
    DecimalLiteral
)

class TestLiteral:
    def test_bool_literal(self):
        l = BoolLiteral(True)
        assert l.value is True

    def test_string_literal(self):
        l = StringLiteral("hello")
        assert l.value == "hello"

    def test_integer_literal(self):
        l = IntegerLiteral(42)
        assert l.value == 42
        
    def test_decimal_literal(self):
        d = Decimal("123.456")
        l = DecimalLiteral(d)
        assert l.value == d
