---
name: spedas-workflow
description: Use when working with SPEDAS, PySPEDAS, or the SPEDAS Agent Kit MCP plugin to discover heliophysics data sources, choose missions/parameters/time ranges, plan science workflows, run safe metadata-first checks, fetch/export artifacts only when appropriate, and preserve provenance.
---

# SPEDAS / PySPEDAS workflow skill

Use this skill when the user asks a heliophysics data question, wants to use SPEDAS/PySPEDAS, or wants an agent runtime to call the SPEDAS Agent Kit MCP plugin.

## Operating model

Think in four layers:

1. **Science question** — event, mission, interval, coordinate system, expected signal, and success criteria.
2. **Workflow layer** — SPEDAS Agent Kit MCP planning/comparison/bundle tools or PySPEDAS recipes.
3. **Unified data layer** — source category `cdaweb`, `pds`, or `spice`; do not expose `xhelio-*` as the user-facing mental model. `spice` is a discovery category here (`browse_data_sources` / `load_data_source` / `browse_data_parameters`), but SPICE geometry is **not** fetched via `fetch_data_product` — route ephemerides/frames through the geometry/SPICE tools (see `reference/geometry-spice.md`).
4. **Artifacts and provenance** — outputs are paths, manifests, hashes, plots, tables, and notes; avoid dumping large arrays/CDF/tplot objects into chat.

## Default workflow

1. Restate the science target: mission(s), time window, parameters, geometry/coordinate needs, and whether real data fetch is allowed.
2. Start metadata-first:
   - MCP: call `spedas_overview`, then `search_spedas_data_sources` or `browse_data_sources`.
   - PySPEDAS: identify the relevant mission loader and variables before loading data.
3. Plan before fetch:
   - MCP: use `plan_spedas_observation` and, when multiple archives are relevant, `compare_cdaweb_pds_spice`.
   - PySPEDAS: decide `trange`, `probe`, `datatype`, `level`, variable names, and cache directory.
4. Fetch only when the user/task calls for it. Keep windows narrow, make caches explicit, and expect public archive rate limits.
5. Save artifacts with provenance: request, tool call/source, versions, cache/output roots, SHA-256 where useful, variable/source mapping, and caveats.
   When the runtime exposes MCP resources, read `spedas-preset://index` before hand-authoring a known paper/event interval and use `spedas-preset://schemas/reproduction_provenance` before inventing a provenance JSON shape.
   If Claude Code exposes tools but not resources, keep the workflow artifact-first and record that preset/schema resources were unavailable.
6. Report results conclusion-first, with paths and exact next actions.

## Preferred SPEDAS Agent Kit MCP tools

- Discovery and mental model: `spedas_overview`.
- Science planning: `search_spedas_data_sources`, `plan_spedas_observation`, `compare_cdaweb_pds_spice`, `create_spedas_analysis_bundle`.
- Unified data layer: `browse_data_sources`, `load_data_source`, `browse_data_parameters`, `fetch_data_product`, `manage_data_cache`.
- Geometry/SPICE: use `get_ephemeris`, `compute_distance`, and `transform_coordinates`; use `browse_data_sources(source_type="spice")` / `manage_data_cache(source_type="spice", action="status")` for discovery and cache context. Geometry is its own workflow — route SPICE positions/frames here, not through `fetch_data_product`.
- Optional archive-specific tools: `browse_hapi_catalog` / `fetch_hapi_data` and `browse_fdsn_datasets` / `fetch_fdsn_data` are visible but may require server extras; use them only when the science question calls for those archives.

For concrete arguments, return-shape notes, and no-fetch caveats for every tool,
see `reference/tool-examples.md`, `reference/geometry-spice.md`, and
`reference/backend-compatibility.md`.

## PySPEDAS package workflow

> **PySPEDAS is a separate layer this plugin does not install.** The MCP tools
> above run via `uvx` and need no Python environment of yours. PySPEDAS + `pytplot`
> are a *local* Python package the **user** installs themselves (`pip install
> pyspedas`); they are not provided by the plugin or by Claude's tool runtime. If a
> PySPEDAS recipe raises `ModuleNotFoundError: No module named 'pyspedas'`, that is
> a missing local install (classify it as an environment-scoping gap, **not** an MCP
> wrapper bug) — see `reference/troubleshooting.md`. Confirm the user has a Python
> env with PySPEDAS before suggesting these recipes.

Use PySPEDAS directly when the user needs Python/tplot workflows, plotting, existing mission routines, or compatibility with SPEDAS notebooks/scripts.

Minimum safe pattern:

```python
import pyspedas
from pytplot import get_data, tplot_names

trange = ["2015-10-16/13:06", "2015-10-16/13:08"]
pyspedas.mms.fgm(trange=trange, probe="1", data_rate="srvy", level="l2", time_clip=True)
print(tplot_names())
```

Before expanding the interval, confirm variable names, data cadence, download/cache behavior, and whether the public archive is rate-limiting.

## Failure classification

When something fails, label it precisely:

- **MCP wrapper issue** — plugin config, server startup, schema, runtime smoke, CLI integration.
- **SPEDAS Agent Kit MCP issue** — unified tool behavior, planning semantics, parameter mapping, error shape.
- **Backend/data gap** — missing CDAWeb variable, incomplete PDS label/metadata, unavailable SPICE kernel.
- **External service limit** — network, archive outage, timeout, HTTP 429, cold cache.
- **Docs/skills gap** — the tool works but first-user instructions or scientific method are unclear.

For per-class error signals, a triage decision tree, diagnostic commands, **which
repo to file each class in** (`spedas_claude` vs `spedas_agent_kit` vs backend archives),
and which provenance artifacts to attach, see `reference/troubleshooting.md`.

## References in this skill folder

- `reference/tool-examples.md` — concrete arguments, return shapes, and no-fetch caveats for the unified workflow + data tools.
- `reference/geometry-spice.md` — current geometry/SPICE tools, safe examples, and the metadata-vs-kernel-download line.
- `reference/backend-compatibility.md` — unified facade, optional backend entrypoints, and when to leave the compact public surface.
- `reference/mcp-quickstart.md` — Claude plugin smoke, local wrapper validation, and first user checks.
- `reference/source-selection.md` — choose CDAWeb vs PDS vs SPICE.
- `reference/pyspedas-patterns.md` — safe PySPEDAS loading/plotting/export patterns.
- `reference/artifact-provenance.md` — what to save for reproducible science (templates in `templates/provenance/`).
- `reference/troubleshooting.md` — failure taxonomy runbook: per-class signals, triage tree, issue routing.
- `reference/science-examples.md` — starter prompts for MMS, Juno, PSP, THEMIS, and upstream solar wind.
- `reference/analysis-recipes.md` — science question → pyspedas function → MCP tool chain, with data-preparation and particle-analysis subsections (current vs. proposed analysis-layer tools).
- `reference/mission-loaders.md` — mission → instruments → canonical CDAWeb dataset IDs → `fetch_data_product` patterns, with dataset-discovery steps (MMS, THEMIS, PSP, Wind/ACE, OMNI, RBSP, …).
- `reference/mms-magnetopause-workflow.md` — canonical MMS magnetopause event: plan → fetch → analyze (LMN/MVA, moments) → plot, with sanity checks.
- `reference/themis-substorm-workflow.md` — canonical THEMIS substorm event: ground + probe plan → fetch → Pi2/dipolarization analysis → plot.
- `reference/rbsp-radiation-belt-workflow.md` — canonical RBSP radiation-belt event: plan → fetch → L-shell/spectra → plot.

## Analysis-layer tool maturity

Beyond the 13 current base MCP tools (discovery, planning, unified data, and geometry/SPICE), the
analysis/transformation/plotting layer is **proposed** on `spedas_agent_kit` (issues
#12–#22) and may not be released yet. The recipe/workflow references above tag these
`[proposed: spedas_agent_kit #NN]`. **Confirm a proposed tool is live** (via
`spedas_overview` / the active tool list) before presenting it as runnable; otherwise
use the PySPEDAS fallback (`reference/pyspedas-patterns.md`) and say so. The
`/analyze` command (`commands/analyze.md`) walks this selection interactively.

Repo-level docs (outside this skill folder): `docs/configuration.md` (env/cache
variables), `docs/safety.md` (fetch/kernel boundary + opt-in), `docs/dependencies.md`
(pinning `spedas_agent_kit`).
