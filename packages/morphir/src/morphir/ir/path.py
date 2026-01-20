from typing import NewType, List
from .name import Name, from_string as name_from_string, to_list as name_to_list

Path = NewType("Path", List[Name])

def from_list(names: List[Name]) -> Path:
    return Path(names)

def to_list(path: Path) -> List[Name]:
    return path

def from_string(s: str) -> Path:
    if not s:
        return Path([])
    parts = s.split(".")
    return Path([name_from_string(p) for p in parts])

def to_string(path: Path, separator: str = ".") -> str:
    from .name import to_title_case
    return separator.join(to_title_case(name) for name in path)
    
def empty() -> Path:
    return Path([])

def append(path: Path, name: Name) -> Path:
    return Path(path[:] + [name])

def concat(path1: Path, path2: Path) -> Path:
    return Path(path1[:] + path2[:])
    
def is_prefix_of(prefix: Path, path: Path) -> bool:
    if len(prefix) > len(path):
        return False
    return path[:len(prefix)] == prefix
