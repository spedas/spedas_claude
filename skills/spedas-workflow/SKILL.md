---
name: spedas-workflow
description: Use when working with SPEDAS, PySPEDAS, or the SPEDAS MCP plugin to discover heliophysics data sources, choose missions/parameters/time ranges, plan science workflows, run safe metadata-first checks, fetch/export artifacts only when appropriate, and preserve provenance.
---

# SPEDAS / PySPEDAS workflow skill

Use this skill when the user asks a heliophysics data question, wants to use SPEDAS/PySPEDAS, or wants an agent runtime to call the SPEDAS MCP plugin.

## Operating model

Think in four layers:

1. **Science question** — event, mission, interval, coordinate system, expected signal, and success criteria.
2. **Workflow layer** — SPEDAS MCP planning/comparison/bundle tools or PySPEDAS recipes.
3. **Unified data layer** — source category `cdaweb`, `pds`, or `spice`; do not expose `xhelio-*` as the user-facing mental model.
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
6. Report results conclusion-first, with paths and exact next actions.

## Preferred SPEDAS MCP tools

- Discovery and mental model: `spedas_overview`.
- Science planning: `search_spedas_data_sources`, `plan_spedas_observation`, `compare_cdaweb_pds_spice`, `create_spedas_analysis_bundle`.
- Unified data layer: `browse_data_sources`, `load_data_source`, `browse_data_parameters`, `fetch_data_product`, `manage_data_cache`.
- Geometry/SPICE: `list_spice_missions`, `list_coordinate_frames`, `get_ephemeris`, `compute_distance`, `transform_coordinates`, `manage_spice_kernels`. Geometry is its own tool family — route SPICE positions/frames here, not through `fetch_data_product`.
- Treat source-specific CDAWeb/PDS tools (`browse_observatories`, `fetch_data`, `browse_pds_missions`, `fetch_pds_data`, …) as compatibility or maintenance surfaces unless the user asks for low-level backend behavior.

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
- **SPEDAS MCP issue** — unified tool behavior, planning semantics, parameter mapping, error shape.
- **Backend/data gap** — missing CDAWeb variable, incomplete PDS label/metadata, unavailable SPICE kernel.
- **External service limit** — network, archive outage, timeout, HTTP 429, cold cache.
- **Docs/skills gap** — the tool works but first-user instructions or scientific method are unclear.

For per-class error signals, a triage decision tree, diagnostic commands, **which
repo to file each class in** (`spedas_claude` vs `spedas_mcp` vs backend archives),
and which provenance artifacts to attach, see `reference/troubleshooting.md`.

## References in this skill folder

- `reference/tool-examples.md` — concrete arguments, return shapes, and no-fetch caveats for the unified workflow + data tools.
- `reference/geometry-spice.md` — the six geometry/SPICE tools, safe examples, and the metadata-vs-kernel-download line.
- `reference/backend-compatibility.md` — unified facade vs. CDAWeb/PDS backend tools, with a name map and decision criteria.
- `reference/mcp-quickstart.md` — Claude plugin smoke, local wrapper validation, and first user checks.
- `reference/source-selection.md` — choose CDAWeb vs PDS vs SPICE.
- `reference/pyspedas-patterns.md` — safe PySPEDAS loading/plotting/export patterns.
- `reference/artifact-provenance.md` — what to save for reproducible science (templates in `templates/provenance/`).
- `reference/troubleshooting.md` — failure taxonomy runbook: per-class signals, triage tree, issue routing.
- `reference/science-examples.md` — starter prompts for MMS, Juno, PSP, THEMIS, and upstream solar wind.

Repo-level docs (outside this skill folder): `docs/configuration.md` (env/cache
variables), `docs/safety.md` (fetch/kernel boundary + opt-in), `docs/dependencies.md`
(pinning `spedas_mcp`).
