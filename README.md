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
- `skills/` — Claude-packaged copy of the 37 canonical Agent Kit shared skills; start with `skills/spedas-skills-index/SKILL.md` or `skills/spedas-workflow/SKILL.md`.
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
        "--from", "git+https://github.com/spedas/spedas_agent_kit.git@df17d32e6ce2da00cd6d8775a90ae726547429df",
        "spedas-agent-kit"
      ]
    }
  }
}
```

The default base surface is intentionally compact: **13 tools** covering
overview, planning, unified data-source routing, and geometry/SPICE basics. The
Agent Kit tool surface is **tiered**, and the rest are gated off by default:

- **+13 analysis tools** (timeseries/coordinate transforms, spectra, particle
  moments/distributions, `render_tplot`, …) register only when the
  `spedas-agent-kit[analysis]` extra is installed.
- **+4 HAPI/FDSN datasource tools** stay hidden from `tools/list` unless
  `SPEDAS_AGENT_KIT_DATASOURCE_TOOLS=1` is set.
- **+8 legacy CDAWeb/PDS compat tools** stay hidden unless
  `SPEDAS_AGENT_KIT_COMPAT_TOOLS=1` is set.

This wrapper does not request any extra or set any gate flag by default. If a
workflow needs optional tools, change the Agent Kit source/env in `.mcp.json`
deliberately (for example a reviewed `spedas-agent-kit[analysis] @ git+...@<sha>`
direct reference, or a gate flag in the server `env`) and rerun the
validator/smoke.

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
  "tool_count": 13,
  "resource_count": 70,
  "missing_base_tools": [],
  "missing_skill_resources": [],
  "missing_preset_resources": [],
  "skill_index_readable": true,
  "workflow_skill_readable": true,
  "preset_index_readable": true,
  "provenance_schema_readable": true,
  "analysis_run_schema_readable": true,
  "missing_groups": [],
  "optional_tiers": {
    "analysis": { "status": "absent", "unlock": "install spedas-agent-kit[analysis]" },
    "datasource": { "status": "absent", "unlock": "SPEDAS_AGENT_KIT_DATASOURCE_TOOLS=1" },
    "compat": { "status": "absent", "unlock": "SPEDAS_AGENT_KIT_COMPAT_TOOLS=1" }
  },
  "dependency_audit": {
    "from_arg": "git+https://github.com/spedas/spedas_agent_kit.git@df17d32e6ce2da00cd6d8775a90ae726547429df",
    "resolved_spedas_agent_kit_commit": "df17d32e6ce2da00cd6d8775a90ae726547429df",
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
performs MCP `initialize` + `tools/list` plus `resources/list` / `resources/read`,
verifies the expected tool groups plus packaged skill and preset resources, and does
not fetch science data or download SPICE kernels.

At the current pin, Agent Kit also exposes packaged runtime-neutral SPEDAS workflow
skills, paper/event reproduction presets, and analysis-bundle provenance schemas
as read-only MCP resources without adding to the 13-tool default surface:

- `spedas-skill://index` — a markdown index of bundled skills.
- `spedas-skill://skills/spedas-skills-index` — the shared skill router.
- `spedas-skill://skills/spedas-workflow` — the primary workflow skill body.
- `spedas-preset://index` — a machine-readable event/paper preset catalog.
- `spedas-preset://events/<id>` — one preset record with interval, data route, recommended skills, quality labels, and caveats.
- `spedas-preset://schemas/reproduction_provenance` — the canonical paper-reproduction provenance JSON schema.
- `spedas-preset://schemas/analysis_bundle_run` — the canonical analysis-bundle `provenance/run.json` schema.

Clients that support MCP resources should call `list_resources` and then
`read_resource` on the relevant `spedas-skill://skills/<name>` or
`spedas-preset://...` URI when they need more workflow detail, a known-event reproduction schema, or the
analysis-bundle run provenance schema. Clients that do not expose resources can still use the
Claude-packaged `skills/spedas-workflow/` files in this wrapper, but should record
that preset/schema resources were unavailable instead of inventing fields.

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
- Skill routing: [`skills/spedas-skills-index/SKILL.md`](skills/spedas-skills-index/SKILL.md).
- Default workflow: [`skills/spedas-workflow/SKILL.md`](skills/spedas-workflow/SKILL.md).

When changing the Agent Kit pin, update `.mcp.json`, `COMPATIBILITY.md`,
`docs/dependencies.md`, this README's smoke evidence, and the changelog together.
