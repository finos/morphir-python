from dataclasses import dataclass
from typing import Tuple, Optional
from .name import Name
from .path import Path
from .qname import QName
from . import name, path

@dataclass(frozen=True)
class FQName:
    package_path: Path
    module_path: Path
    local_name: Name

    @staticmethod
    def from_qname(package_path: Path, qn: QName) -> "FQName":
        return FQName(package_path, qn.module_path, qn.local_name)

    @staticmethod
    def from_tuple(t: Tuple[Path, Path, Name]) -> "FQName":
        return FQName(t[0], t[1], t[2])

    def to_tuple(self) -> Tuple[Path, Path, Name]:
        return (self.package_path, self.module_path, self.local_name)

    @staticmethod
    def fqn(package_str: str, module_str: str, local_str: str) -> "FQName":
         return FQName(
            path.from_string(package_str),
            path.from_string(module_str),
            name.from_string(local_str)
        )

    def to_string(self) -> str:
        package_str = path.to_string(self.package_path, ".")
        module_str = path.to_string(self.module_path, ".")
        local_str = name.to_camel_case(self.local_name)
        return f"{package_str}:{module_str}:{local_str}"

    @staticmethod
    def from_string(s: str, separator: str = ":") -> Optional["FQName"]:
        parts = s.split(separator)
        if len(parts) == 3:
             return FQName(
                path.from_string(parts[0]),
                path.from_string(parts[1]),
                name.from_string(parts[2])
            )
        return None
