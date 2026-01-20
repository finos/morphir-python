import pytest
from morphir.ir.name import Name, from_string, to_camel_case, to_snake_case, to_title_case, to_kebab_case, to_list

class TestName:
    def test_from_string_basic(self):
        assert to_list(from_string("foo")) == ["foo"]
        assert to_list(from_string("Foo")) == ["foo"]
        assert to_list(from_string("fooBar")) == ["foo", "bar"]
        assert to_list(from_string("FooBar")) == ["foo", "bar"]
        assert to_list(from_string("foo_bar")) == ["foo", "bar"]
        assert to_list(from_string("foo-bar")) == ["foo", "bar"]
        assert to_list(from_string("foo.bar")) == ["foo", "bar"]
        assert to_list(from_string("foo bar")) == ["foo", "bar"]

    def test_from_string_complex(self):
        # Improved regex handles acronyms: JSONResponse -> json, response
        assert to_list(from_string("JSONResponse")) == ["json", "response"]
        assert to_list(from_string("UserId")) == ["user", "id"]
        assert to_list(from_string("elm-stuff")) == ["elm", "stuff"]
        
        # Test new delimiters (colon, hash) for FQName safety
        assert to_list(from_string("Morphir:SDK:Int")) == ["morphir", "sdk", "int"]
        assert to_list(from_string("Morphir#Int")) == ["morphir", "int"]
        
    def test_to_camel_case(self):
        name = from_string("foo_bar")
        assert to_camel_case(name) == "fooBar"
        
        name = from_string("FooBar")
        assert to_camel_case(name) == "fooBar"

    def test_to_title_case(self):
        name = from_string("foo_bar")
        assert to_title_case(name) == "FooBar"
        
    def test_to_snake_case(self):
        name = from_string("fooBar")
        assert to_snake_case(name) == "foo_bar"
        
    def test_to_kebab_case(self):
        name = from_string("fooBar")
        assert to_kebab_case(name) == "foo-bar"
