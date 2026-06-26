# Unified facade vs. backend compatibility tools

The SPEDAS MCP surface has two tiers that do overlapping work:

1. **Unified public facade** — `source_type`-parameterized tools. This is the
   intended mental model and the default for new workflows.
2. **Backend compatibility/maintenance tools** — source-specific CDAWeb and PDS
   tools that predate the facade. They still work, but are kept mainly for
   compatibility and low-level maintenance.

The live tool descriptions encode this themselves: each backend tool is labeled
`Compatibility: … Prefer <unified tool>(source_type=…)`. **Default to the unified
facade.** Reach for a backend tool only for the specific reasons below.

## Map: unified facade → backend tools

| Step | Unified facade (prefer) | CDAWeb backend | PDS backend |
|---|---|---|---|
| Browse catalog | `browse_data_sources(source_type=…)` | `browse_observatories` | `browse_pds_missions` |
| Load source context | `load_data_source(source_type, source_id)` | `load_observatory(observatory_id)` | `load_pds_mission(mission_id)` |
| Browse parameters | `browse_data_parameters(source_type, dataset_id, …)` | `browse_parameters(dataset_id, …)` | `browse_pds_parameters(dataset_id, …)` |
| Fetch product (opt-in) | `fetch_data_product(source_type, …)` | `fetch_data(dataset_id, parameters, start, stop, output_dir, …)` | `fetch_pds_data(dataset_id, parameters, start, stop, output_dir, …)` |
| Manage cache | `manage_data_cache(source_type, action, …)` | `manage_cdaweb_cache(action, …)` | `manage_pds_cache(action, …)` |

SPICE has no separate "backend vs unified" duplication for browse/load: geometry
is its own tool family (`list_spice_missions`, `get_ephemeris`,
`compute_distance`, `transform_coordinates`, `list_coordinate_frames`,
`manage_spice_kernels`). The unified `manage_data_cache(source_type="spice")`
covers SPICE data-layer cache status; `manage_spice_kernels` is the
kernel-specific maintenance surface. See
[`geometry-spice.md`](geometry-spice.md).

The workflow tools (`spedas_overview`, `search_spedas_data_sources`,
`plan_spedas_observation`, `compare_cdaweb_pds_spice`,
`create_spedas_analysis_bundle`) sit above both tiers and have no backend
equivalents — they are always called directly.

## Why prefer the unified facade

- **One mental model.** `source_type` of `cdaweb`/`pds`/`spice` replaces three
  parallel toolsets, so a new user/agent learns one browse→load→params→fetch→cache
  pipeline instead of three.
- **Stable public contract.** The facade is the surface this plugin documents and
  smoke-tests; backend tool names/signatures may change as `spedas_mcp` evolves.
- **Fewer wrong-source mistakes.** Choosing `source_type` is an explicit decision
  the planner tools can validate.

## When a backend tool is the right call

Use a source-specific tool only when one of these is true:

- **Low-level/maintenance need.** You are debugging or cleaning a single backend's
  cache and want its native knobs — e.g. `manage_cdaweb_cache` exposes
  `observatory`/`dataset_ids`/`older_than_days`/`dry_run`/`detail`;
  `manage_pds_cache` adds `force`. The unified `manage_data_cache` is the
  status/maintenance front door but the backend tool gives finer control.
- **Reproducing a backend-specific issue.** You need to confirm whether a problem
  lives in the unified facade or in the underlying CDAWeb/PDS backend (the
  "MCP wrapper vs. SPEDAS MCP vs. backend gap" distinction in the failure
  taxonomy). Calling the backend tool directly isolates the layer.
- **A field only the backend tool exposes.** If the facade doesn't surface an
  argument you need, fall back to the backend tool and note it as a compatibility
  use in provenance.

If none of these apply, use the facade.

## Decision checklist

1. Is this a science/planning step? → workflow tool (`spedas_overview`, `plan_…`).
2. Is this geometry/positions/frames? → geometry/SPICE tools.
3. Otherwise (browse/load/params/fetch/cache)? → **unified facade** with the right
   `source_type`.
4. Only drop to a backend tool for low-level maintenance, layer isolation, or a
   facade gap — and record why in provenance.

When you do use a backend tool, label it in provenance as a *compatibility/
maintenance* call so future readers know it was a deliberate exception, not the
default path.
