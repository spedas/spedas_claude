# Compatibility & reproducibility

This file records the pinned runtime dependency triple for the `spedas-claude`
Claude Code wrapper and how to verify or bump it. The goal is reproducible
heliophysics workflows: a paper or lab note should be able to cite the wrapper,
the Agent Kit commit, and the MCP protocol range.

## Pinned compatibility triple

| Component | Pinned value | Source of truth |
|---|---|---|
| `spedas-claude` wrapper | `0.1.0` on `main` (no release tag cut yet) | `.claude-plugin/plugin.json` |
| `spedas_agent_kit` commit | `e6e27a2a2ced1468eeef93ab0d0e1870a57538d9` | `.mcp.json` `--from git+https://github.com/spedas/spedas_agent_kit.git@e6e27a2a2ced1468eeef93ab0d0e1870a57538d9` |
| Default Agent Kit extras | none | base 13-tool surface; analysis/datasource/compat tiers are gated opt-ins |
| MCP protocol range | `mcp>=1.26.0,<2` | `.mcp.json` `--with` |

`.mcp.json` launches:

```jsonc
"command": "uvx",
"args": ["--with", "mcp>=1.26.0,<2",
         "--from", "git+https://github.com/spedas/spedas_agent_kit.git@e6e27a2a2ced1468eeef93ab0d0e1870a57538d9",
         "spedas-agent-kit"]
```

The Agent Kit tool surface is tiered. The base/default surface is **13 tools**.
Optional tiers are gated and off by default in this wrapper: **+13 analysis**
tools (requires the `spedas-agent-kit[analysis]` extra), **+4 HAPI/FDSN**
datasource tools (`SPEDAS_AGENT_KIT_DATASOURCE_TOOLS=1`), and **+8 legacy
CDAWeb/PDS compat** tools (`SPEDAS_AGENT_KIT_COMPAT_TOOLS=1`).

The source is pinned to a full 40-character commit SHA. The MCP dependency has an
upper bound so a future breaking `mcp 2.x` is not pulled silently.

## Verification

```bash
python scripts/validate_plugin.py
python scripts/smoke_mcp_runtime.py --json --timeout 300
```

In the smoke JSON, confirm:

- `dependency_audit.resolved_spedas_agent_kit_commit == "e6e27a2a2ced1468eeef93ab0d0e1870a57538d9"`
- `dependency_audit.ref_kind == "commit"`
- `dependency_audit.is_pinned == true`
- `dependency_audit.mcp_has_upper_bound == true`
- `dependency_audit.spedas_agent_kit_extras == []`
- `dependency_audit.analysis_extra_enabled == false`
- `ok == true`, empty `missing_base_tools`, empty `missing_groups`
- `tool_count == 13` and `resource_count == 61` for the current base/resource surface
- empty `missing_skill_resources` and `missing_preset_resources`
- `provenance_schema_readable == true` and `analysis_run_schema_readable == true`
- every entry under `optional_tiers` reports `"status": "absent"` (this wrapper
  unlocks no optional tier by default)

To confirm the commit still exists upstream:

```bash
gh api repos/spedas/spedas_agent_kit/commits/e6e27a2a2ced1468eeef93ab0d0e1870a57538d9 >/dev/null
```

## Bump procedure

1. Resolve the target Agent Kit commit, e.g.
   `git ls-remote https://github.com/spedas/spedas_agent_kit.git HEAD`.
2. Review the upstream diff before adopting it.
3. Replace only the `@<sha>` in `.mcp.json` unless you are deliberately changing
   the default optional-extra policy.
4. Run the validator and runtime smoke above.
5. Update this file, `docs/dependencies.md`, README smoke evidence, and
   `CHANGELOG.md` with the new commit/tool-count evidence.
6. Only widen the MCP upper bound after verifying the wrapper and Agent Kit work
   against that MCP major.

## Supply-chain note

For lab deployments, audit the pinned Agent Kit commit in the official
`spedas/spedas_agent_kit` repository or use an internally reviewed fork/tag. A
full SHA is content-addressed: the code reviewed is the code `uvx` resolves.
