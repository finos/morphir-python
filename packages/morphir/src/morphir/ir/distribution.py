from dataclasses import dataclass, field
from enum import Enum
from typing import Union

from .documented import Documented
from .fqname import FQName
from .name import Name
from .package import Definition as PackageDefinition
from .package import Specification as PackageSpecification
from .path import Path


@dataclass(frozen=True)
class PackageInfo:
    name: Path
    version: str


@dataclass(frozen=True)
class LibraryDistribution:
    package: PackageInfo
    definition: PackageDefinition
    dependencies: dict[Path, PackageSpecification] = field(default_factory=dict)


@dataclass(frozen=True)
class SpecsDistribution:
    package: PackageInfo
    specification: PackageSpecification
    dependencies: dict[Path, PackageSpecification] = field(default_factory=dict)


class EntryPointKind(Enum):
    Main = "Main"
    Command = "Command"
    Handler = "Handler"
    Job = "Job"
    Policy = "Policy"


@dataclass(frozen=True)
class EntryPoint:
    target: FQName
    kind: EntryPointKind
    doc: Documented[str] | None = None


@dataclass(frozen=True)
class ApplicationDistribution:
    package: PackageInfo
    definition: PackageDefinition
    dependencies: dict[Path, PackageDefinition] = field(default_factory=dict)
    entry_points: dict[Name, EntryPoint] = field(default_factory=dict)


Distribution = Union[LibraryDistribution, SpecsDistribution, ApplicationDistribution]
