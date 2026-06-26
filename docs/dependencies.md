# Dependencies and reproducibility

This document records how `spedas_claude` resolves its one runtime dependency,
the `spedas_mcp` MCP server, and how to pin it for reproducible deployments. It
addresses the reproducibility/provenance concern in issue #3.

## Runtime dependency: `spedas_mcp`

`.mcp.json` launches the MCP server with `uvx`:

```jsonc
{
  "mcpServers": {
    "spedas": {
      "command": "uvx",
      "args": ["--with", "mcp>=1.26.0",
               "--from", "git+https://github.com/spedas/spedas_mcp.git",
               "spedas-mcp"]
    }
  }
}
```

| Field | Value | Notes |
|---|---|---|
| Source repo | `https://github.com/spedas/spedas_mcp.git` | official SPEDAS org repo |
| Ref | default branch (floating) | no explicit `@ref` — resolves to the repo's current default branch HEAD |
| Package name | `spedas-mcp` (`0.1.0` at time of writing) | from `spedas_mcp/pyproject.toml` |
| Console script | `spedas-mcp` | `[project.scripts] spedas-mcp = "spedas_mcp:main"` |
| Python | `>=3.10` | `requires-python` in `spedas_mcp/pyproject.toml` |
| MCP protocol dep | `mcp>=1.26.0` | matches `spedas_mcp`'s own optional `mcp` extra; pinned as a floor here so the plugin asserts a known-good MCP version |

## Why the default is intentionally *not* pinned to an exact commit

Pinning `--from git+...@<sha>` makes a plain clone + smoke depend on a specific
`spedas_mcp` commit existing and matching the plugin's expected tool surface.
Because `spedas_claude` and `spedas_mcp` are two separate repos with independent
release cadences, a hard pin in the default config would require coordinating a
tag/commit bump across both repos on every `spedas_mcp` change, and would break
the "clone and try it now" onboarding flow (issue #12) whenever the pinned commit
drifts from what a new user expects.

So the default floats on the `spedas_mcp` default branch. The packaging validator
(`scripts/validate_plugin.py`) and the runtime smoke (`scripts/smoke_mcp_runtime.py`)
together catch the failure mode a pin would otherwise prevent: if the floating
HEAD changes the tool surface, the smoke's `missing_core_tools` becomes non-empty
and CI fails.

## Recorded resolved source/HEAD (provenance snapshot)

At the time this document was written, the locally available `spedas_mcp` mirror
resolved to:

- Repo: `github.com/spedas/spedas_mcp` (also mirrored at `github.com/huangzesen/spedas-mcp`)
- Branch: `main`
- HEAD (from the local mirror): `e333a1e376b2f16c967af04467b573c9c82a2dbd`
  (`docs: add Juno PDS SPICE workflow (#4)`)
- Package version: `spedas-mcp 0.1.0`

> **Caveat (unproven):** this HEAD was read from a local development mirror whose
> `main` may be ahead of, behind, or otherwise diverged from `spedas/spedas_mcp`
> `main` on GitHub. It is recorded here as a provenance anchor, **not** as a
> verified upstream commit. Before relying on it as a pin, confirm the exact
> upstream SHA with:
>
> ```bash
> git ls-remote https://github.com/spedas/spedas_mcp.git HEAD
> ```

## How to pin for a reproducible deployment

When you need byte-for-byte reproducibility (e.g. a tagged release or an offline
lab), pin the exact ref in `.mcp.json`:

```jsonc
"--from", "git+https://github.com/spedas/spedas_mcp.git@<commit-or-tag>"
```

Recommended procedure:

1. Resolve the upstream commit you want:
   `git ls-remote https://github.com/spedas/spedas_mcp.git HEAD`
2. Set `--from git+https://github.com/spedas/spedas_mcp.git@<sha>` in `.mcp.json`.
3. Run `python scripts/smoke_mcp_runtime.py --json` and confirm `ok: true` with an
   empty `missing_core_tools`.
4. Record the pinned `<sha>` and the smoke's `tool_count` in your release notes.

Optionally also pin the MCP protocol dependency to an exact version
(`--with mcp==<version>`) instead of the `>=` floor for full determinism.
