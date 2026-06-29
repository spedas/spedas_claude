# Dependencies and reproducibility

This document records how `spedas_claude` resolves its one runtime dependency,
the `spedas_mcp` MCP server, and how it is pinned for reproducible, auditable
deployments. It addresses the reproducibility/provenance concern in issue #3.

> The authoritative pinned triple (`spedas-claude` ↔ `spedas_mcp` commit ↔ MCP
> range), the verification command, the bump procedure, and the supply-chain
> trust model live in [`COMPATIBILITY.md`](../COMPATIBILITY.md). This document is
> the narrative companion.

## Runtime dependency: `spedas_mcp`

`.mcp.json` launches the MCP server with `uvx`, **pinned** to an exact upstream
commit, the **analysis** extra enabled, and a **bounded** MCP protocol range:

```jsonc
{
  "mcpServers": {
    "spedas": {
      "command": "uvx",
      "args": ["--with", "mcp>=1.26.0,<2",
               "--from", "spedas-mcp[analysis] @ git+https://github.com/spedas/spedas_mcp.git@5ac9e2087ca7522bff45386c3a8d308e3d9d92b3",
               "spedas-mcp"]
    }
  }
}
```

| Field | Value | Notes |
|---|---|---|
| Source repo | `https://github.com/spedas/spedas_mcp.git` | official SPEDAS org repo |
| Ref | `5ac9e2087ca7522bff45386c3a8d308e3d9d92b3` (full SHA) | content-addressed commit pin — reproducible, auditable |
| Package name | `spedas-mcp` (`0.1.0` at time of writing) | from `spedas_mcp/pyproject.toml` |
| Requested extra | `analysis` | installs the server-side PySPEDAS/matplotlib backend so Claude-callable analysis tools work out of the box (issue #49) |
| Console script | `spedas-mcp` | `[project.scripts] spedas-mcp = "spedas_mcp:main"` |
| Python | `>=3.10` | `requires-python` in `spedas_mcp/pyproject.toml` |
| MCP protocol dep | `mcp>=1.26.0,<2` | floor matches `spedas_mcp`'s own `mcp` extra; upper bound `<2` blocks a breaking `mcp 2.x` from being pulled silently |

## Why the default is pinned (and was changed from floating)

Earlier revisions of this plugin intentionally **floated** on the `spedas_mcp`
default branch, on the theory that the runtime smoke would catch any tool-surface
change. Issue #3 corrects that posture: floating HEAD means every invocation —
from Claude Code, CI, or a researcher's terminal — runs whatever currently sits
at `spedas/spedas_mcp@main`, with no commit pin and no audit trail. A paper
citing a SPEDAS MCP workflow could not be reproduced years later, and an
accidental (or malicious) upstream change would reach every user instantly with
no recovery path.

The default is therefore now pinned to a full commit SHA. Reproducibility and
provenance win over the convenience of auto-tracking upstream. Coordinating a
bump across the two repos is a deliberate, reviewed action (see the bump
procedure in [`COMPATIBILITY.md`](../COMPATIBILITY.md)), not an implicit
every-run resolution.

The packaging validator (`scripts/validate_plugin.py`) now **enforces** this: it
fails if the `spedas_mcp` source regresses to an unpinned git URL, if the default
source stops requesting `[analysis]`, or if the MCP requirement loses its upper
bound. The runtime smoke
(`scripts/smoke_mcp_runtime.py`) additionally prints a dependency-audit object
and verifies the pinned server exposes the expected tool surface.

## Recorded resolved source/HEAD (verified provenance)

The pinned commit was verified against the official upstream at pin time:

- Repo: `github.com/spedas/spedas_mcp`
- Pinned commit: `5ac9e2087ca7522bff45386c3a8d308e3d9d92b3`
- Verified with: `git ls-remote https://github.com/spedas/spedas_mcp.git HEAD`
  (the upstream default-branch HEAD resolved to this SHA at pin time)
- Package version at this commit: `spedas-mcp 0.1.0`
- Runtime smoke against this pin: `ok: true`, required primary tools present,
  empty `missing_core_tools`/`missing_groups`; `tool_count` is currently 30 because the default runtime requests `[analysis]`

To re-verify the pin still exists upstream, query the commit object (or open the
GitHub tree URL). Do not rely on `git ls-remote <url> <sha>` for bare commit
existence, because only advertised refs are guaranteed to appear there:

```bash
gh api repos/spedas/spedas_mcp/commits/5ac9e2087ca7522bff45386c3a8d308e3d9d92b3 >/dev/null
```

## How to bump the pin for a new deployment

See the full bump procedure and supply-chain trust model in
[`COMPATIBILITY.md`](../COMPATIBILITY.md). In short:

1. Resolve the upstream commit you want:
   `git ls-remote https://github.com/spedas/spedas_mcp.git HEAD`
2. Review the upstream diff, then set
   `--from "spedas-mcp[analysis] @ git+https://github.com/spedas/spedas_mcp.git@<sha>"` in `.mcp.json`.
3. Run `python scripts/smoke_mcp_runtime.py --json` and confirm `ok: true` with an
   empty `missing_core_tools`; note the reported `tool_count`.
4. Update the triple in `COMPATIBILITY.md`, the `CHANGELOG.md` table, and this
   document; record the pinned `<sha>` and `tool_count` in your release notes.

Optionally pin the MCP protocol dependency to an exact version
(`--with mcp==<version>`) instead of the bounded `>=…,<2` range for full
determinism.
