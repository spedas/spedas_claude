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

| spedas-claude | spedas_mcp source | MCP protocol floor |
|---|---|---|
| 0.1.0 | `git+https://github.com/spedas/spedas_mcp.git` (unpinned HEAD) | `mcp>=1.26.0` |
| Unreleased | `git+https://github.com/spedas/spedas_mcp.git` (unpinned HEAD) | `mcp>=1.26.0` |

> The `[Unreleased]` features below are already committed to `main` but **no version
> boundary has been cut**: `.claude-plugin/plugin.json` still reads `0.1.0` and no git
> tag exists yet (see *Deferred*). They carry the same dependency posture as `0.1.0`
> — same `spedas_mcp` source and `mcp>=1.26.0` floor — so this row changes nothing
> about reproducibility; it exists only so the unreleased work is not invisible in
> this table. Cutting a real version (bumping `plugin.json` and tagging) is a
> maintainer action.

> **Stability note:** `spedas_mcp` is currently resolved from git `HEAD`, so the
> exact tool set can change between installs. Pinning `spedas_mcp` to a tag or
> commit (a tracked follow-up) will let CI cache the dependency stack and let
> this table promise a reproducible tool surface. Until then, treat the tool
> names and signatures as **subject to upstream change**.

## [Unreleased]

> These features are **committed to `main` and present on disk today**, but a
> release boundary is **deliberately deferred**: the version string stays `0.1.0`
> and no tag is cut until maintainers choose a boundary (see *Deferred*). Installing
> from `main` gets you everything below at version `0.1.0`.

### Added
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
  - The analysis/transformation/plotting MCP tools these reference are **proposed** on
    `spedas_mcp` (#12–#22) and tagged `[proposed]`; the docs give PySPEDAS fallbacks and
    do not claim unreleased tools are available.
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
- `uv` dependency caching is intentionally deferred until `spedas_mcp` is pinned
  to a tag or commit; caching an unpinned git-HEAD install could mask upstream
  breakage that the runtime smoke is meant to catch (#16).
- No release tag or package publication has been cut yet; release execution stays
  manual until maintainers choose a version boundary (#19).

## [0.1.0] - 2026-06-25

Initial plugin wrapper: MCP wiring (`.mcp.json`), the `spedas-workflow` skill,
slash commands, the offline `validate_plugin.py` packaging validator, and the
runtime MCP smoke (`smoke_mcp_runtime.py`).
