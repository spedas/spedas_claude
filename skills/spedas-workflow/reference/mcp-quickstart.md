# SPEDAS MCP quickstart

## Claude Code smoke

From the `spedas_claude` repository:

```bash
claude -p   --plugin-dir .   --mcp-config .mcp.json   --allowedTools mcp__spedas__spedas_overview,mcp__spedas__browse_data_sources,mcp__spedas__plan_spedas_observation   "Use the SPEDAS MCP for a safe metadata-only MMS planning smoke. Do not fetch data."
```

Expected: Claude initializes the `spedas` MCP server and can call `spedas_overview`, `browse_data_sources`, and `plan_spedas_observation`.

## Codex smoke

From the `spedas_codex` repository:

```bash
python scripts/validate_plugin.py
python scripts/smoke_mcp_runtime.py --json
```

Then try Codex CLI:

```bash
codex exec --cd . --sandbox workspace-write   "Validate the SPEDAS Codex wrapper without editing files. Prefer the MCP if available; otherwise run the safe runtime smoke and summarize evidence."
```

Depending on Codex CLI version/config, `.mcp.json` may not automatically expose MCP tools in the interactive session. The runtime smoke is the authoritative wrapper check because it starts the same `uvx ... spedas-mcp` command from `.mcp.json` and performs MCP initialize + tools/list.

## Safe first question

Ask for planning, not data download:

> Which SPEDAS MCP tools and data sources should I use for an MMS magnetopause interval around 2015-10-16T13:06Z? Do not fetch data yet.

