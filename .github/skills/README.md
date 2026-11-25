# Agent skills

Shared skills follow the [Agent Skills specification](https://agentskills.io/specification).
Their instructions use ordinary file access, terminal commands, and available tracker connectors.

## OpenSpec across agents

The `openspec` and `openspec-*` skills come from the OpenSpec CLI. `openspec` is the entry point: it answers
OpenSpec questions and sends a request to the workflow skill that does the work. OpenSpec 2 writes one copy of
each skill to `.agents/skills/`. Agents that have their own skill directory get a relative link to that copy.
Agents that read `.agents/skills/` get no extra copy. Do not edit the skills or the links. To change the version,
install it, run `openspec update`, and commit the result. [OpenSpec](../AGENTS.md#openspec) gives the install
command.

| Agent | Skill directory |
|---|---|
| Codex, GitHub Copilot, Cursor, Gemini CLI, OpenCode, Antigravity, Muse Code and other `.agents` readers | `.agents/skills/openspec*/` |
| Claude Code | `.claude/skills/openspec*/` (links) |
| Grok Build | `.grok/skills/openspec*/` (links) |
| Devin Desktop (formerly Windsurf) | `.devin/skills/openspec*/` (links) |

On Windows, set `git config --global core.symlinks true` before you clone, or each link checks out as a small
text file. `openspec update` then replaces it with a plain copy. The Copilot cloud coding-agent files
(`.github/workflows/copilot-setup-steps.yml` and `.github/agents/openspec.agent.md`) are not installed, and
`openspec/config.yaml` records `cloudAgent: false`.
