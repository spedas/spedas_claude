# Security Policy

The **spedas-claude** plugin is a wrapper that, on use, installs and runs the
official SPEDAS MCP server over the network (`uvx` from
`git+https://github.com/spedas/spedas_mcp.git`) and writes caches under
`~/.cache/spedas/*`. Because it executes code fetched at runtime, we take
disclosure seriously.

`spedas_mcp` is resolved from the upstream **default branch (unpinned)** — there is
no `@<tag/commit>` ref in `.mcp.json` — so whatever is on that branch executes on
every CI run and on a user's first run. To pin an exact commit/tag for a
reproducible or audited deployment, follow the procedure in
[docs/dependencies.md](docs/dependencies.md).

## What belongs here vs. upstream

- **This repo (`spedas_claude`)** — issues in the plugin wrapper: the MCP wiring
  in `.mcp.json`, the default fetch/kernel guard under `hooks/`, the validators and
  smoke scripts, cache-path handling, or anything that could cause the plugin to
  fetch/run unintended code.
- **[spedas/spedas_mcp](https://github.com/spedas/spedas_mcp)** — vulnerabilities
  in the scientific MCP server itself (the tools, data fetching, SPICE kernel
  handling). Please report those to that project.

If you are unsure which layer is affected, report it here and we will coordinate.

## Reporting a vulnerability

**Do not open a public GitHub issue for a security problem.**

Preferred: use GitHub's
[private vulnerability reporting](https://github.com/spedas/spedas_claude/security/advisories/new)
("Report a vulnerability" under the **Security** tab). This keeps the report
private until a fix is ready.

Please include:

- the affected component (which file / MCP tool / cache path);
- the plugin version (`.claude-plugin/plugin.json` `version`) and your OS /
  Python / `uv` versions;
- steps to reproduce, and the impact you observed.

## Supported versions

This is an early-stage (`0.x`) project; only the latest release on `main`
receives security fixes. See [CHANGELOG.md](CHANGELOG.md) for the current
version and the `spedas_mcp` compatibility note.

## Scope notes

- The shipped `hooks/hooks.json` includes an enabled-by-default `PreToolUse`
  fetch/kernel guard. It is intended to ask for permission before real archive
  downloads or large SPICE kernel downloads; reports should include the hook
  event JSON, tool name, and whether the guard asked, stayed quiet, or failed.
- Cache directories are configurable via the environment variables documented in
  [docs/configuration.md](docs/configuration.md); reports about cache location
  should account for that.
