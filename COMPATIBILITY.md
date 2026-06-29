# Compatibility & reproducibility

This file records the **pinned dependency triple** that the `spedas-claude`
plugin resolves at runtime, how to verify it, and how to bump it. It is the
audit anchor requested in
[issue #3](https://github.com/spedas/spedas_claude/issues/3): reproducibility and
provenance are cornerstones of heliophysics research, and a paper that cites a
SPEDAS MCP workflow must be reproducible years later.

## Pinned compatibility triple

| Component | Pinned value | Source of truth |
|---|---|---|
| `spedas-claude` (this wrapper) | `0.1.0` on `main` (no release tag cut yet — see [CHANGELOG](CHANGELOG.md)) | `.claude-plugin/plugin.json` `version` |
| `spedas_mcp` commit | `5ac9e2087ca7522bff45386c3a8d308e3d9d92b3` | `.mcp.json` `--from spedas-mcp[analysis] @ git+...@<sha>` |
| Requested server extra | `analysis` | `.mcp.json` `--from` package extras; installs server-side PySPEDAS/matplotlib (issue #49) |
| MCP protocol range | `mcp>=1.26.0,<2` | `.mcp.json` `--with` |

The `spedas_mcp` source is pinned to a **full 40-char commit SHA**, so it is
content-addressed and fully reproducible. The MCP protocol dependency carries an
**upper bound** (`<2`) so a future breaking `mcp 2.x` cannot be pulled silently
into an install.

`.mcp.json` therefore launches the server as:

```jsonc
"command": "uvx",
"args": ["--with", "mcp>=1.26.0,<2",
         "--from", "spedas-mcp[analysis] @ git+https://github.com/spedas/spedas_mcp.git@5ac9e2087ca7522bff45386c3a8d308e3d9d92b3",
         "spedas-mcp"]
```

## Verification command

The runtime smoke prints a machine-readable dependency-audit object derived from
`.mcp.json` (no network needed for the audit itself), then starts the pinned
server and lists its tools:

```bash
python scripts/smoke_mcp_runtime.py --json --timeout 300
```

In the JSON output, confirm:

- `dependency_audit.resolved_spedas_mcp_commit` ==
  `5ac9e2087ca7522bff45386c3a8d308e3d9d92b3`
- `dependency_audit.ref_kind` == `"commit"` and `dependency_audit.is_pinned` == `true`
- `dependency_audit.mcp_has_upper_bound` == `true`
- `dependency_audit.analysis_extra_enabled` == `true`
- `ok` == `true` with empty `missing_core_tools` and empty `missing_groups`
- record the reported `tool_count` (currently 30) in your release/methods notes

The offline packaging validator independently enforces that the source stays
pinned and the MCP range stays bounded — a regression to a floating HEAD or an
open-ended floor fails CI:

```bash
python scripts/validate_plugin.py
```

To confirm the pinned commit still exists upstream and matches what you expect:

```bash
gh api repos/spedas/spedas_mcp/commits/5ac9e2087ca7522bff45386c3a8d308e3d9d92b3 >/dev/null
# or, to see the current default-branch HEAD you might bump to:
git ls-remote https://github.com/spedas/spedas_mcp.git HEAD
```

## Bump procedure

When you want to move to a newer `spedas_mcp`:

1. Resolve the target commit:
   `git ls-remote https://github.com/spedas/spedas_mcp.git HEAD` (or pick a tag).
2. Review the upstream diff between the current pin and the target (see the
   supply-chain section below) before adopting it.
3. Replace only the `@<sha>` in `.mcp.json` `--from`; keep the
   `spedas-mcp[analysis] @ git+...` direct-reference shape unless you are
   deliberately changing the default backend policy.
4. Run `python scripts/smoke_mcp_runtime.py --json --timeout 300` and confirm
   `ok: true`, empty `missing_core_tools`/`missing_groups`, and note the new
   `tool_count`.
5. Update the triple table above, the [CHANGELOG](CHANGELOG.md) compatibility
   table, and any docs that quote a specific `tool_count`.
6. Only widen the MCP upper bound (`<2` → `<3`) after verifying the wrapper and
   `spedas_mcp` actually work against that MCP major.

## Supply-chain trust / institutional audit

For lab-wide or funded deployments where software provenance is required in
Methods / Data-Availability sections (NASA, NSF):

- **Verify the source before rollout.** Confirm the pinned SHA exists in the
  official org repo with `gh api repos/spedas/spedas_mcp/commits/<sha>` (or by
  opening `https://github.com/spedas/spedas_mcp/tree/<sha>`), and review the
  upstream code at that commit before adopting it organization-wide. Do not rely
  on `git ls-remote <url> <sha>` for bare commit existence: only advertised refs
  are guaranteed to appear there. A full SHA is content-addressed, so the code you
  reviewed is the code that runs.
- **Pin once, audit once.** Because `.mcp.json` is pinned to a commit, every
  install in your lab resolves the *same* code — you audit a single commit, not a
  moving HEAD.
- **Use an internal fork/tag for stricter control.** If your institution requires
  reviewing changes before they reach users, fork `spedas_mcp` (or mirror it to an
  internal registry), tag a reviewed commit, and point `--from` at
  `git+https://your-host/your-org/spedas_mcp.git@<reviewed-tag>`. The validator
  only requires that the source contains `spedas_mcp` and is pinned, so an
  internal mirror is supported.
- **Record provenance in publications.** In a Methods / Data-Availability
  statement, cite the triple: `spedas-claude` version, the `spedas_mcp` commit
  SHA, and the MCP version range. The plugin ships provenance scaffolding under
  [`templates/provenance/`](templates/provenance/) and a capture helper to record
  the resolved environment per run.

See also [`docs/dependencies.md`](docs/dependencies.md) for the longer narrative
and the pinning recipe, and [`docs/safety.md`](docs/safety.md) for the fetch/
kernel boundary.
