# SPEDAS Agent Kit for Claude Code

The Claude Code runtime module is currently the repository root. It stays there so
existing Claude Code plugin installs keep working while the public product identity
moves from "SPEDAS Claude" toward **SPEDAS Agent Kit**.

Claude Code module entry points:

- plugin manifest: [`../../.claude-plugin/plugin.json`](../../.claude-plugin/plugin.json)
- MCP server config: [`../../.mcp.json`](../../.mcp.json)
- skills: [`../../skills/`](../../skills/)
- slash commands: [`../../commands/`](../../commands/)
- default safety hooks: [`../../hooks/hooks.json`](../../hooks/hooks.json)
- validation: [`../../scripts/validate_plugin.py`](../../scripts/validate_plugin.py)

Future repo-level cleanup can move this runtime under `plugins/claude-code/` after
installer expectations and existing links are migrated. This PR intentionally avoids
that breaking move.
