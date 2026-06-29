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
               "--from", "git+https://github.com/spedas/spedas_agent_kit.git@52ccfcb0384dd71fa224bdc65ce813d0fa60a5c7",
               "spedas-agent-kit"]
    }
  }
}
```

| Field | Value |
|---|---|
| Source repo | `https://github.com/spedas/spedas_agent_kit.git` |
| Ref | `52ccfcb0384dd71fa224bdc65ce813d0fa60a5c7` |
| Package / console script | `spedas-agent-kit` |
| Requested extras | none by default |
| MCP protocol dep | `mcp>=1.26.0,<2` |

The base pin exposes the current 17-tool Agent Kit surface. Optional extras such
as `analysis`, `hapi`, and `fdsn` are core-package opt-ins; request them only as a
reviewed change to `.mcp.json` and then update this document and smoke evidence.

## Verify

```bash
python scripts/validate_plugin.py
python scripts/smoke_mcp_runtime.py --json --timeout 300
gh api repos/spedas/spedas_agent_kit/commits/52ccfcb0384dd71fa224bdc65ce813d0fa60a5c7 >/dev/null
```

The smoke should report `ok: true`, `tool_count: 17`, empty missing lists, and a
dependency audit with `resolved_spedas_agent_kit_commit` equal to the SHA above.

## Bump

1. Pick/review a target Agent Kit commit.
2. Update `.mcp.json` `--from` to the new full SHA.
3. Run validator + runtime smoke.
4. Update `COMPATIBILITY.md`, this file, README smoke evidence, and changelog.
