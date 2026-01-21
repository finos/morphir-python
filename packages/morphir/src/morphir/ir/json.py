from typing import Any, Dict, List, Union, cast
from enum import Enum
from dataclasses import asdict, is_dataclass, fields

from .name import Name, from_string as name_from_string, to_string as name_to_string
from .path import Path, from_string as path_from_string, to_string as path_to_string
from .fqname import FQName
from .literal import Literal, BoolLiteral, CharLiteral, StringLiteral, IntegerLiteral, FloatLiteral, DecimalLiteral
from .type import Type, Variable, Reference as TypeRef
from .value import Value, LiteralValue, Variable as ValueVar
from .distribution import Distribution, PackageInfo

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
            return {
                "name": path_to_string(obj.name),
                "version": obj.version
            }
        if isinstance(obj, (BoolLiteral, CharLiteral, StringLiteral, IntegerLiteral, FloatLiteral, DecimalLiteral)):
             # { "IntegerLiteral": { "value": 42 } }
            type_name = type(obj).__name__
            return {
                type_name: {
                    "value": obj.value if not isinstance(obj, DecimalLiteral) else str(obj.value)
                }
            }
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
