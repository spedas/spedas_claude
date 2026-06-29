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
| 0.1.0 | `git+https://github.com/spedas/spedas_agent_kit.git@52ccfcb0384dd71fa224bdc65ce813d0fa60a5c7` (pinned commit, base extras) | `mcp>=1.26.0,<2` |

The current pin exposes the 17-tool base Agent Kit surface. Optional Agent Kit
extras such as `analysis`, `hapi`, and `fdsn` are deliberate opt-ins rather than
this wrapper's default.

## [Unreleased]

### Changed
- Point the Claude Code wrapper at the renamed `spedas_agent_kit` core repo and
  `spedas-agent-kit` command, pinned to `52ccfcb0384dd71fa224bdc65ce813d0fa60a5c7`.
- Reframe this repository as a Claude-only thin wrapper. The Agent Kit core owns
  the MCP server, implementation, and canonical shared skills; Codex lives in the
  separate `spedas_codex` wrapper repository.
- Keep the runtime smoke on the compact 17-tool base Agent Kit surface. Optional
  analysis/HAPI/FDSN extras remain core-package opt-ins.

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
