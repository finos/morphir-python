"""Morphir IR v4 model (draft upstream).

IR v4 is not frozen in finos/morphir. The JSON codec in `morphir.ir.v4.codec` is a
draft pinned to finos/morphir commit efa36060.
"""

from . import incompleteness, module, package
from .access_controlled import AccessControlled
from .decorations import (
    DecorationFormat,
    DecorationValuesFile,
    LayerManifest,
    SchemaRef,
)
from .distribution import (
    ApplicationDistribution,
    Distribution,
    EntryPoint,
    EntryPointKind,
    LibraryDistribution,
    PackageInfo,
    SpecsDistribution,
)
from .document import (
    DocArray,
    DocBool,
    DocFloat,
    DocInt,
    DocNull,
    DocObject,
    DocString,
    Document,
)
from .documented import Documented
from .fqname import FQName
from .incompleteness import (
    DeletedDuringRefactor,
    DraftIncompleteness,
    HoleIncompleteness,
    HoleReason,
    Incompleteness,
    TypeMismatch,
    UnresolvedReference,
)
from .literal import (
    BoolLiteral,
    CharLiteral,
    DecimalLiteral,
    FloatLiteral,
    IntegerLiteral,
    Literal,
    StringLiteral,
)
from .meta import FileMeta, SourceRange
from .name import Name
from .path import Path
from .qname import QName
from .ref import DefRef, FileWithDefs, PointerRef, Ref
from .type import Field, Type, TypeAttributes
from .type_constraints import TypeConstraints
from .type_def import Definition as TypeDefinition
from .type_spec import Specification as TypeSpecification
from .value import Definition as ValueDefinition
from .value import (
    ExternalBinding,
    ExternalBody,
    IncompleteBody,
    NativeBody,
    NativeHint,
    NativeInfo,
    Pattern,
    Value,
    ValueAttributes,
    ValueDefinitionBody,
)
from .value import Specification as ValueSpecification

__all__ = [
    "AccessControlled",
    "ApplicationDistribution",
    "BoolLiteral",
    "CharLiteral",
    "DecimalLiteral",
    "DecorationFormat",
    "DecorationValuesFile",
    "DefRef",
    "DeletedDuringRefactor",
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
    "DraftIncompleteness",
    "EntryPoint",
    "EntryPointKind",
    "ExternalBinding",
    "ExternalBody",
    "FQName",
    "Field",
    "FileMeta",
    "FileWithDefs",
    "FloatLiteral",
    "HoleIncompleteness",
    "HoleReason",
    "IncompleteBody",
    "Incompleteness",
    "IntegerLiteral",
    "LayerManifest",
    "LibraryDistribution",
    "Literal",
    "Name",
    "NativeBody",
    "NativeHint",
    "NativeInfo",
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
    "TypeMismatch",
    "TypeSpecification",
    "UnresolvedReference",
    "Value",
    "ValueAttributes",
    "ValueDefinition",
    "ValueDefinitionBody",
    "ValueSpecification",
    "incompleteness",
    "module",
    "package",
]
