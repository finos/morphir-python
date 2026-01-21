from typing import NewType, List, Tuple
import re

class Name(Tuple[str, ...]):
    pass

def from_list(words: List[str]) -> Name:
    return Name(tuple(word.lower() for word in words))

def to_list(name: Name) -> List[str]:
    return list(name)

def from_string(s: str) -> Name:
    # Split by common delimiters including those used in FQName (colon, hash)
    # IR v4 canonical is kebab-case (hyphens).
    # Also handle underscores (snake_case), dots (paths), spaces, colons, hashes.
    words = re.split(r"[_\-\s\.:#]", s)
    # Filter empty strings
    words = [w for w in words if w]
    
    result = []
    for word in words:
        # Split camelCase / PascalCase / Acronyms
        # Regex explanation:
        # 1. [A-Z]+(?=[A-Z][a-z]) : Acronym followed by Capitalized word (e.g. JSON in JSONResponse)
        # 2. [A-Z][a-z0-9]+       : Capitalized word with at least one lowercase/digit (e.g. Response)
        # 3. [A-Z]+               : Acronym at end or isolated (e.g. SDK, ID in MakeID)
        # 4. [a-z][a-z0-9]*       : Lowercase word
        # 5. [0-9]+               : Numbers
        parts = re.findall(r'[A-Z]+(?=[A-Z][a-z])|[A-Z][a-z0-9]+|[A-Z]+|[a-z][a-z0-9]*|[0-9]+', word)
        
        if not parts:
            parts = [word] # fallback
        
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

def to_string(name: Name) -> str:
    return to_kebab_case(name)

def to_human_words(name: Name) -> List[str]:
    return list(name)
