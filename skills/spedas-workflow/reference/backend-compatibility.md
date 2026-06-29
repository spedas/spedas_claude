# Unified facade and current backend entrypoints

The current pinned `spedas_mcp` base surface is intentionally compact. Use the
`source_type`-parameterized unified facade as the public data-layer mental model:

| Step | Public tool |
|---|---|
| Browse catalog | `browse_data_sources(source_type=...)` |
| Load source context | `load_data_source(source_type, source_id, ...)` |
| Browse parameters | `browse_data_parameters(source_type, dataset_id, ...)` |
| Fetch product (opt-in) | `fetch_data_product(source_type, ...)` |
| Manage cache/status | `manage_data_cache(source_type, action, ...)` |

The wrapper smoke-tests this public surface rather than older source-specific
compatibility names. If an upstream server version exposes additional low-level
backend tools, treat them as maintenance/debugging surfaces and record why you
left the facade in provenance. Do not teach first users to start there.

## Optional backend entrypoints

HAPI and FDSN entrypoints are visible in the base tool list so agents can discover
that the capability exists, but calls may report unavailable until the user
installs the corresponding server extras. Prefer these only when the science
question specifically needs those archives:

- `browse_hapi_catalog` / `fetch_hapi_data`
- `browse_fdsn_datasets` / `fetch_fdsn_data`

## SPICE

SPICE participates in the unified facade for discovery/status (`source_type="spice"`),
but ephemerides/distances/frame transforms use the dedicated geometry tools:
`get_ephemeris`, `compute_distance`, and `transform_coordinates`. See
[`geometry-spice.md`](geometry-spice.md).

## Decision checklist

1. Is this a science/planning step? -> workflow tool (`spedas_overview`, `plan_...`).
2. Is this geometry/positions/frames? -> geometry/SPICE tools.
3. Otherwise (browse/load/params/fetch/cache)? -> unified facade with the right
   `source_type`.
4. Only use optional HAPI/FDSN or any upstream low-level compatibility tool when
   the science question or debugging need specifically calls for it, and record
   the reason in provenance.
