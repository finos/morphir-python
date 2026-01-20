from typing import NewType, List

Name = NewType("Name", List[str])

def from_list(words: List[str]) -> Name:
    return Name([word.lower() for word in words])

def to_list(name: Name) -> List[str]:
    return name

def from_string(s: str) -> Name:
    # Basic implementation - will need more robust splitting logic later
    # to match Gleam's behavior
    import re
    # Split by underscore, hyphen, space, dot
    words = re.split(r"[_\-\s\.]", s)
    # Filter empty strings
    words = [w for w in words if w]
    # Handle camelCase splitting? For now, keep it simple as per initial plan
    # But ideally should split camelCase too. 
    # Let's match gleam logic a bit more: split on boundaries
    
    # Simple regex for splitting camelCase:
    # matches = re.finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', s)
    # actually let's treat the simple split first
    
    result = []
    for word in words:
        # Split camelCase
        parts = re.findall(r'[A-Za-z][a-z0-9]*|[0-9]+', word) # simplistic camelCase split
        if not parts:
            parts = [word] # fallback if no match (e.g. non-alphanumeric)
        
        for part in parts:
            result.append(part.lower())
            
    return Name(result)

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
