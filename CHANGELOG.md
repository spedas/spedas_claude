# Changelog

All notable changes to the **spedas-claude** plugin are documented here. The
format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Naming

- **`spedas-claude`** — Claude Code plugin manifest name.
- **`spedas_claude`** — repository / Python-style identifier.
- **SPEDAS Claude Code plugin** — human-readable wrapper name.

## Dependency compatibility

This repository is a thin Claude Code wrapper around the official
[SPEDAS Agent Kit](https://github.com/spedas/spedas_agent_kit) core.

| spedas-claude | Agent Kit source | MCP protocol range |
|---|---|---|
| 0.1.0 | `git+https://github.com/spedas/spedas_agent_kit.git@bec499f999846571ae1b2964275f9225ac457c27` (pinned commit, no extras) | `mcp>=1.26.0,<2` |

The current pin exposes the **13-tool base** Agent Kit surface and also exposes
**61 MCP resources** (bundled `spedas-skill://...` skills plus `spedas-preset://...` event/provenance resources, including both paper-reproduction and analysis-bundle run schemas) without
adding default tools. The tool surface is tiered: optional **analysis** tools
(`spedas-agent-kit[analysis]` extra),
**HAPI/FDSN datasource** tools (`SPEDAS_AGENT_KIT_DATASOURCE_TOOLS=1`), and legacy
**CDAWeb/PDS compat** tools (`SPEDAS_AGENT_KIT_COMPAT_TOOLS=1`) are gated opt-ins
rather than this wrapper's default.

## [Unreleased]

### Changed
- Repin the Claude Code wrapper to Agent Kit
  `bec499f999846571ae1b2964275f9225ac457c27`, keeping the wrapper aligned with
  the latest runtime-neutral analysis-bundle provenance guidance, no-fetch
  smoke coverage, and MCP-first geomagnetic overview route gates in the upstream Agent Kit.
- Reframe this repository as a Claude-only thin wrapper. The Agent Kit core owns
  the MCP server, implementation, and canonical shared skills; Codex lives in the
  separate `spedas_codex` wrapper repository.
- Rebuild the runtime smoke around the Agent Kit's current **tiered** surface:
  assert the **13-tool base** default surface, and report (never require) the
  gated analysis / HAPI-FDSN datasource / CDAWeb-PDS compat tiers. The previous
  flat 17-tool expectation (which counted HAPI/FDSN as core) is removed because
  #87/#145 demoted those to a gated datasource tier.

### Removed
- Remove the interim multi-runtime `agent-kit.json` module index, nested
  `plugins/codex/` copy, and `scripts/validate_agent_kit.py` from this Claude
  wrapper.

### Fixed
- Update compatibility, dependency, README, safety, provenance, and validator
  references from the old MCP package/repo/command to
  `spedas_agent_kit` / `spedas-agent-kit`.
- Preserve the default fetch/kernel `PreToolUse` safety gate and offline
  validator/self-test coverage for the Claude wrapper.

## [0.1.0] - 2026-06-25

Initial plugin wrapper: MCP wiring (`.mcp.json`), the `spedas-workflow` skill,
slash commands, the offline `validate_plugin.py` packaging validator, and the
runtime MCP smoke (`smoke_mcp_runtime.py`).
