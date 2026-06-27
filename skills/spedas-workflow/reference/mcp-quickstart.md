# SPEDAS MCP quickstart

## Claude Code smoke

From the `spedas_claude` repository:

```bash
claude -p   --plugin-dir .   --mcp-config .mcp.json   --allowedTools mcp__spedas__spedas_overview,mcp__spedas__browse_data_sources,mcp__spedas__plan_spedas_observation   "Use the SPEDAS MCP for a safe metadata-only MMS planning smoke. Do not fetch data."
```

Expected: Claude initializes the `spedas` MCP server and can call `spedas_overview`, `browse_data_sources`, and `plan_spedas_observation`.

## Local wrapper validation

From the `spedas_claude` repository, run the offline package checks and the safe MCP runtime smoke:

```bash
python3 scripts/validate_plugin.py
python3 scripts/test_validate_plugin.py
python3 scripts/test_smoke_groups.py
python3 scripts/smoke_mcp_runtime.py --json --timeout 240
```

Expected: validation exits 0, the negative-case validator tests pass, the offline
tool-group self-tests pass, and the runtime smoke returns JSON with `ok: true`,
`tool_count: 40` (against the pinned `spedas_mcp` commit), no missing core tools,
and `missing_groups: []`. The runtime
smoke starts the same `uvx ... spedas-mcp` command declared in `.mcp.json` and
performs MCP initialize + tools/list — verifying the workflow, unified-data,
geometry/SPICE, and CDAWeb/PDS backend tool groups are all present — without
fetching mission data or downloading SPICE kernels.

For concrete per-tool arguments and return shapes, see
[`tool-examples.md`](tool-examples.md),
[`geometry-spice.md`](geometry-spice.md), and
[`backend-compatibility.md`](backend-compatibility.md).

## Safe first question

Ask for planning, not data download:

> Which SPEDAS MCP tools and data sources should I use for an MMS magnetopause interval around 2015-10-16T13:06Z? Do not fetch data yet.

