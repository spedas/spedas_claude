# SPEDAS Agent Kit runtime modules

The SPEDAS Agent Kit is the umbrella layer above `spedas_mcp`: it bundles the MCP
server configuration with runtime-specific skills, commands/instructions, hooks,
examples, and validation.

Implemented modules in this repository:

| Module | Runtime | Location | Notes |
| --- | --- | --- | --- |
| Claude Code | Claude Code plugin | repository root (`.`), indexed by `plugins/claude-code/README.md` | Kept at the root for backward-compatible Claude Code plugin installs. |
| Codex | Codex plugin | `plugins/codex/` | Imported from the validated `spedas/spedas_codex` wrapper as the second runtime module, with MCP pin/skills/smoke helpers aligned to the root Claude Code module. |

Planned next module: OpenCode (`plugins/opencode/`).

The canonical machine-readable index is [`../agent-kit.json`](../agent-kit.json).
