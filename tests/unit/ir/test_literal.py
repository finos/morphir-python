from decimal import Decimal

from morphir.ir.literal import (
    BoolLiteral,
    DecimalLiteral,
    IntegerLiteral,
    StringLiteral,
)


class TestLiteral:
    def test_bool_literal(self):
        lit = BoolLiteral(True)
        assert lit.value is True

    def test_string_literal(self):
        lit = StringLiteral("hello")
        assert lit.value == "hello"

    def test_integer_literal(self):
        lit = IntegerLiteral(42)
        assert lit.value == 42

    def test_decimal_literal(self):
        d = Decimal("123.456")
        lit = DecimalLiteral(d)
        assert lit.value == d

    def test_document_literal(self):
        from morphir.ir.document import DocString
        from morphir.ir.literal import DocumentLiteral

        doc = DocString("json")
        lit = DocumentLiteral(doc)
        assert lit.value == doc
        assert isinstance(lit.value, DocString)
