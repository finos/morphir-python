import pytest
import json
from morphir.ir.name import from_string as name
from morphir.ir.path import from_string as path
from morphir.ir.fqname import FQName
from morphir.ir.literal import IntegerLiteral, StringLiteral
from morphir.ir.distribution import PackageInfo
from morphir.ir.json import encode

class TestJsonEncoding:
    def test_name_encoding(self):
        n = name("MyName")
        # Canonical: ["my", "name"] -> "my-name" in string context?
        # or list context?
        # Current encoder uses to_string -> "my-name" (kebab)
        assert encode(n) == "my-name"

    def test_path_encoding(self):
        p = path("My/Path")
        # Canonical: "my/path"
        assert encode(p) == "my/path"

    def test_fqname_encoding(self):
        fqn = FQName.from_string("Morphir/SDK:Basics#Int")
        # Canonical: "morphir/sdk:basics#int"
        assert encode(fqn) == "morphir/sdk:basics#int"

    def test_literal_encoding(self):
        l = IntegerLiteral(42)
        # { "IntegerLiteral": { "value": 42 } }
        assert encode(l) == {"IntegerLiteral": {"value": 42}}
        
        s = StringLiteral("hello")
        assert encode(s) == {"StringLiteral": {"value": "hello"}}

    def test_package_info_encoding(self):
        pi = PackageInfo(path("my/pkg"), "1.0.0")
        expected = {
            "name": "my/pkg",
            "version": "1.0.0"
        }
        assert encode(pi) == expected

    def test_document_encoding(self):
        from morphir.ir.document import DocString, DocInt, DocObject
        from morphir.ir.literal import DocumentLiteral
        
        # Test basic DocString
        doc_s = DocString("foo")
        assert encode(doc_s) == {"DocString": "foo"}
        
        # Test DocInt
        doc_i = DocInt(99)
        assert encode(doc_i) == {"DocInt": 99}
        
        # Test nested DocObject
        doc_obj = DocObject({"k": doc_i})
        assert encode(doc_obj) == {"DocObject": {"k": {"DocInt": 99}}}
        
        # Test DocumentLiteral
        lit = DocumentLiteral(doc_obj)
        expected = {
            "DocumentLiteral": {
                "value": {"DocObject": {"k": {"DocInt": 99}}}
            }
        }
        assert encode(lit) == expected

