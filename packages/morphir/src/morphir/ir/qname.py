from dataclasses import dataclass

from . import name, path
from .name import Name
from .path import Path


@dataclass(frozen=True)
class QName:
    module_path: Path
    local_name: Name

    @staticmethod
    def from_tuple(t: tuple[Path, Name]) -> QName:
        return QName(t[0], t[1])

    def to_tuple(self) -> tuple[Path, Name]:
        return (self.module_path, self.local_name)

    @staticmethod
    def from_name(n: Name) -> QName:
        return QName(path.empty(), n)

    def to_string(self) -> str:
        module_str = path.to_string(self.module_path, ".")
        local_str = name.to_camel_case(self.local_name)
        return f"{module_str}:{local_str}"

    @staticmethod
    def from_string(s: str) -> QName:
        parts = s.split(":")
        if len(parts) == 2:
            return QName(path.from_string(parts[0]), name.from_string(parts[1]))
        return QName(path.empty(), name.from_string(s))
