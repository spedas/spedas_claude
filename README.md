# SPEDAS Claude Code plugin

`spedas_claude` is a standalone Claude Code plugin wrapper for the official
[SPEDAS MCP](https://github.com/spedas/spedas_mcp). It does not duplicate the
science tooling. Instead, it packages the MCP connection, Claude-facing workflow
skill, and slash-command style prompts so Claude Code can use SPEDAS as a
heliophysics research assistant.

## What this repo provides

- `.claude-plugin/plugin.json` — plugin metadata.
- `.mcp.json` — starts the `spedas` MCP server from `spedas/spedas_mcp` via `uvx`.
- `skills/spedas-workflow/SKILL.md` — scientific workflow guidance for agents.
- `commands/` — Claude Code command prompts for overview, data, workflows, and geometry.
- `hooks/hooks.json` — placeholder for future safety/provenance hooks.

## Relationship to `spedas_mcp`

The runtime tools live in `spedas_mcp`. This plugin is a thin Claude Code shell:

```text
Claude Code -> spedas_claude plugin -> spedas MCP server -> CDAWeb / PDS / SPICE backends
```

The public mental model is a unified SPEDAS data layer organized by data source
(`cdaweb`, `pds`, `spice`), plus a science workflow layer. The lower-level
`xhelio-*` packages are implementation details of `spedas_mcp`.

## Requirements

- Claude Code with plugin/MCP support.
- `uvx` available on `PATH`.
- Network access the first time `uvx` installs `spedas_mcp` from GitHub.

## Quick smoke prompt

After enabling the plugin in Claude Code, try:

```text
Use SPEDAS to give me an overview of available data sources, then plan a small
MMS solar-wind interval analysis without downloading data yet.
```

Expected behavior:

1. Claude calls `spedas_overview`.
2. Claude uses workflow tools such as `search_spedas_data_sources` and
   `plan_spedas_observation`.
3. Claude prefers unified data-layer tools such as `browse_data_sources` and
   `load_data_source` before any real fetch.

## Local validation

```bash
python scripts/validate_plugin.py
python scripts/smoke_mcp_runtime.py --json
```

`validate_plugin.py` is intentionally network-free; it checks plugin structure and
that `.mcp.json` points at `spedas/spedas_mcp`. `smoke_mcp_runtime.py` is a real
stdio MCP runtime smoke: it starts the configured `spedas` server, performs
`initialize` + `tools/list`, and verifies the core SPEDAS tools without private
credentials, interactive UI, data fetches, or SPICE kernel downloads. It may need
public network access the first time `uvx` installs `spedas_mcp`.

## Real Claude Code CLI smoke

A safe first live check is metadata/planning only:

```bash
claude -p   --plugin-dir .   --mcp-config .mcp.json   --allowedTools mcp__spedas__spedas_overview,mcp__spedas__browse_data_sources,mcp__spedas__plan_spedas_observation   "Use the SPEDAS MCP for a safe metadata-only MMS planning smoke. Do not fetch data or download kernels."
```

Expected result: Claude initializes the `spedas` MCP server and can call SPEDAS MCP tools such as `spedas_overview`, `browse_data_sources`, and `plan_spedas_observation`.

For CI/local wrapper validation without a full Claude session:

```bash
python scripts/validate_plugin.py
python scripts/smoke_mcp_runtime.py --json
```

The runtime smoke isolates SPEDAS data caches and falls back to temporary `uv`/XDG/tmp caches when the default cache location is not writable. First runs may be slow because `uvx` resolves `spedas_mcp` from GitHub.
