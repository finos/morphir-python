"""Migrations between Morphir IR format 3 and IR v4.

`v3_to_v4` always succeeds for a valid v3 Library or Specs. `v4_to_v3` collects
every construct format 3 cannot represent in one pass and fails with all of them,
so users fix every problem at once. A v4 Specs becomes a v3 Specs (format 3.1.0);
a v4 Application has no v3 form. Nothing is invented or dropped, except:

- the package release version, which v3 cannot hold (``package_version_dropped``);
- value source locations, only when ``drop_source_locations=True``
  (``source_location_dropped``);
- value-definition input attributes, only when ``drop_input_attributes=True`` or
  through `drop_input_attributes` (``input_attributes_dropped``). v4 JSON spells
  an input as a bare type, so an input whose attributes hold more than its
  declared type cannot be encoded without this drop.

The mapping follows morphir-moonbit ``migration/v3/migration.mbt``, adjusted for
the Python v4 model. Diagnostic codes are defined in `morphir.ir.diagnostics` and
may be renamed when finos bead ``morphir-diwy`` settles the ecosystem rules.

Example:
    >>> from morphir.ir import v3
    >>> lib = v3.Library(v3.Path(()), v3.package.Definition())
    >>> result = v3_to_v4(lib, package_version="1.2.0")
    >>> result.value.package.version
    '1.2.0'
"""

from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass, field
from typing import cast, overload

from . import diagnostics as d
from .diagnostics import Diagnostic, Location
from .v3 import access_controlled as ac3
from .v3 import distribution as dist3
from .v3 import documented as doc3
from .v3 import fqname as fq3
from .v3 import literal as lit3
from .v3 import module as mod3
from .v3 import name as name3
from .v3 import package as pkg3
from .v3 import path as path3
from .v3 import type as t3
from .v3 import value as v3
from .v4 import access_controlled as ac4
from .v4 import annotation as ann4
from .v4 import distribution as dist4
from .v4 import documented as doc4
from .v4 import fqname as fq4
from .v4 import literal as lit4
from .v4 import module as mod4
from .v4 import name as name4
from .v4 import package as pkg4
from .v4 import path as path4
from .v4 import type as t4
from .v4 import type_def as td4
from .v4 import type_spec as ts4
from .v4 import value as v4


@dataclass(frozen=True)
class Ok[T]:
    """A successful migration, with any warnings about dropped information."""

    value: T
    warnings: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True)
class Err:
    """A failed migration holding every diagnostic found."""

    diagnostics: tuple[Diagnostic, ...]


type MigrationResult[T] = Ok[T] | Err


# --- v3 -> v4 ---


def _name_up(n: name3.Name) -> name4.Name:
    return name4.Name(tuple(n))


def _path_up(p: path3.Path) -> path4.Path:
    return path4.Path(tuple(_name_up(n) for n in p))


def _fqname_up(f: fq3.FQName) -> fq4.FQName:
    return fq4.FQName(
        _path_up(f.package_path), _path_up(f.module_path), _name_up(f.local_name)
    )


def _access_up[A, B](
    item: ac3.AccessControlled[A], value: B
) -> ac4.AccessControlled[B]:
    if item.access is ac3.Access.PUBLIC:
        return ac4.Public(value)
    return ac4.Private(value)


def _literal_up(literal: lit3.Literal) -> lit4.Literal:
    match literal:
        case lit3.BoolLiteral(b):
            return lit4.BoolLiteral(b)
        case lit3.CharLiteral(c):
            return lit4.CharLiteral(c)
        case lit3.StringLiteral(s):
            return lit4.StringLiteral(s)
        case lit3.WholeNumberLiteral(i):
            return lit4.IntegerLiteral(i)
        case lit3.FloatLiteral(f):
            return lit4.FloatLiteral(f)
        case lit3.DecimalLiteral(x):
            return lit4.DecimalLiteral(x)


def _type_up(tpe: t3.Type[None]) -> t4.Type:
    a = t4.TypeAttributes()
    match tpe:
        case t3.Variable(_, n):
            return t4.Variable(a, _name_up(n))
        case t3.Reference(_, f, args):
            return t4.Reference(a, _fqname_up(f), [_type_up(x) for x in args])
        case t3.Tuple(_, elements):
            return t4.Tuple(a, [_type_up(x) for x in elements])
        case t3.Record(_, fields):
            return t4.Record(
                a, [t4.Field(_name_up(f.name), _type_up(f.tpe)) for f in fields]
            )
        case t3.ExtensibleRecord(_, var, fields):
            return t4.ExtensibleRecord(
                a,
                _name_up(var),
                [t4.Field(_name_up(f.name), _type_up(f.tpe)) for f in fields],
            )
        case t3.Function(_, arg, ret):
            return t4.Function(a, _type_up(arg), _type_up(ret))
        case t3.Unit(_):
            return t4.Unit(a)


def _ctors_up(ctors: t3.Constructors[None]) -> ts4.Constructors:
    return {
        _name_up(n): [(_name_up(an), _type_up(at)) for an, at in args]
        for n, args in ctors.items()
    }


def _params_up(params: tuple[name3.Name, ...]) -> list[name4.Name]:
    return [_name_up(p) for p in params]


def _type_spec_up(spec: t3.Specification[None]) -> ts4.Specification:
    match spec:
        case t3.TypeAliasSpecification(params, tpe):
            return ts4.TypeAliasSpecification(_params_up(params), _type_up(tpe))
        case t3.OpaqueTypeSpecification(params):
            return ts4.OpaqueTypeSpecification(_params_up(params))
        case t3.CustomTypeSpecification(params, ctors):
            return ts4.CustomTypeSpecification(_params_up(params), _ctors_up(ctors))
        case t3.DerivedTypeSpecification(params, base, from_base, to_base):
            return ts4.DerivedTypeSpecification(
                _params_up(params),
                ts4.DerivedTypeSpecificationDetails(
                    _type_up(base), _fqname_up(from_base), _fqname_up(to_base)
                ),
            )


def _type_def_up(defn: t3.Definition[None]) -> td4.Definition:
    match defn:
        case t3.TypeAliasDefinition(params, tpe):
            return td4.TypeAliasDefinition(_params_up(params), _type_up(tpe))
        case t3.CustomTypeDefinition(params, ctors):
            return td4.CustomTypeDefinition(
                _params_up(params), _access_up(ctors, _ctors_up(ctors.value))
            )


def _va_up(tpe: t3.Type[None]) -> v4.ValueAttributes:
    return v4.ValueAttributes(inferred_type=_type_up(tpe))


type TypedValue3 = v3.Value[None, t3.Type[None]]
type TypedPattern3 = v3.Pattern[t3.Type[None]]
type TypedDefinition3 = v3.Definition[None, t3.Type[None]]


def _pattern_up(p: TypedPattern3) -> v4.Pattern:
    a = _va_up(p.attributes)
    match p:
        case v3.WildcardPattern(_):
            return v4.WildcardPattern(a)
        case v3.AsPattern(_, inner, n):
            return v4.AsPattern(a, _pattern_up(inner), _name_up(n))
        case v3.TuplePattern(_, elements):
            return v4.TuplePattern(a, [_pattern_up(x) for x in elements])
        case v3.ConstructorPattern(_, f, args):
            return v4.ConstructorPattern(
                a, _fqname_up(f), [_pattern_up(x) for x in args]
            )
        case v3.EmptyListPattern(_):
            return v4.EmptyListPattern(a)
        case v3.HeadTailPattern(_, head, tail):
            return v4.HeadTailPattern(a, _pattern_up(head), _pattern_up(tail))
        case v3.LiteralPattern(_, literal):
            return v4.LiteralPattern(a, _literal_up(literal))
        case v3.UnitPattern(_):
            return v4.UnitPattern(a)


def _value_up(val: TypedValue3) -> v4.Value:
    a = _va_up(val.attributes)
    match val:
        case v3.LiteralValue(_, literal):
            return v4.LiteralValue(a, _literal_up(literal))
        case v3.Constructor(_, f):
            return v4.Constructor(a, _fqname_up(f))
        case v3.Tuple(_, elements):
            return v4.Tuple(a, [_value_up(x) for x in elements])
        case v3.List(_, items):
            return v4.List(a, [_value_up(x) for x in items])
        case v3.Record(_, fields):
            return v4.Record(
                a, [(_name_up(n), _value_up(x)) for n, x in fields.items()]
            )
        case v3.Variable(_, n):
            return v4.Variable(a, _name_up(n))
        case v3.Reference(_, f):
            return v4.Reference(a, _fqname_up(f))
        case v3.Field(_, subject, n):
            return v4.Field(a, _value_up(subject), _name_up(n))
        case v3.FieldFunction(_, n):
            return v4.FieldFunction(a, _name_up(n))
        case v3.Apply(_, function, argument):
            return v4.Apply(a, _value_up(function), _value_up(argument))
        case v3.Lambda(_, pattern, body):
            return v4.Lambda(a, _pattern_up(pattern), _value_up(body))
        case v3.LetDefinition(_, n, defn, in_value):
            return v4.LetDefinition(
                a, _name_up(n), _value_def_up(defn), _value_up(in_value)
            )
        case v3.LetRecursion(_, defs, in_value):
            return v4.LetRecursion(
                a,
                {_name_up(n): _value_def_up(x) for n, x in defs.items()},
                _value_up(in_value),
            )
        case v3.Destructure(_, pattern, subject, in_value):
            return v4.Destructure(
                a, _pattern_up(pattern), _value_up(subject), _value_up(in_value)
            )
        case v3.IfThenElse(_, cond, then_branch, else_branch):
            return v4.IfThenElse(
                a, _value_up(cond), _value_up(then_branch), _value_up(else_branch)
            )
        case v3.PatternMatch(_, subject, cases):
            return v4.PatternMatch(
                a,
                _value_up(subject),
                [(_pattern_up(p), _value_up(b)) for p, b in cases],
            )
        case v3.UpdateRecord(_, subject, fields):
            return v4.UpdateRecord(
                a,
                _value_up(subject),
                [(_name_up(n), _value_up(x)) for n, x in fields.items()],
            )
        case v3.Unit(_):
            return v4.Unit(a)


def _value_def_up(defn: TypedDefinition3) -> v4.Definition:
    return v4.Definition(
        [(_name_up(n), _va_up(va), _type_up(tpe)) for n, va, tpe in defn.input_types],
        _type_up(defn.output_type),
        _value_up(defn.body),
    )


def _value_spec_up(spec: v3.Specification[None]) -> v4.Specification:
    return v4.Specification(
        [(_name_up(n), _type_up(tp)) for n, tp in spec.inputs], _type_up(spec.output)
    )


def _documented_up[A, B](item: doc3.Documented[A], value: B) -> doc4.Documented[B]:
    return doc4.Documented(item.doc, value)


def _module_spec_up(spec: mod3.Specification[None]) -> mod4.Specification:
    return mod4.Specification(
        types={
            _name_up(n): _documented_up(x, _type_spec_up(x.value))
            for n, x in spec.types.items()
        },
        values={
            _name_up(n): _documented_up(x, _value_spec_up(x.value))
            for n, x in spec.values.items()
        },
        doc=spec.doc,
    )


def _module_def_up(defn: mod3.Definition[None, t3.Type[None]]) -> mod4.Definition:
    return mod4.Definition(
        types={
            _name_up(n): _access_up(
                x, _documented_up(x.value, _type_def_up(x.value.value))
            )
            for n, x in defn.types.items()
        },
        values={
            _name_up(n): _access_up(
                x, _documented_up(x.value, _value_def_up(x.value.value))
            )
            for n, x in defn.values.items()
        },
        doc=defn.doc,
    )


def _package_spec_up(spec: pkg3.Specification[None]) -> pkg4.Specification:
    return pkg4.Specification(
        {_path_up(p): _module_spec_up(m) for p, m in spec.modules.items()}
    )


def _package_def_up(defn: pkg3.Definition[None, t3.Type[None]]) -> pkg4.Definition:
    return pkg4.Definition(
        {
            _path_up(p): _access_up(m, _module_def_up(m.value))
            for p, m in defn.modules.items()
        }
    )


@overload
def v3_to_v4(
    dist: dist3.Library,
    *,
    package_version: str | None = None,
    drop_input_attributes: bool = False,
) -> Ok[dist4.LibraryDistribution]: ...
@overload
def v3_to_v4(
    dist: dist3.Specs,
    *,
    package_version: str | None = None,
    drop_input_attributes: bool = False,
) -> Ok[dist4.SpecsDistribution]: ...
def v3_to_v4(
    dist: dist3.Distribution,
    *,
    package_version: str | None = None,
    drop_input_attributes: bool = False,
) -> Ok[dist4.LibraryDistribution] | Ok[dist4.SpecsDistribution]:
    """Migrate a format-3 Library or Specs to the same v4 distribution kind.

    Unit type attributes become empty `TypeAttributes`; each value attribute type
    becomes ``inferred_type``; ``WholeNumberLiteral`` becomes ``IntegerLiteral``.
    A Specs maps its package specification as a Library maps its dependencies.

    Args:
        dist: The v3 Library or Specs.
        package_version: Optional release version for the v4 package identity.
            Without it the version is absent; nothing is invented.
        drop_input_attributes: Reset each value-definition input's attributes to
            its declared type, as `drop_input_attributes` does, so the result can
            be encoded as v4 JSON. Each input that loses information is reported.

    Returns:
        ``Ok`` with the v4 Library or Specs and any ``input_attributes_dropped``
        warnings. Forward migration has no failure paths.
    """
    package = dist4.PackageInfo(_path_up(dist.package_name), package_version)
    dependencies = {
        _path_up(p): _package_spec_up(s) for p, s in dist.dependencies.items()
    }
    if isinstance(dist, dist3.Specs):
        specs = dist4.SpecsDistribution(
            package=package,
            specification=_package_spec_up(dist.specification),
            dependencies=dependencies,
        )
        if drop_input_attributes:
            return _drop_input_attributes(specs)
        return Ok(specs)
    library = dist4.LibraryDistribution(
        package=package,
        definition=_package_def_up(dist.definition),
        dependencies=dependencies,
    )
    if drop_input_attributes:
        return _drop_input_attributes(library)
    return Ok(library)


# --- Per-input attributes ---


class _InputDrop:
    """Resets value-definition input attributes, recording each loss."""

    def __init__(self) -> None:
        self.warnings: list[Diagnostic] = []

    def definition(
        self, defn: v4.ValueDefinitionBody, loc: Location
    ) -> v4.ValueDefinitionBody:
        match defn:
            case v4.Definition():
                return self.expression(defn, loc)
            case v4.ExternalBody(inputs, output, externals, fallback):
                here = (*loc, "ExternalBody", "body")
                return v4.ExternalBody(
                    inputs,
                    output,
                    externals,
                    None if fallback is None else self.value(fallback, here),
                )
            case v4.IncompleteBody(inputs, incompleteness, output, partial):
                here = (*loc, "IncompleteBody", "partial_body")
                return v4.IncompleteBody(
                    inputs,
                    incompleteness,
                    output,
                    None if partial is None else self.value(partial, here),
                )
            case v4.NativeBody():
                return defn

    def expression(self, defn: v4.Definition, loc: Location) -> v4.Definition:
        inputs: list[tuple[name4.Name, v4.ValueAttributes, t4.Type]] = []
        for n, attrs, tpe in defn.input_types:
            declared = v4.ValueAttributes(inferred_type=tpe)
            if attrs not in (v4.ValueAttributes(), declared):
                self.warnings.append(
                    Diagnostic(
                        d.INPUT_ATTRIBUTES_DROPPED,
                        "ValueDefinitionInput",
                        (*loc, "input_types", name4.to_string(n)),
                        f"input {name4.to_string(n)!r} kept only its declared type; "
                        "v4 JSON spells an input as a bare type",
                    )
                )
            inputs.append((n, declared, tpe))
        return v4.Definition(
            inputs, defn.output_type, self.value(defn.body, (*loc, "body"))
        )

    def value(self, val: v4.Value, loc: Location) -> v4.Value:
        here = (*loc, type(val).__name__)
        a = val.attributes
        match val:
            case v4.Tuple(_, elements):
                return v4.Tuple(
                    a, [self.value(x, (*here, i)) for i, x in enumerate(elements)]
                )
            case v4.List(_, items):
                return v4.List(
                    a, [self.value(x, (*here, i)) for i, x in enumerate(items)]
                )
            case v4.Record(_, fields):
                return v4.Record(a, self.fields(fields, here))
            case v4.Field(_, subject, n):
                return v4.Field(a, self.value(subject, (*here, "subject")), n)
            case v4.Apply(_, function, argument):
                return v4.Apply(
                    a,
                    self.value(function, (*here, "function")),
                    self.value(argument, (*here, "argument")),
                )
            case v4.Lambda(_, pattern, body):
                return v4.Lambda(a, pattern, self.value(body, (*here, "body")))
            case v4.LetDefinition(_, n, defn, in_value):
                return v4.LetDefinition(
                    a,
                    n,
                    self.definition(defn, (*here, "definition")),
                    self.value(in_value, (*here, "in_value")),
                )
            case v4.LetRecursion(_, defs, in_value):
                return v4.LetRecursion(
                    a,
                    {
                        k: self.definition(
                            x, (*here, "definitions", name4.to_string(k))
                        )
                        for k, x in defs.items()
                    },
                    self.value(in_value, (*here, "in_value")),
                )
            case v4.Destructure(_, pattern, subject, in_value):
                return v4.Destructure(
                    a,
                    pattern,
                    self.value(subject, (*here, "value_to_destructure")),
                    self.value(in_value, (*here, "in_value")),
                )
            case v4.IfThenElse(_, cond, then_branch, else_branch):
                return v4.IfThenElse(
                    a,
                    self.value(cond, (*here, "condition")),
                    self.value(then_branch, (*here, "then_branch")),
                    self.value(else_branch, (*here, "else_branch")),
                )
            case v4.PatternMatch(_, subject, cases):
                return v4.PatternMatch(
                    a,
                    self.value(subject, (*here, "branch_on")),
                    [
                        (p, self.value(b, (*here, "cases", i)))
                        for i, (p, b) in enumerate(cases)
                    ],
                )
            case v4.UpdateRecord(_, subject, fields):
                return v4.UpdateRecord(
                    a,
                    self.value(subject, (*here, "value_to_update")),
                    self.fields(fields, here),
                )
            case _:
                return val

    def fields(
        self, items: list[tuple[name4.Name, v4.Value]], loc: Location
    ) -> list[tuple[name4.Name, v4.Value]]:
        return [(k, self.value(x, (*loc, name4.to_string(k)))) for k, x in items]

    def package_def(self, defn: pkg4.Definition, loc: Location) -> pkg4.Definition:
        modules: dict[path4.Path, ac4.AccessControlled[mod4.Definition]] = {}
        for p, m in defn.modules.items():
            here = (*loc, path4.to_string(p))
            values = {
                k: _with_access(
                    x,
                    doc4.Documented(
                        x.value.doc,
                        self.definition(
                            x.value.value, (*here, "values", name4.to_string(k))
                        ),
                    ),
                )
                for k, x in m.value.values.items()
            }
            modules[p] = _with_access(
                m, mod4.Definition(m.value.types, values, m.value.doc)
            )
        return pkg4.Definition(modules)

    # Specifications: annotation arguments are expressions too.

    def annotations(
        self, items: list[ann4.Annotation], loc: Location
    ) -> list[ann4.Annotation]:
        result: list[ann4.Annotation] = []
        for i, item in enumerate(items):
            here = (*loc, "annotations", i)
            if isinstance(item, ann4.CompactAnnotation):
                result.append(item)
                continue
            arguments: list[ann4.AnnotationArgument] = []
            for j, arg in enumerate(item.arguments):
                at = (*here, "arguments", j)
                match arg:
                    case ann4.PositionalArgument(value):
                        arguments.append(ann4.PositionalArgument(self.value(value, at)))
                    case ann4.NamedArgument(name, value):
                        arguments.append(
                            ann4.NamedArgument(name, self.value(value, (*at, "value")))
                        )
            result.append(ann4.StructuredAnnotation(item.name, arguments))
        return result

    def module_spec(
        self, spec: mod4.Specification, loc: Location
    ) -> mod4.Specification:
        types = {
            k: doc4.Documented(
                x.doc,
                dataclasses.replace(
                    x.value,
                    annotations=self.annotations(
                        x.value.annotations, (*loc, "types", name4.to_string(k))
                    ),
                ),
            )
            for k, x in spec.types.items()
        }
        values = {
            k: doc4.Documented(
                x.doc,
                dataclasses.replace(
                    x.value,
                    annotations=self.annotations(
                        x.value.annotations, (*loc, "values", name4.to_string(k))
                    ),
                ),
            )
            for k, x in spec.values.items()
        }
        return mod4.Specification(
            types, values, spec.doc, self.annotations(spec.annotations, loc)
        )

    def package_spec(
        self, spec: pkg4.Specification, loc: Location
    ) -> pkg4.Specification:
        return pkg4.Specification(
            {
                p: self.module_spec(m, (*loc, path4.to_string(p)))
                for p, m in spec.modules.items()
            }
        )


def _with_access[A, B](
    item: ac4.AccessControlled[A], value: B
) -> ac4.AccessControlled[B]:
    return ac4.Public(value) if isinstance(item, ac4.Public) else ac4.Private(value)


def drop_input_attributes[D: dist4.Distribution](dist: D) -> Ok[D]:
    """Reset every value-definition input's attributes to its declared type.

    v4 JSON spells an input as a bare type (kit case ``definitions-0027``), so
    the draft codec refuses an input whose attributes hold anything else, such as
    the resolved types morphir-elm writes for typed inputs. This drop makes such
    a distribution encodable. Module-level and let-bound definitions are covered.

    Args:
        dist: Any v4 distribution. Dependencies and the expressions in
            specification annotation arguments are covered too.

    Returns:
        ``Ok`` with the distribution and one ``input_attributes_dropped`` warning
        per input whose attributes were neither empty nor its declared type.
    """
    return _drop_input_attributes(dist)


def _drop_input_attributes[D: dist4.Distribution](dist: D) -> Ok[D]:
    job = _InputDrop()
    loc: Location = ("distribution", "modules")

    def dep(p: path4.Path) -> Location:
        return ("distribution", "dependencies", path4.to_string(p))

    result: dist4.Distribution
    match dist:
        case dist4.SpecsDistribution(package, specification, deps):
            result = dist4.SpecsDistribution(
                package,
                job.package_spec(specification, loc),
                {p: job.package_spec(s, dep(p)) for p, s in deps.items()},
            )
        case dist4.LibraryDistribution(package, definition, deps):
            result = dist4.LibraryDistribution(
                package,
                job.package_def(definition, loc),
                {p: job.package_spec(s, dep(p)) for p, s in deps.items()},
            )
        case dist4.ApplicationDistribution(package, definition, deps, entry_points):
            result = dist4.ApplicationDistribution(
                package,
                job.package_def(definition, loc),
                {p: job.package_def(x, dep(p)) for p, x in deps.items()},
                entry_points,
            )
    return Ok(cast("D", result), tuple(job.warnings))


# --- v4 -> v3 ---

_CLASSIC_WORD = re.compile(r"^[a-z0-9]+$")


@dataclass
class _Downgrade:
    drop_source_locations: bool
    errors: list[Diagnostic] = field(default_factory=list)
    dropped_sources: int = 0

    def error(self, code: str, construct: str, loc: Location, message: str) -> None:
        self.errors.append(Diagnostic(code, construct, loc, message))

    # Names

    def name(self, n: name4.Name, loc: Location) -> name3.Name:
        for word in n:
            if not _CLASSIC_WORD.match(word):
                self.error(
                    d.INVALID_NAME,
                    "Name",
                    loc,
                    f"name word {word!r} has no classic (v3) form",
                )
        return name3.Name(tuple(n))

    def path(self, p: path4.Path, loc: Location) -> path3.Path:
        return path3.Path(tuple(self.name(n, loc) for n in p))

    def fqname(self, f: fq4.FQName, loc: Location) -> fq3.FQName:
        return fq3.FQName(
            self.path(f.package_path, loc),
            self.path(f.module_path, loc),
            self.name(f.local_name, loc),
        )

    def access[A, B](
        self, item: ac4.AccessControlled[A], value: B
    ) -> ac3.AccessControlled[B]:
        if isinstance(item, ac4.Public):
            return ac3.public(value)
        return ac3.private(value)

    def documented[A, B](
        self, item: doc4.Documented[A], value: B, construct: str, loc: Location
    ) -> doc3.Documented[B]:
        if item.doc is None:
            self.error(
                d.UNSUPPORTED_DOCUMENTATION_DOWNGRADE,
                construct,
                loc,
                f"{construct} has no documentation; v3 member documentation is a "
                "required string",
            )
            return doc3.Documented("", value)
        return doc3.Documented(item.doc, value)

    # Attributes

    def type_attributes(self, a: t4.TypeAttributes, loc: Location) -> None:
        present = [
            label
            for label, on in (
                ("source", a.source is not None),
                ("constraints", a.constraints is not None),
                ("extensions", bool(a.extensions)),
            )
            if on
        ]
        if present:
            self.error(
                d.UNSUPPORTED_ATTRIBUTES_DOWNGRADE,
                "TypeAttributes",
                loc,
                f"type attributes carry {', '.join(present)}, which v3 cannot hold",
            )

    def value_attributes(
        self, a: v4.ValueAttributes, construct: str, loc: Location
    ) -> t3.Type[None]:
        if a.extensions:
            self.error(
                d.UNSUPPORTED_ATTRIBUTES_DOWNGRADE,
                construct,
                loc,
                "value attributes carry extensions, which v3 cannot hold",
            )
        if a.source is not None:
            if self.drop_source_locations:
                self.dropped_sources += 1
            else:
                self.error(
                    d.UNSUPPORTED_ATTRIBUTES_DOWNGRADE,
                    construct,
                    loc,
                    "value attributes carry a source location; pass "
                    "drop_source_locations=True to drop it",
                )
        if a.inferred_type is None:
            self.error(
                d.MISSING_INFERRED_TYPE,
                construct,
                loc,
                f"{construct} has no inferred_type; v3 value attributes are types",
            )
            return t3.Unit(None)
        return self.type(a.inferred_type, (*loc, "inferred_type"))

    # Types

    def type(self, tpe: t4.Type, loc: Location) -> t3.Type[None]:
        self.type_attributes(tpe.attributes, loc)
        here = (*loc, type(tpe).__name__)
        match tpe:
            case t4.Variable(_, n):
                return t3.Variable(None, self.name(n, here))
            case t4.Reference(_, f, args):
                return t3.Reference(
                    None,
                    self.fqname(f, here),
                    tuple(self.type(x, (*here, i)) for i, x in enumerate(args)),
                )
            case t4.Tuple(_, elements):
                return t3.Tuple(
                    None,
                    tuple(self.type(x, (*here, i)) for i, x in enumerate(elements)),
                )
            case t4.Record(_, fields):
                return t3.Record(None, self.fields(fields, here))
            case t4.ExtensibleRecord(_, var, fields):
                return t3.ExtensibleRecord(
                    None, self.name(var, here), self.fields(fields, here)
                )
            case t4.Function(_, arg, ret):
                return t3.Function(
                    None,
                    self.type(arg, (*here, "argument_type")),
                    self.type(ret, (*here, "return_type")),
                )
            case t4.Unit(_):
                return t3.Unit(None)
            case t4.Union():
                self.unsupported("Union", here)
                return t3.Unit(None)

    def fields(
        self, fields: list[t4.Field], loc: Location
    ) -> tuple[t3.Field[None], ...]:
        return tuple(
            t3.Field(self.name(f.name, loc), self.type(f.tpe, (*loc, "fields", i)))
            for i, f in enumerate(fields)
        )

    def ctors(self, ctors: ts4.Constructors, loc: Location) -> t3.Constructors[None]:
        return {
            self.name(n, loc): tuple(
                (self.name(an, loc), self.type(at, (*loc, name4.to_string(n), i)))
                for i, (an, at) in enumerate(args)
            )
            for n, args in ctors.items()
        }

    def params(self, params: list[name4.Name], loc: Location) -> tuple[name3.Name, ...]:
        return tuple(self.name(p, loc) for p in params)

    def annotations(self, items: list[ann4.Annotation], loc: Location) -> None:
        if items:
            self.unsupported("Annotations", (*loc, "annotations"))

    def type_spec(
        self, spec: ts4.Specification, loc: Location
    ) -> t3.Specification[None]:
        self.annotations(spec.annotations, loc)
        params = self.params(spec.type_params, loc)
        match spec:
            case ts4.TypeAliasSpecification(_, tpe):
                return t3.TypeAliasSpecification(params, self.type(tpe, loc))
            case ts4.OpaqueTypeSpecification(_):
                return t3.OpaqueTypeSpecification(params)
            case ts4.CustomTypeSpecification(_, ctors):
                return t3.CustomTypeSpecification(params, self.ctors(ctors, loc))
            case ts4.DerivedTypeSpecification(_, details):
                return t3.DerivedTypeSpecification(
                    params,
                    self.type(details.base_type, loc),
                    self.fqname(details.from_base_type, loc),
                    self.fqname(details.to_base_type, loc),
                )

    def type_def(self, defn: td4.Definition, loc: Location) -> t3.Definition[None]:
        params = self.params(defn.type_params, loc)
        match defn:
            case td4.TypeAliasDefinition(_, tpe):
                return t3.TypeAliasDefinition(params, self.type(tpe, loc))
            case td4.CustomTypeDefinition(_, ctors):
                return t3.CustomTypeDefinition(
                    params, self.access(ctors, self.ctors(ctors.value, loc))
                )
            case td4.IncompleteTypeDefinition():
                self.unsupported(
                    "IncompleteTypeDefinition", (*loc, "IncompleteTypeDefinition")
                )
                return t3.TypeAliasDefinition(params, t3.Unit(None))

    # Values

    def literal(self, literal: lit4.Literal, loc: Location) -> lit3.Literal:
        match literal:
            case lit4.BoolLiteral(b):
                return lit3.BoolLiteral(b)
            case lit4.CharLiteral(c):
                return lit3.CharLiteral(c)
            case lit4.StringLiteral(s):
                return lit3.StringLiteral(s)
            case lit4.IntegerLiteral(i):
                return lit3.WholeNumberLiteral(i)
            case lit4.FloatLiteral(f):
                return lit3.FloatLiteral(f)
            case lit4.DecimalLiteral(x):
                return lit3.DecimalLiteral(x)
            case lit4.DocumentLiteral():
                self.unsupported("DocumentLiteral", loc)
                return lit3.StringLiteral("")

    def unsupported(self, construct: str, loc: Location) -> None:
        self.error(
            d.UNSUPPORTED_V4_DOWNGRADE,
            construct,
            loc,
            f"{construct} exists only in IR v4 and cannot be written as format 3.0.0",
        )

    def pattern(self, p: v4.Pattern, loc: Location) -> TypedPattern3:
        construct = type(p).__name__
        here = (*loc, construct)
        a = self.value_attributes(p.attributes, construct, here)
        match p:
            case v4.WildcardPattern(_):
                return v3.WildcardPattern(a)
            case v4.AsPattern(_, inner, n):
                return v3.AsPattern(
                    a, self.pattern(inner, (*here, "pattern")), self.name(n, here)
                )
            case v4.TuplePattern(_, elements):
                return v3.TuplePattern(
                    a,
                    tuple(self.pattern(x, (*here, i)) for i, x in enumerate(elements)),
                )
            case v4.ConstructorPattern(_, f, args):
                return v3.ConstructorPattern(
                    a,
                    self.fqname(f, here),
                    tuple(self.pattern(x, (*here, i)) for i, x in enumerate(args)),
                )
            case v4.EmptyListPattern(_):
                return v3.EmptyListPattern(a)
            case v4.HeadTailPattern(_, head, tail):
                return v3.HeadTailPattern(
                    a,
                    self.pattern(head, (*here, "head")),
                    self.pattern(tail, (*here, "tail")),
                )
            case v4.LiteralPattern(_, literal):
                return v3.LiteralPattern(a, self.literal(literal, here))
            case v4.UnitPattern(_):
                return v3.UnitPattern(a)

    def named_values(
        self, items: list[tuple[name4.Name, v4.Value]], construct: str, loc: Location
    ) -> dict[name3.Name, TypedValue3]:
        result: dict[name3.Name, TypedValue3] = {}
        for n, x in items:
            key = self.name(n, loc)
            if key in result:
                self.error(
                    d.DUPLICATE_MEMBER,
                    construct,
                    loc,
                    f"field {name4.to_string(n)!r} appears more than once; v3 record "
                    "fields are a dictionary",
                )
            result[key] = self.value(x, (*loc, name4.to_string(n)))
        return result

    def value(self, val: v4.Value, loc: Location) -> TypedValue3:
        construct = type(val).__name__
        here = (*loc, construct)
        if isinstance(val, (v4.Hole, v4.Native, v4.External)):
            self.unsupported(construct, here)
            return v3.Unit(t3.Unit(None))
        a = self.value_attributes(val.attributes, construct, here)
        match val:
            case v4.LiteralValue(_, literal):
                return v3.LiteralValue(a, self.literal(literal, here))
            case v4.Constructor(_, f):
                return v3.Constructor(a, self.fqname(f, here))
            case v4.Tuple(_, elements):
                return v3.Tuple(
                    a, tuple(self.value(x, (*here, i)) for i, x in enumerate(elements))
                )
            case v4.List(_, items):
                return v3.List(
                    a, tuple(self.value(x, (*here, i)) for i, x in enumerate(items))
                )
            case v4.Record(_, fields):
                return v3.Record(a, self.named_values(fields, construct, here))
            case v4.Variable(_, n):
                return v3.Variable(a, self.name(n, here))
            case v4.Reference(_, f):
                return v3.Reference(a, self.fqname(f, here))
            case v4.Field(_, subject, n):
                return v3.Field(
                    a, self.value(subject, (*here, "subject")), self.name(n, here)
                )
            case v4.FieldFunction(_, n):
                return v3.FieldFunction(a, self.name(n, here))
            case v4.Apply(_, function, argument):
                return v3.Apply(
                    a,
                    self.value(function, (*here, "function")),
                    self.value(argument, (*here, "argument")),
                )
            case v4.Lambda(_, pattern, body):
                return v3.Lambda(
                    a,
                    self.pattern(pattern, (*here, "pattern")),
                    self.value(body, (*here, "body")),
                )
            case v4.LetDefinition(_, n, defn, in_value):
                return v3.LetDefinition(
                    a,
                    self.name(n, here),
                    self.value_def(defn, (*here, "definition")),
                    self.value(in_value, (*here, "in_value")),
                )
            case v4.LetRecursion(_, defs, in_value):
                return v3.LetRecursion(
                    a,
                    {
                        self.name(n, here): self.value_def(
                            x, (*here, "definitions", name4.to_string(n))
                        )
                        for n, x in defs.items()
                    },
                    self.value(in_value, (*here, "in_value")),
                )
            case v4.Destructure(_, pattern, subject, in_value):
                return v3.Destructure(
                    a,
                    self.pattern(pattern, (*here, "pattern")),
                    self.value(subject, (*here, "value_to_destructure")),
                    self.value(in_value, (*here, "in_value")),
                )
            case v4.IfThenElse(_, cond, then_branch, else_branch):
                return v3.IfThenElse(
                    a,
                    self.value(cond, (*here, "condition")),
                    self.value(then_branch, (*here, "then_branch")),
                    self.value(else_branch, (*here, "else_branch")),
                )
            case v4.PatternMatch(_, subject, cases):
                return v3.PatternMatch(
                    a,
                    self.value(subject, (*here, "branch_on")),
                    tuple(
                        (
                            self.pattern(p, (*here, "cases", i)),
                            self.value(b, (*here, "cases", i)),
                        )
                        for i, (p, b) in enumerate(cases)
                    ),
                )
            case v4.UpdateRecord(_, subject, fields):
                return v3.UpdateRecord(
                    a,
                    self.value(subject, (*here, "value_to_update")),
                    self.named_values(fields, construct, here),
                )
            case _:
                return v3.Unit(a)

    def value_def(
        self, defn: v4.ValueDefinitionBody, loc: Location
    ) -> TypedDefinition3:
        if not isinstance(defn, v4.Definition):
            construct = type(defn).__name__
            self.unsupported(construct, (*loc, construct))
            return v3.Definition((), t3.Unit(None), v3.Unit(t3.Unit(None)))
        inputs = []
        for n, va, tpe in defn.input_types:
            here = (*loc, "input_types", name4.to_string(n))
            inputs.append(
                (
                    self.name(n, here),
                    self.value_attributes(va, "ValueDefinitionInput", here),
                    self.type(tpe, here),
                )
            )
        return v3.Definition(
            tuple(inputs),
            self.type(defn.output_type, (*loc, "output_type")),
            self.value(defn.body, (*loc, "body")),
        )

    def value_spec(
        self, spec: v4.Specification, loc: Location
    ) -> v3.Specification[None]:
        self.annotations(spec.annotations, loc)
        return v3.Specification(
            tuple(
                (self.name(n, loc), self.type(tp, (*loc, "inputs", name4.to_string(n))))
                for n, tp in spec.inputs
            ),
            self.type(spec.output, (*loc, "output")),
        )

    # Modules and packages

    def module_spec(
        self, spec: mod4.Specification, loc: Location
    ) -> mod3.Specification[None]:
        self.annotations(spec.annotations, loc)
        types = {}
        for n, x in spec.types.items():
            here = (*loc, "types", name4.to_string(n))
            types[self.name(n, here)] = self.documented(
                x, self.type_spec(x.value, here), "TypeSpecification", here
            )
        values = {}
        for n, y in spec.values.items():
            here = (*loc, "values", name4.to_string(n))
            values[self.name(n, here)] = self.documented(
                y, self.value_spec(y.value, here), "ValueSpecification", here
            )
        return mod3.Specification(types, values, spec.doc)

    def module_def(
        self, defn: mod4.Definition, loc: Location
    ) -> mod3.Definition[None, t3.Type[None]]:
        types = {}
        for n, x in defn.types.items():
            here = (*loc, "types", name4.to_string(n))
            types[self.name(n, here)] = self.access(
                x,
                self.documented(
                    x.value, self.type_def(x.value.value, here), "TypeDefinition", here
                ),
            )
        values = {}
        for n, y in defn.values.items():
            here = (*loc, "values", name4.to_string(n))
            values[self.name(n, here)] = self.access(
                y,
                self.documented(
                    y.value,
                    self.value_def(y.value.value, here),
                    "ValueDefinition",
                    here,
                ),
            )
        return mod3.Definition(types, values, defn.doc)

    def package_spec(
        self, spec: pkg4.Specification, loc: Location
    ) -> pkg3.Specification[None]:
        return pkg3.Specification(
            {
                self.path(p, loc): self.module_spec(m, (*loc, path4.to_string(p)))
                for p, m in spec.modules.items()
            }
        )

    def package_def(
        self, defn: pkg4.Definition, loc: Location
    ) -> pkg3.Definition[None, t3.Type[None]]:
        return pkg3.Definition(
            {
                self.path(p, loc): self.access(
                    m, self.module_def(m.value, (*loc, path4.to_string(p)))
                )
                for p, m in defn.modules.items()
            }
        )


@overload
def v4_to_v3(
    dist: dist4.LibraryDistribution, *, drop_source_locations: bool = False
) -> MigrationResult[dist3.Library]: ...
@overload
def v4_to_v3(
    dist: dist4.SpecsDistribution, *, drop_source_locations: bool = False
) -> MigrationResult[dist3.Specs]: ...
@overload
def v4_to_v3(
    dist: dist4.ApplicationDistribution, *, drop_source_locations: bool = False
) -> Err: ...
def v4_to_v3(
    dist: dist4.Distribution, *, drop_source_locations: bool = False
) -> MigrationResult[dist3.Library] | MigrationResult[dist3.Specs]:
    """Migrate a v4 Library or Specs to format 3, or report why it cannot.

    Every unsupported construct is collected in one pass. A Specs becomes a v3
    Specs, which format 3.1.0 introduced; an Application has no format-3 form.

    Args:
        dist: The v4 distribution.
        drop_source_locations: Drop value source locations instead of failing.
            This is the only opt-in loss.

    Returns:
        ``Ok`` with the v3 Library or Specs and any warnings, or ``Err`` with
        every diagnostic found.
    """
    if isinstance(dist, dist4.ApplicationDistribution):
        return Err(
            (
                Diagnostic(
                    d.UNSUPPORTED_V4_DOWNGRADE,
                    "Application",
                    ("distribution",),
                    "Application distributions cannot be written as format 3, "
                    "which has no Application",
                ),
            )
        )
    job = _Downgrade(drop_source_locations)
    loc: Location = ("distribution",)

    def dependencies() -> dict[path3.Path, pkg3.Specification[None]]:
        return {
            job.path(p, loc): job.package_spec(
                s, (*loc, "dependencies", path4.to_string(p))
            )
            for p, s in dist.dependencies.items()
        }

    # Fields are migrated in declaration order, so diagnostics keep that order.
    result: dist3.Library | dist3.Specs
    if isinstance(dist, dist4.SpecsDistribution):
        result = dist3.Specs(
            package_name=job.path(dist.package.name, (*loc, "package")),
            specification=job.package_spec(dist.specification, (*loc, "modules")),
            dependencies=dependencies(),
        )
    else:
        result = dist3.Library(
            package_name=job.path(dist.package.name, (*loc, "package")),
            definition=job.package_def(dist.definition, (*loc, "modules")),
            dependencies=dependencies(),
        )
    if job.errors:
        return Err(tuple(job.errors))
    warnings: list[Diagnostic] = []
    if dist.package.version is not None:
        warnings.append(
            Diagnostic(
                d.PACKAGE_VERSION_DROPPED,
                "PackageInfo",
                (*loc, "package", "version"),
                f"package version {dist.package.version!r} was dropped; format 3 "
                "has no package version",
            )
        )
    if job.dropped_sources:
        warnings.append(
            Diagnostic(
                d.SOURCE_LOCATION_DROPPED,
                "ValueAttributes",
                loc,
                f"{job.dropped_sources} value source location(s) were dropped",
            )
        )
    # Ok is invariant, so each kind is returned under its own narrowed type.
    if isinstance(result, dist3.Specs):
        return Ok(result, tuple(warnings))
    return Ok(result, tuple(warnings))


__all__ = [
    "Err",
    "MigrationResult",
    "Ok",
    "drop_input_attributes",
    "v3_to_v4",
    "v4_to_v3",
]
