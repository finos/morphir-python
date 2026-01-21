from dataclasses import fields, is_dataclass
from typing import Any

from .decorations import (
    DecorationFormat,
    DecorationValuesFile,
    LayerManifest,
    SchemaRef,
)
from .distribution import PackageInfo
from .document import DocArray, DocBool, DocFloat, DocInt, DocNull, DocObject, DocString
from .fqname import FQName
from .literal import (
    BoolLiteral,
    CharLiteral,
    DecimalLiteral,
    DocumentLiteral,
    FloatLiteral,
    IntegerLiteral,
    StringLiteral,
)
from .name import Name
from .name import to_string as name_to_string
from .path import Path
from .path import to_string as path_to_string

# Placeholder for full implementation.
# This will eventually contain robust encoders/decoders for all IR types.


class MorphirJSONEncoder:
    def encode(self, obj: Any) -> Any:
        if isinstance(obj, Name):
            return name_to_string(obj)
        if isinstance(obj, Path):
            return path_to_string(obj)
        if isinstance(obj, FQName):
            return obj.to_string()
        if isinstance(obj, PackageInfo):
            return {"name": path_to_string(obj.name), "version": obj.version}

        # Decorations Encoding (Basic Dataclass Support handles these mostly, but explicit checks help)
        if is_dataclass(obj) and isinstance(
            obj, (DecorationFormat, LayerManifest, DecorationValuesFile, SchemaRef)
        ):
            # Use standard dataclass conversion but recursively encode values
            return {f.name: self.encode(getattr(obj, f.name)) for f in fields(obj)}

        # Document Encoding
        if isinstance(obj, DocNull):
            return {"DocNull": {}}
        if isinstance(obj, DocBool):
            return {"DocBool": obj.value}
        if isinstance(obj, DocInt):
            return {"DocInt": obj.value}
        if isinstance(obj, DocFloat):
            return {"DocFloat": obj.value}
        if isinstance(obj, DocString):
            return {"DocString": obj.value}
        if isinstance(obj, DocArray):
            return {"DocArray": [self.encode(elem) for elem in obj.elements]}
        if isinstance(obj, DocObject):
            return {"DocObject": {k: self.encode(v) for k, v in obj.fields.items()}}

        # Literal Encoding
        if isinstance(
            obj,
            (
                BoolLiteral,
                CharLiteral,
                StringLiteral,
                IntegerLiteral,
                FloatLiteral,
                DecimalLiteral,
            ),
        ):
            # { "IntegerLiteral": { "value": 42 } }
            type_name = type(obj).__name__
            return {
                type_name: {
                    "value": obj.value
                    if not isinstance(obj, DecimalLiteral)
                    else str(obj.value)
                }
            }
        if isinstance(obj, DocumentLiteral):
            # DocumentLiteral wraps a Document
            return {"DocumentLiteral": {"value": self.encode(obj.value)}}
        if is_dataclass(obj):
            # Generic fallback for simple dataclasses
            # Real implementation needs to handle tagged unions (Value, Type, Pattern) specifically
            return {f.name: self.encode(getattr(obj, f.name)) for f in fields(obj)}

        if isinstance(obj, list):
            return [self.encode(item) for item in obj]
        if isinstance(obj, dict):
            return {k: self.encode(v) for k, v in obj.items()}

        return obj


def encode(obj: Any) -> Any:
    return MorphirJSONEncoder().encode(obj)
