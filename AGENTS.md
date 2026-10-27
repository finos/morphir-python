# Agent Guidelines for Morphir Python

This document provides guidelines for AI code agents working on the Morphir Python codebase.

## Project Overview

Morphir Python is a port of Morphir to Python, providing functional domain modeling capabilities. The project follows functional programming principles while maintaining Pythonic usability.

## Monorepo Structure

```
morphir-python/
├── packages/
│   ├── morphir/           # Core library - IR models, types, pure functions
│   └── morphir-tools/     # CLI tools and extensions (depends on morphir)
├── tests/
│   ├── unit/             # Unit tests for morphir package
│   └── tools/            # Unit tests for morphir-tools package
└── features/             # BDD feature tests (behave)
```

### Package Responsibilities

**`morphir` (core library)**
- Morphir IR (Intermediate Representation) models, in two versions:
  `morphir.ir.v3` (formats 3.0.0 and 3.1.0; morphir-elm is normative for 3.0.0,
  finos/morphir for the 3.1.0 `Specs` distribution) and `morphir.ir.v4`
  (draft upstream; `morphir.ir` re-exports it). Read `formatVersion` only through
  `morphir.ir.format_version`, convert only through `morphir.ir.migrate`, and keep
  diagnostic codes in `morphir.ir.diagnostics`. See
  [packages/morphir/README.md](packages/morphir/README.md#morphir-ir-versions) and
  the `ir/*` and `tools/ir-interchange` specs in `openspec/specs/`
- Type definitions and type algebra
- Pure functional primitives
- Morphir SDK runtime (`morphir.sdk`): Basics, Char, String, List, Dict, Set, Maybe, Result, Tuple, Decimal, Int, Number
- Zero CLI or IO dependencies
- Should be usable as a standalone library

**`morphir-tools` (CLI/tools)**
- Command-line interface (`morphir-tools`, Typer): `ir inspect`, `ir convert`
- File I/O operations
- Code generation backends
- Depends on `morphir` core library

## Coding Principles

### 1. Functional Programming

**Immutability by Default**

Use frozen dataclasses for all data structures:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Name:
    """An immutable name consisting of parts."""
    parts: tuple[str, ...]
```

**Pure Functions**

Functions should be pure - same inputs always produce same outputs with no side effects:

```python
# Good: Pure function
def qualify(module_name: Name, local_name: Name) -> Name:
    return Name(parts=module_name.parts + local_name.parts)

# Bad: Side effect
def qualify(module_name: Name, local_name: Name) -> Name:
    print(f"Qualifying {local_name}")  # Side effect!
    return Name(parts=module_name.parts + local_name.parts)
```

### 2. Algebraic Data Types (ADTs)

Model domains using sum types (unions) and product types (dataclasses):

```python
from dataclasses import dataclass
from typing import Union

# Product type (AND)
@dataclass(frozen=True)
class FunctionType:
    argument_type: "Type"
    return_type: "Type"

@dataclass(frozen=True)
class RecordType:
    fields: tuple[tuple[str, "Type"], ...]

@dataclass(frozen=True)
class UnitType:
    pass

# Sum type (OR) - Making illegal states unrepresentable
Type = Union[FunctionType, RecordType, UnitType]
```

### 3. Make Illegal States Unrepresentable

Design types so that invalid states cannot be constructed:

```python
# Bad: Allows invalid states
@dataclass
class User:
    name: str | None
    email: str | None
    is_verified: bool  # Can be True even if email is None!

# Good: Invalid states are impossible
@dataclass(frozen=True)
class UnverifiedUser:
    name: str
    email: str

@dataclass(frozen=True)
class VerifiedUser:
    name: str
    email: str
    verified_at: datetime

User = Union[UnverifiedUser, VerifiedUser]
```

### 4. Type Annotations

All code must have complete type annotations. We use strict mode for both mypy and pyright.

```python
from typing import TypeVar, Callable, Sequence

T = TypeVar("T")
U = TypeVar("U")

def map_list(func: Callable[[T], U], items: Sequence[T]) -> list[U]:
    """Apply a function to each item in a sequence."""
    return [func(item) for item in items]
```

### 5. Pattern Matching

Use structural pattern matching for handling sum types:

```python
def type_to_string(t: Type) -> str:
    match t:
        case FunctionType(arg, ret):
            return f"({type_to_string(arg)} -> {type_to_string(ret)})"
        case RecordType(fields):
            field_strs = [f"{name}: {type_to_string(typ)}" for name, typ in fields]
            return f"{{ {', '.join(field_strs)} }}"
        case UnitType():
            return "()"
```

## Code Style

### Docstrings

Use Google-style docstrings:

```python
def process_type(type_def: Type, context: Context) -> Result[ProcessedType, Error]:
    """Process a type definition within a context.

    Args:
        type_def: The type definition to process.
        context: The processing context containing scope information.

    Returns:
        A Result containing either the processed type or an error.

    Raises:
        ValueError: If the type definition is malformed.
    """
```

### Formatting

- Use ruff for formatting (configured in pyproject.toml)
- Line length: 88 characters
- Double quotes for strings
- 4-space indentation

## Testing

### TDD Workflow

Follow red-green-refactor:

1. **Red**: Write a failing test first
2. **Green**: Write minimal code to make it pass
3. **Refactor**: Clean up while keeping tests green

### Unit Tests (pytest)

```python
# tests/unit/test_name.py
import pytest
from morphir.ir import Name

class TestName:
    def test_from_string_splits_on_separators(self) -> None:
        name = Name.from_string("hello.world")
        assert name.parts == ("hello", "world")

    def test_to_string_joins_with_dot(self) -> None:
        name = Name(parts=("hello", "world"))
        assert name.to_string() == "hello.world"
```

### BDD Tests (behave)

Write behavior-driven scenarios for user-facing features:

```gherkin
# features/type_checking.feature
Feature: Type Checking
  As a developer
  I want type checking for my domain models
  So that I catch errors at compile time

  Scenario: Function type matches argument
    Given a function type from Int to String
    And a value of type Int
    When I apply the function to the value
    Then the result type should be String
```

### Test Coverage

- Minimum 80% coverage required
- All public APIs must have tests
- Edge cases and error conditions must be tested

## Development Commands

```bash
# Run all checks
mise run check

# Individual commands
mise run lint          # Linting
mise run format        # Format code
mise run typecheck     # Type checking (mypy + pyright)
mise run test          # Unit tests
mise run test-bdd      # BDD tests
mise run coverage      # Coverage report
```

## Git Workflow

1. Create feature branch from main
2. Make changes following TDD
3. Ensure all checks pass: `mise run check`
4. Submit PR with clear description
5. Address review feedback

## Dependencies

When adding dependencies:

- **morphir package**: Should have minimal/zero dependencies
- **morphir-tools package**: Can have CLI and IO dependencies
- Always pin minimum versions in pyproject.toml

## Error Handling

Use Result types instead of exceptions where appropriate:

```python
from dataclasses import dataclass
from typing import TypeVar, Union

T = TypeVar("T")
E = TypeVar("E")

@dataclass(frozen=True)
class Ok[T]:
    value: T

@dataclass(frozen=True)
class Err[E]:
    error: E

Result = Union[Ok[T], Err[E]]
```

## Performance Considerations

- Use `tuple` instead of `list` for immutable sequences
- Use `frozenset` instead of `set` for immutable sets
- Consider `__slots__` for frequently instantiated classes
- Profile before optimizing

## Documentation

- All public APIs must have docstrings
- Keep README.md up to date
- Document non-obvious design decisions in code comments

## Issue tracking with beads

Work is tracked with [beads](https://github.com/steveyegge/beads) (`bd`) in the **shared Morphir tracker**, not
in a database of this repository. The database lives in finos/morphir and syncs over its `refs/dolt/data` ref.
`.beads/config.yaml` points `bd` at it, so you do not need a finos/morphir checkout.

### Set up and sync

```shell
bd bootstrap          # first time on a machine: clones the shared database
bd dolt pull          # before you start work
bd dolt push          # after you change issues
```

The readable JSONL mirror on the `beads-sync` branch is published from finos/morphir, so pushing the database is
all you need to do here. Run `bd prime` for the full command reference.

### Worktrees

All worktrees use one database: `.beads/embeddeddolt` in the main checkout. A worktree finds it through the git
common directory, inside or outside the repository, so it needs no `.beads/redirect` file.

Run `bd bootstrap` in the main checkout before you open a worktree or start an agent session. Any `bd` command,
including the SessionStart `bd prime` hook, makes an empty local database when it finds none. An empty database in
the main checkout stops `bd bootstrap` ("Database already exists"), and a database in a worktree hides the shared
one.

To repair, move the empty `embeddeddolt` (and `backup`) directory aside and run `bd bootstrap` in the main
checkout again. Use `bd count` to make sure that a database is empty before you move it.

### Find this repository's work

Issues whose work happens here carry the label `repo:morphir-python`:

```shell
bd ready --label repo:morphir-python        # unblocked work
bd list --label repo:morphir-python --all   # everything, including closed
bd show <id> --long                          # description, design, notes and comments
```

## Specs and plans are HTML documents

Write superpowers specs, implementation plans and other documents a person reviews as HTML pages, not Markdown.
A long Markdown plan gets skimmed; an HTML page with a table of contents, tables, collapsible sections and
highlighted code gets read, questioned and corrected, and its explicit structure lets an agent re-read and edit
its own document reliably on every later pass. HTML costs more output tokens per document, so the rule covers
specs, plans and reports, not commit messages, issue text or notes.

- Start from [docs/templates/agent-document.html](docs/templates/agent-document.html). Keep its `<head>` as it is,
  so every document looks the same and the effort goes into content.
- Reference styles and scripts; do not embed them. They are files in the project, in `docs/templates/assets/`: the
  document styles, the highlight.js setup and highlight.js 11.12.0 (vendored from `@highlightjs/cdn-assets`, with
  its license). A document holds only its content, so an agent that reads it does not read the CSS and JavaScript
  too. In a copy of the template, change each `assets/` prefix to the relative path from the copy to
  `docs/templates/assets/`, for example `../../docs/templates/assets/` from `.dev/beads-specs/`. Add no `<style>`
  element, no inline script, no other script and no external resource. If the files do not load, the page shows
  unstyled content and plain code blocks.
- Put code in `<pre><code class="language-python">` (also `json`, `toml`, `bash`, `diff`).
- Escape `<`, `>` and `&`. Give every section an `id` and list the sections in `nav.toc`.
- A plan has one `<section class="task" id="task-N">` with an `<h3>Task N: title</h3>` heading per task.
- Files: `.dev/beads-specs/<epic>.html` and `.dev/beads-plans/<plan-epic>.html`. `.dev/` is gitignored; beads is
  the record (next section).

OpenSpec changes follow this rule only for the design. The `openspec` CLI parses `proposal.md`, `tasks.md` and the
`spec.md` files, so those stay Markdown: they are the contract the tool validates and merges, not the review page.
The design is the HTML page for review. The project schema `openspec/schemas/html-design/`, which
`openspec/config.yaml` selects, makes each change write `design.html` from a copy of this template. Its `<head>`
references the same assets from `openspec/changes/<name>/`, and the archive guidance in `openspec/config.yaml`
adds one `../` when the change moves to `openspec/changes/archive/`. When you change the template's `<head>`, copy
the change into `openspec/schemas/html-design/templates/design.html`. The generated `openspec-*` skills say
`design.md`; in this repository that file is `design.html`.

### Specs, plans and ledgers live in beads

Superpowers specs, implementation plans and execution ledgers are stored in beads, not committed here. This
overrides the superpowers skill defaults for spec, plan and ledger location. OpenSpec changes and specs are
different: they live in `openspec/` and are committed. See [OpenSpec](.github/AGENTS.md#openspec). Beads still
track them. Each change has an epic bead whose spec id is `openspec/changes/<name>`, named in the proposal's
`## Beads` section and in the design's meta line. Each `## N.` group in `tasks.md` is a child task bead, with its
id at the end of the group heading. A requirement that comes from a bead ends with `(bead: <id>)`. The
`html-design` schema instructions and the archive guidance in `openspec/config.yaml` say when to create, claim,
close and relink these beads. Sync tracker changes with `bd dolt push`.

### Working rules

- Commits use Conventional Commits, in plain English, with no AI attribution and no `Co-Authored-By` lines.
- Merges, releases and anything irreversible wait for the maintainer's approval unless a beads memory records it
  (`bd memories approval`).

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
