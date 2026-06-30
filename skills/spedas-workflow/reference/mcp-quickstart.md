# SPEDAS Agent Kit MCP quickstart

## Claude Code smoke

From the `spedas_claude` repository:

```bash
claude -p   --plugin-dir .   --mcp-config .mcp.json   --allowedTools mcp__spedas__spedas_overview,mcp__spedas__browse_data_sources,mcp__spedas__plan_spedas_observation   "Use the SPEDAS Agent Kit MCP for a safe metadata-only MMS planning smoke. Do not fetch data."
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
`tool_count: 13` (the base surface against the pinned `spedas_agent_kit` commit),
no missing base tools, and `missing_groups: []`. Every entry under
`optional_tiers` reports `"status": "absent"` because this wrapper unlocks no
optional tier by default. The runtime smoke starts the same
`uvx ... spedas-agent-kit` command declared in `.mcp.json` and performs MCP
initialize + tools/list — verifying the workflow, unified-data, and
geometry/SPICE base tool groups are all present, and also verifies the packaged
SPEDAS skill and preset resources with `resources/list` / `resources/read`, without fetching
mission data or downloading SPICE kernels. (The HAPI/FDSN datasource tools and
the legacy CDAWeb/PDS compat tools are gated off by default and are reported as
optional tiers, not base groups.)

## MCP skill resources

The current Agent Kit pin exposes the packaged SPEDAS workflow skills as
read-only MCP resources while keeping `tools/list` compact:

- `spedas-skill://index` — markdown index of bundled skills.
- `spedas-skill://skills/spedas-workflow` — primary workflow skill body.

Use `list_resources` to discover the full catalog and `read_resource` on a
`spedas-skill://skills/<name>` URI when the conversation needs deeper workflow
guidance than the tool schemas alone provide.

## MCP preset resources

The current Agent Kit pin also exposes paper/event reproduction presets and the
canonical provenance schema as read-only resources, not tools:

- `spedas-preset://index` — read this before hand-authoring time ranges for known solar-wind or magnetospheric events.
- `spedas-preset://events/<id>` — one preset record with interval, data route, recommended skills, quality labels, and caveats.
- `spedas-preset://schemas/reproduction_provenance` — the JSON schema for paper/event reproduction provenance.

When Claude Code exposes MCP resources, use `resources/list` / `resources/read` for
these URIs before making a known-event plan or provenance object. If the runtime only
exposes MCP tools, keep the workflow artifact-first and explicitly record that preset
resources were unavailable rather than pretending they are tool calls.

For concrete per-tool arguments and return shapes, see
[`tool-examples.md`](tool-examples.md),
[`geometry-spice.md`](geometry-spice.md), and
[`backend-compatibility.md`](backend-compatibility.md).

## Safe first question

Ask for planning, not data download:

> Which SPEDAS Agent Kit MCP tools and data sources should I use for an MMS magnetopause interval around 2015-10-16T13:06Z? Do not fetch data yet.
