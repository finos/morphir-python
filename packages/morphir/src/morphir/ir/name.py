from typing import NewType, List, Tuple
import re

Name = NewType("Name", Tuple[str, ...])

def from_list(words: List[str]) -> Name:
    return Name(tuple(word.lower() for word in words))

def to_list(name: Name) -> List[str]:
    return list(name)

def from_string(s: str) -> Name:
    # Basic implementation - will need more robust splitting logic later
    # to match Gleam's behavior
    
    # Split by underscore, hyphen, space, dot
    words = re.split(r"[_\-\s\.]", s)
    # Filter empty strings
    words = [w for w in words if w]
    
    result = []
    for word in words:
        # Split camelCase
        parts = re.findall(r'[A-Za-z][a-z0-9]*|[0-9]+', word) # simplistic camelCase split
        if not parts:
            parts = [word] # fallback if no match
        
        for part in parts:
            result.append(part.lower())
            
    return Name(tuple(result))

def to_title_case(name: Name) -> str:
    return "".join(word.capitalize() for word in name)

def to_camel_case(name: Name) -> str:
    if not name:
        return ""
    return name[0] + "".join(word.capitalize() for word in name[1:])

def to_snake_case(name: Name) -> str:
    return "_".join(name)

def to_kebab_case(name: Name) -> str:
    return "-".join(name)

def to_human_words(name: Name) -> List[str]:
    return list(name)
