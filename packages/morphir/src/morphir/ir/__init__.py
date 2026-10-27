"""Morphir IR.

The default model is IR v4 (`morphir.ir.v4`); every name here is the same object
as its `morphir.ir.v4` counterpart. Format 3.0.0 lives in `morphir.ir.v3`.
"""

from . import module, package
from .v4.access_controlled import AccessControlled
from .v4.decorations import (
    DecorationFormat,
    DecorationValuesFile,
    LayerManifest,
    SchemaRef,
)
from .v4.distribution import (
    ApplicationDistribution,
    Distribution,
    EntryPoint,
    EntryPointKind,
    LibraryDistribution,
    PackageInfo,
    SpecsDistribution,
)
from .v4.document import (
    DocArray,
    DocBool,
    DocFloat,
    DocInt,
    DocNull,
    DocObject,
    DocString,
    Document,
)
from .v4.documented import Documented
from .v4.fqname import FQName
from .v4.literal import (
    BoolLiteral,
    CharLiteral,
    DecimalLiteral,
    FloatLiteral,
    IntegerLiteral,
    Literal,
    StringLiteral,
)
from .v4.meta import FileMeta, SourceRange
from .v4.name import Name
from .v4.path import Path
from .v4.qname import QName
from .v4.ref import DefRef, FileWithDefs, PointerRef, Ref
from .v4.type import Field, Type, TypeAttributes
from .v4.type_constraints import TypeConstraints
from .v4.type_def import Definition as TypeDefinition
from .v4.type_spec import Specification as TypeSpecification
from .v4.value import Definition as ValueDefinition
from .v4.value import Pattern, Value, ValueAttributes
from .v4.value import Specification as ValueSpecification

__all__ = [
    "AccessControlled",
    "ApplicationDistribution",
    "BoolLiteral",
    "CharLiteral",
    "DecimalLiteral",
    "DecorationFormat",
    "DecorationValuesFile",
    "DefRef",
    "Distribution",
    "DocArray",
    "DocBool",
    "DocFloat",
    "DocInt",
    "DocNull",
    "DocObject",
    "DocString",
    "Document",
    "Documented",
    "EntryPoint",
    "EntryPointKind",
    "FQName",
    "Field",
    "FileMeta",
    "FileWithDefs",
    "FloatLiteral",
    "IntegerLiteral",
    "LayerManifest",
    "LibraryDistribution",
    "Literal",
    "Name",
    "PackageInfo",
    "Path",
    "Pattern",
    "PointerRef",
    "QName",
    "Ref",
    "SchemaRef",
    "SourceRange",
    "SpecsDistribution",
    "StringLiteral",
    "Type",
    "TypeAttributes",
    "TypeConstraints",
    "TypeDefinition",
    "TypeSpecification",
    "Value",
    "ValueAttributes",
    "ValueDefinition",
    "ValueSpecification",
    "module",
    "package",
]
