---
description: Run the SPEDAS unified data-layer workflow (browse/load/inspect; opt-in fetch).
argument-hint: "[source_type] [source_id/dataset_id] [parameters] [interval]"
---

# SPEDAS data-layer workflow

Use unified data-layer tools:

1. `browse_data_sources(source_type="all"|"cdaweb"|"pds"|"spice")`
2. `load_data_source(source_type, source_id)`
3. `browse_data_parameters(source_type, dataset_id, ...)`
4. `fetch_data_product(source_type, ...)` only after confirming scope/cache/output.
5. `manage_data_cache(source_type, ...)` for cache inspection or cleanup.

`spice` participates in `browse_data_sources` / `load_data_source` /
`browse_data_parameters` for discovery, but **geometry retrieval does not go through
`fetch_data_product`** — `fetch_data_product(source_type="spice", ...)` is rejected.
SPICE ephemerides, distances, and frame transforms use the dedicated geometry/SPICE
tools instead; see [`/geometry`](geometry.md) and
[`skills/spedas-workflow/reference/geometry-spice.md`](../skills/spedas-workflow/reference/geometry-spice.md).

Keep fetches narrow. Return artifact paths and provenance, not large raw arrays.
`fetch_data_product` / `fetch_hapi_data` / `fetch_fdsn_data` are **opt-in network
downloads** subject to archive rate limits — confirm scope and record opt-in first.
See the fetch safety boundary in [`docs/safety.md`](../docs/safety.md).

Concrete arguments, return shapes, and no-fetch caveats for each tool are in
[`skills/spedas-workflow/reference/tool-examples.md`](../skills/spedas-workflow/reference/tool-examples.md).
For optional HAPI/FDSN entrypoints and when to leave the compact public surface, see
[`skills/spedas-workflow/reference/backend-compatibility.md`](../skills/spedas-workflow/reference/backend-compatibility.md).

## Invocation arguments

User-supplied arguments (may be empty): `$ARGUMENTS`

Parse `$ARGUMENTS` for the discovery scope. Expected (free-form, all optional):

- **source_type** — `all` | `cdaweb` | `pds` | `spice`.
- **source_id / dataset_id** — the source or dataset to load/inspect (e.g.
  `mms1_fgm_srvy_l2`).
- **parameters** — variable names to narrow `browse_data_parameters`.
- **interval** — ISO time or range for the request scope.

Example: `/data cdaweb mms1_fgm_srvy_l2`. Stay metadata-first: do not call
`fetch_data_product` until scope/cache/output and opt-in are confirmed, even if
arguments name a dataset. If arguments are missing, ask which source_type to
browse.
