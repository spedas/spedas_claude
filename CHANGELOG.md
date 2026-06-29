# Changelog

All notable changes to the **spedas-claude** plugin are documented here. The
format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Naming

This project is referred to three ways, intentionally (see
[CONTRIBUTING.md](CONTRIBUTING.md#naming)):

- **`spedas-claude`** — the Claude Code plugin *manifest name*
  (`.claude-plugin/plugin.json` `name`). This is the identifier Claude Code uses.
- **`spedas_claude`** — the *repository* and Python-style identifier
  (`github.com/spedas/spedas_claude`).
- **"SPEDAS Claude Code plugin"** — the human-readable title used in the README.

## Dependency compatibility

This plugin is a thin wrapper: its only runtime dependency is the official
[SPEDAS MCP server](https://github.com/spedas/spedas_mcp), resolved by `uvx`
from `.mcp.json`.

| spedas-claude | spedas_mcp source | MCP protocol range |
|---|---|---|
| 0.1.0 | `git+https://github.com/spedas/spedas_mcp.git` (unpinned HEAD) | `mcp>=1.26.0` |
| Unreleased | `spedas-mcp[analysis] @ git+https://github.com/spedas/spedas_mcp.git@5ac9e2087ca7522bff45386c3a8d308e3d9d92b3` (pinned commit + analysis extra) | `mcp>=1.26.0,<2` |

> The `[Unreleased]` features below are already committed to `main` but **no version
> boundary has been cut**: `.claude-plugin/plugin.json` still reads `0.1.0` and no git
> tag exists yet (see *Deferred*). Unlike `0.1.0`, the unreleased posture **pins**
> `spedas_mcp` to a full commit SHA and **bounds** the MCP range (`<2`) — see issue
> #3. The authoritative compatibility triple, verification command, and bump
> procedure live in [`COMPATIBILITY.md`](COMPATIBILITY.md). Cutting a real version
> (bumping `plugin.json` and tagging) is a maintainer action.

> **Stability note:** `spedas_mcp` is now resolved from a **pinned commit**
> (`5ac9e20…`), so the tool surface is stable per install and CI can later cache
> the dependency stack keyed on the resolved set. The pinned commit exposes
> **17 primary/base tools** plus analysis-enabled advanced tools from the requested `[analysis]` extra
> (`tool_count: 30`, verified by `scripts/smoke_mcp_runtime.py`). Treat the required
> primary tool names/signatures as fixed at this pin; they only change when the pin
> or requested extras are deliberately changed.

## [Unreleased]

> These features are **committed to `main` and present on disk today**, but a
> release boundary is **deliberately deferred**: the version string stays `0.1.0`
> and no tag is cut until maintainers choose a boundary (see *Deferred*). Installing
> from `main` gets you everything below at version `0.1.0`.

### Fixed
- Enable the default fetch/kernel `PreToolUse` safety gate (issue #6):
  `hooks/hooks.json` now asks Claude Code for explicit permission before real
  archive downloads or `allow_kernel_download: true` geometry/SPICE calls proceed.
  The guard warns on wide time ranges, nudges source-specific fetches toward the
  unified `fetch_data_product` workflow, and is covered by `scripts/test_fetch_guard.py`
  plus validator checks that fail if the hook goes empty or drops a guarded tool.
- Install the upstream server's `analysis` extra by default (issue #49): `.mcp.json`
  now uses `spedas-mcp[analysis] @ git+https://github.com/spedas/spedas_mcp.git@...`
  so Claude-callable analysis/plotting tools have their PySPEDAS/matplotlib backend
  in the MCP subprocess instead of failing first-use with `dependency_missing`. The
  validator now fails if the default source loses `[analysis]`, and the smoke audit
  reports requested extras. HAPI/FDSN heavyweight extras remain opt-in upstream.

### Added
- Reproducible dependency pinning (Batch S, #3): `.mcp.json` now pins `spedas_mcp`
  to commit `5ac9e2087ca7522bff45386c3a8d308e3d9d92b3` and bounds the MCP range to
  `mcp>=1.26.0,<2`. New root [`COMPATIBILITY.md`](COMPATIBILITY.md) records the
  pinned triple, verification command, bump procedure, and supply-chain trust
  model; `docs/dependencies.md`, `docs/safety.md`, and the README were updated to
  the pinned posture. `scripts/validate_plugin.py` now fails if the source goes
  back to an unpinned git URL or the MCP requirement loses its upper bound (with
  negative tests). `scripts/smoke_mcp_runtime.py --json` now emits a
  `dependency_audit` object (configured URL, pinned ref/kind, resolved commit, MCP
  bound) and `cache_diagnostics` (resolved cache paths + writability; refs #5),
  with offline parsing tests.
- Analysis-workflow guidance (Batch H, #41/#42/#43/#44), wrapper-only — no MCP compute
  added here:
  - `skills/spedas-workflow/reference/analysis-recipes.md` — science question →
    pyspedas function → MCP tool chain, with data-preparation and particle-analysis
    subsections (#41).
  - `commands/analyze.md` — `/analyze` guided analysis-tool selection by science
    question, with YAML frontmatter + `$ARGUMENTS` (#42).
  - `skills/spedas-workflow/reference/mission-loaders.md` — mission/instrument →
    canonical CDAWeb dataset-ID cheatsheet + `fetch_data_product` patterns and
    dataset-discovery steps (#43).
  - Canonical event workflows
    `skills/spedas-workflow/reference/{mms-magnetopause,themis-substorm,rbsp-radiation-belt}-workflow.md`
    — plan → fetch → analyze → plot with sanity checks (#44).
  - The analysis/transformation/plotting MCP tools these reference target the
    server's optional `[analysis]` surface when present; the docs keep PySPEDAS
    fallbacks and still tell users to confirm the live tool list before a workflow.
- Repository governance scaffolding: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
  `SECURITY.md`, GitHub issue/PR templates, and this changelog (#19).
- `maintainer` contact in `.claude-plugin/plugin.json` (#19).
- Runnable example script `examples/run_overview.py` exercising a key MCP
  workflow end to end (#19).
- CI hardening: cross-platform/Python validation matrix, `concurrency` control,
  and job/step `timeout-minutes` in `.github/workflows/validate.yml` (#16).
- YAML frontmatter (`description`, `argument-hint`) and `$ARGUMENTS` argument
  substitution on all four slash commands (`overview`, `data`, `workflow`,
  `geometry`), so they can be invoked parameterized (e.g. `/geometry PSP HCI
  2024-06-25`). `validate_plugin.py` now enforces command frontmatter and the
  `$ARGUMENTS` reference, with focused negative tests (#11).

### Deferred
- `uv` dependency caching in CI is still deferred, but the original blocker is now
  resolved: `spedas_mcp` is pinned to a commit (#3), so a future `actions/cache`
  step keyed on the resolved dependency set can be added safely without masking
  upstream breakage. Widening the runtime smoke beyond Linux can follow the same
  step (#16).
- No release tag or package publication has been cut yet; release execution stays
  manual until maintainers choose a version boundary (#19).

## [0.1.0] - 2026-06-25

Initial plugin wrapper: MCP wiring (`.mcp.json`), the `spedas-workflow` skill,
slash commands, the offline `validate_plugin.py` packaging validator, and the
runtime MCP smoke (`smoke_mcp_runtime.py`).
