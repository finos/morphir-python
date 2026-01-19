# Agent Skills

This directory contains agentic skills for the Morphir Python project, following the [Agent Skills Specification](https://agentskills.io/).

## What are Agent Skills?

Agent Skills are folders of instructions, scripts, and resources that AI agents can discover and use to perform tasks more accurately and efficiently. They provide a simple, open format for extending agent capabilities with:

- **Procedural knowledge** - Step-by-step instructions for complex tasks
- **Contextual information** - Project-specific knowledge
- **Scripts** - Executable code for common operations
- **References** - Additional documentation

## Directory Structure

Each skill should be in its own subdirectory with a `SKILL.md` file:

```
.agents/skills/
├── README.md              # This file
├── skill-name/
│   ├── SKILL.md          # Required - skill definition
│   ├── scripts/          # Optional - executable scripts
│   ├── references/       # Optional - additional docs
│   └── assets/           # Optional - templates, data files
└── another-skill/
    └── SKILL.md
```

## SKILL.md Format

Each skill must have a `SKILL.md` file with YAML frontmatter:

```yaml
---
name: skill-name
description: A description of what this skill does and when to use it.
license: Apache-2.0
compatibility: Requirements (e.g., "Requires Python 3.14+")
metadata:
  author: finos
  version: "1.0"
---

# Skill Instructions

Step-by-step instructions for the skill...
```

### Required Fields

| Field | Description |
|-------|-------------|
| `name` | Lowercase, hyphenated name (must match directory name) |
| `description` | What the skill does and when to use it (max 1024 chars) |

### Optional Fields

| Field | Description |
|-------|-------------|
| `license` | License for the skill |
| `compatibility` | Environment requirements |
| `metadata` | Additional key-value metadata |
| `allowed-tools` | Pre-approved tools for the skill |

## Creating a New Skill

1. Create a directory with your skill name (lowercase, hyphenated)
2. Add a `SKILL.md` file with the required frontmatter
3. Add any supporting scripts, references, or assets
4. Test the skill with an agent to verify it works correctly

## Validation

Use the reference library to validate skills:

```bash
npx skills-ref validate ./skill-name
```

## Resources

- [Agent Skills Specification](https://agentskills.io/specification)
- [Example Skills](https://github.com/anthropics/skills)
- [Reference Library](https://github.com/agentskills/agentskills/tree/main/skills-ref)
