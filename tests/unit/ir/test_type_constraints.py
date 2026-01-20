import pytest
from morphir.ir.type_constraints import (
    TypeConstraints,
    Signed,
    Unsigned,
    FloatingPoint,
    Bounded,
    Decimal,
    StringConstraint,
    StringEncoding,
    CollectionConstraint
)

class TestTypeConstraints:
    def test_empty_constraints(self):
        tc = TypeConstraints()
        assert tc.numeric is None
        assert tc.string is None
        assert tc.collection is None
        assert tc.custom == []

    def test_numeric_constraints(self):
        s = Signed(32)
        tc = TypeConstraints(numeric=s)
        assert tc.numeric == s
        assert isinstance(tc.numeric, Signed) # type: ignore
        assert tc.numeric.bits == 32

        b = Bounded(min=1, max=10)
        tc_b = TypeConstraints(numeric=b)
        assert tc_b.numeric.min == 1
        assert tc_b.numeric.max == 10

    def test_string_constraints(self):
        sc = StringConstraint(encoding=StringEncoding.UTF8, min_length=1, max_length=100)
        tc = TypeConstraints(string=sc)
        assert tc.string.encoding == StringEncoding.UTF8
        assert tc.string.min_length == 1
        assert tc.string.max_length == 100

    def test_collection_constraints(self):
        cc = CollectionConstraint(unique_items=True)
        tc = TypeConstraints(collection=cc)
        assert tc.collection.unique_items is True
