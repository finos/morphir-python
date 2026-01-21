from dataclasses import dataclass, field
from typing import Dict, Union, Optional
from enum import Enum
from .name import Name
from .path import Path
from .fqname import FQName
from .package import Specification as PackageSpecification, Definition as PackageDefinition
from .documented import Documented

@dataclass(frozen=True)
class PackageInfo:
    name: Path
    version: str

@dataclass(frozen=True)
class LibraryDistribution:
    package: PackageInfo
    definition: PackageDefinition
    dependencies: Dict[Path, PackageSpecification] = field(default_factory=dict)

@dataclass(frozen=True)
class SpecsDistribution:
    package: PackageInfo
    specification: PackageSpecification
    dependencies: Dict[Path, PackageSpecification] = field(default_factory=dict)

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
    doc: Optional[Documented] = None

@dataclass(frozen=True)
class ApplicationDistribution:
    package: PackageInfo
    definition: PackageDefinition
    dependencies: Dict[Path, PackageDefinition] = field(default_factory=dict)
    entry_points: Dict[Name, EntryPoint] = field(default_factory=dict)

Distribution = Union[
    LibraryDistribution,
    SpecsDistribution,
    ApplicationDistribution
]
