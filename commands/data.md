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
`fetch_data_product` / `fetch_data` / `fetch_pds_data` are **opt-in network
downloads** subject to archive rate limits — confirm scope and record opt-in first.
See the fetch safety boundary in [`docs/safety.md`](../docs/safety.md).

Concrete arguments, return shapes, and no-fetch caveats for each tool are in
[`skills/spedas-workflow/reference/tool-examples.md`](../skills/spedas-workflow/reference/tool-examples.md).
For when to drop from these unified tools to source-specific CDAWeb/PDS tools, see
[`skills/spedas-workflow/reference/backend-compatibility.md`](../skills/spedas-workflow/reference/backend-compatibility.md).
