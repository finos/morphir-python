from morphir.ir.documented import Documented


def test_documented_creation():
    d = Documented(doc="This is a test", value=123)
    assert d.doc == "This is a test"
    assert d.value == 123


def test_documented_no_doc():
    d = Documented(doc=None, value="value")
    assert d.doc is None
    assert d.value == "value"
