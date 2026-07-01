# Dependencies and reproducibility

`spedas_claude` has one runtime dependency: the official
[`spedas_agent_kit`](https://github.com/spedas/spedas_agent_kit) MCP server. The
wrapper resolves it with `uvx` from `.mcp.json` and pins it to a full commit SHA
for reproducibility.

## Current runtime command

```jsonc
{
  "mcpServers": {
    "spedas": {
      "command": "uvx",
      "args": ["--with", "mcp>=1.26.0,<2",
               "--from", "git+https://github.com/spedas/spedas_agent_kit.git@a6e8f7e486c3d7fdfc0aeb17fc1b3a9ffe8adfd0",
               "spedas-agent-kit"]
    }
  }
}
```

| Field | Value |
|---|---|
| Source repo | `https://github.com/spedas/spedas_agent_kit.git` |
| Ref | `a6e8f7e486c3d7fdfc0aeb17fc1b3a9ffe8adfd0` |
| Package / console script | `spedas-agent-kit` |
| Requested extras | none by default |
| MCP protocol dep | `mcp>=1.26.0,<2` |

The base pin exposes the current **13-tool base** Agent Kit surface. The surface
is tiered: optional **analysis** tools (`spedas-agent-kit[analysis]` extra), the
**HAPI/FDSN datasource** tools (`SPEDAS_AGENT_KIT_DATASOURCE_TOOLS=1`), and legacy
**CDAWeb/PDS compat** tools (`SPEDAS_AGENT_KIT_COMPAT_TOOLS=1`) are gated off by
default. Unlock a tier only as a reviewed change to `.mcp.json` and then update
this document and the smoke evidence.

## Verify

```bash
python scripts/validate_plugin.py
python scripts/smoke_mcp_runtime.py --json --timeout 300
gh api repos/spedas/spedas_agent_kit/commits/a6e8f7e486c3d7fdfc0aeb17fc1b3a9ffe8adfd0 >/dev/null
```

The smoke should report `ok: true`, `tool_count: 13`, `resource_count: 61`, empty
missing tool/resource lists, readable `spedas-skill://index`,
`spedas-skill://skills/spedas-workflow`, and the bundled provenance schema
resources, every `optional_tiers` entry `"status": "absent"`, and a dependency
audit with `resolved_spedas_agent_kit_commit` equal to the SHA above.

## Bump

1. Pick/review a target Agent Kit commit.
2. Update `.mcp.json` `--from` to the new full SHA.
3. Run validator + runtime smoke.
4. Update `COMPATIBILITY.md`, this file, README smoke evidence, and changelog.
