import pytest
from morphir.ir.name import from_string as name_from_string
from morphir.ir.path import Path, from_string, to_string, is_prefix_of, append, concat

class TestPath:
    def test_from_string(self):
        path = from_string("Morphir.IR.Name")
        assert len(path) == 3
        assert path[0] == name_from_string("morphir")
        assert path[1] == name_from_string("IR") # "IR" -> ["i", "r"] 
        # Wait, IR usually stays as ir if parsed as Name("IR"). 
        # Name("IR") -> ["ir"] or ["i", "r"]?
        # My current regex "IR" -> ["ir"] because I didn't implement full specialized logic yet?
        # Let's check Name implementation logic again.
        # implementation: parts = re.findall(r'[A-Za-z][a-z0-9]*|[0-9]+', word)
        # "IR" -> "I", "R"? No. 
        # python re.findall(r'[A-Za-z][a-z0-9]*|[0-9]+', "IR") -> ['I', 'R']
        # Because R is uppercase, it matches [A-Za-z] but consumes only one char because following is not [a-z0-9]*
        
        # So "IR" -> ["i", "r"]
        # In Gleam "IR" -> ["i", "r"] ? 
        # Gleam: split_on_boundaries creates ["i", "r"] if they are uppercase
        pass 
        
    def test_path_string_conversion(self):
        p = from_string("Morphir.SDK")
        assert to_string(p) == "Morphir.SDK"
        # Name("SDK") -> ["s", "d", "k"] -> Title case -> Sdk? No.
        # "S" -> "S", "D" -> "D", "K" -> "K". 
        # to_title_case(["s", "d", "k"]) -> "SDK"
        
        # Let's verify what from_string does to "SDK"
        # "SDK" -> re.findall -> ['S', 'D', 'K']
        # Name(['s', 'd', 'k'])
        # to_title_case -> "S" + "D" + "K" -> "SDK"
        
        assert to_string(p) == "Morphir.SDK"

    def test_is_prefix_of(self):
        p1 = from_string("Morphir.SDK")
        p2 = from_string("Morphir.SDK.String")
        
        assert is_prefix_of(p1, p2)
        assert not is_prefix_of(p2, p1)
        assert is_prefix_of(p1, p1)
