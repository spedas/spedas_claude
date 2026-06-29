# SPEDAS Claude Code plugin

`spedas_claude` is a thin Claude Code wrapper for the official
[SPEDAS Agent Kit](https://github.com/spedas/spedas_agent_kit) core. It packages
Claude-facing MCP wiring, slash commands, workflow guidance, safety hooks,
examples, provenance templates, and validation scripts so Claude Code can use
SPEDAS tools without this wrapper owning or duplicating the Agent Kit science
logic.

```text
Claude Code -> spedas_claude plugin -> spedas-agent-kit MCP server -> CDAWeb / PDS / SPICE backends
```

The shared MCP server, tool implementations, and canonical shared skills live in
`spedas/spedas_agent_kit`. The Codex wrapper lives separately in
`spedas/spedas_codex`; this repository is Claude Code only.

## What this repo provides

- `.claude-plugin/plugin.json` — Claude Code plugin metadata and resource declarations.
- `.mcp.json` — starts the pinned `spedas-agent-kit` MCP server from
  `spedas/spedas_agent_kit` via `uvx`.
- `skills/spedas-workflow/SKILL.md` — Claude-consumable SPEDAS workflow guidance.
- `commands/` — Claude Code slash-command prompts: `overview`, `data`, `workflow`,
  `geometry`, and `analyze`.
- `hooks/hooks.json` plus `hooks/fetch_guard.py` — default `PreToolUse` posture for
  real archive fetches and SPICE kernel downloads.
- `scripts/validate_plugin.py` — offline wrapper/packaging validator.
- `scripts/smoke_mcp_runtime.py` — real stdio MCP smoke for the configured server.
- `templates/provenance/` — small provenance scaffolds for reproducible research runs.

## Runtime dependency

`.mcp.json` launches the base Agent Kit pin:

```jsonc
{
  "mcpServers": {
    "spedas": {
      "command": "uvx",
      "args": [
        "--with", "mcp>=1.26.0,<2",
        "--from", "git+https://github.com/spedas/spedas_agent_kit.git@52ccfcb0384dd71fa224bdc65ce813d0fa60a5c7",
        "spedas-agent-kit"
      ]
    }
  }
}
```

The default base surface is intentionally compact: 17 tools covering overview,
planning, unified data-source routing, geometry/SPICE basics, HAPI, and FDSN
entrypoints. Optional Agent Kit extras such as `analysis`, `hapi`, and `fdsn` are
owned by the core package; this wrapper does not request them by default. If a
workflow needs optional analysis tools, first change the Agent Kit source in
`.mcp.json` deliberately (for example to a reviewed `spedas-agent-kit[analysis] @
git+...@<sha>` direct reference) and rerun the validator/smoke.

## Requirements

- Claude Code with plugin + MCP support.
- [`uv`/`uvx`](https://docs.astral.sh/uv/) available on `PATH`.
- Network access the first time `uvx` installs the pinned `spedas_agent_kit` commit
  from GitHub. After that, `uv` caches the resolved environment.
- Python 3.10+ for the validation scripts and hook guard.

## First-run flow

```bash
git clone https://github.com/spedas/spedas_claude.git
cd spedas_claude
python scripts/validate_plugin.py
python scripts/test_validate_plugin.py
python scripts/test_fetch_guard.py
python scripts/test_smoke_groups.py
python scripts/test_cache_paths.py
python scripts/smoke_mcp_runtime.py --json --timeout 300
```

Expected runtime-smoke evidence at the current pin:

```json
{
  "ok": true,
  "tool_count": 17,
  "missing_core_tools": [],
  "missing_groups": [],
  "dependency_audit": {
    "from_arg": "git+https://github.com/spedas/spedas_agent_kit.git@52ccfcb0384dd71fa224bdc65ce813d0fa60a5c7",
    "resolved_spedas_agent_kit_commit": "52ccfcb0384dd71fa224bdc65ce813d0fa60a5c7",
    "ref_kind": "commit",
    "is_pinned": true,
    "mcp_requirement": "mcp>=1.26.0,<2",
    "mcp_has_upper_bound": true,
    "spedas_agent_kit_extras": [],
    "analysis_extra_enabled": false
  }
}
```

The smoke starts the same `uvx ... spedas-agent-kit` command from `.mcp.json`,
performs MCP `initialize` + `tools/list`, verifies the expected groups, and does
not fetch science data or download SPICE kernels.

## Use from Claude Code

Enable this repository as a Claude Code plugin directory, then ask for a
metadata-first SPEDAS plan, for example:

```text
Use SPEDAS to compare CDAWeb, PDS, and SPICE for a Juno magnetic-field analysis
near Jupiter. Do not download large data; produce a plan and provenance.
```

The plugin's default safety hook asks for explicit confirmation before tools make
real archive fetches or allow SPICE kernel downloads. Keep runs artifact-first:
write data, figures, and provenance files rather than pasting large arrays into
chat.

## Maintenance

- Compatibility and bump procedure: [`COMPATIBILITY.md`](COMPATIBILITY.md).
- Dependency narrative: [`docs/dependencies.md`](docs/dependencies.md).
- Cache/env configuration: [`docs/configuration.md`](docs/configuration.md).
- Safety posture: [`docs/safety.md`](docs/safety.md).
- Troubleshooting and issue-routing: [`skills/spedas-workflow/reference/troubleshooting.md`](skills/spedas-workflow/reference/troubleshooting.md).

When changing the Agent Kit pin, update `.mcp.json`, `COMPATIBILITY.md`,
`docs/dependencies.md`, this README's smoke evidence, and the changelog together.
