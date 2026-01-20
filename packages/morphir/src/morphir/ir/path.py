from typing import NewType, List, Tuple
from .name import Name, from_string as name_from_string

Path = NewType("Path", Tuple[Name, ...])

def from_list(names: List[Name]) -> Path:
    return Path(tuple(names))

def to_list(path: Path) -> List[Name]:
    return list(path)

def from_string(s: str) -> Path:
    if not s:
        return Path(tuple())
    parts = s.split(".")
    return Path(tuple(name_from_string(p) for p in parts))

def to_string(path: Path, separator: str = ".") -> str:
    from .name import to_title_case
    return separator.join(to_title_case(name) for name in path)
    
def empty() -> Path:
    return Path(tuple())

def append(path: Path, name: Name) -> Path:
    return Path(path + (name,))

def concat(path1: Path, path2: Path) -> Path:
    return Path(path1 + path2)
    
def is_prefix_of(prefix: Path, path: Path) -> bool:
    if len(prefix) > len(path):
        return False
    return path[:len(prefix)] == prefix
