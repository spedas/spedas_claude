# SPEDAS Claude Code plugin wrapper

This repository is the Claude Code wrapper for the official SPEDAS Agent Kit
core. The runtime resources live at the repository root for compatibility with
Claude Code plugin discovery:

- plugin manifest: [`../../.claude-plugin/plugin.json`](../../.claude-plugin/plugin.json)
- MCP server config: [`../../.mcp.json`](../../.mcp.json)
- skills: [`../../skills/`](../../skills/)
- slash commands: [`../../commands/`](../../commands/)
- default safety hooks: [`../../hooks/hooks.json`](../../hooks/hooks.json)
- validation: [`../../scripts/validate_plugin.py`](../../scripts/validate_plugin.py)

Codex and future runtimes live in their own thin wrapper repositories; this repo
does not aggregate or own the Agent Kit core.
