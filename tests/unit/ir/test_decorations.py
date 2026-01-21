from morphir.ir.decorations import (
    DecorationFormat,
    DecorationValuesFile,
    SchemaRef,
    deep_merge,
    merge_decoration_values,
)
from morphir.ir.json import encode


class TestDecorations:
    def test_schema_ref(self):
        ref = SchemaRef(
            display_name="Docs", local_path="schemas/doc.json", entry_point="Doc#Main"
        )
        assert ref.display_name == "Docs"

    def test_decoration_format(self):
        fmt = DecorationFormat(format_version="4.0.0", layers=["core", "user"])
        assert fmt.layers == ["core", "user"]

    def test_merge_decoration_values(self):
        # Layer 0 (Base)
        layer0 = {
            "node1": {"summary": "Base Summary", "details": ["base"]},
            "node2": {"tag": "base"},
        }

        # Layer 10 (Override)
        layer10 = {
            "node1": {
                "summary": "Override Summary",
                "details": ["extra"],
            },  # details should merge? dict merge logic check
            # deep_merge logic:
            # list + list -> concat
            # dict + dict -> recursive merge
        }

        # If details is list, "base" + "extra" = ["base", "extra"]

        merged = merge_decoration_values([(0, layer0), (10, layer10)])

        assert merged["node1"]["summary"] == "Override Summary"
        assert merged["node1"]["details"] == ["base", "extra"]  # concat
        assert merged["node2"]["tag"] == "base"  # unchanged

    def test_deep_merge_simple(self):
        assert deep_merge(1, 2) == 2
        assert deep_merge("a", "b") == "b"
        assert deep_merge([1], [2]) == [1, 2]
        assert deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}
        assert deep_merge({"a": 1}, {"a": 2}) == {"a": 2}

    def test_json_encoding(self):
        # Smoke test for JSON encoding
        d = DecorationValuesFile(
            format_version="4.0.0",
            decoration_type="doc",
            layer="user",
            values={"foo": 1},
        )
        json_out = encode(d)
        assert json_out["values"]["foo"] == 1
